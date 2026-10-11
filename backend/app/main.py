import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     [%(name)s] %(message)s")
logger = logging.getLogger(__name__)


class _RedactShareToken(logging.Filter):
    """접속 로그에 공유 토큰이 남지 않게 가린다 (?share=토큰, /shared/토큰). 토큰이 곧 열람 권한이다."""

    _patterns = (re.compile(r"(share=)[^&\s\"]+"), re.compile(r"(/shared/)[^?\s\"]+"))

    def filter(self, record: logging.LogRecord) -> bool:
        if record.args:
            record.args = tuple(self._redact(a) if isinstance(a, str) else a for a in record.args)
        if isinstance(record.msg, str):
            record.msg = self._redact(record.msg)
        return True

    def _redact(self, text: str) -> str:
        for pattern in self._patterns:
            text = pattern.sub(r"\1***", text)
        return text


logging.getLogger("uvicorn.access").addFilter(_RedactShareToken())
for _handler in logging.getLogger().handlers:  # 앱 로그(app.*)도 같은 처리
    _handler.addFilter(_RedactShareToken())

from app import db 
from app.schemas import (
    AiAnalysis,
    AnalysisListResponse,
    AnalysisRequest,
    AnalysisResponse,
    ClientResponse,
    Detections,
    HealthResponse,
    ModelResult,
    RagReference,
    ReportResponse,
    DeleteAnalysisRequest,
    OwnerCheckRequest,
    ShareResponse,
    VisibilityRequest,
)
from app.services import (
    allowlist,
    blacklist,
    explain,
    guides,
    homograph,
    owner,
    reputation,
    detections,
    followup,
    model,
    rag,
    report,
    report_pdf,
    verdict,
)
from app.services.llm_openai import OpenAIJsonClient
from app.services.shorteners import is_shortener_host


