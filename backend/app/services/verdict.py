"""최종 판정 (verdict / confidence / risk_score / risk_level).

codes/ml_integration/risk_judge.py(ML 담당, 팀 합의 규칙)의 judge()를 그대로 호출한다.
    1) 블랙리스트 매치 -> 즉시 phishing 확정
    2) 미매치 -> 점수(0~100)로 판정

RAG 점수는 아직 없으므로 ML 점수만 쓴다 (임시).
judge()는 현재 RAG 가중치 1.0 / ML 가중치 0.0으로 되어 있어서,
ML 점수를 rag_score 자리에 넣어야 ML 점수가 그대로 반영된다.
RAG 점수가 생기면 이 부분과 risk_judge.py의 가중치를 함께 바꿔야 한다.
"""

from app.schemas import BlacklistResult, ModelResult
from app.services import model  # noqa: F401  codes/ml_integration을 import 경로에 추가한다

import risk_judge  # noqa: E402

_EMPTY = {"verdict": None, "confidence": None, "risk_score": None, "risk_level": None}


def decide(blacklist: BlacklistResult, model_result: ModelResult) -> dict:
    """판정에 쓸 점수가 없으면(블랙리스트 미매치 + 모델 미준비) 모두 None으로 반환한다."""
    if not blacklist.matched and model_result.risk_score is None:
        return dict(_EMPTY)

    result = risk_judge.judge(
        blacklist,  # judge()는 matched, match_type만 읽는다
        risk_judge.RagResult(),
        rag_score=model_result.risk_score or 0.0,
    )
    return {key: result[key] for key in _EMPTY}
