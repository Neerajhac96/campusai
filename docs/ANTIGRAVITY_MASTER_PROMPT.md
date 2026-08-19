# CampusAI — Antigravity Master Implementation Prompt

## 1. ROLE

You are the primary implementation agent for the CampusAI project.

You are responsible for converting the approved CampusAI technical design into a
working, secure, production-ready application.

The project is a multi-tenant B2B SaaS platform for Indian colleges.

The approved architecture is defined in:

docs/CAMPUSAI_BUILD_DESIGN.md

That document is the primary technical source of truth.

Do not invent a different architecture unless the existing repository makes the
specified architecture technically impossible or a change is required for
security/correctness.

If a design change is necessary, explain it before implementing it.

---

# 2. PRIMARY OBJECTIVE

Transform the current CampusAI prototype into the target architecture defined in:

docs/CAMPUSAI_BUILD_DESIGN.md

The implementation must preserve existing working functionality where compatible.

Do NOT perform a blind rewrite.

Do NOT replace working modules without first inspecting them.

Do NOT modify unrelated functionality.

The final system must support:

- Multi-tenant college isolation
- Secure authentication
- Role-based access control
- Student registration
- College administration
- Department management
- Faculty management
- Document management
- Secure RAG
- Hindi / English / Hinglish interaction
- Conversation history
- Source citations
- Analytics
- Usage limits
- Rate limiting
- Production storage
- Automated security tests

---

# 3. FIRST ACTION — INSPECT THE REPOSITORY

Before changing any code, inspect the complete repository structure.

Identify:

- Backend entry point
- Frontend entry point
- Authentication implementation
- Database implementation
- Models
- API routes
- Services
- RAG pipeline
- Vector database implementation
- Document ingestion
- File storage
- Conversation system
- Student registration
- Admin dashboards
- Faculty dashboards
- Super admin functionality
- Configuration/environment handling
- Existing tests
- Deployment configuration

Do not modify anything during this first inspection.

Create an internal understanding of the existing architecture.

Then provide a concise audit containing:

1. What already works
2. What partially works
3. What is missing
4. What conflicts with CAMPUSAI_BUILD_DESIGN.md
5. Which files will be affected in Phase 1

Do not start Phase 1 until this inspection is complete.

---

# 4. SOURCE OF TRUTH

Use this priority order:

1. CAMPUSAI_BUILD_DESIGN.md
2. Existing working functionality
3. Existing tests
4. Existing code structure
5. Reasonable implementation decisions

Security requirements always take priority over convenience.

If existing code conflicts with the security requirements of the design,
modify the existing code.

Never preserve an insecure implementation merely because it already works.

---

# 5. IMPLEMENTATION RULE

Work incrementally.

For every phase:

1. Inspect relevant existing code.
2. Identify exact files affected.
3. Explain what will change.
4. Implement only that phase.
5. Run tests.
6. Fix failures caused by the implementation.
7. Run relevant security/manual verification.
8. Report changed files.
9. Report tests executed.
10. Report remaining issues.

Never silently skip a phase.

Never combine multiple large phases into one operation unless explicitly
requested.

---

# 6. NON-NEGOTIABLE SECURITY RULE

CampusAI is a multi-tenant SaaS.

The most important security requirement is:

A user belonging to College A must NEVER access protected data belonging to
College B.

This applies to:

- Database records
- Documents
- Conversations
- Messages
- Students
- Faculty
- Departments
- Analytics
- Vector search
- Files
- API responses

Tenant identity must come from the authenticated server-side identity.

Never trust:

college_id supplied by the frontend.

---

# 7. ROLE SYSTEM

The following roles must remain:

SUPER_ADMIN
COLLEGE_ADMIN
HOD
DEPT_COORDINATOR
FACULTY
STUDENT

Authorization must always be enforced on the backend.

Frontend route protection alone is never sufficient.

Every protected API must validate:

Authentication
+
Role
+
Tenant
+
Department where required
+
Resource ownership where required

---

# 8. PHASE 1 — SECURITY FOUNDATION

Start implementation with security.

Do not begin PostgreSQL migration before fixing critical authentication and
authorization problems.

Inspect and fix:

## 8.1 JWT Secret

