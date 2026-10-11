import logging
import time
from concurrent.futures import ThreadPoolExecutor
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware

load_dotenv(Path(__file__).resolve().parents[1] / ".env")

logging.basicConfig(level=logging.INFO, format="%(levelname)s:     [%(name)s] %(message)s")
logger = logging.getLogger(__name__)

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


@app.get("/health", response_model=HealthResponse)
def health():
    # 배포 환경에서 어떤 모델·scikit-learn 버전이 돌고 있는지 Render 로그 없이도 확인할 수 있게 한다
    return HealthResponse(status="ok", model=_model_info() or None)


def _client_key(client_id: uuid.UUID | None) -> str | None:
    return str(client_id) if client_id else None


@app.post("/api/v1/clients", response_model=ClientResponse)
def create_client():
    return ClientResponse(client_id=str(uuid.uuid4()))

_background = ThreadPoolExecutor(max_workers=4)


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
            detection_result.reputation = reputation.to_detection(reputation_job.result(timeout=10))
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

    try:
        db.save_analysis(result, _client_key(x_client_id))
        if request.owner_name or request.owner_secret:
            db.save_owner(
                result.id,
                result.owner_name,
                owner.hash_secret(request.owner_secret) if request.owner_secret else None,
                owner.hash_name(request.owner_name) if request.owner_name else None,
            )
    except Exception:
        logger.exception("분석 기록 저장 실패: %s", request.url)
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

