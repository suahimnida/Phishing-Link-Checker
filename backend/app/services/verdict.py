from app.schemas import AllowlistResult, BlacklistResult, ModelResult
from app.services import model  # noqa: F401  (ml_integration 경로를 sys.path에 넣는다)

import risk_judge

_EMPTY = {"verdict": None, "confidence": None, "risk_score": None, "risk_level": None}

ALLOWLIST_CAP = 25.0
# 단축 URL은 목적지를 알 수 없으므로 URL 문자열 점수와 관계없이 '의심' 구간에 둔다
SHORTENER_RANGE = (30.0, 59.0)
# 공식 도메인을 동형 문자로 흉내 낸 퓨니코드 도메인은 최소 이 점수(피싱·위험)로 본다
HOMOGRAPH_FLOOR = 90.0
# 한 이름 안에 라틴·키릴·그리스 문자가 섞인 퓨니코드 도메인은 최소 '의심'
MIXED_SCRIPT_FLOOR = 30.0


# 공식 도메인 목록으로 정한 정상 판정의 신뢰도. ML 점수가 아니라 목록 일치로 정한 판정이므로 높게 둔다.
ALLOWLIST_CONFIDENCE = 0.95


def confidence(verdict: str, score: float) -> float:
    """판정 쪽으로 점수가 얼마나 기울었는지 (0~1).

    예전 공식 |점수-50|/50은 정상 25점을 50%로 표시해, 정상인데 신뢰도가 낮아 보였다 (QA).
    - 정상: 1 - 점수/100 (25점 → 75%, 2.1점 → 98%)
    - 피싱: 점수/100 (99.9점 → 100%, 60점 → 60%)
    - 의심: 0.5 (정상과 피싱 사이에서 판단을 보류한 상태)
    """
    if verdict == "normal":
        return round(1 - score / 100, 2)
    if verdict == "phishing":
        return round(score / 100, 2)
    return 0.5


def _with_score(result: dict, score: float, verdict: str | None = None) -> None:
    score = round(score, 2)
    verdict = verdict or ("phishing" if score >= 60 else "suspicious" if score >= 30 else "normal")
    result.update(
        verdict=verdict,
        risk_score=score,
        risk_level=risk_judge.risk_level_from_score(score),
        confidence=confidence(verdict, score),
    )


def decide(blacklist: BlacklistResult, model_result: ModelResult, allow: AllowlistResult | None = None,
           *, shortener: bool = False, homograph=None) -> dict:
    if not blacklist.matched and model_result.risk_score is None:
        return dict(_EMPTY)

    result = risk_judge.judge(
        blacklist,
        risk_judge.RagResult(),
        rag_score=model_result.risk_score or 0.0,
    )
    if blacklist.matched:
        return {key: result[key] for key in _EMPTY}

    _with_score(result, result["risk_score"])
    if allow is not None and allow.matched:
        _with_score(result, min(result["risk_score"], ALLOWLIST_CAP), "normal")
        result["confidence"] = ALLOWLIST_CONFIDENCE
    if shortener:
        low, high = SHORTENER_RANGE
        _with_score(result, min(max(result["risk_score"], low), high), "suspicious")
    if homograph is not None and homograph.imitates and result["risk_score"] < HOMOGRAPH_FLOOR:
        _with_score(result, HOMOGRAPH_FLOOR)
    elif homograph is not None and homograph.mixed_script and result["risk_score"] < MIXED_SCRIPT_FLOOR:
        _with_score(result, MIXED_SCRIPT_FLOOR)
    return {key: result[key] for key in _EMPTY}
