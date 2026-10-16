from fastapi.testclient import TestClient

from app.main import app
from app.schemas import Detections
from app.services import detections, findings, guides, reputation

client = TestClient(app)


def _explain(url):
    return findings.explain(Detections(**detections.analyze(url)))


def test_brand_domain_gets_plain_explanation_with_stat():
    items = _explain("http://kakaobank-secure-login.xyz/verify")
    keys = [i["key"] for i in items]
    assert "suspicious_tld" in keys
    tld = next(i for i in items if i["key"] == "suspicious_tld")
    assert tld["why"] and tld["harm"] and tld["detail"]
    # 비율은 '이 특징이 있으면 N%가 피싱'이 아니라 피싱·정상 각각에서 나타난 비율로 보여 준다
    assert "피싱 URL의" in tld["stat"]["text"] and "정상 URL의" in tld["stat"]["text"]


def test_same_feature_is_listed_once():
    items = _explain("http://192.168.0.1/login")
    keys = [i["key"] for i in items]
    assert keys.count("ip_host") == 1


def test_normal_url_has_no_findings():
    assert _explain("https://www.naver.com") == []


def test_small_sample_feature_hides_stat(monkeypatch):
    monkeypatch.setitem(findings._load_rates()["features"], "punycode", {"phishing": 10, "normal": 0})
    assert findings.stat_for("punycode") is None


def test_stat_numbers_can_be_cited_in_explanation():
    url = "http://secure-login-verify.xyz/account"
    det = Detections(**detections.analyze(url))
    evidence = [{"id": "E1", "source": "최종 판정", "text": "최종 위험도는 80점으로 '피싱' 판정입니다.", "used_in_verdict": True}]
    for item in det.domain["reasons"]:
        stat = findings.stat_sentence(item)
        if stat:
            evidence.append({"id": "E2", "source": "탐지 결과", "text": f"{item} {stat}", "used_in_verdict": False})
            break
    assert len(evidence) == 2
    pct = findings.stat_for("suspicious_tld")["phishing_pct"]
    text = f"피싱 URL의 {pct}에서 나타난 특징입니다 [E2]."
    assert guides.check_citations(text, evidence, []) == text


def test_response_guide_lists_situations_with_official_contacts():
    res = client.get("/api/v1/response-guide")
    assert res.status_code == 200
    situations = {s["id"]: s for s in res.json()["situations"]}
    assert "not_visited" not in situations
    phones = {c["phone"] for c in situations["financial_loss"]["contacts"]}
    assert {"112", "1332"} <= phones
    assert all(s["actions"] for s in situations.values())


def test_reputation_checks_never_mention_visiting_site():
    info = {
        "domain": "example.xyz", "platform": False,
        "rdap": {"status": "ok", "created": "2026-10-01", "age_days": 5},
        "ct": {"status": "none"},
        "hosting": {"status": "ok", "ip": "1.2.3.4", "country": "US", "as_name": "EXAMPLE"},
    }
    checks = {c["key"]: c for c in reputation.to_detection(info)["checks"]}
    assert checks["domain_age"]["state"] == "warn"
    assert checks["certificate"]["state"] == "none"
    assert checks["hosting"]["state"] == "ok"


def test_analysis_response_includes_findings():
    res = client.post("/api/v1/analyses", json={"url": "http://192.168.0.1/login"})
    assert res.status_code == 200
    assert any(f["key"] == "ip_host" for f in res.json()["findings"])
