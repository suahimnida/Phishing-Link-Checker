"""백엔드 QA에서 나온 문제의 회귀 테스트.

- 입력 검증 (길이, 제어 문자, 스킴, 도메인 형식, 성명·암호 짝)
- 본인 확인 잠금이 DB에 남는지, 15분 뒤 풀리는지
- 공유 링크 동시 생성, 리포트 동시 요청, 저장 실패·DB 장애 처리
- 평판 조회 대기 시간, /health 설정 정보, 로그의 공유 토큰 가림
"""
import logging
import sqlite3
import threading
import time
import uuid

import pytest
from fastapi.testclient import TestClient

from app import db, main
from app.main import app
from app.services import owner

client = TestClient(app)
SECRET = "Abc123Xyz789"


def headers():
    return {"X-Client-Id": str(uuid.uuid4())}


def analyze(url="http://secure-login-verify.tk/account", h=None, **extra):
    res = client.post("/api/v1/analyses", json={"url": url, **extra}, headers=h or headers())
    return res


# ---------- 입력 검증 ----------

@pytest.mark.parametrize("url", [
    "", "   ", "a" * 10, "https://a.com/" + "a" * 3000, "http://ev\x00il.com", "http://a.com/\r\nX: 1",
    "javascript:alert(1)", "data:text/html,hi", "ftp://a.com/x", "http://a.com:99999/", "naver",
])
def test_invalid_urls_are_rejected(url):
    assert analyze(url).status_code == 422


@pytest.mark.parametrize("url", [
    "naver.com", "https://네이버.com/로그인", "http://192.168.0.1/login", "http://[::1]/login",
    "https://a.com/" + "a" * 2000, "HTTPS://EXAMPLE.COM/PATH",
])
def test_valid_urls_are_accepted(url):
    assert analyze(url).status_code == 200


@pytest.mark.parametrize("extra", [{"owner_name": "김수아"}, {"owner_secret": SECRET}])
def test_owner_name_and_secret_must_come_together(extra):
    assert analyze(is_public=True, **extra).status_code == 422


# ---------- 본인 확인 잠금 ----------

def test_lock_survives_restart_and_expires_after_15_minutes(monkeypatch):
    aid = analyze(is_public=True, owner_name="김수아", owner_secret=SECRET).json()["id"]
    for _ in range(owner.MAX_FAILURES):
        assert client.post(f"/api/v1/analyses/{aid}/verify-owner", json={"name": "김수아", "secret": "Wrong1234"}).status_code == 403
    assert client.post(f"/api/v1/analyses/{aid}/verify-owner", json={"name": "김수아", "secret": SECRET}).status_code == 429

    # 서버 재시작: 실패 기록은 DB에 있으므로 새 클라이언트(새 lifespan)에서도 잠겨 있어야 한다
    with TestClient(app) as restarted:
        assert restarted.post(f"/api/v1/analyses/{aid}/verify-owner", json={"name": "김수아", "secret": SECRET}).status_code == 429

    now = time.time()
    monkeypatch.setattr(owner.time, "time", lambda: now + 14 * 60 + 50)
    assert owner.locked(aid)
    monkeypatch.setattr(owner.time, "time", lambda: now + 15 * 60 + 10)
    assert not owner.locked(aid)
    assert client.post(f"/api/v1/analyses/{aid}/verify-owner", json={"name": "김수아", "secret": SECRET}).status_code == 200


def test_delete_removes_failure_record():
    aid = analyze(is_public=True, owner_name="김수아", owner_secret=SECRET).json()["id"]
    client.post(f"/api/v1/analyses/{aid}/verify-owner", json={"name": "김수아", "secret": "Wrong1234"})
    assert db.get_failures(aid)[0] == 1
    res = client.post(f"/api/v1/analyses/{aid}/delete",
                      json={"name": "김수아", "secret": SECRET, "confirm_text": owner.CONFIRM_TEXT})
    assert res.status_code == 200 and db.get_failures(aid) is None


# ---------- 동시 요청 ----------

