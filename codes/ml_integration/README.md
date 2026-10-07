# ML 데이터 정제 스크립트 (성주 작업분)

## 사용법
```bash
pip install pandas
python preprocess.py --input <원본_데이터셋.csv> --output features_output.csv
```
- 원본 CSV의 URL/라벨 컬럼명이 다르면 `--url-col`, `--label-col`로 지정
  (예: `--url-col URL --label-col label`)
- 라벨은 1=피싱, 0=정상으로 자동 통일 (phishing/legitimate/bad/good 등 텍스트 라벨도 인식)

### ⚠️ UCI PHIUSIIL 데이터셋을 쓸 때는 반드시 `--invert-label` 추가
UCI 공식 데이터 카드 확인 결과, PHIUSIIL 원본 라벨은 **1=정상(legitimate), 0=피싱(phishing)**
으로 되어 있어 우리 프로젝트 표준(1=피싱, 0=정상)과 정반대입니다. 그대로 돌리면 정상/피싱이
뒤바뀌므로, UCI 원본 CSV를 넣을 때는 꼭 이 옵션을 붙이세요:
```bash
python preprocess.py --input PhiUSIIL_Phishing_URL_Dataset.csv --output features_output.csv \
  --url-col URL --label-col label --invert-label
```
(`--invert-label` 적용 여부와 결과는 `test_invert.csv` 샘플로 검증 완료)

## 정제 처리 내용
- 결측치/빈 URL 제거, 중복 URL 제거
- 라벨 표기 통일 (1=피싱, 0=정상)

## 추출 특징 (24개)
| 구분 | 특징 |
|---|---|
| 길이 | url_length, host_length, path_length, query_length |
| 구조 | subdomain_count, count_dash/at/dot/equal/www |
| 비율 | special_char_ratio, digit_ratio |
| 위험 신호 | is_ip_domain, has_punycode, is_shortener, suspicious_keyword_count |
| 복잡도 | url_entropy, path_entropy, host_entropy |
| 패턴 | top_3gram_1~3 (문자 3-gram 최빈값) |

## 확인 필요 사항
- UCI PHIUSIIL 데이터셋을 실제로 돌릴 때, 원본 라벨 컬럼명과 0/1 방향(데이터 카드 기준)을 확인 후 필요시 `normalize_label()` 함수 조정 필요
- 샘플 10건(정상 5 / 피싱 5)으로 동작 검증 완료 (`sample_test.csv`, `features_output.csv` 첨부)

## 다음 단계 제안
- 이 출력(features_output.csv)을 기반으로 분류 모델(로지스틱 회귀 등) 학습 가능
- top_3gram 컬럼은 참고용이며, 실제 모델 학습 시 TF-IDF/CountVectorizer로 별도 벡터화 필요

---

## ML 모델 학습 (train_model.py)
```bash
python train_model.py --input features_output.csv --output-dir models
```
- Logistic Regression / Random Forest / XGBoost 3종을 모두 학습 후 ROC-AUC 기준 best model 자동 선택
- 결과물: `models/best_model.joblib`, `models/scaler.joblib`, `models/feature_columns.json`, `models/model_report.json`
- **주의**: 지금 레포에 있는 `features_output.csv`는 샘플 10건짜리 검증용이라 실제 학습에는
  UCI PHIUSIIL 전체 데이터셋으로 만든 features_output.csv가 필요합니다. 전체 데이터셋 CSV를 받으면
  `python preprocess.py --input PhiUSIIL_Phishing_URL_Dataset.csv --output features_output_full.csv --url-col URL --label-col label --invert-label`
  로 먼저 전처리한 뒤 train_model.py를 돌리면 됩니다.

## 최종 판정 규칙 (risk_judge.py)
팀 합의(10/02) 기준 verdict/confidence/risk_score/risk_level 산출 로직:
1. 블랙리스트(KISA) 매치 시 즉시 `phishing` 확정 (risk_score=100)
2. 미매치 시 RAG 점수(+ML 연동 후엔 ML 점수) 가중평균으로 risk_score 산출 (ML 연동 전까지 RAG 100% 가중치)
3. risk_level: 0-30 safe / 30-60 caution / 60-85 warning / 85-100 danger
```bash
python risk_judge.py   # 예시 3건 출력
```

## ML 모델 연동 (model_integration.py)
FastAPI 백엔드에서 `model: {status, risk_score, label}` 필드를 채울 때 사용.
```python
from model_integration import predict_model
result = predict_model(url)  # {'status': 'ready'|'not_ready', 'risk_score': float|None, 'label': str|None}
```
- 학습된 모델(`models/`)이 없으면 `status: "not_ready"`로 안전하게 반환 (프론트 null 처리 그대로 호환)
