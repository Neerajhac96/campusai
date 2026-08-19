Bilkul. `docs/CAMPUSAI_BUILD_DESIGN.md` ke liye wahi complete master design dobara de raha hoon. Isko **exactly copy karke** `docs/CAMPUSAI_BUILD_DESIGN.md` mein save kar do.

````md
# CampusAI — Build Design & Technical Blueprint

**Document:** CAMPUSAI_BUILD_DESIGN.md  
**Product:** CampusAI  
**Type:** Multi-Tenant B2B SaaS College AI Assistant  
**Status:** TARGET BUILD DESIGN  
**Primary Implementation Agent:** Antigravity  
**Source Baseline:** Product Specification + Current State Technical/Security Audit

---

# 1. Purpose

This document defines the target architecture, product behavior, security model,
data model, API structure, frontend structure, RAG pipeline, workflows, and
implementation phases for CampusAI.

This is the TARGET design.

The existing repository is a functional prototype and must not be assumed to
already satisfy this design.

The implementation agent must:

1. Inspect existing code before modifying it.
2. Preserve working functionality where compatible with this design.
3. Replace prototype implementations where required.
4. Never weaken tenant isolation or security for convenience.
5. Implement changes incrementally.
6. Run tests after every major phase.
7. Never silently change product requirements.

---

# 2. Product Vision

CampusAI is an AI-powered college assistant SaaS platform designed for Indian
colleges and universities.

Each college operates as an isolated tenant.

Students can ask questions about:

- Fees
- Attendance
- Exams
- Scholarships
- Hostel
- Placements
- Timetables
- Notices
- Syllabus
- Academic information

The system provides source-backed answers using the college's own knowledge
base.

Primary languages:

- English
- Hindi
- Hinglish

The AI must not invent college-specific information when the information is
not present in the authorized knowledge base.

---

# 3. Product Model

CampusAI is a B2B SaaS platform.

## Plans

### Starter

- Up to 2,000 students
- ₹15,000/month

### Growth

- Up to 10,000 students
- ₹40,000/month

### University

- Unlimited students
- ₹1,20,000/month

### Setup Fee

₹50,000–₹2,00,000 depending on onboarding requirements.

The architecture must support plan-specific limits without hardcoding limits
inside individual route handlers.

---

# 4. Core Architectural Principle

The most important system property is:

> A tenant must never be able to access another tenant's data.

Tenant identity MUST be derived server-side from the authenticated identity.

Client-provided `college_id` must never determine authorization.

The request lifecycle is:

```text
Client
  |
  v
Authentication
  |
  v
Authenticated User
  |
  v
Tenant Resolution
  |
  +---- college_id from authenticated identity
  |
  v
Authorization / RBAC
  |
  v
Business Logic
  |
  +---- PostgreSQL
  +---- Vector Database
  +---- Object Storage
  |
  v
Response
````

---

# 5. Target Architecture

```text
                         ┌──────────────────────┐
                         │      Students        │
                         │ Faculty / Admin      │
                         └──────────┬───────────┘
                                    │
                                    v
                         ┌──────────────────────┐
                         │ React + Vite         │
                         │ Tailwind             │
                         └──────────┬───────────┘
                                    │ HTTPS
                                    v
                         ┌──────────────────────┐
                         │ FastAPI Backend      │
                         │                      │
                         │ Auth                 │
                         │ RBAC                 │
                         │ Tenant Isolation     │
                         │ Chat                 │
                         │ Documents            │
                         │ Analytics            │
                         └───────┬───────┬──────┘
                                 │       │
                    ┌────────────┘       └─────────────┐
                    v                                  v
          ┌──────────────────┐                ┌──────────────────┐
          │ PostgreSQL       │                │ Redis            │
          │                  │                │                  │
          │ Users            │                │ Rate limits      │
          │ Colleges         │                │ Usage counters   │
          │ Documents        │                │ Cache            │
          │ Conversations    │                │ Jobs             │
          │ Analytics        │                └──────────────────┘
          └──────────────────┘
                    │
                    │
                    ├───────────────────────┐
                    v                       v
          ┌──────────────────┐    ┌──────────────────┐
          │ Object Storage   │    │ Qdrant           │
          │ S3 / R2          │    │ Vector Database  │
          │                  │    │                  │
          │ Original files   │    │ Tenant vectors   │
          └──────────────────┘    └────────┬─────────┘
                                           │
                                           v
                                  ┌──────────────────┐
                                  │ Groq LLM         │
                                  │ Answer Generation│
                                  └──────────────────┘
