"""단축 URL 서비스 도메인 목록.

단축 URL은 실제로 이동할 주소가 가려져 있어 URL 문자열만으로는 안전한지 판단할 수 없다.
- KISA 목록에는 과거 피싱에 쓰인 단축 도메인(bit.ly, naver.me 등)이 '호스트 단위'로 들어 있어,
  모든 단축 링크가 피싱 100점으로 확정되는 문제가 있었다 → 호스트 일치로는 확정하지 않는다.
- 허용 목록에도 일부(t.co, bit.ly 등)가 들어 있어 정상 25점이 되는 문제가 있었다 → 허용하지 않는다.
- 대신 최종 판정을 '의심'으로 고정하고, 목적지를 확인하라는 근거·가이드를 붙인다 (verdict.py).
KISA 목록과 URL이 정확히 일치하는 단축 링크는 여전히 피싱으로 확정한다.
"""

SHORTENER_HOSTS = frozenset({
    # 해외
    "bit.ly", "bitly.com", "j.mp", "tinyurl.com", "goo.gl", "t.co", "is.gd", "v.gd", "ow.ly", "buff.ly",
    "cutt.ly", "rebrand.ly", "rb.gy", "shorturl.at", "tiny.cc", "t.ly", "s.id", "lnkd.in", "qrco.de",
    "shorturl.asia", "bl.ink", "short.io", "abit.ly", "abre.ai", "tr.ee", "u.to", "clck.ru",
    # 국내
    "naver.me", "me2.do", "han.gl", "han.gg", "vo.la", "buly.kr", "url.kr", "c11.kr", "zrr.kr",
    "kko.to", "kakaolink.com", "muz.so", "gg.gg", "bitly.kr", "lrl.kr", "di.do", "link24.kr",
})


def _clean(host: str) -> str:
    host = (host or "").lower().strip().strip(".")
    return host[4:] if host.startswith("www.") else host


def is_shortener_host(host: str) -> bool:
    return _clean(host) in SHORTENER_HOSTS
