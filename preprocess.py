"""
scripts/preprocess.py

data/한국인터넷진흥원_피싱사이트_20241231.csv (131,752행, 컬럼: 날짜, 홈페이지주소)
를 읽어 중복을 제거하고 build/urls.json, build/hosts.json 두 개의
블랙리스트 데이터 파일을 만든다.

실행: python scripts/preprocess.py
      (phishing-checker/ 디렉터리 기준으로 실행한다고 가정)
"""
import csv
import re
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_CSV = os.path.join(BASE_DIR, "data", "한국인터넷진흥원_피싱사이트_20241231.csv")
BUILD_DIR = os.path.join(BASE_DIR, "build")
OUT_URLS = os.path.join(BUILD_DIR, "urls.json")
OUT_HOSTS = os.path.join(BUILD_DIR, "hosts.json")


def normalize(raw_url: str) -> str:
    """URL 정규화: 프로토콜과 끝 슬래시를 제거하고 소문자로 통일한다."""
    u = raw_url.strip()
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = u.rstrip("/")
    return u.lower()


def host_of(normalized_url: str) -> str:
    """정규화된 주소에서 도메인(첫 '/' 이전) 부분만 추출한다."""
    return normalized_url.split("/")[0]


def main():
    urls = set()
    hosts = set()

    with open(INPUT_CSV, encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        next(reader)

        for row in reader:
            if len(row) < 2 or not row[1].strip():
                continue
            n = normalize(row[1])
            if not n:
                continue
            urls.add(n)
            hosts.add(host_of(n))

    urls_list = sorted(urls)
    hosts_list = sorted(hosts)

    os.makedirs(BUILD_DIR, exist_ok=True)

    with open(OUT_URLS, "w", encoding="utf-8") as f:
        json.dump(urls_list, f, ensure_ascii=False, separators=(",", ":"))

    with open(OUT_HOSTS, "w", encoding="utf-8") as f:
        json.dump(hosts_list, f, ensure_ascii=False, separators=(",", ":"))

    print(f"고유 URL:   {len(urls_list):,}개 -> {OUT_URLS}")
    print(f"고유 도메인: {len(hosts_list):,}개 -> {OUT_HOSTS}")


if __name__ == "__main__":
    main()