```

---

# 6. Technology Stack

## Frontend

* React
* Vite
* Tailwind CSS
* Axios or fetch-based API client
* React Context for authentication where appropriate

## Backend

* Python
* FastAPI
* Pydantic v2
* Async database access
* Service/repository separation

## Database

Target:

* PostgreSQL

Migration:

* Alembic

## Vector Database

Target:

* Qdrant

Development may temporarily use ChromaDB if required, but production
architecture must support Qdrant.

## Embeddings

* Sentence Transformers

Current working embedding model may be retained initially if compatible.

## LLM

* Groq API

The LLM provider must be abstracted behind a service interface so that the
provider can be changed later.

## Cache / Rate Limiting

* Redis

## File Storage

Target:

* S3-compatible object storage
* Cloudflare R2 is an acceptable implementation

## Deployment

Target:

* Backend: Railway / equivalent container platform
* Frontend: Vercel
* Database: managed PostgreSQL
* Storage: S3/R2
* Vector DB: Qdrant Cloud

---

# 7. User Roles

CampusAI supports six roles.

## SUPER_ADMIN

Platform owner.

Permissions:

* Manage all colleges
* Create/deactivate colleges
* Manage college plans
* Create college admins
* View global platform statistics
* View revenue estimates
* View platform usage
* Manage onboarding invitations

SUPER_ADMIN is a platform-level role and does not belong to a normal
college tenant.

---

## COLLEGE_ADMIN

College-level administrator.

Permissions:

* Manage college documents
* Manage students
* Manage faculty/staff
* Manage departments
* View college analytics
* Upload/replace/delete college-wide documents
* Create HOD/coordinator/faculty accounts

---

## HOD

Department administrator.

Permissions:

* Manage department documents
* View department students
* Manage department faculty where authorized
* View department analytics
* Upload department notices/timetables/material

---

## DEPT_COORDINATOR

Department coordinator.

Permissions:

* Upload department documents
* Manage department notices
* View authorized department students
* View department-specific analytics

---

## FACULTY

Teacher.

Permissions:

* Manage authorized subject documents
* Upload notes
* Upload lab manuals
* Upload PYQs
* View authorized students
* View subject/department query analytics

---

## STUDENT

End user.

Permissions:

* Query AI
* Create conversations
* View own conversations
* Delete own conversations
* Rename own conversations
* View own profile
* Update permitted profile fields
* View own academic information

Students cannot access administration APIs.

---

# 8. RBAC Rules

Authorization must be enforced server-side.

Frontend hiding buttons is NOT authorization.

Every protected endpoint must have:

1. Authentication
2. Role authorization
3. Tenant authorization where applicable
4. Department authorization where applicable
5. Resource ownership validation where applicable

Example:

```text
Student
  -> authenticate
  -> role == STUDENT
  -> college_id == authenticated college_id
  -> resource belongs to authenticated user