def _model_info() -> dict:
    try:
        from model_integration import model_info

        return model_info()
    except Exception:
        logger.exception("모델 정보 확인 실패")
        return {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    started = time.perf_counter()
    blacklist.load_blacklist()
    try:
        db.init_db()
    except Exception:
        logger.exception("DB 연결 실패: %s", db.describe())
        raise
    logger.info("분석 기록 저장소: %s", db.describe())
    try:
        rag.load_rag()
    except Exception:
        logger.exception("RAG 로드 실패: RAG 없이 서버를 실행합니다")
    info = _model_info()
    logger.info(
        "ML 모델: %s (sha256 %s, 학습 %s, 학습 시 scikit-learn %s / 현재 %s)",
        info.get("model"), info.get("sha256"), info.get("trained_at"), info.get("trained_sklearn"), info.get("sklearn"),
    )
    if info.get("trained_sklearn") and info.get("sklearn") != info.get("trained_sklearn"):
        logger.warning("scikit-learn 버전이 학습 때와 다릅니다. 점수가 달라질 수 있으니 requirements.txt를 확인하세요.")
    logger.info("서버 준비 완료: %.2f초", time.perf_counter() - started)
    yield


app = FastAPI(title="피싱 URL 분석 API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=(os.environ.get("CORS_ORIGINS") or "http://localhost:5173").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


def _is_db_error(error: Exception) -> bool:
    import sqlite3

    if isinstance(error, sqlite3.Error):
        return True
    try:
        import psycopg

        return isinstance(error, psycopg.Error)
    except ImportError:
        return False


@app.exception_handler(Exception)
async def _unhandled(request: Request, error: Exception):
    # DB 장애면 날것의 500 대신 "잠시 후 다시" 안내를 돌려준다 (QA)
    if _is_db_error(error):
        logger.error("DB 오류로 요청 실패: %s %s (%s)", request.method, request.url.path, type(error).__name__)
        return JSONResponse(status_code=503, content={"detail": "저장소에 연결할 수 없습니다. 잠시 후 다시 시도해 주세요."})
    logger.exception("처리하지 못한 오류: %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "서버 오류가 발생했습니다."})


def _llm_status() -> dict:
    """LLM 환경변수가 설정됐는지만 알려 준다 (값은 절대 내보내지 않는다).

    Render 대시보드에 접근할 수 없는 팀원도 '설명이 template으로 나오는 게 키가 없어서인지' 확인할 수 있다.
    """
    def configured(prefix: str) -> bool:
        return bool(os.environ.get(f"{prefix}_AUTH_TOKEN") or os.environ.get(f"{prefix}_API_KEY"))

    return {
        "claude": {"configured": configured("ANTHROPIC"), "model": rag.CLAUDE_MODEL,
                   "loaded": bool((rag._state or {}).get("client"))},
        "followup": {"configured": configured("FOLLOWUP_OPENAI"),
                     "model": os.environ.get("FOLLOWUP_OPENAI_MODEL") or followup.DEFAULT_FOLLOWUP_MODEL or None},
        "report": {"configured": configured("REPORT_OPENAI"),
                   "model": os.environ.get("REPORT_OPENAI_MODEL") or report.DEFAULT_REPORT_MODEL or None},
        "database": db.describe().split(" ")[0],
        "cors_origins": [o for o in (os.environ.get("CORS_ORIGINS") or "http://localhost:5173").split(",") if o],
    }


@app.get("/health", response_model=HealthResponse)
def health():
    # 배포 환경에서 어떤 모델·라이브러리 버전과 LLM 설정으로 돌고 있는지 Render 로그 없이도 확인할 수 있게 한다
    return HealthResponse(status="ok", model=_model_info() or None, llm=_llm_status())


def _client_key(client_id: uuid.UUID | None) -> str | None:
    return str(client_id) if client_id else None


@app.post("/api/v1/clients", response_model=ClientResponse)
def create_client():
    return ClientResponse(client_id=str(uuid.uuid4()))

_background = ThreadPoolExecutor(max_workers=8)
# 평판 조회(외부 서비스)를 기다리는 최대 시간. 넘으면 평판 없이 결과를 돌려준다.
# 예전 10초는 외부 서비스가 멈추면 분석마다 10초씩 늦어졌다 (QA: 10.5초)
REPUTATION_WAIT = float(os.environ.get("REPUTATION_WAIT_SECONDS") or 4)


@app.post("/api/v1/analyses", response_model=AnalysisResponse)
def create_analysis(request: AnalysisRequest, x_client_id: uuid.UUID | None = Header(None)):
    started = time.perf_counter()
    blacklist_result = blacklist.check_blacklist(request.url)
    allowlist_result = allowlist.check(request.url)
    shortener = is_shortener_host(blacklist._extract_host(request.url))
    homograph_result = homograph.check(request.url, allowlist.domains())
    reputation_job = _background.submit(reputation.lookup, request.url) if reputation.enabled() else None
    if blacklist_result.matched:
        rag_result = rag.RagResult()
        model_result = ModelResult(status="not_ready")
    else:
        rag_result = rag.similar(request.url)
        model_result = model.predict(request.url)

    try:
        detection_result = Detections(**detections.analyze(request.url))
    except Exception:
        logger.exception("탐지 결과 생성 실패: %s", request.url)
        detection_result = Detections()
    if reputation_job is not None:
        try:
            detection_result.reputation = reputation.to_detection(reputation_job.result(timeout=REPUTATION_WAIT))
        except Exception:
            logger.exception("평판 신호 조회 실패: %s", request.url)

    decided = verdict.decide(blacklist_result, model_result, allowlist_result,
                             shortener=shortener, homograph=homograph_result)
    explanation = explain.build(request.url, model_used=model_result.status == "ready")

    evidence = guides.build_evidence(
        verdict=decided["verdict"], risk_score=decided["risk_score"], blacklist=blacklist_result,
        allowlist=allowlist_result, model=model_result, explanation=explanation,
        detections=detection_result, similar_cases=rag_result.similar_cases,
        shortener=shortener, homograph=homograph_result,
    )
    found = guides.retrieve(guides.evidence_tags(request.url, decided["verdict"], evidence), evidence)
    written = None if blacklist_result.matched else rag.compose(evidence, found)
    ai_analysis = AiAnalysis(
        summary=written or guides.template_explanation(decided["verdict"], evidence, found),
        written_by=rag.CLAUDE_MODEL if written else "template",
        evidence=evidence,
        guides=found,
    )

    result = AnalysisResponse(
        id=str(uuid.uuid4()),
        status="completed",
        url=request.url,
        is_public=request.is_public,
        **decided,
        detections=detection_result,
        ai_analysis=ai_analysis,
        extracted_features=rag_result.features,
        # 공식 도메인은 유사 사례를 보여 주지 않는다. 사례 검색은 URL 특징 21개 기준이라
        # 'www.coupang.com' 같은 홈페이지도 피싱 사례와 가깝게 나와 정상 판정과 반대되는 인상을 준다 (QA)
        similar_cases=[] if allowlist_result.matched and not blacklist_result.matched else rag_result.similar_cases,
        blacklist=blacklist_result,
        allowlist=allowlist_result,
        explanation=explanation,
        owner_name=owner.mask_name(request.owner_name) if request.owner_name else None,
        rag=RagReference(
            matched=bool(found),
            source=[f"{g['title']} ({g['source']})" for g in found],
        ),
        model=model_result,
    )

    owner_row = None
    if request.owner_name and request.owner_secret:
        owner_row = (result.owner_name, owner.hash_secret(request.owner_secret), owner.hash_name(request.owner_name))
    try:
        db.save_analysis(result, _client_key(x_client_id), owner_row)
    except Exception:
        # DB 장애에도 분석 결과는 돌려준다. 다만 저장되지 않은 결과라는 것을 알려,
        # 프론트가 공유·공개 전환·리포트 버튼을 숨기게 한다 (QA: 저장 안 된 id로 요청하면 전부 404)
        logger.exception("분석 기록 저장 실패 (분석 id %s)", result.id)
        result.saved = False
    result.viewer = "owner"
    logger.info("분석 완료: %.2f초, 판정 %s, 설명 %s", time.perf_counter() - started, result.verdict, ai_analysis.written_by)
    return result


@app.get("/api/v1/analyses", response_model=AnalysisListResponse)
def list_analyses(
    scope: Literal["mine", "public"],
    limit: int = Query(20, ge=1, le=100),
    x_client_id: uuid.UUID | None = Header(None),
):
    if scope == "public":
        return AnalysisListResponse(items=db.list_analyses(limit))
    if x_client_id is None:
        raise HTTPException(status_code=400, detail="X-Client-Id 헤더가 필요합니다.")
    return AnalysisListResponse(items=db.list_analyses(limit, _client_key(x_client_id)))


@app.get("/api/v1/analyses/{analysis_id}", response_model=AnalysisResponse)
def read_analysis(analysis_id: str, x_client_id: uuid.UUID | None = Header(None)):

    record = db.get_analysis_access(analysis_id, _client_key(x_client_id))
    if record is None:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")
    result, _, owner = record
    return _for_viewer(result, "owner" if owner else "public")


def _for_viewer(result: AnalysisResponse, viewer: str) -> AnalysisResponse:
    result.viewer = viewer

    result.share_token = db.get_share_token(result.id) if viewer == "owner" else None
    return result


def _require_owner(analysis_id: str, x_client_id) -> str:
    client_key = _client_key(x_client_id)
    if not db.is_owner(analysis_id, client_key):
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")
    return client_key


@app.patch("/api/v1/analyses/{analysis_id}/visibility", response_model=AnalysisResponse)
def change_visibility(analysis_id: str, request: VisibilityRequest, x_client_id: uuid.UUID | None = Header(None)):
    result = db.set_visibility(analysis_id, _client_key(x_client_id), request.is_public)
    if result is None:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")
    return _for_viewer(result, "owner")


@app.post("/api/v1/analyses/{analysis_id}/share", response_model=ShareResponse)
def create_share_link(analysis_id: str, x_client_id: uuid.UUID | None = Header(None)):
    _require_owner(analysis_id, x_client_id)
    return ShareResponse(token=db.create_share(analysis_id))


@app.delete("/api/v1/analyses/{analysis_id}/share", response_model=ShareResponse)
def delete_share_link(analysis_id: str, x_client_id: uuid.UUID | None = Header(None)):
    _require_owner(analysis_id, x_client_id)
    db.delete_share(analysis_id)
    return ShareResponse(token=None)


def _check_owner(analysis_id: str, name: str, secret: str) -> None:
    stored = db.get_owner(analysis_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="삭제할 수 있는 분석 결과가 없습니다.")
    if owner.locked(analysis_id):
        raise HTTPException(status_code=429, detail="여러 번 틀려 잠시 후 다시 시도해야 합니다.")
    name_ok = owner.verify_name(name, stored["name_hash"], stored["masked_name"])
    secret_ok = owner.verify_secret(secret, stored["secret_hash"])
    if not (name_ok and secret_ok):
        owner.record_failure(analysis_id)
        raise HTTPException(status_code=403, detail="성명 또는 사용자 식별 암호가 일치하지 않습니다.")


@app.post("/api/v1/analyses/{analysis_id}/verify-owner")
def verify_owner(analysis_id: str, request: OwnerCheckRequest):
    _check_owner(analysis_id, request.name, request.secret)
    return {"ok": True}


@app.post("/api/v1/analyses/{analysis_id}/delete")
def delete_analysis(analysis_id: str, request: DeleteAnalysisRequest):
    _check_owner(analysis_id, request.name, request.secret)
    if request.confirm_text.strip() != owner.CONFIRM_TEXT:
        raise HTTPException(status_code=400, detail=f"'{owner.CONFIRM_TEXT}'를 정확히 입력해야 합니다.")
    db.delete_analysis(analysis_id)
    owner.clear_failures(analysis_id)
    return {"deleted": True}


@app.get("/api/v1/shared/{token}", response_model=AnalysisResponse)
def read_shared(token: str):
    record = db.get_shared(token)
    if record is None:
        raise HTTPException(status_code=404, detail="공유가 중지됐거나 없는 링크입니다.")
    return _for_viewer(record[0], "shared")


_llm_clients: dict = {}
_report_locks: dict[str, threading.Lock] = {}
_report_locks_guard = threading.Lock()


def _report_lock(analysis_id: str) -> threading.Lock:
    with _report_locks_guard:
        if len(_report_locks) > 1000:  # 오래된 잠금 정리 (사용 중이 아닌 것만)
            for key in [k for k, v in _report_locks.items() if not v.locked()]:
                _report_locks.pop(key, None)
        return _report_locks.setdefault(analysis_id, threading.Lock())



def _followup_client():
    if "followup" not in _llm_clients:
        _llm_clients["followup"] = OpenAIJsonClient.from_env(
            "FOLLOWUP", "후속 조치 조사", followup.DEFAULT_FOLLOWUP_MODEL
        )
    return _llm_clients["followup"]


def _report_client():
    if "report" not in _llm_clients:
        _llm_clients["report"] = OpenAIJsonClient.from_env(
            "REPORT", "리포트 작성", report.DEFAULT_REPORT_MODEL
        )
    return _llm_clients["report"]


def _load_report(analysis_id: str, client_key: str | None, share: str | None = None) -> ReportResponse:
    record = db.get_analysis_record(analysis_id, client_key)
    if record is None and share:
        shared = db.get_shared(share)
        if shared is not None and shared[0].id == analysis_id:
            record = shared
    if record is None:
        raise HTTPException(status_code=404, detail="분석 결과를 찾을 수 없습니다.")
    analysis, analyzed_at = record

    cached = db.get_report(analysis_id)
    if cached is not None:
        return cached

    # 같은 분석의 리포트를 동시에 요청하면 앞 요청이 만드는 동안 기다렸다가 저장본을 받는다.
    # 예전에는 DB 중복 저장은 없었지만 LLM이 요청 수만큼 실행됐다 (QA: 3번 동시 요청 → 3번 호출)
    with _report_lock(analysis_id):
        cached = db.get_report(analysis_id)
        if cached is not None:
            return cached
        research = followup.research(analysis, client=_followup_client())
        result = report.generate_report(
            analysis, research, client=_report_client(), analyzed_at=analyzed_at
        )
        try:
            db.save_report(result)
        except Exception:
            logger.exception("리포트 저장 실패: %s", analysis_id)
    return result


@app.post("/api/v1/analyses/{analysis_id}/report", response_model=ReportResponse)
def create_report(
    analysis_id: str,
    share: str | None = Query(None, description="공유 링크 토큰"),
    x_client_id: uuid.UUID | None = Header(None),
):
    return _load_report(analysis_id, _client_key(x_client_id), share)


@app.get("/api/v1/analyses/{analysis_id}/report.pdf")
def download_report_pdf(
    analysis_id: str,
    share: str | None = Query(None, description="공유 링크 토큰"),
    x_client_id: uuid.UUID | None = Header(None),
):
    result = _load_report(analysis_id, _client_key(x_client_id), share)
    pdf = report_pdf.render_report_pdf(result)
    filename = f"phishing-report-{analysis_id[:8]}.pdf"
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )

