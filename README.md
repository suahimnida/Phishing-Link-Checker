# Phishing Site Analyzer — Frontend

AI 기반 피싱 사이트 분석 서비스의 프론트엔드입니다.

사용자가 URL을 입력하면 분석 과정을 보여주고, 분석 결과와 분석 기록을 확인할 수 있는 웹 인터페이스를 제공합니다.

---

## 1. 프로젝트 개요

### 서비스 목적

사용자가 입력한 URL을 대상으로 URL 구조, 도메인, 웹페이지 콘텐츠 등의 보안 정보를 분석하고, AI Agent가 분석 결과를 종합하여 피싱 가능성과 위험 근거를 제공하는 웹 보안 분석 서비스입니다.

### 프론트엔드 역할

* URL 입력 및 분석 요청
* 분석 공개/비공개 설정
* URL 분석 진행 화면
* 분석 결과 화면
* 분석 기록 조회
* 프로젝트 분석 방법 및 데이터셋/ML 모델 정보 제공
* 백엔드 API와의 데이터 연동

> AI Agent, ML 모델, RAG, 데이터 처리 등의 실제 분석 로직은 백엔드에서 담당합니다.

---

# 2. 기술 스택

* React
* Vite
* JavaScript
* CSS
* REST API

---

# 3. 현재 프론트엔드 구조

```text
frontend/
├── src/
│   ├── components/
│   ├── pages/
│   │   ├── Home/
│   │   ├── Analysis/
│   │   ├── Result/
│   │   ├── History/
│   │   ├── DetectionMethods/
│   │   ├── Dataset/
│   │   └── MLModel/
│   ├── assets/
│   ├── services/
│   │   └── api.js
│   ├── styles/
│   │   └── global.css
│   ├── App.jsx
│   ├── App.css
│   └── main.jsx
├── public/
├── package.json
├── package-lock.json
├── vite.config.js
└── README.md
```

---

# 4. 현재 구현 상태

## ✅ 완료

### 기본 프론트엔드

* [x] React + Vite 프로젝트 구성
* [x] 기본 페이지 구조 구성
* [x] 공통 레이아웃 구성
* [x] 다크 테마 UI 구성
* [x] 사이드바 네비게이션 구성

### 메인 / 대시보드

* [x] URL 입력 UI
* [x] URL 분석 버튼
* [x] 분석 대상 URL 표시
* [x] 최근 분석 기록 영역
* [x] 공개 / 비공개 분석 선택 UI

### URL 분석

* [x] 분석 대상 URL 표시
* [x] 분석 진행 화면
* [x] URL 구조 분석 단계
* [x] URL 통계 분석 단계
* [x] 도메인 분석 단계
* [x] HTML 분석 단계
* [x] 페이지 콘텐츠 분석 단계
* [x] AI Agent 분석 단계
* [x] 분석 서버 연결 오류 UI

### 프로젝트 정보

* [x] 탐지 방법 페이지
* [x] 데이터셋 페이지
* [x] ML 모델 페이지

### 분석 공개 설정

* [x] 비공개 분석
* [x] 공개 분석
* [x] 공개 여부를 API 요청에 포함
* [x] Client ID 기반 API 요청 구조

### Git

* [x] 프론트엔드 전용 `frontend` 브랜치 구성
* [x] 프론트엔드 변경사항 커밋
* [x] 원격 `frontend` 브랜치 Push

---

# 5. 현재 API 연동 상태

프론트엔드에서는 백엔드 API와 연결하기 위한 기본 구조가 구현되어 있습니다.

API 서버:

```text
http://localhost:8000
```

현재 사용 예정 API:

```text
POST /api/v1/clients
POST /api/v1/analyses
GET  /api/v1/analyses/{analysis_id}
GET  /api/v1/analyses?scope=mine
GET  /api/v1/analyses?scope=public
```

Client ID는 브라우저의 `localStorage`에 저장합니다.

```text
phishingClientId
```

분석 요청 시:

```http
X-Client-Id: {client_id}
```

를 사용합니다.

---

# 6. 현재 백엔드 연결 상태

현재 백엔드와의 실제 통합 테스트는 아직 완료되지 않았습니다.

현재 프론트엔드에서 분석 요청을 보내도록 구현되어 있지만, 백엔드 서버가 정상적으로 실행되는 환경에서 최종 테스트가 필요합니다.

### 현재 확인된 문제

백엔드 실행 시:

```text
ERROR: Error loading ASGI app. Could not import module "app.main".
```

현재 로컬 `backend/app/`에 `main.py`가 존재하지 않는 상태여서 서버 실행이 되지 않았습니다.

따라서 현재는 프론트엔드에서 실제 API 요청 → 분석 결과 반환 → Result 페이지 이동까지의 전체 흐름을 확인하지 못한 상태입니다.

> 백엔드 코드는 프론트엔드에서 수정하지 않습니다.
> 백엔드 정상 실행 및 API 제공은 백엔드 담당 영역입니다.

---

# 7. 앞으로 구현해야 할 것

## 🔴 우선 구현

### Result 페이지

분석 요청이 완료되면 분석 결과를 표시해야 합니다.

표시할 주요 정보:

* [ ] 최종 위험도
* [ ] 피싱 여부 / 판정
* [ ] Risk Score
* [ ] 분석 대상 URL
* [ ] Blacklist 검사 결과
* [ ] URL 분석 결과
* [ ] 도메인 분석 결과
* [ ] HTML / 콘텐츠 분석 결과
* [ ] ML 분석 결과
* [ ] AI Agent 분석 결과
* [ ] RAG 기반 근거
* [ ] 권장 대응 방법

---

## 🟠 History 페이지 API 연동