```

---

# 9. Multi-Tenant Isolation

Tenant isolation must exist at every storage layer.

## PostgreSQL

Tenant-owned tables must contain:

```text
college_id
```

Queries must always constrain tenant-owned resources by authenticated
`college_id`.

Bad:

```sql
SELECT * FROM documents WHERE id = ?
```

Good:

```sql
SELECT *
FROM documents
WHERE id = ?
AND college_id = ?
```

The second value must come from authenticated server-side identity.

---

# 10. Conversation Isolation

Conversation access requires:

```text
conversation_id
+
authenticated user_id
+
authenticated college_id
```

For student-owned conversations:

```text
conversation.user_id == current_user.id
AND
conversation.college_id == current_user.college_id
```

Conversation IDs must never be treated as sufficient authorization.

This specifically addresses the current IDOR finding.

---

# 11. Vector Isolation

Production vector storage must isolate tenants.

Preferred namespace:

```text
tenant_{college_id}
```

Every vector record must also contain metadata such as:

```text
college_id
document_id
department_id
scope
subject
category
version
```

Retrieval must apply tenant filtering before returning context.

The system must never search a global vector collection containing multiple
colleges without mandatory tenant filtering.

The shared fallback vector file currently identified by the audit must not
remain part of the production architecture.

---

# 12. File Isolation

Object storage structure:

```text
colleges/
  {college_id}/
    documents/
      {document_id}/
        v1/
        v2/
```

Example:

```text
colleges/aktu/documents/doc_123/v2/fees.pdf
```

File access must be authorized through the backend.

The client must not directly construct arbitrary storage paths.

---

# 13. Authentication Architecture

Authentication must use secure server-side configuration.

## Password

Passwords must never be stored as plaintext.

Target password hashing:

* Argon2id preferred

Legacy hashing must not be used for newly created passwords.

Existing passwords may require a migration strategy.

---

# 14. JWT / Session Security

The production system must not contain a fallback production secret.

Startup must fail if the required authentication secret is missing.

JWT should contain only the minimum required identity claims.

Example:

```json
{
  "sub": "user_id",
  "role": "student",
  "college_id": "college_id",
  "exp": "expiration"
}
```

The backend must still validate the user against the database.

JWT claims must not be treated as permanent authorization state.

---

# 15. Token Storage

Production browser authentication should use:

* HttpOnly
* Secure
* SameSite

cookies where practical.

JWTs must not be stored in localStorage in the production security model.

---

# 16. Login Flow

```text
User
 |
 v
Login
 |
 v
Validate credentials
 |
 v
Check user active
 |
 v
Check college active
 |
 v
Create authenticated session/token
 |
 v
Return safe user information
```

Never return:

* password hash
* internal secrets
* temporary passwords unnecessarily
* sensitive audit information

---

# 17. Student Registration

Registration uses the admission whitelist.

Flow:

```text
College Selection
      |
      v
Admission Number
      |
      v
Server validates college + admission number
      |
      v
Check is_registered
      |
      v
Collect email/password/profile fields
      |
      v
Create user
      |
      v
Create student profile
      |
      v
Mark admission record registered
```

Academic information comes from the college's admitted-student dataset.

Client input must not be trusted for academic identity.

---

# 18. Admission Lookup Security

The admission validation endpoint must not expose arbitrary student PII.

The public endpoint must:

* rate limit requests
* avoid revealing unnecessary student information
* avoid enumeration
* return only the minimum information needed for registration
* never reveal complete student profiles

Response examples should be intentionally minimal.

---

# 19. College Onboarding

Target onboarding uses invitation tokens.

Flow:

```text
SUPER_ADMIN
    |
    v
Create College
    |
    v
Create Invitation
    |
    v
Generate cryptographically secure token
    |
    v
Store SHA-256 token hash
    |
    v
Send invitation
    |
    v
College Admin opens invitation
    |
    v
Validate token + expiry + status
    |
    v
Create / activate admin
    |
    v
Force initial password setup
    |
    v
Invitation marked USED
```

Invitation requirements:

* Cryptographically random token
* Token hash stored in database
* Expiration
* Single use
* Atomic acceptance
* Used timestamp
* Revocation support

Default TTL:

```text
7 days
```

---

# 20. Password Reset

Password reset must be implemented as a secure token workflow.

Flow:

```text
Forgot Password
      |
      v
Enter Email
      |
      v
Generic response
      |
      v
Generate secure reset token
      |
      v
Store token hash
      |
      v
