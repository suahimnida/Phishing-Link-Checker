import json
import os
from functools import lru_cache
from pathlib import Path
import re
from urllib.parse import urlsplit

from app.schemas import BlacklistResult
from app.services.shorteners import is_shortener_host

SOURCE = "KISA 2024"
# KISA 공개 목록의 기준일. 결과 화면에 표시해 목록이 언제 기준인지 알린다
SOURCE_DATE = "2024-12-31"
# 사용자 신고를 사람이 검토해 추가한 주소
REVIEWED_SOURCE = "검토된 사용자 신고"
_DEFAULT_DIR = Path(__file__).resolve().parents[2] / "resources" / "blacklist"


def _data_dir() -> Path:
    return Path(os.environ.get("BLACKLIST_DIR") or _DEFAULT_DIR)


# KISA 원본에는 'kca', 'club', '.com', 전화번호처럼 도메인이 아닌 값이 섞여 있다.
# 그대로 두면 'kca'만 입력해도 피싱 100점이 나오므로 도메인 형식인 값만 쓴다.
_HOST_OK = re.compile(r"^(?:\d{1,3}(?:\.\d{1,3}){3}|(?:[a-z0-9_](?:[a-z0-9_-]*[a-z0-9_])?\.)+(?:[a-z]{2,63}|xn--[a-z0-9-]+))$")


def _clean_host(raw: str) -> str:
    """'host:6013', 'host?=3bd', 'host,'처럼 포트나 찌꺼기가 붙은 값은 호스트 부분만 남긴다."""
    return re.split(r"[:?,/]", raw.strip().lower(), maxsplit=1)[0].strip(".")


def _valid_host(host: str) -> bool:
    return bool(_HOST_OK.match(host))


@lru_cache(maxsize=1)
def load_blacklist() -> tuple[frozenset[str], frozenset[str]]:
    d = _data_dir()
    with open(d / "urls.json", encoding="utf-8") as f:
        urls = frozenset(
            n for n in (_normalize_url(u) for u in json.load(f))
            if _valid_host(_extract_host(n))
        )
    with open(d / "hosts.json", encoding="utf-8") as f:
        hosts = frozenset(h for h in (_clean_host(h) for h in json.load(f)) if _valid_host(h))
    return urls, hosts


def _normalize_url(url: str) -> str:
    url = url.strip()
    if "://" in url:
        url = url.split("://", 1)[1]
    host, sep, rest = url.partition("/")
    return (host.lower() + sep + rest).rstrip("/")


def _extract_host(url: str) -> str:
    """아이디·비밀번호(@ 앞부분)와 포트를 뺀 호스트 이름. 끝의 '.'도 지운다.

    netloc을 그대로 쓰면 'http://naver.com@피싱주소/'나 '피싱주소./'가 호스트 일치를 피해 갔다 (QA).
    """
    url = url.strip()
    if "://" not in url:
        url = "http://" + url
    try:
        host = urlsplit(url).hostname or ""
    except ValueError:
        return ""
    return host.lower().strip(".")


def _read_list(name: str) -> list[str]:
    """exclusions.txt / additions.txt: 한 줄에 하나, '#' 뒤는 설명."""
    try:
        lines = (_data_dir() / name).read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return []
    return [line.split("#", 1)[0].strip().lower() for line in lines if line.split("#", 1)[0].strip()]


@lru_cache(maxsize=1)
def load_reviewed() -> tuple[frozenset[str], frozenset[str], frozenset[str]]:
    """사람이 검토한 예외(호스트)와 자체 추가 목록(정확한 주소, 호스트)."""
    exclusions = frozenset(_clean_host(h) for h in _read_list("exclusions.txt"))
    added = [_normalize_url(u) for u in _read_list("additions.txt")]
    return exclusions, frozenset(u for u in added if "/" in u), frozenset(u for u in added if "/" not in u)


def is_shared_host(host: str) -> bool:
    """여러 사람·기관이 함께 쓰는 주소라 호스트 하나로 피싱을 확정하면 안 되는지.

    KISA 목록에는 'pf.kakao.com'(카카오톡 채널 전체), 'www.nhis.or.kr'(국민건강보험공단 공식 사이트)처럼
    사칭 대상이나 플랫폼 주소가 호스트 단위로 섞여 있어, 정상 사이트가 피싱 확정되는 문제가 있었다 (2026-10-16 점검).
    - 공식 도메인 목록(allowlist)에 있는 도메인의 주소 (pf.kakao.com, line.me, m.site.naver.com 등)
    - 플랫폼 주소 자체 (t.me, wa.me). 단 'abc.netlify.app'처럼 공격자가 만든 하위 주소는 해당하지 않는다
    - 사람이 검토해 exclusions.txt에 적은 주소
    """
    from app.services import allowlist  # allowlist가 shorteners를 불러오므로 함수 안에서 불러 순환을 피한다

    if not host:
        return False
    if host in load_reviewed()[0]:
        return True
    if host in allowlist.USER_CONTENT:
        return True
    if allowlist._is_user_content(host):
        return False
    return allowlist.registered_domain(host) in allowlist.domains()


def check_blacklist(url: str) -> BlacklistResult:
    urls, hosts = load_blacklist()
    _, added_urls, added_hosts = load_reviewed()
    normalized = _normalize_url(url)
    host = _extract_host(url)
    shared = is_shared_host(host)

    # 경로까지 정확히 일치하면 확정한다. 공용 주소라도 신고된 그 페이지는 피싱이다.
    # 다만 공용 주소의 '경로 없는 주소'(www.nhis.or.kr 등)는 사칭 대상이 목록에 들어간 경우라 확정하지 않는다
    has_path = "/" in normalized
    if normalized in added_urls:
        return BlacklistResult(matched=True, match_type="exact", source=REVIEWED_SOURCE)
    if normalized in urls and (has_path or not shared):
        return BlacklistResult(matched=True, match_type="exact", source=SOURCE)
    # 공용 주소와 단축 URL 도메인은 호스트 단위로 확정하지 않는다 (shorteners.py 설명 참고)
    if shared or is_shortener_host(host):
        return BlacklistResult(matched=False, match_type="none", source=SOURCE)
    if host in added_hosts:
        return BlacklistResult(matched=True, match_type="host", source=REVIEWED_SOURCE)
    if host in hosts:
        return BlacklistResult(matched=True, match_type="host", source=SOURCE)
    return BlacklistResult(matched=False, match_type="none", source=SOURCE)