Remove insecure fallback production secrets.

Bad:

SECRET_KEY = os.getenv("SECRET_KEY", "default-secret")

Required behavior:

- SECRET_KEY must come from environment.
- Application startup must fail if required production secret is missing.
- Never commit production secrets.

---

## 8.2 Password Hashing

New passwords must use Argon2id.

Do not store plaintext passwords.

Do not log:

- password
- password hash
- temporary password

If legacy passwords use another hashing scheme, design a safe migration strategy.

Do not unnecessarily invalidate existing users.

---

## 8.3 JWT

Use minimum required claims.

Preferred structure:

sub
role
college_id
exp
iat

Do not put unnecessary sensitive information into JWT.

JWT must not be treated as the only source of authorization truth.

Validate the current user against the database where appropriate.

---

## 8.4 Conversation Authorization

Fix any IDOR vulnerability.

A conversation must only be accessible when:

conversation.user_id == current_user.id

AND

conversation.college_id == current_user.college_id

Do not authorize access using conversation_id alone.

Apply the same rule to messages.

---

## 8.5 Document Authorization

Document access must validate:

document_id
+
authenticated college_id
+
role
+
department/subject scope where applicable

Never allow:

GET /documents/{id}

to return a document solely because the ID exists.

---

## 8.6 Admission Registration

Review student admission validation.

Prevent:

- Cross-college admission lookup
- Student enumeration
- Unnecessary PII exposure

Return only the minimum information required for registration.

Add rate limiting later in Phase 7, but immediately remove unnecessary PII
exposure.

---

## 8.7 CORS

Remove wildcard production CORS.

Allowed origins must come from environment configuration.

Do not use wildcard origins with credentialed authentication.

---

## 8.8 Sensitive Logging

Audit all logging.

Never log:

- Passwords
- Password hashes
- JWTs
- API keys
- Invitation tokens
- Password reset tokens
- Temporary passwords

Remove sensitive values from audit details.

---

# 9. PHASE 1 SECURITY TESTS

Create automated tests for:

1. User authentication
2. Invalid token
3. Expired token
4. Inactive user
5. Inactive college
6. Role authorization
7. Student conversation ownership
8. Cross-tenant conversation access
9. Cross-tenant document access
10. Admission PII exposure
11. CORS behavior

Mandatory test:

College A user attempts to access College B resource.

Expected:

403 or 404.

Never 200.

Repeat this for:

- Conversations
- Messages
- Documents
- Students
- Faculty
- Departments
- Analytics

---

# 10. PHASE 2 — DATABASE FOUNDATION

After Phase 1 security tests pass:

Introduce production database architecture.

Target:

PostgreSQL

Migration tooling:

Alembic

Database architecture must support:

- colleges
- users
- admitted_students
- student_profiles
- faculty_profiles
- departments
- documents
- document_versions
- conversations
- messages
- query_logs
- audit_logs
- college_invitations
- usage_records
- password_reset_tokens

Every tenant-owned table must support college_id where appropriate.

Add proper:

- Primary keys
- Foreign keys
- Unique constraints
- Indexes
- Timestamps

Important unique constraints include:

(college_id, admission_no)

(college_id, employee_id)

(college_id, department_code)

---

# 11. SQLITE MIGRATION RULE

Do not immediately delete SQLite.

First:

1. Create PostgreSQL models/migrations.
2. Verify schema.
3. Verify CRUD operations.
4. Verify authentication.
5. Verify student registration.
6. Verify documents.
7. Verify conversations.
8. Run tests.
9. Confirm PostgreSQL works.

Only then remove production dependence on SQLite.

---

# 12. PHASE 3 — FILE STORAGE

Introduce a storage abstraction.

Create a service concept similar to:

StorageService

It should support:

upload
download
delete
exists

Application business logic must not depend directly on local filesystem paths.

Production target:

S3-compatible storage.

Cloudflare R2 is acceptable.

Storage layout:

colleges/{college_id}/documents/{document_id}/v{version}/

The backend must authorize every file operation.

Do not allow arbitrary client-generated storage paths.

---

# 13. PHASE 4 — VECTOR DATABASE

Move production vector architecture toward Qdrant.

