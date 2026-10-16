"""탐지 결과를 일반 사용자가 이해할 수 있는 설명으로 바꾼다.

탐지 결과(detections)의 이유 문장은 "도메인 문자 엔트로피가 4.3으로 높아…"처럼 기술적이다.
여기서는 같은 특징을 (1) 쉬운 제목, (2) 왜 의심스러운지, (3) 어떤 피해로 이어질 수 있는지,
(4) 학습 데이터에서 피싱·정상 URL에 각각 얼마나 나타났는지로 정리한다.

데이터 비교는 "이 특징이 있으면 N%가 피싱"이 아니라 "피싱 URL의 N%, 정상 URL의 M%에서 나타남"으로
보여 준다. 우리 데이터의 정상 URL은 대부분 유명 사이트 첫 화면이라, 앞의 방식은 거의 모든 특징이
97~100%로 나와 실제보다 확실해 보이기 때문이다. 수치는 scripts/build_feature_rates.py로 미리 계산한다.
"""

import json
from pathlib import Path

_RATES_PATH = Path(__file__).resolve().parents[2] / "resources" / "reference" / "feature_rates.json"

# 이 건수 미만으로 나타난 특징은 비율이 우연에 크게 흔들리므로 수치를 보여 주지 않는다
MIN_SAMPLE = 100

