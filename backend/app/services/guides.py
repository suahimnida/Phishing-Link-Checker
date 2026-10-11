import json
import re
from pathlib import Path

from sklearn.feature_extraction.text import TfidfVectorizer

_PATH = Path(__file__).resolve().parents[2] / "resources" / "guides" / "guides.json"

TAG_LABELS = {
    "phishing_site": "피싱 판정",
    "brand_impersonation": "브랜드 사칭",
    "login_page": "로그인·계정 화면 흉내",
    "compromised_site": "해킹된 사이트 경로",
    "shortener": "단축 URL",
    "smishing": "문자로 받은 링크",
    "financial": "금융 관련",
    "personal_info": "개인정보 입력 유도",
    "account": "계정 정보",
    "money_sent": "송금·결제",
    "app_install": "앱 설치 유도",
    "file_download": "파일 내려받기",
    "prevention": "예방",
}
LOGIN_WORDS = ("login", "signin", "logon", "verify", "account", "auth", "password", "secure", "update")
FINANCE_WORDS = ("bank", "pay", "card", "wallet", "banking", "kbstar", "shinhan", "woori", "hana", "toss",
                 "kakaobank", "nonghyup", "ibk", "loan", "coin", "crypto")
DOWNLOAD_EXT = (".apk", ".exe", ".zip", ".msi", ".scr", ".dmg")

_state: dict = {}


def _load() -> dict:
    if not _state:
        data = json.loads(_PATH.read_text(encoding="utf-8"))
        guides = data["guides"]
        texts = [f"{g['title']} {g['text']} " + " ".join(TAG_LABELS.get(t, t) for t in g["tags"]) for g in guides]
        vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))
        _state.update(guides=guides, vectorizer=vectorizer, matrix=vectorizer.fit_transform(texts),
                      checked=data.get("checked"))
    return _state


def guide_for_action(action_id: str) -> dict | None:
    return next((g for g in _load()["guides"] if action_id in g["actions"]), None)


def build_evidence(*, verdict, risk_score, blacklist, allowlist, model, explanation, detections,
                   similar_cases, shortener: bool = False, homograph=None) -> list[dict]:
    items = []

    def add(source, text, used):
        items.append({"id": f"E{len(items) + 1}", "source": source, "text": text, "used_in_verdict": used})

    if blacklist.matched:
        add("KISA 블랙리스트", f"KISA 피싱 사이트 목록과 일치해 피싱으로 확정됐습니다 ({blacklist.source}).", True)
    elif verdict is not None and risk_score is not None:
        # 첫 근거는 항상 최종 판정. 템플릿 설명의 첫 문장이 이 근거를 인용한다 (QA: 판정 문장이 ML 원점수를 인용하던 문제)
        add("최종 판정", f"최종 위험도는 {risk_score:g}점으로 '{VERDICT_KO.get(verdict, verdict)}' 판정입니다.", True)

    allowlisted = allowlist.matched and not blacklist.matched
    shortened = shortener and not blacklist.matched
    ml_ready = model.status == "ready" and model.risk_score is not None

    # 최종 판정을 ML 점수와 다르게 정한 이유를 판정 바로 다음 근거로 둔다.
    # 이때는 ML 원점수를 따로 내세우지 않는다 (QA: 정상 25점인데 "ML 점수가 매우 높다"고 설명하던 문제)
    # 원점수 숫자는 넣지 않는다. 숫자가 있으면 LLM이 "ML 점수가 88.54점으로 매우 높게" 같은 문장을 써서
    # 최종 판정과 충돌했다 (QA). 원점수는 화면의 ML 모델 섹션에 참고용으로만 보인다.
    if allowlisted:
        add("공식 도메인 허용 목록",
            f"{allowlist.domain}은(는) 공식 도메인 목록에 있는 사이트라 정상으로 판정했습니다. "
            "공식 도메인에서는 URL 문자 패턴 점수를 판정에 쓰지 않습니다.", True)
    if shortened:
        add("단축 URL", "단축 URL이라 실제로 이동할 주소를 URL만으로 확인할 수 없어, URL 문자 패턴 점수와 관계없이 "
            "'피싱 의심'으로 표시합니다.", True)
    if homograph is not None and getattr(homograph, "matched", False) and not blacklist.matched:
        if homograph.imitates:
            add("동형 문자 도메인",
                f"도메인 '{homograph.decoded}'은(는) 공식 도메인 {homograph.imitates}의 글자를 비슷하게 생긴 다른 "
                "문자로 바꾼 사칭 주소입니다.", True)
        elif homograph.mixed_script:
            add("동형 문자 도메인",
                f"도메인 '{homograph.decoded}'은(는) 한 이름 안에 서로 다른 문자 체계가 섞여 있어 다른 주소로 착각하게 만들 수 있습니다.",
                True)

    if ml_ready and not allowlisted and not shortened:
        add("ML 모델", f"URL 문자 패턴으로 계산한 위험 점수는 {model.risk_score:g}점입니다.", True)
        parts = sorted([p for p in ((explanation or {}).get("model") or {}).get("parts", [])
                        if p["contribution"] > 0.3 and p["text"]], key=lambda p: -p["contribution"])[:3]
        if parts:
            add("ML 모델 · 부분별 기여",
                "점수를 가장 크게 올린 부분은 " + ", ".join(f"{p['part']} '{p['text']}'(+{p['contribution']:.2f})" for p in parts) + "입니다.",
                True)

    for key, title in (("url", "URL 구조"), ("domain", "도메인 분석"), ("url_stats", "URL 통계"), ("reputation", "평판 신호")):
        item = getattr(detections, key, None)
        if item and item.get("status") == "suspicious":
            for reason in item.get("reasons", [])[:2]:
                if shortener and "단축 URL" in reason:
                    continue
                add(f"탐지 결과 · {title}", reason, False)

    # 공식 도메인은 유사 사례를 근거로 쓰지 않는다 (정상 판정과 반대되는 인상을 주므로)
    if similar_cases and not allowlisted:
        phishing = sum(1 for c in similar_cases if c.label == 1)
        add("유사 사례", f"특징이 가장 비슷한 과거 사례 {len(similar_cases)}건 중 피싱이 {phishing}건입니다.", False)
    return items[:10]


