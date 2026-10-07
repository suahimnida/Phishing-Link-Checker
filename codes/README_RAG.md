# 피싱 URL 판별 RAG 웹 서비스

`preprocess.py`로 만든 특징 데이터를 벡터 스토어에 넣고,
새로운 URL이 들어오면 유사한 과거 사례를 검색해서(Retrieval)
그 사례를 근거로 Claude가 최종 판정을 내리는(Generation) 구조입니다.

## 파일 구성

- `preprocess.py`: URL 특징 추출 / 데이터 정제
- `build_vector_store.py`: 특징 CSV → FAISS 벡터 스토어 생성
- `rag_app.py`: FastAPI 웹 서비스 (RAG 판정 API)
- `requirements.txt`: 필요 패키지 목록

**주의**: phiusiil+phishing+url+dataset.zip 을 다운받아 나머지 파일들과 같은 위치에 압축해제하여 아래의 방법을 따라서 실행

## 실행 순서

### 1) 패키지 설치

```bash
pip install -r requirements.txt --break-system-packages
```

### 2) 특징 데이터 생성 (preprocess.py)

```bash
python preprocess.py --input PhiUSIIL_Phishing_URL_Dataset.csv --output features_output.csv --invert-label
```

### 3) 벡터 스토어 구축

```bash
python build_vector_store.py --input features_output.csv --index-dir vector_store
```
* 여기서 좀 매우 많이 오래걸렸어요.....한 30분 정도 걸린거 같습니다..;;;;

시간 지체로 인해 빠른 확인을 희망하시는 경우
Ctrl + C를 하여 중단하신 후 아래의 명령어를 따라 실행해주시고
오래 걸려도 데이터베이스가 모두 구축 되기까지 기다리실 경우에는 아래의 내용은 무시하고
4 단계로 넘어가주세요
```
python -c "import pandas as pd; df = pd.read_csv('features_output.csv');
df.sample(20000, random_state=42).to_csv('features_sample.csv', index=False)"
python build_vector_store.py --input features_sample.csv --index-dir vector_store
```

### 4) Anthropic API 키 설정

```bash
$env:ANTHROPIC_API_KEY="sk-ant-(개인 디코 메시지로 보낸 API 키)"
```

### 5) 웹 서비스 실행

```bash
uvicorn rag_app:app --reload
```

### 6) 테스트

```bash
curl -X POST http://localhost:8000/check \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"http://paypal-verify-account.tk/login\"}"
```

응답 예시:

```json
{
  "url": "http://paypal-verify-account.tk/login",
  "verdict": "phishing",
  "confidence": 0.92,
  "reason": "검색된 유사 사례 대부분이 피싱으로 라벨링되어 있고, 브랜드명(paypal)과 의심 키워드(verify, login)가 도메인/경로에 포함되어 있어 피싱 가능성이 높습니다.",
  "extracted_features": { ... },
  "similar_cases": [
    {"url": "...", "label": 1, "similarity": 0.87},
    ...
  ]
}
```

## 동작 원리 요약

1. **특징 추출**: 입력 URL을 `preprocess.py`의 `extract_features()`로 분석 (엔트로피, 의심 키워드, IP 도메인 여부 등)
2. **설명 텍스트 변환**: 특징 딕셔너리를 사람이 읽을 수 있는 문장으로 변환
3. **검색(Retrieval)**: 이 문장을 임베딩해 FAISS 인덱스에서 코사인 유사도가 높은 과거 URL(피싱/정상 라벨 포함) 상위 K개를 검색
4. **생성(Generation)**: 검색된 사례들을 근거로 Claude에게 "이 URL이 피싱인지 정상인지, 왜 그런지"를 JSON 형식으로 요청
5. 판정 결과 + 근거 + 검색된 유사 사례를 함께 JSON으로 반환 → 웹 프론트엔드에서 그대로 표시 가능