# match: 탐지 이유 문장에 들어 있으면 이 특징으로 본다 (detections.py·reputation.py의 문장 기준)
# 위에서부터 먼저 맞는 특징 하나로 분류한다
FEATURES = [
    {
        "key": "cms_login",
        "match": ["관리용 폴더"],
        "title": "해킹된 사이트에 숨겨 둔 페이지 같아요",
        "why": "사이트 관리용 폴더 안에 로그인 화면이나 다른 회사 이름이 들어 있어요. 해킹한 정상 사이트에 가짜 페이지를 숨길 때 자주 보이는 모습이에요.",
        "harm": "평범한 사이트 주소처럼 보여서 의심 없이 계정 정보를 입력하게 될 수 있어요.",
    },
    {
        "key": "embedded_domain",
        "match": ["경로 안에 다른 공식 도메인"],
        "title": "주소 뒷부분에 진짜 사이트 주소를 끼워 넣었어요",
        "why": "공식 사이트 주소가 주소 중간에 들어 있지만, 실제로 접속되는 곳은 맨 앞의 다른 도메인이에요.",
        "harm": "공식 사이트로 착각해 로그인하거나 결제 정보를 입력하게 될 수 있어요.",
    },
    {
        "key": "brand_login",
        "match": ["브랜드 이름과 로그인"],
        "title": "회사 이름과 로그인 화면을 흉내 냈어요",
        "why": "은행·쇼핑몰 같은 회사 이름과 '로그인', '인증' 같은 단어가 함께 있지만, 그 회사의 공식 주소가 아니에요.",
        "harm": "가짜 로그인 화면에 아이디와 비밀번호를 입력하면 계정을 빼앗길 수 있어요.",
    },
    {
        "key": "brand_domain",
        "match": ["브랜드명을 쓰지만 공식 도메인"],
        "title": "유명 회사 이름을 넣은 가짜 주소예요",
        "why": "주소에 잘 알려진 회사 이름이 들어 있지만, 그 회사가 실제로 쓰는 공식 주소가 아니에요.",
        "harm": "공식 사이트인 줄 알고 개인정보나 결제 정보를 입력하게 될 수 있어요.",
    },
    {
        "key": "punycode",
        "match": ["퓨니코드"],
        "title": "생김새가 비슷한 다른 글자를 썼어요",
        "why": "영어 알파벳과 똑같이 보이는 다른 나라 글자로 주소를 만들 수 있어, 눈으로는 진짜 주소와 구별하기 어려워요.",
        "harm": "주소창을 확인해도 속을 수 있어 가짜 사이트에 정보를 입력하게 될 수 있어요.",
    },
    {
        "key": "ip_host",
        "match": ["IP 주소"],
        "title": "도메인 이름 없이 숫자 주소를 써요",
        "why": "정상적인 서비스는 대부분 이름이 있는 주소를 써요. 숫자 주소는 임시로 만든 서버에서 자주 보여요.",
        "harm": "누가 운영하는 곳인지 알 수 없는 서버에 정보를 보내게 될 수 있어요.",
    },
    {
        "key": "at_sign",
        "match": ["'@'"],
        "title": "주소에 '@'가 들어 있어요",
        "why": "주소에 '@'가 있으면 그 앞부분은 무시되고 뒤쪽 주소로 접속돼요. 앞에 진짜 사이트 이름을 붙여 속이는 방법이에요.",
        "harm": "보이는 것과 전혀 다른 사이트로 이동하게 될 수 있어요.",
    },
    {
        "key": "shortener",
        "match": ["단축 URL"],
        "title": "실제 주소가 가려진 짧은 링크예요",
        "why": "짧게 줄인 주소는 눌러 보기 전까지 실제로 어디로 연결되는지 알 수 없어요.",
        "harm": "모르는 사이에 피싱 사이트로 이동하거나 악성 앱을 내려받게 될 수 있어요.",
    },
    {
        "key": "suspicious_tld",
        "match": ["최상위 도메인입니다"],
        "title": "피싱에 자주 쓰이는 주소 끝자리예요",
        "why": "'.xyz', '.top'처럼 값이 싸고 쉽게 만들 수 있는 주소 끝자리는 가짜 사이트를 대량으로 만들 때 자주 쓰여요.",
        "harm": "며칠만 쓰고 사라지는 가짜 사이트일 수 있어, 피해가 생겨도 추적하기 어려워요.",
    },
    {
        "key": "host_keywords",
        "match": ["의심 키워드"],
        "title": "'로그인', '보안' 같은 단어를 여러 개 넣었어요",
        "why": "주소 이름에 'login', 'secure', 'verify' 같은 단어를 여러 개 넣어 공식 안내처럼 보이게 만드는 경우가 많아요.",
        "harm": "공식 보안 안내로 착각해 계정 정보를 입력하게 될 수 있어요.",
    },
    {
        "key": "many_hyphens",
        "match": ["하이픈(-)이"],
        "title": "여러 단어를 '-'로 이어 붙인 주소예요",
        "why": "'회사이름-보안-확인'처럼 여러 단어를 이어 붙여 그럴듯하게 보이게 만드는 형태예요.",
        "harm": "공식 사이트의 다른 주소로 착각하게 될 수 있어요.",
    },
    {
        "key": "deep_subdomain",
        "match": ["서브도메인이"],
        "title": "주소 앞부분이 여러 단계로 길어요",
        "why": "주소 앞쪽에 점(.)으로 나뉜 이름을 여러 개 붙이면, 앞부분만 보고 진짜 사이트로 착각하기 쉬워요.",
        "harm": "공식 사이트 주소를 앞에 붙여 둔 가짜 사이트에 접속하게 될 수 있어요.",
    },
    {
        "key": "random_host",
        "match": ["엔트로피가"],
        "title": "의미 없는 글자를 섞은 주소예요",
        "why": "사람이 기억하기 어려운 무작위 글자 조합은 자동으로 대량 생성한 주소에서 자주 보여요.",
        "harm": "차단을 피하려고 계속 새로 만드는 가짜 사이트일 수 있어요.",
    },
    {
        "key": "long_host",
        "match": ["매우 깁니다"],
        "title": "도메인 이름이 지나치게 길어요",
        "why": "휴대폰 화면에서는 긴 주소의 뒷부분이 잘려 보여, 앞부분만 보고 진짜 사이트로 착각하기 쉬워요.",
        "harm": "주소를 끝까지 확인하지 못한 채 가짜 사이트에 정보를 입력하게 될 수 있어요.",
    },
    {
        "key": "digit_host",
        "match": ["숫자입니다"],
        "title": "도메인에 숫자가 많이 섞여 있어요",
        "why": "정상 서비스 이름에는 숫자가 많지 않아요. 숫자를 섞은 주소는 자동으로 만든 가짜 사이트에서 자주 보여요.",
        "harm": "차단을 피하려고 계속 새로 만드는 가짜 사이트일 수 있어요.",
    },
    {
        "key": "new_domain",
        "match": ["등록됐습니다. 새로 만든"],
        "title": "최근에 새로 만든 주소예요",
        "why": "피싱 사이트는 차단되기 전에 쓰고 버리기 위해 만든 지 얼마 안 된 주소를 쓰는 경우가 많아요.",
        "harm": "아직 신고·차단 목록에 오르지 않은 새 피싱 사이트일 수 있어요.",
    },
    {
        "key": "new_certificate",
        "match": ["첫 인증서가"],
        "title": "보안 인증서를 최근에 처음 받았어요",
        "why": "자물쇠 표시(HTTPS)는 누구나 무료로 금방 받을 수 있어요. 최근에 처음 받은 인증서는 새로 만든 사이트라는 뜻이에요.",
        "harm": "자물쇠 표시만 보고 안전한 사이트로 믿게 될 수 있어요.",
    },
    {
        "key": "nxdomain",
        "match": ["DNS에 도메인이 존재하지"],
        "title": "지금은 존재하지 않는 주소예요",
        "why": "주소가 이미 차단됐거나 만료됐을 때 이렇게 나타나요. 신고된 피싱 사이트에서 자주 보여요.",
        "harm": "같은 문자에 다른 링크가 함께 왔다면 그 링크도 피싱일 수 있어요.",
    },
]

