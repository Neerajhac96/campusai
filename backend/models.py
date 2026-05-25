from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


RoleType = Literal["student", "admin", "super_admin"]
PlanType = Literal["starter", "growth", "university"]
LanguageType = Literal["hindi", "english"]
ConfidenceType = Literal["high", "low", "uncertain"]
DocumentStatus = Literal["processing", "active", "error", "archived"]
DocumentCategory = Literal[
    "fees",
    "attendance",
    "exam",
    "hostel",
    "scholarship",
    "placement",
    "syllabus",
    "rules",
    "notices",
    "general",
]


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)


class UserInfo(BaseModel):
    id: str
    college_id: str | None = None
    college_name: str | None = None
    email: EmailStr
    role: RoleType
    name: str
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_hours: int
    user: UserInfo


class LogoutResponse(BaseModel):
    success: bool
    message: str


class QueryRequest(BaseModel):
    query: str = Field(min_length=2, max_length=4000)


class QueryResponse(BaseModel):
    answer: str
    sources: list[str]
    language: LanguageType
    confidence: ConfidenceType
    escalate: bool
    response_time_ms: int


class QueryLogResponse(BaseModel):
    id: str
    query_text: str
    response_text: str
    language: LanguageType
    confidence: ConfidenceType
    escalated: bool
    sources: list[str]
    response_time_ms: int
    created_at: datetime | str


class PaginatedQueryHistory(BaseModel):
    page: int
    limit: int
    total: int
    items: list[QueryLogResponse]


class DocumentCreateResponse(BaseModel):
    doc_id: str
    status: DocumentStatus
    message: str


class DocumentRecord(BaseModel):
    id: str
    college_id: str
    file_name: str
    original_name: str
    category: DocumentCategory
    status: DocumentStatus
    chunk_count: int
    file_size: int | None = None
    uploaded_by: str | None = None
    uploaded_at: datetime | str | None = None
    last_indexed: datetime | str | None = None
    auto_refresh: bool = False
    version: int = 1


class DocumentListResponse(BaseModel):
    items: list[DocumentRecord]
    total: int


class CreateStudentRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2, max_length=100)


class CollegeCreateRequest(BaseModel):
    id: str = Field(pattern=r"^col_[a-z0-9_]+$")
    name: str = Field(min_length=2, max_length=120)
    slug: str = Field(min_length=2, max_length=80, pattern=r"^[a-z0-9-]+$")
    plan: PlanType = "starter"
    api_key: str | None = None


class CollegeUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    plan: PlanType | None = None
    is_active: bool | None = None


class CollegeResponse(BaseModel):
    id: str
    name: str
    slug: str
    api_key: str | None = None
    plan: PlanType
    is_active: bool
    created_at: datetime | str | None = None
    total_users: int = 0
    total_documents: int = 0
    total_queries: int = 0


class CreateCollegeAdminRequest(BaseModel):
    college_id: str
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2, max_length=100)


class AdminAnalyticsSummary(BaseModel):
    total_queries_month: int
    language_breakdown: dict[str, int]
    resolution_rate: float
    top_questions: list[dict[str, int]]
    queries_per_day: list[dict[str, int | str]]
    category_breakdown: list[dict[str, int | str]]


class SuperStats(BaseModel):
    total_colleges: int
    total_students: int
    total_queries_today: int
    total_queries_week: int
    total_queries_month: int
    revenue_estimate_inr: int
    most_active_colleges: list[dict[str, int | str]]