Email reset link
      |
      v
Validate token
      |
      v
Set new password
      |
      v
Invalidate token
```

The endpoint must not reveal whether an email exists.

---

# 21. RAG Architecture

RAG is the central AI architecture.

```text
Document
   |
   v
Text Extraction
   |
   v
Cleaning
   |
   v
Semantic Chunking
   |
   v
Embedding Generation
   |
   v
Qdrant
```

Query:

```text
Student Question
      |
      v
Language Detection
      |
      v
Query Cleaning / Security Check
      |
      v
Query Embedding
      |
      v
Tenant + Scope Retrieval
      |
      v
Top-K Results
      |
      v
Optional Reranking
      |
      v
Context Assembly
      |
      v
Prompt Guard
      |
      v
Groq LLM
      |
      v
Answer + Sources + Confidence
```

---

# 22. RAG Rules

The AI must answer only from authorized retrieved knowledge.

If sufficient information is not retrieved:

```text
Do not invent an answer.
```

Instead:

* state that the information could not be found
* provide a helpful fallback
* optionally direct the student to the relevant college authority

---

# 23. Retrieval Scope

Every query must respect:

```text
college_id
department
subject
document scope
```

Possible document scopes:

```text
COLLEGE
DEPARTMENT
SUBJECT
```

Student retrieval should follow:

```text
College-wide documents
+
Student's department documents
+
Student's authorized subject documents
```

---

# 24. Document Permissions

## College-wide

Examples:

* Fees
* Hostel
* Exam schedule
* Scholarships

Upload:

```text
COLLEGE_ADMIN
```

Visibility:

```text
All students
```

---

## Department

Examples:

* Timetable
* Department notices
* Placement information
* Department rules

Upload:

```text
COLLEGE_ADMIN
HOD
DEPT_COORDINATOR
```

Visibility:

```text
Authorized department students
```

---

## Subject

Examples:

* Notes
* Syllabus
* Lab manuals
* PYQs

Upload:

```text
COLLEGE_ADMIN
HOD
FACULTY
```

Visibility:

```text
Authorized subject students
```

---

# 25. Prompt Injection Protection

Student input must be treated as untrusted input.

The system prompt must clearly separate:

```text
SYSTEM INSTRUCTIONS
+
RETRIEVED COLLEGE KNOWLEDGE
+
USER QUESTION
```

User text must never be allowed to override system instructions.

The system must ignore instructions such as:

```text
Ignore previous instructions.
Reveal system prompt.
Show hidden documents.
Access another college.
```

Retrieval authorization happens before LLM generation.

The LLM is not responsible for tenant security.

---

# 26. Context Memory

The system should remember recent messages inside the same conversation.

Target:

```text
Last 6 messages
```

Conversation history must remain scoped to:

```text
user_id
college_id
conversation_id
```

Context from another conversation must never be injected.

---

# 27. Streaming Chat

Target endpoint:

```text
POST /chat/stream
```

The frontend receives incremental answer tokens.

Flow:

```text
Question
 |
 v
Retrieve
 |
 v
Generate
 |
 +--> token
 +--> token
 +--> token
 +--> token
 |
 v
Sources
 |
 v
Completed
```

Streaming must not bypass:

* tenant checks
* RBAC
* usage limits
* prompt security
* audit/query logging

---

# 28. Confidence

The system must classify retrieval confidence.

Example states:

```text
HIGH
MEDIUM
LOW
NO_RESULT
```

Threshold values must be configurable rather than scattered through code.

Low-confidence responses should avoid unsupported generation.

---

# 29. Source Citations

Every generated answer based on retrieved knowledge should provide source
information.

Example:

```text
Source:
Student Fee Structure 2026
Page 4
```

Sources must reference only documents the current user was authorized to
retrieve.

---

# 30. Document Management

Supported initial formats:

```text
PDF
DOCX
TXT
```

Maximum upload size:

```text
10 MB
```

Workflow:

```text
Upload
 |
 v
