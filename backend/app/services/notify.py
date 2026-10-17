"""'이 판정이 틀렸나요?' 신고가 들어오면 관리자 메일로 알린다.

Render 무료 플랜은 SMTP 포트(25·465·587)로 나가는 연결을 막으므로, HTTPS로 보내는 메일 API(Resend)를 쓴다.
환경변수가 없으면 아무것도 보내지 않는다 (로컬 개발·테스트에서 실제 메일이 나가지 않게).

    RESEND_API_KEY        Resend에서 발급한 API 키 (필수)
    FEEDBACK_NOTIFY_TO    받을 메일 주소 (필수). 도메인 인증 전에는 Resend 가입 메일 주소만 받을 수 있다
    FEEDBACK_NOTIFY_FROM  보내는 주소 (선택). 기본값은 Resend 테스트 주소
    FEEDBACK_MAIL_DAILY_LIMIT  하루 최대 발송 수 (선택, 기본 50)

보안
- 사용자가 쓴 의견은 일반 텍스트 메일로만 보낸다. HTML에 넣으면 메일 안에 가짜 링크를 심을 수 있다.
- 주소는 '?' 뒤를 가려 보낸다 (privacy.mask_url). 메일은 서버 밖으로 나가는 정보다.
- 하루 발송 상한을 둔다. 여러 브라우저로 신고를 몰아 보내도 메일함이 넘치지 않고, 의견은 DB에 계속 쌓인다.
- 발송 실패는 로그만 남기고 신고 저장에는 영향을 주지 않는다.
"""

import logging
import os
import threading
from datetime import datetime, timezone

import httpx

from app.services.privacy import mask_url

logger = logging.getLogger(__name__)

RESEND_URL = "https://api.resend.com/emails"
DEFAULT_FROM = "피싱 사이트 분석기 <onboarding@resend.dev>"

CLAIM_KO = {"actually_safe": "실제로는 안전한 사이트", "actually_phishing": "실제로는 피싱 사이트", "other": "기타 의견"}
VERDICT_KO = {"phishing": "위험", "suspicious": "주의", "normal": "안전"}

_lock = threading.Lock()
_sent = {"day": "", "count": 0}


def _daily_limit() -> int:
    try:
        return int(os.environ.get("FEEDBACK_MAIL_DAILY_LIMIT") or 50)
    except ValueError:
        return 50


def configured() -> bool:
    return bool(os.environ.get("RESEND_API_KEY") and os.environ.get("FEEDBACK_NOTIFY_TO"))


def _take_quota() -> bool:
    """오늘(UTC) 보낼 수 있는 메일이 남았으면 1건 쓰고 True. 서버 메모리 기준이라 재시작하면 다시 센다."""
    today = datetime.now(timezone.utc).date().isoformat()
    with _lock:
        if _sent["day"] != today:
            _sent["day"], _sent["count"] = today, 0
        if _sent["count"] >= _daily_limit():
            return False
        _sent["count"] += 1
        return True


def _clean(text: str | None) -> str:
    """메일 본문에 넣을 사용자 입력. 줄바꿈 외 제어 문자를 빼고 길이를 제한한다."""
    if not text:
        return "(없음)"
    text = "".join(ch for ch in text if ch == "\n" or ch.isprintable())
    return text[:300]


def build_message(item: dict) -> dict:
    """Resend에 보낼 메일 내용. 일반 텍스트만 쓴다."""
    claim = CLAIM_KO.get(item["claim"], item["claim"])
    verdict = VERDICT_KO.get(item.get("verdict") or "", "판정 불가")
    body = "\n".join([
        "'이 판정이 틀렸나요?'로 새 의견이 들어왔습니다.",
        "",
        f"신고 id : {item['id']}",
        f"분석 id : {item['analysis_id']}",
        f"주소    : {mask_url(item['url'])}",
        f"판정    : {verdict}",
        f"의견    : {claim}",
        f"내용    : {_clean(item.get('comment'))}",
        "",
        "이 의견은 아직 반영되지 않았습니다. 확인한 뒤 저장소 루트에서 처리하세요.",
        f"  승인: python scripts/review_feedback.py accept {item['id']} --note \"확인한 근거\"",
        f"  거절: python scripts/review_feedback.py reject {item['id']} --note \"거절 사유\"",
        "",
        "메일 속 주소는 열지 마세요. 피싱으로 판정됐을 수 있는 주소입니다 ('?' 뒤는 가려져 있습니다).",
    ])
    return {
        "from": os.environ.get("FEEDBACK_NOTIFY_FROM") or DEFAULT_FROM,
        "to": [os.environ["FEEDBACK_NOTIFY_TO"]],
        "subject": f"[피싱 분석기] 판정 오류 의견: {verdict} → {claim}",
        "text": body,
    }


def feedback_received(item: dict) -> bool:
    """신고 알림 메일을 보낸다. 보냈으면 True. 백그라운드 작업으로 실행되므로 예외를 밖으로 내보내지 않는다."""
    if not configured():
        return False
    if not _take_quota():
        logger.warning("오늘 의견 알림 메일 상한(%s통)에 도달해 메일을 보내지 않습니다. 의견은 DB에 저장됐습니다.",
                       _daily_limit())
        return False
    try:
        response = httpx.post(
            RESEND_URL,
            headers={"Authorization": f"Bearer {os.environ['RESEND_API_KEY']}"},
            json=build_message(item),
            timeout=10,
        )
        if response.status_code >= 400:
            # 응답 본문에는 사용자 내용이 없지만, 키가 섞일 수 있는 헤더는 남기지 않는다
            logger.warning("의견 알림 메일 발송 실패: HTTP %s %s", response.status_code, response.text[:200])
            return False
        logger.info("의견 알림 메일 발송: 신고 %s", item["id"])
        return True
    except Exception as error:
        logger.warning("의견 알림 메일 발송 실패: %s", type(error).__name__)
        return False