Development may temporarily use ChromaDB if required.

Production must not depend on one shared fallback vector file containing
multiple colleges.

Every vector must contain metadata such as:

college_id
document_id
department_id
scope
subject
category
version

Retrieval MUST filter by authenticated college_id.

The LLM must never be responsible for tenant isolation.

Authorization must happen before context reaches the LLM.

---

# 14. PHASE 5 — COLLEGE ONBOARDING

Implement secure college onboarding.

Super admin creates:

- College
- College admin invitation

Invitation token requirements:

- Cryptographically secure
- Store token hash, not raw token
- Expiration
- Single use
- Revocation
- Used timestamp
- Atomic acceptance

Default invitation lifetime:

7 days

College admin must create/set a secure password.

Temporary passwords should not be permanently stored.

---

# 15. PHASE 6 — PASSWORD RESET

Implement:

POST /auth/forgot-password

POST /auth/reset-password

Forgot-password responses must be generic.

Do not reveal whether an email exists.

Reset tokens must be:

- Random
- Hashed in database
- Expiring
- Single-use

Invalidate the token immediately after successful reset.

---

# 16. PHASE 7 — RAG UPGRADE

Improve the existing RAG pipeline without destroying working functionality.

Pipeline:

Document
→ Text Extraction
→ Cleaning
→ Chunking
→ Embedding
→ Vector Storage

Query:

Question
→ Language Detection
→ Query Processing
→ Tenant/Scope Retrieval
→ Top-K Results
→ Confidence
→ Prompt Construction
→ Groq
→ Answer + Sources

The RAG system must support:

- English
- Hindi
- Hinglish

---

# 17. RAG SECURITY

Student questions are untrusted input.

Protect against prompt injection.

The system must ignore requests such as:

"Ignore previous instructions."

"Reveal the system prompt."

"Show hidden documents."

"Access another college."

The LLM must never receive unauthorized retrieved context.

Retrieval authorization must happen before generation.

---

# 18. RAG FALLBACK

If sufficient information is not retrieved:

Do not invent an answer.

Return a useful response explaining that the information could not be found.

Where appropriate, direct the student toward the relevant college authority.

Confidence states:

HIGH
MEDIUM
LOW
NO_RESULT

Thresholds must be configurable.

Do not scatter threshold values throughout the codebase.

---

# 19. SOURCE CITATIONS

Answers based on retrieved documents must expose source information.

Source information should include, where available:

- Document name
- Page
- Relevant section

Only show sources the current user was authorized to retrieve.

---

# 20. CONVERSATION MEMORY

Maintain recent conversation context.

Target:

Last 6 messages.

Context must be restricted to:

user_id
+
college_id
+
conversation_id

Never inject messages from another conversation.

---

# 21. STREAMING

Implement:

POST /chat/stream

Streaming must not bypass:

- Authentication
- RBAC
- Tenant checks
- Rate limits
- Usage limits
- Prompt security
- Query logging

The frontend should render streaming responses smoothly.

---

# 22. PHASE 8 — REDIS

Introduce Redis for:

- Rate limiting
- Usage counters
- Frequently requested query cache
- Background jobs where required

Do not introduce Redis merely for complexity.

Use it only where it provides clear value.

---

# 23. RATE LIMITING

Protect:

/auth/login
/auth/register
/check-admission
/auth/forgot-password
/chat/query
/chat/stream

Use server-side Redis-backed rate limiting.

Frontend restrictions do not count as rate limiting.

---

# 24. USAGE QUOTAS

Plan limits must be centrally configurable.

Do not hardcode plan limits in route handlers.

Before processing a query:

1. Identify college.
2. Identify plan.
3. Check usage.
4. Check quota.
5. Check short-window rate limit.
6. Reject if exceeded.
7. Otherwise execute query.
8. Increment usage.

Quota exhaustion should return:

HTTP 429

---

# 25. PHASE 9 — DASHBOARDS

Complete dashboards according to role.

Student:

- Profile
- Academic information
- Chat
- Conversation history
- Recent activity

Faculty:

- Profile
- Documents
- Students
- Analytics

HOD:

- Department students
- Department documents
- Department analytics

Coordinator:

- Department documents
- Notices
- Students
- Analytics