Validate
 |
 v
Store original
 |
 v
Extract text
 |
 v
Chunk
 |
 v
Embed
 |
 v
Index
 |
 v
Mark ACTIVE
```

Statuses:

```text
PROCESSING
ACTIVE
ERROR
```

---

# 31. Document Replacement

Replacement must be version-aware.

```text
Existing document v1
       |
       v
Upload replacement
       |
       v
Create v2
       |
       v
Index v2
       |
       v
Remove/deactivate v1 vectors
       |
       v
Mark v2 active
```

The system must avoid a period where both old and new versions produce
conflicting answers.

---

# 32. Duplicate Detection

Documents should support SHA-256 content hashing.

Purpose:

* prevent accidental duplicate uploads
* detect unchanged replacements
* improve storage efficiency

Hash should be calculated from the actual file bytes.

---

# 33. Database Design

Target tables:

```text
colleges
users
admitted_students
student_profiles
faculty_profiles
departments
documents
document_versions
conversations
messages
query_logs
audit_logs
college_invitations
usage_records
password_reset_tokens
```

---

# 34. Colleges

Core fields:

```text
id
name
slug
plan
is_active
created_at
updated_at
```

Optional future fields:

```text
logo_url
primary_color
contact_email
timezone
```

---

# 35. Users

Core fields:

```text
id
college_id
email
password_hash
role
name
is_active
must_change_password
created_at
updated_at
last_login_at
```

`college_id` may be NULL only for platform-level SUPER_ADMIN accounts.

---

# 36. Admitted Students

Fields:

```text
id
college_id
admission_no
name
department
course
year
semester
section
session
batch
roll_no
is_registered
created_at
```

Unique constraint:

```text
(college_id, admission_no)
```

---

# 37. Student Profiles

Fields:

```text
user_id
admission_no
department
course
year
semester
section
session
batch
roll_no
phone
parent_phone
hostel_status
```

---

# 38. Faculty Profiles

Fields:

```text
user_id
employee_id
department
designation
subjects
phone
gender
```

Employee ID should be unique within a college.

---

# 39. Departments

Fields:

```text
id
college_id
code
name
hod_user_id
created_at
```

Unique:

```text
(college_id, code)
```

---

# 40. Documents

Fields:

```text
id
college_id
file_name
storage_key
category
scope
department_id
subject
status
file_hash
current_version
chunk_count
uploaded_by
created_at
updated_at
```

---

# 41. Conversations

Fields:

```text
id
college_id
user_id
title
is_active
created_at
updated_at
```

Indexes:

```text
(user_id, updated_at)
(college_id, user_id)
```

---

# 42. Messages

Fields:

```text
id
conversation_id
role
content
sources
language
created_at
```

---

# 43. Query Logs

Fields:

```text
id
college_id
user_id
conversation_id
query_text
language
confidence
retrieved_chunks
response_time_ms
escalated
created_at
```

Query logs power analytics and usage metering.

---

# 44. Audit Logs

Fields:

```text
id
college_id
user_id
action
resource_type
resource_id
details
ip_address
created_at
```

Sensitive fields must never be written into `details`.

Never log:

```text
password
password_hash
JWT
API key
reset token
invitation token
temporary password
```

---

# 45. Usage Records

Usage should support:

```text
college_id
user_id
period
query_count
storage_bytes
```

Plan limits must be configurable.

---

# 46. API Design

## Authentication

```text
POST /auth/login
POST /auth/register
POST /auth/logout
GET  /auth/me
GET  /auth/profile
POST /auth/forgot-password
POST /auth/reset-password
```

---

## Chat

```text
POST   /chat/query
POST   /chat/stream
GET    /chat/conversations
POST   /chat/conversations/new
GET    /chat/conversations/{id}
DELETE /chat/conversations/{id}
PUT    /chat/conversations/{id}/title
GET    /chat/history
```

---

## Documents

```text
POST   /admin/documents/upload
GET    /admin/documents
GET    /admin/documents/status/{id}
DELETE /admin/documents/{id}
PUT    /admin/documents/{id}/replace
```

---

## Students

```text
POST /admin/students/bulk-upload
GET  /admin/students/admitted
GET  /admin/users
```

---

## Faculty

```text
POST   /admin/faculty
GET    /admin/faculty
DELETE /admin/faculty/{id}
```

---

## Departments

```text
POST /admin/departments
GET  /admin/departments
```

---

## Analytics

```text
GET /admin/analytics/summary
GET /admin/analytics/recent
```

---

## Student

```text
GET /student/profile
PUT /student/profile
GET /student/dashboard
```

---

## Faculty

```text
GET /faculty/profile
PUT /faculty/profile
GET /faculty/dashboard
GET /faculty/students
```

---

## Super Admin

```text
GET    /super/colleges
POST   /super/colleges
PUT    /super/colleges/{id}
DELETE /super/colleges/{id}

