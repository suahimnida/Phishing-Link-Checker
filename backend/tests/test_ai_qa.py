"""AI 개발 QA에서 나온 문제의 회귀 테스트.

- 기준 URL 점수 고정 (모델·전처리가 바뀌면 바로 알 수 있게)
- 대소문자·끝 '/' 표기 차이
- 단축 URL, 블랙리스트 정리, 동형 문자 도메인
- 정상 판정의 가이드, AI 설명 검사
"""
import pytest

from app.schemas import AllowlistResult, BlacklistResult, ModelResult
from app.services import allowlist, blacklist, guides, homograph, verdict
from app.services.shorteners import is_shortener_host

from model_integration import predict_model
from url_features import canonical_url

# 2026-10-12 기준 서비스 점수 (url_model_v2.joblib, sha256 cbc4dbe42ab7, canonical_url 적용)
# 모델이나 전처리를 바꿨다면 점수 차이를 확인한 뒤 이 표를 갱신한다.
REFERENCE_SCORES = {
    "https://www.naver.com": 43.52,                        # 정상 홈페이지 (허용 목록이 최종 25점으로 낮춤)
    "https://github.com/suahimnida/TEST": 27.12,           # 경로가 있는 정상 URL
    "https://myschool.ac.kr/notice/view?id=12": 4.79,      # 경로가 있는 정상 URL
    "https://www.coupang.com/vp/products/123": 18.32,      # 경로가 있는 정상 URL
    "http://192.168.0.1/login": 99.58,                     # IP 주소 URL
    "http://xn--80ak6aa92e.com/": 92.78,                   # 퓨니코드
    "http://paypal.com@evil.xyz/login": 99.99,             # @ 포함 URL
    "http://login-kakao.secure-auth.top/verify": 99.99,    # 의심 키워드가 들어간 서브도메인
    "https://kbstar-verify.com/account/update": 99.53,     # 금융 브랜드 흉내
}


@pytest.mark.parametrize("url,expected", REFERENCE_SCORES.items())
def test_reference_scores_are_fixed(url, expected):
    assert predict_model(url)["risk_score"] == pytest.approx(expected, abs=0.5)


# ---------- 표기 차이 ----------

def test_canonical_url_lowercases_scheme_and_host_only():
    assert canonical_url("HTTP://SECURE-LOGIN-KAKAO.XYZ/VERIFY") == "http://secure-login-kakao.xyz/VERIFY"
    assert canonical_url("Example.COM/Path?Q=1") == "example.com/Path?Q=1"


def test_canonical_url_drops_single_root_slash():
    assert canonical_url("https://example-shop.co.kr/") == "https://example-shop.co.kr"
    assert canonical_url("example.com/") == "example.com"
    assert canonical_url("https://example.com/a/") == "https://example.com/a/"


def test_uppercase_url_cannot_bypass_model():
    lower = predict_model("http://secure-login-kakao.xyz/verify")["risk_score"]
    upper = predict_model("HTTP://SECURE-LOGIN-KAKAO.XYZ/VERIFY")["risk_score"]
    assert lower >= 60 and upper >= 60


@pytest.mark.parametrize("base", ["myschool.ac.kr/notice", "coupang.com/vp/products/123", "example-shop.co.kr",
                                  "secure-login-kakao.xyz/verify"])
def test_notation_variants_score_close(base):
    host, _, rest = base.partition("/")
    rest = "/" + rest if rest else ""
    # 스킴 없이 도메인만 쓴 경우('myshop.kr')는 모델 특성상 점수가 더 높게 나올 수 있어 제외한다
    # (docs/limitations.md 참고). 여기서는 http/https, 대소문자, 끝 '/' 차이만 본다.
    variants = [f"https://{base}", f"http://{base}", f"https://{base}/" if not rest else f"https://{base}",
                f"HTTPS://{host.upper()}{rest}"]
    scores = [predict_model(v)["risk_score"] for v in variants]
    assert max(scores) - min(scores) <= 15


# ---------- 단축 URL ----------

@pytest.mark.parametrize("host", ["bit.ly", "naver.me", "tinyurl.com", "t.co", "han.gg", "www.bit.ly"])
def test_shortener_hosts(host):
    assert is_shortener_host(host)


@pytest.mark.parametrize("url", ["https://bit.ly/abc123", "https://naver.me/xAbC", "https://tinyurl.com/a"])
def test_shortener_is_not_confirmed_by_host_match(url):
    assert blacklist.check_blacklist(url).match_type != "host"


@pytest.mark.parametrize("url", ["https://t.co/abc", "https://bit.ly/abc", "https://goo.gl/abc"])
def test_shortener_is_not_allowlisted(url):
    assert not allowlist.check(url).matched


@pytest.mark.parametrize("score", [5.0, 45.0, 99.0])
def test_shortener_verdict_is_always_suspicious(score):
    decided = verdict.decide(BlacklistResult(matched=False, match_type="none", source="KISA 2024"), ModelResult(status="ready", risk_score=score, label="normal"),
                             AllowlistResult(), shortener=True)
    assert decided["verdict"] == "suspicious" and 30 <= decided["risk_score"] < 60


def test_exact_blacklisted_shortener_is_still_phishing():
    decided = verdict.decide(BlacklistResult(matched=True, match_type="exact", source="KISA 2024"),
                             ModelResult(status="not_ready"), AllowlistResult(), shortener=True)
    assert decided["verdict"] == "phishing" and decided["risk_score"] == 100


# ---------- 블랙리스트 정리 ----------

@pytest.mark.parametrize("junk", ["kca", "club", ".com", "1522-6582"])
def test_blacklist_ignores_non_domain_values(junk):
    assert not blacklist.check_blacklist(junk).matched