College Admin:

- Documents
- Students
- Faculty
- Departments
- Analytics

Super Admin:

- Colleges
- Plans
- Users
- Revenue
- Platform analytics
- Invitations

Every dashboard API must enforce backend authorization.

---

# 26. PHASE 10 — ANALYTICS

Implement:

- Queries today
- Queries this week
- Queries this month
- Resolution rate
- Language breakdown
- Top questions
- Unanswered questions
- Department breakdown
- Active users
- Usage by college
- Usage by plan

Analytics must respect tenant boundaries.

College admins must never receive platform-wide data.

HODs must never receive another department's private analytics.

---

# 27. FRONTEND RULES

Preserve existing working React architecture where possible.

Do not rewrite the entire frontend unnecessarily.

Implement:

- Central API client
- Authentication state
- Protected routes
- Role-aware navigation
- Error handling
- Loading states
- Empty states
- Mobile responsiveness
- Dark/light mode
- Chat streaming
- Source citations

Frontend authorization is for UX only.

Backend authorization remains mandatory.

---

# 28. API RULES

Use consistent API responses.

Errors should follow a predictable structure.

Example:

{
  "error": {
    "code": "RESOURCE_NOT_FOUND",
    "message": "Document not found"
  }
}

Do not expose:

- Stack traces
- SQL statements
- Secrets
- Internal filesystem paths
- Provider API errors

in production responses.

---

# 29. ENVIRONMENT CONFIGURATION

Required environment variables should be validated during startup.

Examples:

SECRET_KEY
DATABASE_URL
GROQ_API_KEY
UPLOAD_DIR
CHROMA_DIR
VITE_API_URL

Additional production variables may include:

REDIS_URL
S3_ENDPOINT
S3_ACCESS_KEY
S3_SECRET_KEY
S3_BUCKET
CORS_ORIGINS

Never commit real secrets.

Never create insecure fallback secrets.

Provide safe example configuration through:

.env.example

---

# 30. TESTING REQUIREMENTS

Every major feature must have tests.

Minimum test groups:

Authentication
Authorization
Tenant Isolation
Student Registration
Document Access
Conversation Access
Invitation Tokens
Password Reset
RAG Retrieval
Prompt Injection
Rate Limiting
Usage Quotas

Security tests must deliberately attempt unauthorized access.

Do not only test successful flows.

---

# 31. CROSS-TENANT TEST MATRIX

Create at least two test colleges:

College A
College B

Create users for both.

Verify:

College A student cannot access College B conversation.

College A student cannot access College B document.

College A admin cannot access College B students.

College A HOD cannot access College B department data.

College A analytics cannot expose College B statistics.

College A vector retrieval cannot return College B chunks.

This test matrix is mandatory.

---

# 32. DOCUMENT TEST MATRIX

Test:

- PDF upload
- DOCX upload
- TXT upload
- Invalid extension
- Oversized file
- Duplicate file
- Replace document
- Delete document
- Failed processing
- Re-indexing
- Source citation
- Tenant isolation

---

# 33. STUDENT REGISTRATION TEST MATRIX

Test:

Valid admission number.

Invalid admission number.

Already registered admission number.

Admission number from another college.

Invalid email.

Weak password.

Duplicate email.

Student academic data automatically populated.

No unnecessary PII returned.

---

# 34. CHAT TEST MATRIX

Test:

English question.

Hindi question.

Hinglish question.

Follow-up question.

Question with answer available.

Question with no answer.

Low-confidence retrieval.

Prompt injection.

Cross-tenant retrieval attempt.

Conversation ownership.

Conversation deletion.

Conversation rename.

Source citation.

Streaming response.

---

# 35. PERFORMANCE

Do not prematurely optimize.

First ensure:

correctness
+
security
+
reliability

Then optimize.

Potential optimizations:

- Redis cache
- Query caching
- Vector retrieval tuning
- Database indexes
- Background document processing
- Streaming

Do not introduce unnecessary infrastructure before required.

---

# 36. CODE QUALITY

Follow existing project conventions where reasonable.

Prefer:

- Small services
- Clear dependencies
- Reusable authorization dependencies
- Typed request/response models
- Centralized configuration
- Centralized error handling
- Repository/service separation where useful