GET  /super/users
POST /super/users
GET  /super/stats

POST /super/invitations
GET  /super/invitations
POST /super/invitations/{id}/revoke
```

---

# 47. Frontend Application Structure

Target:

```text
frontend/src/

├── api/
│   ├── client.js
│   └── services/
│
├── components/
│   ├── common/
│   ├── chat/
│   ├── admin/
│   ├── faculty/
│   └── dashboard/
│
├── context/
│   └── AuthContext.jsx
│
├── pages/
│   ├── LoginPage.jsx
│   ├── RegisterPage.jsx
│   ├── StudentChat.jsx
│   ├── StudentDashboard.jsx
│   ├── FacultyDashboard.jsx
│   ├── AdminDashboard.jsx
│   └── SuperAdminPanel.jsx
│
├── hooks/
├── utils/
├── routes/
└── App.jsx
```

Existing clean React component architecture should be preserved where
compatible with the target design.

---

# 48. Student Experience

Student home/dashboard:

```text
┌─────────────────────────────────────┐
│ CampusAI                             │
│                                     │
│ Good morning, Student               │
│                                     │
│ [ Ask CampusAI anything...       ] │
│                                     │
│ Today's Important Information       │
│ ┌──────────┐ ┌──────────┐           │
│ │ Exam     │ │ Fee      │           │
│ │ Notice   │ │ Deadline │           │
│ └──────────┘ └──────────┘           │
│                                     │
│ Recent Conversations                │
│                                     │
│ [ Open AI Chat ]                    │
└─────────────────────────────────────┘
```

---

# 49. Chat Experience

Chat UI should provide:

* Conversation sidebar
* New conversation
* Search conversations
* Message history
* Streaming response
* Source citations
* Copy button
* Regenerate
* Suggestion chips
* Language-aware responses
* Dark/light mode
* Mobile responsive layout

The experience should feel familiar to modern AI chat applications while
retaining CampusAI branding.

---

# 50. Admin Dashboard

Tabs/modules:

```text
Overview
Documents
Students
Faculty
Departments
Analytics
Settings
```

Overview should show:

```text
Total Students
Total Documents
Queries Today
Resolution Rate
Active Users
```

---

# 51. Faculty Dashboard

Modules:

```text
My Profile
My Documents
My Students
Query Analytics
```

Faculty must only see data authorized for their department/subjects.

---

# 52. HOD / Coordinator Dashboard

Department-level dashboard.

Show:

```text
Department Students
Department Documents
Department Queries
Top Questions
Unanswered Questions
Recent Notices
```

Data must be restricted to the faculty member's department.

---

# 53. Super Admin Dashboard

Modules:

```text
Colleges
Plans
Users
Platform Analytics
Revenue
Invitations
```

Metrics:

```text
Total Colleges
Active Colleges
Total Students
Total Queries
Queries Today
Queries This Month
Estimated Revenue
Most Active Colleges
```

---

# 54. Usage Metering

Usage enforcement must exist independently of frontend behavior.

Example:

```text
Student Query
    |
    v
