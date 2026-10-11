"""유사 사례 검색용 사례 목록(metadata.jsonl)을 v2 학습 데이터로 다시 만든다.

기존 metadata.jsonl은 PhiUSIIL에서 뽑은 것이라 정상 URL이 모두 'https://www.도메인' 형태(경로 없음)였다.
그래서 경로가 있는 정상 URL을 넣어도 비슷한 사례가 대부분 피싱으로 나왔다 (QA: 정상 입력의 88%).
ML v2와 같은 데이터(train_v2.csv, 형태 편향 제거)에서 라벨별로 같은 수를 뽑아 이 문제를 고친다.

사용법 (저장소 루트에서):
    python scripts/build_training_set.py          # data/train_v2.csv가 없을 때만
    python scripts/build_similar_cases.py         # backend/resources/vector_store/metadata.jsonl 덮어씀
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend" / "ml_integration"))

from url_features import split_url  # noqa: E402

TRAIN = ROOT / "data" / "train_v2.csv"
OUT = ROOT / "backend" / "resources" / "vector_store" / "metadata.jsonl"


def has_path(url: str) -> bool:
    p = split_url(url)
    return bool(p["path"].strip("/") or p["query"])


def main():
    parser = argparse.ArgumentParser(description="유사 사례 목록 다시 만들기")
    parser.add_argument("--per-label", type=int, default=2500, help="라벨별 사례 수")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if not TRAIN.exists():
        sys.exit(f"{TRAIN}이 없습니다. 먼저 scripts/build_training_set.py를 실행하세요.")

    df = pd.read_csv(TRAIN)
    df = df[df.url.astype(str).str.len().between(4, 300)]
    # 한 도메인이 여러 번 나오지 않게 도메인당 1건만 남긴다
    df = df.sample(frac=1, random_state=args.seed).drop_duplicates("domain")
    df["has_path"] = [has_path(u) for u in df.url]

    parts = []
    for label in (0, 1):
        pool = df[df.label == label]
        # 경로 있는 URL과 없는 URL을 반반씩 뽑아 형태가 한쪽으로 쏠리지 않게 한다
        for flag in (True, False):
            sub = pool[pool.has_path == flag]
            parts.append(sub.sample(n=min(len(sub), args.per_label // 2), random_state=args.seed))
    out = pd.concat(parts).sample(frac=1, random_state=args.seed)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        for r in out.itertuples():
            name = "피싱" if r.label == 1 else "정상"
            f.write(json.dumps({"url": r.url, "label": int(r.label), "description": f"{name} 사례 ({r.source})"},
                               ensure_ascii=False) + "\n")

    print(f"저장: {OUT} ({len(out)}건)")
    for label, name in ((0, "정상"), (1, "피싱")):
        sub = out[out.label == label]
        print(f"  {name} {len(sub)}건 | 경로 있음 {sub.has_path.mean():.0%} | 출처 {sub.source.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
