import logging
import sys
from pathlib import Path

_ML_DIR = Path(__file__).resolve().parents[2] / "ml_integration"
if str(_ML_DIR) not in sys.path:
    sys.path.append(str(_ML_DIR))

import url_explain 

logger = logging.getLogger(__name__)


def build(url: str, model_used: bool) -> dict | None:
    result = {"model": None, "reference": []}
    try:
        result["reference"] = url_explain.reference(url)
    except Exception:
        logger.exception("참고 지표 계산 실패: %s", url)

    if model_used:
        try:
            from model_integration import _load_v2

            from url_features import canonical_url

            v2 = _load_v2()
            if v2 is not None:
                # 점수 계산과 같은 입력(스킴·호스트 소문자)으로 기여도를 계산해야 숫자가 맞는다
                result["model"] = url_explain.explain_model(v2["model"], canonical_url(url))
        except Exception:
            logger.exception("모델 기여도 계산 실패: %s", url)

    return result if result["model"] or result["reference"] else None