_rates: dict = {}


def _load_rates() -> dict:
    if not _rates:
        try:
            _rates.update(json.loads(_RATES_PATH.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            _rates["features"] = {}
    return _rates


def classify(reason: str) -> dict | None:
    """탐지 이유 문장 하나를 특징 하나로 분류한다. 해당하는 특징이 없으면 None."""
    for feature in FEATURES:
        if any(m in reason for m in feature["match"]):
            return feature
    return None


def _pct(count: int, total: int) -> str:
    """0.1% 단위로 표시한다. 0은 아니지만 0.1% 미만이면 '0.1% 미만'."""
    if total <= 0:
        return "0%"
    value = count / total * 100
    if count and value < 0.1:
        return "0.1% 미만"
    return f"{value:.1f}%".replace(".0%", "%")


def stat_for(key: str) -> dict | None:
    """학습 데이터에서 이 특징이 피싱·정상 URL에 나타난 비율. 표본이 적으면 None."""
    rates = _load_rates()
    item = (rates.get("features") or {}).get(key)
    if not item or item["phishing"] + item["normal"] < MIN_SAMPLE:
        return None
    total_p, total_n = rates["phishing_total"], rates["normal_total"]
    phishing_pct, normal_pct = _pct(item["phishing"], total_p), _pct(item["normal"], total_n)
    return {
        "phishing_pct": phishing_pct,
        "normal_pct": normal_pct,
        "text": f"학습 데이터에서 이 특징은 피싱 URL의 {phishing_pct}, 정상 URL의 {normal_pct}에서 나타났습니다.",
        "source": rates.get("source_label", "학습 데이터"),
    }


def stat_sentence(reason: str) -> str | None:
    """근거 문장 뒤에 붙일 데이터 비교 문장 (LLM이 이 숫자만 인용할 수 있게 근거에 넣는다)."""
    feature = classify(reason)
    if not feature:
        return None
    stat = stat_for(feature["key"])
    return stat["text"] if stat else None


def explain(detections) -> list[dict]:
    """탐지 결과 전체에서 의심 특징을 뽑아 쉬운 설명 목록을 만든다 (같은 특징은 한 번만)."""
    if detections is None:
        return []
    items, seen = [], set()
    for key in ("domain", "url", "url_stats", "reputation"):
        detection = getattr(detections, key, None)
        if not isinstance(detection, dict):
            continue
        for reason in detection.get("reasons") or []:
            feature = classify(reason)
            if not feature or feature["key"] in seen:
                continue
            seen.add(feature["key"])
            items.append({
                "key": feature["key"],
                "title": feature["title"],
                "why": feature["why"],
                "harm": feature["harm"],
                "detail": reason,
                "stat": stat_for(feature["key"]),
            })
    return items