def test_blacklist_host_ignores_userinfo_port_and_trailing_dot():
    urls, hosts = blacklist.load_blacklist()
    host = sorted(h for h in hosts if not is_shortener_host(h) and h.count(".") == 1)[0]
    for url in (f"http://{host}/", f"http://naver.com@{host}/login", f"http://{host}./", f"http://{host}:8080/"):
        assert blacklist.check_blacklist(url).match_type in ("host", "exact"), url


# ---------- 동형 문자 도메인 ----------

def test_homograph_imitating_official_domain_is_phishing():
    result = homograph.check("https://xn--nver-loa.com/", allowlist.domains())
    assert result.imitates == "naver.com"
    decided = verdict.decide(BlacklistResult(matched=False, match_type="none", source="KISA 2024"), ModelResult(status="ready", risk_score=24.0, label="normal"),
                             allowlist.check("https://xn--nver-loa.com/"), homograph=result)
    assert decided["verdict"] == "phishing"


def test_korean_idn_is_not_flagged():
    result = homograph.check("https://xn--3e0b707e.com", allowlist.domains())
    assert result.matched and result.imitates is None and not result.mixed_script


@pytest.mark.parametrize("url", ["https://naver.com.evil.xyz/login", "https://navercom.xyz/", "https://naver.com@evil.xyz/"])
def test_lookalike_domains_are_not_allowlisted(url):
    assert not allowlist.check(url).matched


# ---------- 가이드와 AI 설명 ----------

def test_normal_verdict_gets_prevention_guides_only():
    tags = guides.evidence_tags("https://www.kbstar.com/login", "normal", [])
    assert tags == {"prevention"}
    found = guides.retrieve(tags, [])
    assert found and all("prevention" in g["matched"] or "예방" in g["matched"] for g in found)


def test_phishing_verdict_can_get_damage_guides():
    tags = guides.evidence_tags("http://kbstar-verify.com/login", "phishing", [])
    assert {"phishing_site", "financial", "login_page"} <= tags


EVIDENCE = [{"id": "E1", "source": "최종 판정", "text": "최종 위험도는 91.5점으로 '피싱' 판정입니다."},
            {"id": "E2", "source": "유사 사례", "text": "특징이 가장 비슷한 과거 사례 5건 중 피싱이 4건입니다."}]
GUIDES = [{"id": "G1", "title": "신고", "text": "보호나라에 신고합니다."}]


def test_citation_check_accepts_numbers_from_evidence():
    text = "최종 위험도는 91.5점입니다 [E1]. 비슷한 사례 5건 중 4건이 피싱입니다 [E2]. 보호나라에 신고하세요 [G1]."
    assert guides.check_citations(text, EVIDENCE, GUIDES) == text


def test_citation_check_rejects_invented_numbers():
    with pytest.raises(ValueError, match="숫자"):
        guides.check_citations("이 도메인은 3일 전에 등록됐습니다 [E1]. 신고하세요 [G1].", EVIDENCE, GUIDES)


def test_allowlisted_evidence_does_not_cite_high_ml_score_or_cases():
    from app.schemas import Detections, SimilarCase

    evidence = guides.build_evidence(
        verdict="normal", risk_score=25.0, blacklist=BlacklistResult(matched=False, match_type="none", source="KISA 2024"),
        allowlist=AllowlistResult(matched=True, domain="naver.com"),
        model=ModelResult(status="ready", risk_score=88.5, label="phishing"), explanation=None,
        detections=Detections(), similar_cases=[SimilarCase(url="http://evil.tk", label=1, similarity=0.9)],
    )
    sources = [e["source"] for e in evidence]
    assert sources[0] == "최종 판정"
    assert "ML 모델" not in sources and "유사 사례" not in sources
    assert "정상으로 판정" in evidence[1]["text"]


def test_allowlisted_evidence_has_no_raw_ml_number():
    from app.schemas import Detections

    evidence = guides.build_evidence(
        verdict="normal", risk_score=25.0, blacklist=BlacklistResult(matched=False, match_type="none", source="KISA 2024"),
        allowlist=AllowlistResult(matched=True, domain="naver.com"),
        model=ModelResult(status="ready", risk_score=88.54, label="phishing"), explanation=None,
        detections=Detections(), similar_cases=[],
    )
    assert all("88.54" not in e["text"] for e in evidence)


# ---------- 신뢰도 ----------

NONE = BlacklistResult(matched=False, match_type="none", source="KISA 2024")


@pytest.mark.parametrize("score,expected", [(2.1, 0.98), (20.8, 0.79), (25.0, 0.75), (45.0, 0.5), (60.0, 0.6), (99.9, 1.0)])
def test_confidence_leans_toward_verdict(score, expected):
    decided = verdict.decide(NONE, ModelResult(status="ready", risk_score=score, label="normal"), AllowlistResult())
    assert decided["confidence"] == expected


@pytest.mark.parametrize("ml", [2.1, 88.54, 99.53])
def test_allowlisted_normal_has_high_confidence(ml):
    decided = verdict.decide(NONE, ModelResult(status="ready", risk_score=ml, label="normal"),
                             AllowlistResult(matched=True, domain="naver.com"))
    assert decided["verdict"] == "normal" and decided["risk_score"] <= 25 and decided["confidence"] == 0.95


def test_schemeless_host_explains_deployed_score_gap():
    # 배포 88.54점 / 로컬 99.5점 차이의 원인: 'nid.naver.com'(도메인만)과 로그인 경로 URL은 다른 입력이다
    assert predict_model("nid.naver.com")["risk_score"] == pytest.approx(88.54, abs=0.5)
    assert predict_model("https://nid.naver.com/nidlogin.login")["risk_score"] == pytest.approx(99.53, abs=0.5)
