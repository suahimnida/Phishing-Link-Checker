import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


class AnalysisRequest(BaseModel):
    url: str = Field(..., examples=["https://example.com"])
    is_public: bool = False
    owner_name: str | None = Field(None, max_length=30)
    owner_secret: str | None = None

    @field_validator("url")
    @classmethod
    def url_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("url이 비어 있습니다.")
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
