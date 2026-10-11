import json
import os

import joblib
import pandas as pd

from preprocess import extract_features

MODEL_DIR = os.environ.get("ML_MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))

_model = None
_scaler = None
_feature_cols = None
_report = None
_load_error = None


def _load_artifacts():
    global _model, _scaler, _feature_cols, _report, _load_error
    if _model is not None or _load_error is not None:
        return
    try:
        _model = joblib.load(os.path.join(MODEL_DIR, "best_model.joblib"))
        _scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.joblib"))
        with open(os.path.join(MODEL_DIR, "feature_columns.json"), encoding="utf-8") as f:
            _feature_cols = json.load(f)
        with open(os.path.join(MODEL_DIR, "model_report.json"), encoding="utf-8") as f:
            _report = json.load(f)
    except FileNotFoundError as e:
        _load_error = str(e)


_v2 = None


def _load_v2():
    global _v2
    if _v2 is None:
        path = os.path.join(MODEL_DIR, "url_model_v2.joblib")
        report = os.path.join(MODEL_DIR, "url_model_v2_report.json")
        if os.path.exists(path) and os.path.exists(report):
            with open(report, encoding="utf-8") as f:
                _v2 = {"model": joblib.load(path), "report": json.load(f)}
        else:
            _v2 = False
    return _v2 or None


def model_info() -> dict:
    """배포 환경에서 어떤 모델이 로드됐는지 확인하기 위한 정보 (/health와 시작 로그에 표시)."""
    import hashlib

    import numpy
    import scipy
    import sklearn

    # 배포와 로컬의 점수가 다를 때 라이브러리 버전부터 비교할 수 있게 함께 보여 준다
    info = {"sklearn": sklearn.__version__, "numpy": numpy.__version__, "scipy": scipy.__version__,
            "model": None, "sha256": None, "trained_at": None, "trained_sklearn": None}
    v2 = _load_v2()
    if v2 is None:
        _load_artifacts()
        info["model"] = "v1" if _load_error is None else "not_ready"
        return info
    path = os.path.join(MODEL_DIR, "url_model_v2.joblib")
    with open(path, "rb") as f:
        info["sha256"] = hashlib.sha256(f.read()).hexdigest()[:12]
    report = v2["report"]
    info.update(model="v2", trained_at=report.get("trained_at"), trained_sklearn=report.get("sklearn_version"))
    return info


def _predict_v2(v2: dict, url: str) -> dict:
    from url_features import calibrate, canonical_url

    raw = float(v2["model"].predict_proba([canonical_url(url)])[0][1]) * 100
    t = v2["report"]["thresholds"]
    risk_score = round(calibrate(raw, t["suspicious"], t["phishing"]), 2)
    label = "phishing" if risk_score >= 60 else "normal"
    return {"status": "ready", "risk_score": risk_score, "label": label}


def predict_model(url: str) -> dict:
    v2 = _load_v2()
    if v2 is not None:
        return _predict_v2(v2, url)
    _load_artifacts()
    if _load_error is not None:
        return {"status": "not_ready", "risk_score": None, "label": None}

    feats = extract_features(url)
    row = {col: feats.get(col, 0) for col in _feature_cols}
    X = pd.DataFrame([row], columns=_feature_cols)

    if _report.get("needs_scaling"):
        X = _scaler.transform(X)

    proba_phishing = float(_model.predict_proba(X)[0][1])
    risk_score = round(proba_phishing * 100, 2)
    label = "phishing" if proba_phishing >= 0.5 else "normal"

    return {"status": "ready", "risk_score": risk_score, "label": label}


if __name__ == "__main__":
    print(predict_model("http://secure-paypal-login.verify-account.tk"))
    print(predict_model("https://www.naver.com"))
