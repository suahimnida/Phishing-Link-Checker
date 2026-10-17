"""개인정보 보호용 공통 처리.

사용자가 입력한 URL의 '?' 뒤(쿼리)와 '#' 뒤에는 이메일, 전화번호, 인증 토큰이 들어 있는 경우가 많다.
로그에는 이 부분을 가리고 남긴다. 분석 결과 화면에는 사용자가 입력한 주소를 그대로 보여 준다.
"""

import os
import re

# 분석 기록 보관 기간(일). 지나면 분석 기록과 딸린 리포트·공유 링크·신고를 지운다
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS") or 90)

_QUERY = re.compile(r"([?#])[^\s\"']+")


def mask_url(url: str | None) -> str:
    """'https://a.com/login?email=me@x.com' → 'https://a.com/login?***'"""
    if not url:
        return ""
    return _QUERY.sub(r"\1***", str(url))
