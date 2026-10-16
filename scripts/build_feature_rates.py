"""학습 원본 데이터에서 특징별로 피싱·정상 URL에 나타난 건수를 세어
resources/reference/feature_rates.json에 저장한다.

실행 (저장소 루트에서):
    python scripts/build_feature_rates.py

입력 (저장소 루트의 data/ 폴더, git에는 올리지 않음):
    - PhiUSIIL_Phishing_URL_Dataset.csv  (label 1 = 정상, 0 = 피싱)
    - 한국인터넷진흥원_피싱사이트 URL_*.csv  (모두 피싱)

탐지 결과는 서비스와 같은 detections.analyze()로 만들고, 같은 findings.classify()로 분류한다.
그래서 화면에 보이는 특징과 통계가 정확히 같은 기준이다.
평판 신호(등록일·인증서)는 외부 조회가 필요해 여기서 계산하지 않는다 (설명만 보여 준다).
"""

import glob
import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "ml_integration"))

from app.services import detections, findings  # noqa: E402

DATA = ROOT / "data"
OUT = BACKEND / "resources" / "reference" / "feature_rates.json"


def _read(path: str) -> pd.DataFrame:
    try:
        return pd.read_csv(path, encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv(path, encoding="cp949")


def load() -> tuple[list[str], list[str]]:
    phiusiil = pd.read_csv(DATA / "PhiUSIIL_Phishing_URL_Dataset.csv", usecols=["URL", "label"])
    normal = phiusiil.loc[phiusiil.label == 1, "URL"]
    phishing = [phiusiil.loc[phiusiil.label == 0, "URL"]]
    kisa_files = [f for f in glob.glob(str(DATA / "*.csv")) if "PhiUSIIL" not in f and "sample" not in f]
    for f in kisa_files:
        df = _read(f)
        if "홈페이지주소" in df.columns:
            phishing.append(df["홈페이지주소"])
    phishing = pd.concat(phishing)
    clean = lambda s: list(dict.fromkeys(str(u).strip() for u in s.dropna() if str(u).strip()))  # noqa: E731
    return clean(normal), clean(phishing)


def count(urls: list[str]) -> tuple[Counter, int]:
    counter, total = Counter(), 0
    for url in urls:
        try:
            result = detections.analyze(url)
        except Exception:
            continue
        total += 1
        keys = set()
        for detection in result.values():
            for reason in (detection or {}).get("reasons", []):
                feature = findings.classify(reason)
                if feature:
                    keys.add(feature["key"])
        counter.update(keys)
    return counter, total


def main() -> None:
    normal, phishing = load()
    normal_counts, normal_total = count(normal)
    phishing_counts, phishing_total = count(phishing)
    keys = sorted(set(normal_counts) | set(phishing_counts))
    data = {
        "created": date.today().isoformat(),
        "source_label": "학습 원본 데이터 (PhiUSIIL 공개 데이터셋, KISA 피싱 사이트 URL)",
        "phishing_total": phishing_total,
        "normal_total": normal_total,
        "note": "특징별로 피싱·정상 URL 중 몇 건에서 나타났는지. 비율은 각 집단 안에서 계산한다.",
        "features": {k: {"phishing": phishing_counts[k], "normal": normal_counts[k]} for k in keys},
    }
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"피싱 {phishing_total:,}건, 정상 {normal_total:,}건 → {OUT}")
    for k in keys:
        p, n = phishing_counts[k], normal_counts[k]
        print(f"  {k:18} 피싱 {p:>6} ({p / phishing_total:6.2%})  정상 {n:>6} ({n / normal_total:6.2%})")


if __name__ == "__main__":
    main()