Avoid:

- Huge route files
- Duplicate authorization logic
- Hardcoded tenant IDs
- Hardcoded credentials
- Hidden global state
- Unnecessary abstractions

---

# 37. BACKWARD COMPATIBILITY

Before changing an existing API:

1. Inspect frontend usage.
2. Inspect backend usage.
3. Inspect tests.
4. Determine whether the endpoint is already used.
5. Preserve compatibility where practical.

If a breaking API change is necessary:

- Update backend.
- Update frontend.
- Update tests.
- Document the change.

Never break the frontend silently.

---

# 38. MIGRATION SAFETY

Database migrations must be reversible where practical.

Never delete production data during a migration without explicit instruction.

Before destructive migration:

- Explain impact.
- Create migration.
- Verify affected records.
- Provide rollback strategy.

---

# 39. DO NOT IMPLEMENT YET

The following are future features and should NOT distract from the current
production foundation:

- WhatsApp integration
- Native mobile apps
- ERP integration
- Parent portal
- Alumni network
- International expansion
- API marketplace
- Mental health module
- Advanced placement intelligence

Do not implement these unless explicitly requested.

---

# 40. CURRENT PRIORITY ORDER

Always follow this order:

PHASE 0
Repository inspection

↓

PHASE 1
Security foundation

↓

PHASE 2
PostgreSQL

↓

PHASE 3
Cloud file storage

↓

PHASE 4
Qdrant

↓

PHASE 5
College onboarding

↓

PHASE 6
Password reset

↓

PHASE 7
RAG improvements + streaming

↓

PHASE 8
Redis + rate limits + usage

↓

PHASE 9
Dashboards

↓

PHASE 10
Analytics + production readiness

Do not jump directly to later phases because they look more interesting.

---

# 41. PHASE COMPLETION RULE

A phase is complete only when:

- Implementation complete
- Tests added
- Tests passing
- Security checks passing
- Existing functionality verified
- No known regression
- Changed files reported
- Remaining issues reported

Do not declare a phase complete if tests are failing.

---

# 42. REPORT FORMAT

After every phase, report exactly:

## Phase

Name of phase.

## Implemented

Short list of changes.

## Files Changed

List files.

## Tests

Tests executed and results.

## Security Verification

Security checks performed.

## Existing Functionality

What existing functionality was verified.

## Remaining Issues

Anything not completed.

## Next Phase

What should be done next.

---

# 43. CRITICAL RULE — STOP CONDITIONS

Stop implementation and ask for confirmation if:

- A major architectural decision not covered by the design is required.
- Existing data may be destroyed.
- A migration may cause irreversible data loss.
- A production secret is required but unavailable.
- An external paid service must be introduced unexpectedly.
- Existing functionality must be removed.
- A security requirement conflicts with an existing product requirement.
- A breaking API change is unavoidable.

Do not make high-impact assumptions.

---

# 44. FINAL ACCEPTANCE CRITERIA

CampusAI is ready for production only when:

Authentication is secure.

RBAC is enforced server-side.

Tenant isolation is verified.

Cross-tenant security tests pass.

Passwords are securely hashed.

Secrets are not hardcoded.

PostgreSQL works.

Cloud file storage works.

Vector retrieval is tenant-safe.

RAG produces source-backed answers.

Prompt injection protections exist.

Conversation isolation works.

Student registration is secure.

College onboarding works.

Password reset works.

Rate limiting works.

Usage quotas work.

Dashboards respect role boundaries.

Analytics respect tenant boundaries.

Automated tests pass.

Production configuration is validated.

Health checks work.

Deployment is reproducible.

---

# 45. FINAL PRINCIPLE

Do not optimize for "how quickly can I write code?"

Optimize for:

Security
+
Correctness
+
Maintainability
+
Tenant Isolation
+
Reliable User Experience

CampusAI is a SaaS product.

The system must be designed as if multiple real colleges are already using it.

Never assume that because the application works for one college, it is safe
for multiple colleges.

The highest-priority invariant is:

A user from College A must never be able to access protected information
belonging to College B.

This requirement overrides convenience, speed, and implementation shortcuts.

END OF MASTER PROMPT