def test_concurrent_share_creation_returns_one_token():
    h = headers()
    aid = analyze(h=h).json()["id"]
    results = []

    def make():
        res = client.post(f"/api/v1/analyses/{aid}/share", headers=h)
        results.append((res.status_code, res.json().get("token")))

    threads = [threading.Thread(target=make) for _ in range(5)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert {code for code, _ in results} == {200}
    assert len({token for _, token in results}) == 1


def test_concurrent_report_requests_call_llm_once(monkeypatch):
    h = headers()
    aid = analyze(h=h).json()["id"]
    calls = []
    original = main.followup.research

    def slow_research(*args, **kwargs):
        calls.append(1)
        time.sleep(0.5)
        return original(*args, **kwargs)

    monkeypatch.setattr(main.followup, "research", slow_research)
    codes = []
    threads = [threading.Thread(target=lambda: codes.append(
        client.post(f"/api/v1/analyses/{aid}/report", headers=h).status_code)) for _ in range(3)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert codes == [200, 200, 200] and len(calls) == 1


# ---------- 저장 실패·DB 장애 ----------

def test_save_failure_still_returns_result_marked_unsaved(monkeypatch):
    def broken(*args, **kwargs):
        raise sqlite3.OperationalError("database is locked")

    monkeypatch.setattr(db, "save_analysis", broken)
    res = analyze()
    assert res.status_code == 200
    body = res.json()
    assert body["saved"] is False and body["verdict"] is not None


def test_saved_flag_is_true_normally_and_not_stored():
    h = headers()
    body = analyze(h=h).json()
    assert body["saved"] is True
    assert client.get(f"/api/v1/analyses/{body['id']}", headers=h).json()["saved"] is True


def test_db_outage_returns_503_not_500(monkeypatch):
    def broken(*args, **kwargs):
        raise sqlite3.OperationalError("unable to open database file")

    monkeypatch.setattr(db, "list_analyses", broken)
    res = TestClient(app, raise_server_exceptions=False).get("/api/v1/analyses?scope=public")
    assert res.status_code == 503 and "잠시 후" in res.json()["detail"]


# ---------- 평판 조회 대기 ----------

def test_slow_reputation_does_not_delay_analysis_much(monkeypatch):
    monkeypatch.setenv("REPUTATION_ENABLED", "1")
    monkeypatch.setattr(main, "REPUTATION_WAIT", 1.0)
    monkeypatch.setattr(main.reputation, "lookup", lambda url: (time.sleep(5), {})[1])
    started = time.perf_counter()
    res = analyze("https://slow-reputation.example.com/x")
    assert res.status_code == 200
    assert time.perf_counter() - started < 3
    assert res.json()["detections"]["reputation"] is None


# ---------- 배포 확인용 정보·로그 ----------

def test_health_shows_llm_settings_without_secrets(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "sk-secret-value")
    body = client.get("/health").json()
    assert body["llm"]["claude"]["configured"] is True
    assert "sk-secret-value" not in str(body)
    assert body["llm"]["database"] in ("SQLite", "PostgreSQL")


def test_access_log_hides_share_token():
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                               ("1.2.3.4", "GET", "/api/v1/analyses/x/report.pdf?share=SECRETTOKEN&a=1", "1.1", 200),
                               None)
    main._RedactShareToken().filter(record)
    assert "SECRETTOKEN" not in record.getMessage() and "share=***" in record.getMessage()
    record = logging.LogRecord("uvicorn.access", logging.INFO, __file__, 1, '%s - "%s %s HTTP/%s" %d',
                               ("1.2.3.4", "GET", "/api/v1/shared/SECRETTOKEN", "1.1", 200), None)
    main._RedactShareToken().filter(record)
    assert "SECRETTOKEN" not in record.getMessage()


# ---------- 저장된 리포트 조회 ----------

def test_saved_report_is_returned_without_generating(monkeypatch):
    h = headers()
    aid = analyze(h=h).json()["id"]
    assert client.get(f"/api/v1/analyses/{aid}/report", headers=h).status_code == 404

    calls = []
    original = main.followup.research
    monkeypatch.setattr(main.followup, "research", lambda *a, **k: (calls.append(1), original(*a, **k))[1])
    created = client.post(f"/api/v1/analyses/{aid}/report", headers=h).json()

    saved = client.get(f"/api/v1/analyses/{aid}/report", headers=h)
    assert saved.status_code == 200 and saved.json()["created_at"] == created["created_at"]
    assert len(calls) == 1  # GET은 LLM을 부르지 않는다


def test_saved_report_follows_same_access_rules():
    owner_h, other_h = headers(), headers()
    aid = analyze(h=owner_h).json()["id"]
    client.post(f"/api/v1/analyses/{aid}/report", headers=owner_h)
    assert client.get(f"/api/v1/analyses/{aid}/report", headers=other_h).status_code == 404
    token = client.post(f"/api/v1/analyses/{aid}/share", headers=owner_h).json()["token"]
    assert client.get(f"/api/v1/analyses/{aid}/report?share={token}", headers=other_h).status_code == 200