def evidence_tags(url: str, verdict: str | None, evidence: list[dict]) -> set:
    text = " ".join(e["text"] for e in evidence).lower()
    lower = url.lower()
    tags = set()
    if verdict not in ("phishing", "suspicious"):
        # 정상(또는 판정 불가)이면 예방 안내만 붙인다. 도메인에 'bank', 'login' 같은 단어가 있다고
        # 지급정지·피해 대응 가이드를 붙이지 않는다 (QA: 정상인 kbstar.com에 '일괄 지급정지' 가이드)
        tags.add("prevention")
        if "단축 url" in text:
            tags.update({"shortener", "smishing"})
        return tags
    tags.add("phishing_site")
    if "브랜드" in text or "사칭" in text or "공식 도메인(" in text:
        tags.add("brand_impersonation")
    if any(w in lower for w in LOGIN_WORDS):
        tags.update({"login_page", "account"})
    if "관리용 폴더" in text:
        tags.add("compromised_site")
    if "단축 url" in text:
        tags.update({"shortener", "smishing"})
    if any(w in lower for w in FINANCE_WORDS):
        tags.update({"financial", "personal_info"})
    if lower.split("?")[0].endswith(DOWNLOAD_EXT) or "download" in lower:
        tags.update({"app_install", "file_download"})
    return tags


def retrieve(tags: set, evidence: list[dict], top_k: int = 4) -> list[dict]:
    state = _load()
    query = " ".join(e["text"] for e in evidence) + " " + " ".join(TAG_LABELS.get(t, t) for t in tags)
    similarity = (state["vectorizer"].transform([query]) @ state["matrix"].T).toarray()[0]
    scored = []
    for i, g in enumerate(state["guides"]):
        matched = [t for t in g["tags"] if t in tags]
        if matched:
            scored.append((len(matched) + float(similarity[i]), i, matched))
    scored.sort(reverse=True)
    hits = []
    for rank, (score, i, matched) in enumerate(scored[:top_k], start=1):
        g = state["guides"][i]
        hits.append({
            "id": f"G{rank}", "key": g["key"], "title": g["title"], "source": g["source"], "url": g["url"],
            "text": g["text"], "matched": [TAG_LABELS.get(t, t) for t in matched], "score": round(score, 3),
            "checked": state["checked"],
        })
    return hits


_CITATION = re.compile(r"\[([EG]\d+)\]")
_FORBIDDEN = re.compile(r"https?://|www\.|(?<!\d)\d{2,4}-\d{3,4}-\d{4}(?!\d)|(?<![\d.])(?:112|118|1332)(?![\d.])")


_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def _numbers(text: str) -> set:
    return set(_NUMBER.findall(_CITATION.sub(" ", text)))


def check_citations(text: str, evidence: list[dict], guides: list[dict]) -> str:
    text = (text or "").strip()
    if not text:
        raise ValueError("설명이 비어 있습니다")
    if _FORBIDDEN.search(text):
        raise ValueError("설명에 주소나 전화번호가 들어 있습니다 (출처 링크는 서버가 보여 준다)")
    valid = {e["id"] for e in evidence} | {g["id"] for g in guides}
    cited = _CITATION.findall(text)
    if not cited:
        raise ValueError("출처 표시가 없습니다")
    unknown = set(cited) - valid
    if unknown:
        raise ValueError(f"없는 출처 번호를 썼습니다: {sorted(unknown)}")
    sentences = [s for s in re.split(r"(?<=[.!?])\s+(?!\[)", text) if s.strip()]
    if any(not _CITATION.search(s) for s in sentences):
        raise ValueError("출처 표시가 없는 문장이 있습니다")
    # 숫자는 근거나 가이드에 있는 것만 쓸 수 있다 ("3일 전에 등록" 같은 지어낸 수치를 막는다)
    allowed = _numbers(" ".join(e["text"] for e in evidence) + " " + " ".join(g["text"] for g in guides))
    invented = _numbers(text) - allowed
    if invented:
        raise ValueError(f"근거에 없는 숫자를 썼습니다: {sorted(invented)}")
    return text


VERDICT_KO = {"phishing": "피싱", "suspicious": "피싱 의심", "normal": "정상"}


def template_explanation(verdict: str | None, evidence: list[dict], guides: list[dict]) -> str:
    def cite(text, ref):
        return f"{text.rstrip('.')} [{ref}]."

    sentences = []
    if evidence:
        head = evidence[0]
        if head["source"] in ("최종 판정", "KISA 블랙리스트"):
            sentences.append(cite(head["text"], head["id"]))
        else:
            sentences.append(cite(f"이 URL은 '{VERDICT_KO.get(verdict, '판정 불가')}'(으)로 판정됐습니다", head["id"]))
            sentences.append(cite(head["text"], head["id"]))
    for e in evidence[1:3]:
        sentences.append(cite(f"{e['source']}: {e['text']}", e["id"]))
    for g in guides[:2]:
        first = g["text"].split(". ")[0]
        sentences.append(cite(f"{g['title']} 안내에 따르면 {first}", g["id"]))
    return " ".join(sentences)