현재 History는 프론트엔드에서 임시 데이터를 사용하는 구조입니다.

백엔드 연동 후 다음과 같이 변경합니다.

```text
GET /api/v1/analyses?scope=mine
```

분석 목록:

```text
ID
URL
판정
분석 시간
```

각 기록을 선택하면:

```text
GET /api/v1/analyses/{analysis_id}
```

를 호출하여 상세 결과를 표시합니다.

### 구현 예정

* [ ] `getMyAnalyses()` API 함수 추가
* [ ] `getAnalysis(id)` API 함수 추가
* [ ] History 페이지 API 연동
* [ ] 분석 기록 클릭 → 상세 결과 이동
* [ ] 실제 백엔드 결과 표시
* [ ] localStorage 기반 임시 기록 제거

> 현재 백엔드에는 분석 삭제 API가 없으므로, 삭제 기능은 실제 API가 제공된 이후 결정합니다.

---

# 8. Home 최근 분석 기록

현재 Home의 최근 분석 기록도 임시 데이터 기반입니다.

백엔드 연동 후:

```text
GET /api/v1/analyses?scope=mine
```

을 이용하여 실제 분석 기록을 가져옵니다.

### 구현 예정

* [ ] 최근 분석 기록 API 연동
* [ ] 최신 분석 순으로 표시
* [ ] 기록 클릭 → Result 페이지 이동
* [ ] 실제 분석 결과와 연결

---

# 9. Result 데이터 구조

백엔드에서 제공되는 분석 결과를 기반으로 UI를 구성합니다.

현재 예상되는 주요 데이터:

```text
{
  id,
  ai_analysis,
  extracted_features,
  similar_cases,
  blacklist,
  model
}
```

예상 구조:

### blacklist

```text
matched
match_type
source
```

### model

```text
status
risk_score
label
```

### extracted_features

URL 및 페이지 분석을 통해 추출된 특징

### similar_cases

RAG를 통해 검색된 유사 피싱 사례

### ai_analysis

AI Agent가 분석 결과를 종합한 설명

> 실제 연동 시 백엔드 API의 최종 응답 구조를 기준으로 프론트엔드를 수정합니다.

---

# 10. 최종 사용자 흐름

```text
[Home]
   │
   │ URL 입력
   │ 공개 / 비공개 선택
   ▼
[Analysis]
   │
   │ 백엔드 API 요청
   │
   │ URL 분석
   │ ML 분석
   │ HTML / 콘텐츠 분석
   │ RAG 검색
   │ AI Agent 종합
   ▼
[Result]
   │
   ├── 위험도
   ├── 피싱 판정
   ├── 분석 근거
   ├── 유사 사례
   ├── AI 분석
   └── 대응 방법
   │
   ▼
[History]
   │
   └── 이전 분석 결과 조회
```

---

# 11. 프론트엔드 개발 순서

백엔드가 준비되지 않은 동안:

```text
1. Result 페이지 UI 구현
        ↓
2. Result 페이지 Mock 데이터 연결
        ↓
3. History UI 정리
        ↓
4. Home 최근 기록 UI 정리
        ↓
5. 실제 API 응답에 맞춰 데이터 구조 연결
        ↓
6. 백엔드 정상 실행 후 통합 테스트
        ↓
7. 오류 / 예외 상황 처리
        ↓
8. 최종 UI 수정
```

---

# 12. 백엔드 통합 테스트 체크리스트

백엔드가 정상적으로 실행된 이후 확인합니다.

### 기본 연결

* [ ] `POST /api/v1/clients` 정상 동작
* [ ] Client ID 발급 확인
* [ ] Client ID localStorage 저장 확인

### 분석

* [ ] URL 분석 요청 성공
* [ ] 공개 분석 요청 성공
* [ ] 비공개 분석 요청 성공
* [ ] 분석 결과 정상 반환
* [ ] Result 페이지 자동 이동
* [ ] 결과 데이터 정상 표시

### 기록

* [ ] 내 분석 기록 조회
* [ ] 공개 분석 기록 조회
* [ ] 특정 분석 상세 조회
* [ ] History → Result 이동

### 예외 처리

* [ ] 잘못된 URL
* [ ] 서버 연결 실패
* [ ] 분석 실패
* [ ] 존재하지 않는 분석 ID
* [ ] 비공개 분석에 대한 권한 없는 접근

---

# 13. 디자인 방향

전체 UI는 보안 분석 서비스의 느낌을 유지하면서 정보 확인이 쉽도록 구성합니다.

### 기본 색상

```text
Background   #0a0c0d
Surface      #131617
Surface      #1b1f20
Border       #292e2f
Text         #f4f7f6
Muted        #899291
Mint         #42e8c4
Danger       #ff4d5a
Warning      #ffb84d
```

### UI 방향

* Dark UI
* 보안 서비스 / 분석 도구 느낌
* 정보 중심 레이아웃
* 분석 결과를 단계적으로 확인할 수 있는 구조
* Mint → 일반적인 강조
* Red → 피싱 / 위험 경고
* 과도한 장식보다 분석 데이터 가독성 우선

참고 서비스:

* VirusTotal
* ScamAdviser

단, UI를 그대로 복제하지 않고 프로젝트에 맞게 재구성합니다.

---

# 14. 현재 작업 범위

### Frontend 담당

```text
UI
페이지
컴포넌트
사용자 흐름
API 연결
Result 표시
History 표시
예외 상태 표시
```

### Backend / AI 담당

```text
URL 분석
ML 모델
Blacklist
RAG
AI Agent
분석 결과 생성
DB 저장
API 서버
```

프론트엔드는 백엔드의 분석 로직을 직접 구현하지 않고, 제공되는 API 결과를 화면에 표시하는 역할을 담당합니다.
