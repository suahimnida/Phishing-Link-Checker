"""3단계: 판정 오류 신고, 블랙리스트 공용 주소 예외, LLM 비용 관리, 개인정보 보관 기간."""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app import db, main
from app.main import app
from app.services import blacklist, privacy, rag

client = TestClient(app)


def _analyze(url, client_id, public=False):
    res = client.post("/api/v1/analyses", json={"url": url, "is_public": public}, headers={"X-Client-Id": client_id})
    assert res.status_code == 200
    return res.json()


# ---------- 블랙리스트 공용 주소 ----------

@pytest.mark.parametrize("url", [
    "https://www.nhis.or.kr",            # 국민건강보험공단 공식 사이트
    "https://www.nhis.or.kr/nhis/index.do",
    "https://pf.kakao.com/_newchannel",  # 카카오톡 채널 전체
    "https://t.me/anychannel",
    "https://telegram.org",
    "https://line.me/R/ti/p/abc",
    "https://m.site.naver.com/abc",
])
def test_shared_hosts_are_not_confirmed_by_host(url):
    assert not blacklist.check_blacklist(url).matched


def test_exact_reported_page_on_shared_host_is_still_confirmed():
    urls, _ = blacklist.load_blacklist()
    reported = next(u for u in urls if u.startswith("pf.kakao.com/"))
    assert blacklist.check_blacklist("https://" + reported).matched


def test_attacker_subdomain_on_platform_is_still_confirmed():
    assert blacklist.check_blacklist("https://httpswwwgovkr.wordpress.com").matched


# ---------- 판정 오류 신고 ----------

def test_feedback_is_saved_once_as_pending():
    cid = str(uuid.uuid4())
    analysis = _analyze("http://secure-login-verify.xyz/account", cid)
    url = f"/api/v1/analyses/{analysis['id']}/feedback"
    first = client.post(url, json={"claim": "actually_safe", "comment": "회사 사내 사이트예요"}, headers={"X-Client-Id": cid})
    assert first.status_code == 200 and first.json()["received"] is True
    again = client.post(url, json={"claim": "actually_safe"}, headers={"X-Client-Id": cid})
    assert again.json()["received"] is False
    pending = db.list_feedback("pending")
    assert [f["analysis_id"] for f in pending] == [analysis["id"]]
    assert pending[0]["verdict"] == analysis["verdict"]


def test_feedback_needs_access_to_the_result():
    owner = str(uuid.uuid4())
    analysis = _analyze("http://secure-login-verify.xyz/account", owner, public=False)
    stranger = str(uuid.uuid4())
    res = client.post(f"/api/v1/analyses/{analysis['id']}/feedback", json={"claim": "other"},
                      headers={"X-Client-Id": stranger})
    assert res.status_code == 404


def test_feedback_rejects_unknown_claim_and_long_comment():
    cid = str(uuid.uuid4())
    analysis = _analyze("http://secure-login-verify.xyz/account", cid)
    url = f"/api/v1/analyses/{analysis['id']}/feedback"
    assert client.post(url, json={"claim": "add_to_allowlist"}, headers={"X-Client-Id": cid}).status_code == 422
    assert client.post(url, json={"claim": "other", "comment": "가" * 201}, headers={"X-Client-Id": cid}).status_code == 422


def test_feedback_review_changes_status_only_once():
    cid = str(uuid.uuid4())
    analysis = _analyze("http://secure-login-verify.xyz/account", cid)
    client.post(f"/api/v1/analyses/{analysis['id']}/feedback", json={"claim": "actually_safe"}, headers={"X-Client-Id": cid})
    item = db.list_feedback("pending")[0]
    assert db.review_feedback(item["id"], "rejected", "공식 도메인 아님") is True
    assert db.review_feedback(item["id"], "accepted", None) is False
    assert db.list_feedback("pending") == []


# ---------- LLM 비용 관리 ----------

def test_llm_is_not_called_for_normal_verdict(monkeypatch):
    calls = []
    monkeypatch.setattr(main.rag, "compose", lambda e, g: calls.append(1) or None)
    result = _analyze("https://www.naver.com", str(uuid.uuid4()))
    assert result["verdict"] == "normal" and calls == []
    _analyze("http://secure-login-verify.xyz/account", str(uuid.uuid4()))
    assert calls == [1]


def test_explanation_cache_reuses_checked_text():
    rag._cache_put("k", "설명 [E1].")
    assert rag._cache_get("k") == "설명 [E1]."
    rag._explain_cache["k"] = (0.0, "오래된 설명")
    assert rag._cache_get("k") is None


# ---------- 개인정보 ----------

def test_mask_url_hides_query_and_fragment():
    assert privacy.mask_url("https://a.com/login?email=me@x.com&t=1") == "https://a.com/login?***"
    assert privacy.mask_url("a.com/p#token=abc") == "a.com/p#***"
    assert privacy.mask_url("https://a.com/path") == "https://a.com/path"


def test_purge_removes_old_analysis_and_its_feedback():
    cid = str(uuid.uuid4())
    old = _analyze("http://secure-login-verify.xyz/account", cid)
    new = _analyze("http://secure-login-verify.xyz/other", cid)
    client.post(f"/api/v1/analyses/{old['id']}/feedback", json={"claim": "other"}, headers={"X-Client-Id": cid})
    past = (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()
    with db._connect() as (conn, p):
        conn.execute(f"UPDATE analyses SET created_at = {p} WHERE id = {p}", (past, old["id"]))
    assert db.purge_older_than(90) == 1
    assert db.get_analysis(old["id"], cid) is None
    assert db.get_analysis(new["id"], cid) is not None
    assert db.list_feedback("pending") == []
