"""'이 판정이 틀렸나요?' 신고를 검토하고 반영한다 (관리자용).

신고는 서버가 자동으로 반영하지 않는다. 공격자가 자기 피싱 사이트를 '정상'이라고 반복 신고해
허용 목록이나 학습 데이터를 오염시킬 수 있기 때문이다. 이 스크립트로 사람이 하나씩 확인한다.

실행 (저장소 루트에서, 운영 DB를 볼 때는 DATABASE_URL 환경변수를 설정):
    python scripts/review_feedback.py list                     # 검토 대기 목록
    python scripts/review_feedback.py accept <신고 id> --note "공식 사내 도메인 확인"
    python scripts/review_feedback.py reject <신고 id> --note "피싱 확인됨, 신고 내용 틀림"

승인(accept)하면 신고 종류에 따라 반영한다.
- 실제로는 안전(actually_safe):
    · KISA 목록 때문에 피싱 확정됐던 경우 → resources/blacklist/exclusions.txt 에 호스트 추가
    · 모델 점수 때문이었던 경우 → data/feedback_labels.csv 에 정상(0)으로 추가 (재학습 때 반영)
- 실제로는 피싱(actually_phishing):
    · resources/blacklist/additions.txt 에 주소 추가 (다음 배포부터 바로 피싱 확정)
    · data/feedback_labels.csv 에 피싱(1)으로 추가
- 기타(other): 상태만 바꾼다

승인 전에 확인할 것 (checklist):
    1. 도메인 등록 정보(RDAP)와 인증서 기록으로 운영 주체가 맞는지
    2. 공식 기관·회사 누리집에 그 주소가 안내돼 있는지 (정상 주장일 때)
    3. KISA 보호나라 등 공개 신고 자료에 같은 주소가 있는지 (피싱 주장일 때)
    4. 같은 도메인으로 짧은 시간에 신고가 몰리지 않았는지 (조작 신고 의심)
"""

import argparse
import csv
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "ml_integration"))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(BACKEND / ".env")

from app import db  # noqa: E402
from app.services import blacklist  # noqa: E402

BLACKLIST_DIR = BACKEND / "resources" / "blacklist"
LABELS = ROOT / "data" / "feedback_labels.csv"
CLAIMS = {"actually_safe": "실제로는 안전", "actually_phishing": "실제로는 피싱", "other": "기타"}


def _without_query(url: str) -> str:
    """학습 라벨에는 '?' 뒤를 빼고 남긴다. 쿼리에는 개인정보가 들어 있는 경우가 많다."""
    return url.split("#", 1)[0].split("?", 1)[0]


def _append(path: Path, line: str) -> None:
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    if line.split("#", 1)[0].strip() in {l.split("#", 1)[0].strip() for l in text.splitlines()}:
        print(f"  이미 있음: {path.name}")
        return
    with path.open("a", encoding="utf-8") as f:
        f.write(("" if text.endswith("\n") or not text else "\n") + line + "\n")
    print(f"  추가: {path.relative_to(ROOT)} ← {line}")


def _add_label(url: str, label: int) -> None:
    LABELS.parent.mkdir(parents=True, exist_ok=True)
    new = not LABELS.exists()
    with LABELS.open("a", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        if new:
            writer.writerow(["url", "label", "reviewed_at"])
        writer.writerow([_without_query(url), label, date.today().isoformat()])
    print(f"  추가: {LABELS.relative_to(ROOT)} ← {'피싱' if label else '정상'}")


def cmd_list(args) -> None:
    items = db.list_feedback(args.status, args.limit)
    if not items:
        print(f"'{args.status}' 상태인 신고가 없습니다.")
        return
    for f in items:
        print(f"[{f['id']}] {f['created_at'][:16]}  판정 {f['verdict']} → 신고 '{CLAIMS.get(f['claim'], f['claim'])}'")
        print(f"    주소: {f['url']}")
        if f.get("comment"):
            print(f"    의견: {f['comment']}")
        if f.get("review_note"):
            print(f"    검토: {f['review_note']}")


def _find(feedback_id: str) -> dict:
    item = next((f for f in db.list_feedback("pending", 10_000) if f["id"] == feedback_id), None)
    if item is None:
        sys.exit("검토 대기 중인 신고에서 찾지 못했습니다. id를 확인하세요.")
    return item


def cmd_accept(args) -> None:
    item = _find(args.id)
    note = args.note or "승인"
    url = item["url"]
    host = blacklist._extract_host(url)
    today = date.today().isoformat()
    if item["claim"] == "actually_safe":
        if blacklist.check_blacklist(url).matched:
            _append(BLACKLIST_DIR / "exclusions.txt", f"{host}  # {today}, 사용자 신고 검토: {note}")
        _add_label(url, 0)
    elif item["claim"] == "actually_phishing":
        _append(BLACKLIST_DIR / "additions.txt", f"{_without_query(blacklist._normalize_url(url))}  # {today}, 사용자 신고 검토: {note}")
        _add_label(url, 1)
    db.review_feedback(item["id"], "accepted", note)
    print("승인했습니다. 블랙리스트 파일이 바뀌었다면 커밋·배포해야 서비스에 반영됩니다.")


def cmd_reject(args) -> None:
    item = _find(args.id)
    db.review_feedback(item["id"], "rejected", args.note or "거절")
    print("거절했습니다.")


def main() -> None:
    parser = argparse.ArgumentParser(description="판정 오류 신고 검토")
    sub = parser.add_subparsers(required=True)
    p = sub.add_parser("list", help="신고 목록")
    p.add_argument("--status", default="pending", choices=["pending", "accepted", "rejected"])
    p.add_argument("--limit", type=int, default=50)
    p.set_defaults(func=cmd_list)
    for name, func in (("accept", cmd_accept), ("reject", cmd_reject)):
        p = sub.add_parser(name)
        p.add_argument("id")
        p.add_argument("--note", help="검토 근거 (무엇을 확인했는지)")
        p.set_defaults(func=func)
    args = parser.parse_args()
    db.init_db()
    args.func(args)


if __name__ == "__main__":
    main()