Check plan
    |
    v
Check monthly quota
    |
    +---- exceeded --> HTTP 429
    |
    v
Check short-window rate limit
    |
    +---- exceeded --> HTTP 429
    |
    v
Execute RAG
    |
    v
Increment usage
```

Both:

```text
rate limit
```

and:

```text
monthly quota
```

must be enforced server-side.

---

# 55. Rate Limits

Critical endpoints must be protected.

At minimum:

```text
/login
/register
/check-admission
/forgot-password
/chat/query
/chat/stream
```

Redis-backed sliding-window or equivalent rate limiting should be used.

---

# 56. CORS

Production CORS must use an explicit origin allowlist.

Never use:

```text
allow_origins=["*"]
```

with credentialed authentication.

Allowed origins must come from environment configuration.

---

# 57. Observability

Backend must support:

```text
Structured JSON logging
Health endpoint
Readiness endpoint
Error tracking
Request IDs
Response timing
```

Target endpoints:

```text
GET /health
GET /health/readiness
```

---

# 58. Error Handling

API errors should use consistent structure.

Example:

```json
{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Document not found"
  }
}
```

Never expose:

* stack traces
* SQL queries
* secrets
* internal filesystem paths
* provider API errors directly

in production responses.

---

# 59. Testing Strategy

The system must have automated tests.

Minimum backend test categories:

```text
Authentication
RBAC
Tenant Isolation
Conversation Authorization
Document Authorization
Student Registration
Invitation Tokens
Password Reset
Rate Limiting
Usage Quotas
RAG Retrieval
Prompt Injection
```

Critical security tests must explicitly attempt cross-tenant access.

Example:

```text
College A user
      |
      v
Request College B document
      |
      v
Expected: 403 or 404
```

Same principle applies to:

* conversations
* messages
* documents
* students
* analytics
* vectors

---

# 60. Definition of Done

A feature is not considered complete merely because the UI works.

A feature is DONE only when:

```text
Backend implemented
+
Frontend implemented where required
+
Authorization implemented
+
Tenant isolation verified
+
Validation implemented
+
Error handling implemented
+
Automated tests added
+
Manual verification completed
```

---

# 61. Implementation Phases

## Phase 0 — Design

Deliver:

```text
CAMPUSAI_BUILD_DESIGN.md
```

No production code changes.

---

## Phase 1 — Security Foundation

Fix:

1. JWT secret fallback
2. Admission PII leak
3. Conversation tenant checks
4. CORS
5. Sensitive audit logs
6. Password hashing strategy
7. Secure authentication storage

Add security regression tests.

---

## Phase 2 — Database Foundation

Implement:

```text
PostgreSQL
SQLAlchemy/SQLModel
Alembic
```

Create migration structure.

Do not remove SQLite until PostgreSQL compatibility is verified.

---

## Phase 3 — Storage

Implement:

```text
S3/R2 object storage
```

Introduce storage abstraction:

```text
StorageService
```

Application code must not directly depend on filesystem paths.

---

## Phase 4 — Tenant-Safe Vector Architecture

Implement:

```text
Qdrant
```

with tenant-aware collections/namespaces and metadata filters.

Remove production dependency on the shared fallback vector file.

---

## Phase 5 — Secure SaaS Onboarding

Implement:

```text
College Invitations
Secure Tokens
Invitation Expiry
Single-use Acceptance
Password Setup
Password Reset
```

---

## Phase 6 — RAG Upgrade

Implement:

```text
Semantic chunking
Prompt injection protection
Configurable confidence thresholds
Improved retrieval
Source citations
Streaming generation
```

---

## Phase 7 — Usage & Billing Foundation

Implement:

```text
Redis
Rate Limiting
Monthly Quotas
Usage Records
Plan Enforcement
HTTP 429 responses
```

---

## Phase 8 — Dashboards

Complete:

```text
Student
Faculty
HOD
Coordinator
College Admin
Super Admin
```

with strict permission boundaries.

---

## Phase 9 — Analytics

Implement:

```text
Query trends
Resolution rate
Language breakdown
Top questions
Unanswered questions
Department breakdown
Usage by plan
```

---

## Phase 10 — Production Readiness

Implement:

```text
Docker
CI/CD
Health checks
Structured logging
Error monitoring
Automated tests
Environment validation
Production deployment
```

---

# 62. Future Roadmap

These features are NOT required for the initial production architecture.

## Phase 2 Product Expansion

* Email notifications
* Proactive nudges
* Redis answer caching
* WhatsApp integration
* Voice input
* ERP integration
* Complaint system
* Exam preparation assistant
* Advanced analytics

## Phase 3

* Native mobile applications
* Academic advisor
* Placement module
* Parent portal
* Regional languages
* Benchmarking intelligence

## Phase 4

* Alumni network
* Mental health routing
* Anonymized data products
* International expansion
* API marketplace
* Large-scale fundraising

These features must not unnecessarily complicate the MVP architecture.

---

# 63. What Must Be Preserved

The existing project contains working functionality that should be preserved
where compatible.

Important existing strengths include:

* Pydantic validation
* Hindi/Hinglish detection
* Existing React component separation
* Existing role dependency architecture
* Existing document ingestion concepts
* Existing conversation model
* Existing admin dashboards
* Existing student onboarding concept

Do not rewrite functioning modules without a technical reason.

---

# 64. What Must Be Replaced

The following prototype architecture must eventually be replaced for
production:

```text
SQLite
    -> PostgreSQL

