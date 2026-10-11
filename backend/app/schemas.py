import re
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

MAX_URL_LENGTH = 2048
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_SCHEME = re.compile(r"^([a-zA-Z][a-zA-Z0-9+.-]*):")


class AnalysisRequest(BaseModel):
    url: str = Field(..., examples=["https://example.com"])
    is_public: bool = False
    owner_name: str | None = Field(None, max_length=30)
    owner_secret: str | None = None

    @field_validator("url")
    @classmethod
    def url_valid(cls, v: str) -> str:
        """분석할 수 있는 URL인지 확인한다 (QA: 10만 자, 제어 문자, javascript:가 그대로 저장되던 문제).

        - 앞뒤 공백 제거 후 비어 있으면 거절
        - 2,048자 초과 거절 (브라우저 주소창 한계 수준)
        - 제어 문자(줄바꿈, NUL 등) 거절. NUL은 PostgreSQL이 저장을 거부해 '저장 안 된 결과'가 생겼다
        - http/https 또는 스킴 없는 주소만 허용 (javascript:, data:, ftp: 등 거절)
        - 호스트가 도메인(점 포함)·IPv4·IPv6 형식이어야 함. 한글 도메인은 허용
        """
        v = v.strip()
        if not v:
            raise ValueError("url이 비어 있습니다.")
        if len(v) > MAX_URL_LENGTH:
            raise ValueError(f"url은 {MAX_URL_LENGTH}자 이하여야 합니다.")
        if _CONTROL.search(v):
            raise ValueError("url에 줄바꿈이나 제어 문자를 넣을 수 없습니다.")
        has_scheme = "://" in v
        scheme = _SCHEME.match(v)
        if has_scheme and v.split("://", 1)[0].lower() not in ("http", "https"):
            raise ValueError("http 또는 https 주소만 분석할 수 있습니다.")
        if not has_scheme and scheme and scheme.group(1).lower() in ("javascript", "data", "vbscript", "file", "mailto"):
            raise ValueError("http 또는 https 주소만 분석할 수 있습니다.")
        try:
            parts = urlsplit(v if has_scheme else "http://" + v)
            host = parts.hostname or ""
            parts.port  # 잘못된 포트(99999 등)면 ValueError
        except ValueError:
            raise ValueError("URL 형식이 올바르지 않습니다.")
        if not ("." in host.strip(".") or host.count(":") >= 2):
            raise ValueError("도메인 형식이 아닙니다. 예: https://example.com")
        return v

    @field_validator("owner_name")
    @classmethod
    def name_not_blank(cls, v: str | None) -> str | None:
        if v is not None and not v.strip():
            raise ValueError("성명이 비어 있습니다.")
        return v.strip() if v else v

    @field_validator("owner_secret")
    @classmethod
    def secret_format(cls, v: str | None) -> str | None:
        if v is not None and not re.fullmatch(r"[A-Za-z0-9]{8,12}", v):
            raise ValueError("사용자 식별 암호는 영문 대소문자와 숫자 8~12자리여야 합니다.")
        return v

    @model_validator(mode="after")
    def owner_pair(self):
        # 둘 중 하나만 저장되면 그 결과는 영원히 삭제할 수 없다 (QA). 함께 보내거나 둘 다 빼야 한다.
        if bool(self.owner_name) != bool(self.owner_secret):
            raise ValueError("성명과 사용자 식별 암호는 함께 입력해야 합니다.")
        return self


class OwnerCheckRequest(BaseModel):
    name: str
    secret: str


class DeleteAnalysisRequest(BaseModel):
    name: str
    secret: str
    confirm_text: str


class BlacklistResult(BaseModel):
    matched: bool
    match_type: Literal["none", "exact", "host"]
    source: str


class RagReference(BaseModel):

    matched: bool = False
    source: list[str] = [] 
    evidence: str | None = None 


class ModelResult(BaseModel):

    status: Literal["ready", "not_ready"]
    risk_score: float | None = None 
    label: Literal["phishing", "normal"] | None = None


class SimilarCase(BaseModel):
    url: str
    label: int 
    similarity: float


class Detections(BaseModel):

    url: dict | None = None
    url_stats: dict | None = None
    domain: dict | None = None
    reputation: dict | None = None


class AiAnalysis(BaseModel):

    summary: str | None = None
    reasons: list[str] = []
    written_by: str | None = None  
    evidence: list[dict] = [] 
    guides: list[dict] = []  


class AllowlistResult(BaseModel):

    matched: bool = False
    domain: str | None = None


class AnalysisResponse(BaseModel):
    id: str
    status: Literal["completed", "failed"]
    url: str
    viewer: Literal["owner", "public", "shared"] | None = None
    # 분석 결과가 DB에 저장됐는지. False면 공유·공개 전환·리포트·삭제를 할 수 없다 (프론트가 버튼을 숨김)
    saved: bool = True
    share_token: str | None = None
    owner_name: str | None = None 
    is_public: bool = False
    verdict: Literal["phishing", "suspicious", "normal"] | None = None
    confidence: float | None = None
    risk_score: float | None = None 
    risk_level: Literal["safe", "caution", "warning", "danger"] | None = None
    detections: Detections = Detections()
    ai_analysis: AiAnalysis = AiAnalysis()
    extracted_features: dict = {}
    similar_cases: list[SimilarCase] = []
    blacklist: BlacklistResult
    allowlist: AllowlistResult = AllowlistResult()
    explanation: dict | None = None 
    rag: RagReference = RagReference() 
    model: ModelResult 


class AnalysisSummary(BaseModel):

    id: str
    url: str
    verdict: Literal["phishing", "suspicious", "normal"] | None = None
    created_at: str
    owner_name: str | None = None 


class AnalysisListResponse(BaseModel):
    items: list[AnalysisSummary]


class ClientResponse(BaseModel):
    client_id: str


class HealthResponse(BaseModel):
    status: str
    model: dict | None = None
    llm: dict | None = None

class FollowupResult(BaseModel):
    research_summary: str 
    priority_action_ids: list[str]
    action_notes: dict[str, str]
    generated_by: str 


class ReportEvidence(BaseModel):

    source: str 
    finding: str
    used_in_verdict: bool


class ReportAction(BaseModel):
    id: str
    title: str
    steps: list[str]
    priority: bool = False
    note: str | None = None
    source: str | None = None  
    source_url: str | None = None


class ReportActionGroup(BaseModel):

    situation: str 
    actions: list[ReportAction]


class ReportContact(BaseModel):
    name: str
    phone: str | None = None
    url: str | None = None
    purpose: str


class ReportResponse(BaseModel):
    analysis_id: str
    created_at: str
    generated_by: str 
    followup_by: str 
    url: str
    verdict: Literal["phishing", "suspicious", "normal"] | None = None
    risk_score: float | None = None
    risk_level: Literal["safe", "caution", "warning", "danger"] | None = None
    confidence: float | None = None
    analyzed_at: str | None = None
    summary: str
    risk_assessment: str
    evidence: list[ReportEvidence]
    similar_cases: list[SimilarCase] = []
    ai_analysis: str | None = None  
    ai_evidence: list[dict] = []  
    ai_guides: list[dict] = []  
    followup_summary: str  
    action_groups: list[ReportActionGroup]
    contacts: list[ReportContact]
    limitations: list[str]
    references: list[str]



class VisibilityRequest(BaseModel):
    is_public: bool


class ShareResponse(BaseModel):
    token: str | None = None 
