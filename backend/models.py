from datetime import datetime
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


RoleType = Literal["student", "admin", "super_admin", "hod", "dept_coordinator", "faculty"]
PlanType = Literal["starter", "growth", "university"]
LanguageType = Literal["hindi", "english"]
ConfidenceType = Literal["high", "low", "uncertain"]
DocumentStatus = Literal["processing", "active", "error", "archived"]
FacultyRoleType = Literal["hod", "dept_coordinator", "faculty"]
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
    "registrar",
    "notes",
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


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    sources: list[str]
    language: str
    confidence: str
    escalated: bool
    response_time_ms: int
    created_at: str


class ConversationResponse(BaseModel):
    id: str
    title: str
    is_active: bool
    created_at: str
    updated_at: str
    last_message: str = ""
    message_count: int = 0


class ConversationDetailResponse(BaseModel):
    id: str
    title: str
    messages: list[MessageResponse]
    created_at: str
    updated_at: str


class ChatQueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=500)
    conversation_id: str | None = None


class ChatQueryResponse(BaseModel):
    answer: str
    sources: list[str]
    language: str
    confidence: str
    escalate: bool
    response_time_ms: int
    conversation_id: str
    message_id: str
    conversation_title: str


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
    department: str | None = None
    subject: str | None = None
    doc_scope: str = "college"
    uploaded_role: str = "admin"


class DocumentListResponse(BaseModel):
    items: list[DocumentRecord]
    total: int


class CreateStudentRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=2, max_length=100)


class AdmittedStudentRow(BaseModel):
    admission_no: str = Field(min_length=1)
    name: str = Field(min_length=1)
    department: str = Field(min_length=1)
    course: str = Field(min_length=1)
    year: int = Field(ge=1, le=4)
    semester: int = Field(ge=1, le=8)
    section: str = Field(min_length=1, max_length=5)
    session: str = Field(min_length=1)
    batch: str = Field(min_length=1)
    roll_no: str | None = None
    phone: str | None = None
    gender: str | None = None
    category: str | None = "general"
    is_hosteler: bool | None = False


class BulkUploadResponse(BaseModel):
    total_uploaded: int
    success: int
    failed: int
    errors: list[str]


class StudentRegisterRequest(BaseModel):
    college_id: str = Field(min_length=1)
    admission_no: str = Field(min_length=1)
    email: EmailStr
    password: str = Field(min_length=6)
    confirm_password: str = Field(min_length=6)
    parent_phone: str | None = None


class StudentRegisterResponse(BaseModel):
    success: bool
    message: str
    user_id: str


class StudentProfileResponse(BaseModel):
    id: str
    user_id: str
    college_id: str
    admission_no: str
    department: str
    course: str
    year: int
    semester: int
    section: str
    session: str
    batch: str
    roll_no: str | None = None
    phone: str | None = None
    gender: str | None = None
    category: str = "general"
    is_hosteler: bool = False
    parent_phone: str | None = None
    created_at: datetime | str | None = None
    name: str
    email: EmailStr
    college_name: str


class AdmissionCheckResponse(BaseModel):
    valid: bool
    message: str
    name: str | None = None
    department: str | None = None
    course: str | None = None


class StudentProfileUpdateRequest(BaseModel):
    phone: str | None = None
    parent_phone: str | None = None
    gender: str | None = None
    is_hosteler: bool | None = None


class FacultyProfileResponse(BaseModel):
    id: str
    user_id: str
    college_id: str
    college_name: str
    employee_id: str
    department: str
    designation: str
    role_type: FacultyRoleType
    subjects: list[str] = []
    employment_type: str = "full_time"
    joining_date: str | None = None
    phone: str | None = None
    gender: str | None = None
    name: str
    email: EmailStr
    is_active: bool = True
    created_at: datetime | str | None = None


class CreateFacultyRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    employee_id: str = Field(min_length=1, max_length=50)
    department: str = Field(min_length=1, max_length=80)
    designation: str = Field(min_length=2, max_length=80)
    role_type: FacultyRoleType
    subjects: list[str] = []
    employment_type: str = "full_time"
    phone: str | None = None
    gender: str | None = None
    joining_date: str | None = None


class FacultyProfileUpdateRequest(BaseModel):
    phone: str | None = None
    subjects: list[str] | None = None
    gender: str | None = None


class DepartmentResponse(BaseModel):
    id: str
    college_id: str
    name: str
    code: str
    hod_name: str | None = None
    coordinator_name: str | None = None
    is_active: bool = True
    total_faculty: int = 0
    total_students: int = 0


class CreateDepartmentRequest(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    code: str = Field(min_length=1, max_length=20)


class FacultyDashboardResponse(BaseModel):
    profile: FacultyProfileResponse
    department_info: DepartmentResponse
    my_documents: list[dict]
    total_documents: int
    student_queries_today: int
    top_queries: list[str]


class DocumentUploadScope:
    COLLEGE_WIDE = ["admin"]
    DEPARTMENT_LEVEL = ["admin", "hod", "dept_coordinator"]
    SUBJECT_LEVEL = ["admin", "hod", "faculty"]


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
