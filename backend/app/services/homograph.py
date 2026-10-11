"""퓨니코드(xn--) 동형 문자 도메인 탐지.

'xn--nver-loa.com'(nàver.com)처럼 라틴 문자와 비슷하게 생긴 다른 문자로 공식 도메인을 흉내 낸 주소는
문자 n-gram 모델이 'xn--' 글자만 보고 판단해 정상으로 나올 수 있었다 (QA: 정상 24점).
도메인을 디코딩해 비슷한 글자를 기본 라틴 문자로 바꾼 뒤(스켈레톤), 공식 도메인 허용 목록과 같아지면
'공식 도메인 흉내'로 본다. 한글 도메인처럼 한 가지 문자만 쓰는 정상 국제화 도메인은 건드리지 않는다.
"""
import unicodedata
from urllib.parse import urlsplit

from pydantic import BaseModel

# 라틴 문자와 헷갈리는 키릴·그리스 문자 등 (자주 쓰이는 것 위주)
_CONFUSABLE = str.maketrans({
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j", "ѕ": "s",
    "ԁ": "d", "ӏ": "l", "һ": "h", "ԛ": "q", "ԝ": "w", "ɡ": "g", "ν": "v", "ο": "o", "α": "a", "ρ": "p",
    "τ": "t", "κ": "k", "ι": "i", "υ": "u", "ε": "e", "ɑ": "a", "ı": "i", "ℓ": "l", "ꓲ": "l",
    "А": "a", "В": "b", "Е": "e", "К": "k", "М": "m", "Н": "h", "О": "o", "Р": "p", "С": "c", "Т": "t",
    "Х": "x", "Ү": "y", "Ι": "i", "Ο": "o", "Ρ": "p", "Α": "a", "Β": "b", "Ε": "e", "Κ": "k", "Τ": "t",
})


class HomographResult(BaseModel):
    matched: bool = False          # 퓨니코드 도메인인지
    decoded: str | None = None     # 사람이 보는 실제 글자
    imitates: str | None = None    # 흉내 낸 공식 도메인 (있을 때만)
    mixed_script: bool = False     # 한 이름 안에 라틴 문자와 키릴·그리스 문자가 섞였는지


def _host(url: str) -> str:
    url = url.strip()
    if "://" not in url:
        url = "http://" + url
    try:
        return (urlsplit(url).hostname or "").lower().strip(".")
    except ValueError:
        return ""


def _decode(host: str) -> str:
    labels = []
    for label in host.split("."):
        if label.startswith("xn--"):
            try:
                label = label.encode("ascii").decode("idna")
            except (UnicodeError, ValueError):
                pass
        labels.append(label)
    return ".".join(labels)


def _skeleton(text: str) -> str:
    text = text.translate(_CONFUSABLE)
    # 'à' → 'a'처럼 악센트를 떼어 낸다
    text = "".join(c for c in unicodedata.normalize("NFKD", text) if not unicodedata.combining(c))
    return text.lower()


def _scripts(label: str) -> set:
    found = set()
    for c in label:
        if c.isascii():
            if c.isalpha():
                found.add("LATIN")
            continue
        name = unicodedata.name(c, "")
        for script in ("LATIN", "CYRILLIC", "GREEK"):
            if name.startswith(script):
                found.add(script)
    return found


def check(url: str, official_domains: set) -> HomographResult:
    host = _host(url)
    if "xn--" not in host:
        return HomographResult()
    from url_features import registered_domain

    decoded = _decode(host)
    skeleton = _skeleton(decoded)
    mixed = any(len(_scripts(label)) >= 2 for label in decoded.split("."))
    imitates = None
    if skeleton.isascii() and skeleton != host:
        domain = registered_domain(skeleton)
        if domain in official_domains and registered_domain(host) != domain:
            imitates = domain
    return HomographResult(matched=True, decoded=decoded, imitates=imitates, mixed_script=mixed)
