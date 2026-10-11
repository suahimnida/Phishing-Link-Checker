import hashlib
import hmac
import re
import secrets
import time

SECRET_PATTERN = re.compile(r"^[A-Za-z0-9]{8,12}$")
CONFIRM_TEXT = "분석 결과를 삭제하겠습니다"
ITERATIONS = 200_000
MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60



def mask_name(name: str) -> str:
    chars = [c for c in name.strip() if not c.isspace()]
    if not chars:
        return ""
    if len(chars) == 1:
        return "*"
    return chars[0] + "*" * (len(chars) - 1)


def _hash(value: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", value.encode(), salt, ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify(value: str, stored: str | None) -> bool:
    if not stored:
        return False
    try:
        _, iterations, salt, expected = stored.split("$")
        digest = hashlib.pbkdf2_hmac("sha256", value.encode(), bytes.fromhex(salt), int(iterations))
    except ValueError:
        return False
    return hmac.compare_digest(digest.hex(), expected)


def normalize_name(name: str) -> str:
    return "".join((name or "").split())


def hash_secret(secret: str) -> str:
    return _hash(secret)


def verify_secret(secret: str, stored: str | None) -> bool:
    return bool(SECRET_PATTERN.match(secret or "")) and _verify(secret, stored)


def hash_name(name: str) -> str:
    return _hash(normalize_name(name))


def verify_name(name: str, stored_hash: str | None, masked: str | None) -> bool:
    if not normalize_name(name):
        return False
    if stored_hash:
        return _verify(normalize_name(name), stored_hash)
    return bool(masked) and mask_name(name) == masked


def locked(analysis_id: str) -> bool:
    """5번 틀린 뒤 첫 실패로부터 15분 동안 잠근다. 실패 기록은 DB에 있어 서버를 재시작해도 유지된다."""
    from app import db

    row = db.get_failures(analysis_id)
    if row is None:
        return False
    count, first = row
    if time.time() - first > LOCK_SECONDS:
        db.clear_failures(analysis_id)
        return False
    return count >= MAX_FAILURES


def record_failure(analysis_id: str) -> None:
    from app import db

    db.record_failure(analysis_id, time.time(), LOCK_SECONDS)


def clear_failures(analysis_id: str) -> None:
    from app import db

    db.clear_failures(analysis_id)
