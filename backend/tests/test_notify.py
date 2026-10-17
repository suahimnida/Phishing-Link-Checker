"""의견 알림 메일 (notify.py). 실제 메일은 보내지 않고 httpx.post를 가로챈다."""

import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import notify

client = TestClient(app)

ITEM = {
    "id": "fb-1",
    "analysis_id": "an-1",
    "url": "http://secure-login.xyz/verify?email=me@example.com",
    "verdict": "phishing",
    "claim": "actually_safe",
    "comment": "회사 사이트예요 <a href='http://evil'>클릭</a>",
}


class _Response:
    def __init__(self, status=200):
        self.status_code = status
        self.text = ""


@pytest.fixture
def mail(monkeypatch):
    monkeypatch.setenv("RESEND_API_KEY", "test-key")
    monkeypatch.setenv("FEEDBACK_NOTIFY_TO", "admin@example.com")
    monkeypatch.setitem(notify._sent, "day", "")
    sent = []
    monkeypatch.setattr(notify.httpx, "post", lambda url, **kw: sent.append(kw) or _Response())
    return sent


def test_no_mail_without_settings(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    monkeypatch.setattr(notify.httpx, "post", lambda *a, **k: pytest.fail("메일을 보내면 안 됩니다"))
    assert notify.feedback_received(ITEM) is False


def test_mail_is_plain_text_with_masked_url(mail):
    assert notify.feedback_received(ITEM) is True
    body = mail[0]["json"]
    assert "html" not in body
    assert "me@example.com" not in body["text"]
    assert "secure-login.xyz/verify?***" in body["text"]
    assert "review_feedback.py accept fb-1" in body["text"]
    assert body["to"] == ["admin@example.com"]
    assert mail[0]["headers"]["Authorization"] == "Bearer test-key"


def test_daily_limit_stops_mail(mail, monkeypatch):
    monkeypatch.setenv("FEEDBACK_MAIL_DAILY_LIMIT", "2")
    results = [notify.feedback_received(ITEM) for _ in range(3)]
    assert results == [True, True, False]
    assert len(mail) == 2


def test_send_failure_does_not_raise(monkeypatch, mail):
    def boom(*a, **k):
        raise RuntimeError("network down")
    monkeypatch.setattr(notify.httpx, "post", boom)
    assert notify.feedback_received(ITEM) is False


def test_feedback_endpoint_sends_mail_once(mail):
    cid = str(uuid.uuid4())
    analysis = client.post("/api/v1/analyses", json={"url": "http://secure-login-verify.xyz/account"},
                           headers={"X-Client-Id": cid}).json()
    url = f"/api/v1/analyses/{analysis['id']}/feedback"
    assert client.post(url, json={"claim": "actually_safe"}, headers={"X-Client-Id": cid}).json()["received"]
    assert len(mail) == 1
    # 중복 신고는 저장되지 않으므로 메일도 보내지 않는다
    client.post(url, json={"claim": "actually_safe"}, headers={"X-Client-Id": cid})
    assert len(mail) == 1
