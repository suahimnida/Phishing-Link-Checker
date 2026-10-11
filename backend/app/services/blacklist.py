import json
import os
from functools import lru_cache
from pathlib import Path
import re
from urllib.parse import urlsplit

from app.schemas import BlacklistResult
from app.services.shorteners import is_shortener_host

SOURCE = "KISA 2024"
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


def check_blacklist(url: str) -> BlacklistResult:
    urls, hosts = load_blacklist()

    if _normalize_url(url) in urls:
        return BlacklistResult(matched=True, match_type="exact", source=SOURCE)

    host = _extract_host(url)
    # 단축 URL 도메인은 호스트 단위로 확정하지 않는다 (shorteners.py 설명 참고)
    if host in hosts and not is_shortener_host(host):
        return BlacklistResult(matched=True, match_type="host", source=SOURCE)

    return BlacklistResult(matched=False, match_type="none", source=SOURCE)