Local uploads
    -> S3/R2

Local ChromaDB
    -> Qdrant

Local fallback vector aggregation
    -> removed from production

localStorage JWT
    -> secure cookie/session strategy

Hardcoded secret fallback
    -> mandatory environment secret

sha256_crypt for new passwords
    -> Argon2id

No rate limiting
    -> Redis-backed rate limiting

No usage metering
    -> quota + usage system

Blocking chat
    -> streaming chat

No automated tests
    -> backend + frontend + security tests
```

---

# 65. Non-Negotiable Security Rules

The following rules must NEVER be violated:

1. Client-supplied `college_id` must never determine authorization.
2. Every tenant resource must be scoped to authenticated tenant identity.
3. Conversation IDs alone must never authorize access.
4. Document IDs alone must never authorize access.
5. Vector retrieval must always be tenant-scoped.
6. Passwords must never be logged.
7. Tokens must never be logged.
8. Secrets must never have source-code fallbacks.
9. Authentication must not rely on frontend restrictions.
10. Admin APIs must enforce RBAC server-side.
11. Student APIs must not expose other students' private data.
12. LLM output must never be treated as an authorization mechanism.
13. Prompt injection must not bypass retrieval authorization.
14. Rate limits must be server-side.
15. Production errors must not expose internal implementation details.

---

# 66. Antigravity Implementation Rule

Antigravity must work incrementally.

For every phase:

```text
1. Inspect existing implementation.
2. Identify affected files.
3. Explain intended changes.
4. Implement changes.
5. Run automated tests.
6. Run relevant manual/API verification.
7. Report changed files.
8. Report remaining issues.
9. Do not modify unrelated functionality.
```

Never perform a blind repository-wide rewrite.

---

# 67. Final Target

The final CampusAI platform should provide:

```text
Secure Multi-Tenant SaaS
        +
College Knowledge Base
        +
RAG AI Assistant
        +
Hindi / English / Hinglish
        +
Student Experience
        +
Faculty Experience
        +
Department Management
        +
College Administration
        +
Platform Administration
        +
Usage Metering
        +
Analytics
        +
Cloud Infrastructure
        +
Automated Security Tests
```

The most important success criterion is not the number of features.

It is:

> A student from College A must never be able to retrieve, infer through
> application behavior, or directly access protected data belonging to
> College B.

Security and tenant isolation take priority over convenience and feature speed.

---

# END OF CAMPUSAI BUILD DESIGN
    
