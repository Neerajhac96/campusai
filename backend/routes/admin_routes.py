import csv
import io
import json
import os
import re
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import aiofiles
from dotenv import load_dotenv
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from pydantic import ValidationError

from auth import hash_password, require_role
from database import execute, fetch_all, fetch_one, log_audit
from ingest import delete_document_vectors, ingest_document
from models import (
    AdmittedStudentRow,
    AdminAnalyticsSummary,
    BulkUploadResponse,
    CreateDepartmentRequest,
    CreateFacultyRequest,
    CreateStudentRequest,
    DepartmentResponse,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentRecord,
    DocumentUploadScope,
    FacultyProfileResponse,
    UserInfo,
)


load_dotenv()

router = APIRouter(tags=["Admin"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt"}
ALLOWED_CATEGORIES = {
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
}

BASE_DIR = Path(__file__).resolve().parents[1]
UPLOAD_DIR = os.getenv("UPLOAD_DIR", "./uploads")
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
CSV_COLUMNS = {
    "admission_no",
    "name",
    "department",
    "course",
    "year",
    "semester",
    "section",
    "session",
    "batch",
    "roll_no",
    "phone",
    "gender",
    "category",
    "is_hosteler",
}


def _resolve_upload_dir() -> Path:
    path = Path(UPLOAD_DIR)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def _sanitize_file_name(original_name: str) -> str:
    ext = Path(original_name).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


def _parse_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"true", "1", "yes", "y"}


def _parse_subjects(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
        return decoded if isinstance(decoded, list) else []
    except json.JSONDecodeError:
        return []


async def _get_faculty_profile(user_id: str) -> dict | None:
    return await fetch_one(
        """
        SELECT fp.*, u.name, u.email, c.name AS college_name
        FROM faculty_profiles fp
        JOIN users u ON u.id = fp.user_id
        JOIN colleges c ON c.id = fp.college_id
        WHERE fp.user_id = ? AND fp.is_active = 1 AND u.is_active = 1
        """,
        (user_id,),
    )


def _faculty_response(row: dict) -> FacultyProfileResponse:
    payload = dict(row)
    payload["subjects"] = _parse_subjects(payload.get("subjects"))
    payload["is_active"] = bool(payload.get("is_active"))
    return FacultyProfileResponse(**payload)


async def _department_response(row: dict) -> DepartmentResponse:
    total_faculty = await fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM faculty_profiles
        WHERE college_id = ? AND department = ? AND is_active = 1
        """,
        (row["college_id"], row["code"]),
    )
    total_students = await fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM student_profiles
        WHERE college_id = ?
          AND (lower(department) = lower(?) OR lower(department) = lower(?))
        """,
        (row["college_id"], row["code"], row["name"]),
    )
    return DepartmentResponse(
        id=row["id"],
        college_id=row["college_id"],
        name=row["name"],
        code=row["code"],
        hod_name=row.get("hod_name"),
        coordinator_name=row.get("coordinator_name"),
        is_active=bool(row.get("is_active")),
        total_faculty=int((total_faculty or {}).get("total", 0) or 0),
        total_students=int((total_students or {}).get("total", 0) or 0),
    )


async def _resolve_document_scope(
    current_user: dict,
    requested_scope: str,
    requested_department: str | None,
    requested_subject: str | None,
) -> tuple[str, str | None, str | None]:
    role = current_user["role"]
    scope = (requested_scope or "college").strip().lower()
    if scope not in {"college", "department", "subject"}:
        raise HTTPException(status_code=400, detail="Invalid document scope")

    allowed = {
        "college": DocumentUploadScope.COLLEGE_WIDE,
        "department": DocumentUploadScope.DEPARTMENT_LEVEL,
        "subject": DocumentUploadScope.SUBJECT_LEVEL,
    }[scope]
    if role not in allowed:
        raise HTTPException(status_code=403, detail=f"{role} cannot upload {scope}-scoped documents")

    department = requested_department.strip() if requested_department else None
    subject = requested_subject.strip() if requested_subject else None

    if role in {"hod", "dept_coordinator", "faculty"}:
        profile = await _get_faculty_profile(current_user["id"])
        if not profile:
            raise HTTPException(status_code=404, detail="Faculty profile not found")
        department = profile["department"]

    if scope in {"department", "subject"} and not department:
        raise HTTPException(status_code=400, detail="Department is required for this document scope")
    if scope == "subject" and not subject:
        raise HTTPException(status_code=400, detail="Subject is required for subject-scoped documents")

    return scope, department, subject


async def _store_upload(file: UploadFile) -> tuple[str, str, int]:
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported file type. Allowed: PDF, DOCX, TXT",
        )

    payload = await file.read()
    file_size = len(payload)
    if file_size == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    max_size = MAX_FILE_SIZE_MB * 1024 * 1024
    if file_size > max_size:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File size exceeds {MAX_FILE_SIZE_MB}MB limit",
        )

    upload_dir = _resolve_upload_dir()
    upload_dir.mkdir(parents=True, exist_ok=True)
    file_name = _sanitize_file_name(file.filename or "document.txt")
    saved_path = upload_dir / file_name

    async with aiofiles.open(saved_path, "wb") as out_file:
        await out_file.write(payload)

    return str(saved_path), file_name, file_size


async def _run_ingestion_and_update_document(
    doc_id: str,
    college_id: str,
    file_path: str,
    file_name: str,
    doc_name: str,
    category: str,
    user_id: str,
    action_label: str,
    department: str | None = None,
    subject: str | None = None,
    doc_scope: str = "college",
) -> None:
    result = await ingest_document(
        file_path=file_path,
        college_id=college_id,
        doc_id=doc_id,
        doc_name=doc_name,
        category=category,
        department=department,
        subject=subject,
        doc_scope=doc_scope,
    )

    if result["success"]:
        await execute(
            """
            UPDATE documents
            SET status = ?, chunk_count = ?, last_indexed = ?
            WHERE id = ? AND college_id = ?
            """,
            (
                "active",
                result["chunks"],
                datetime.now(timezone.utc).isoformat(),
                doc_id,
                college_id,
            ),
        )
    else:
        await execute(
            """
            UPDATE documents
            SET status = ?, last_indexed = ?
            WHERE id = ? AND college_id = ?
            """,
            ("error", datetime.now(timezone.utc).isoformat(), doc_id, college_id),
        )

    await log_audit(
        action_label,
        json.dumps(
            {
                "doc_id": doc_id,
                "file_name": file_name,
                "original_name": doc_name,
                "category": category,
                "department": department,
                "subject": subject,
                "doc_scope": doc_scope,
                "success": result["success"],
                "chunks": result["chunks"],
                "message": result["message"],
            },
            ensure_ascii=False,
        ),
        college_id=college_id,
        user_id=user_id,
    )


@router.post("/documents/upload", response_model=DocumentCreateResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    category: str = Form(default="general"),
    department: str | None = Form(default=None),
    subject: str | None = Form(default=None),
    doc_scope: str = Form(default="college"),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("admin", "hod", "dept_coordinator", "faculty")),
) -> DocumentCreateResponse:
    try:
        college_id = current_user["college_id"]
        if not college_id:
            raise HTTPException(status_code=400, detail="Admin is not linked to any college")
        if category not in ALLOWED_CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category")
        resolved_scope, resolved_department, resolved_subject = await _resolve_document_scope(
            current_user=current_user,
            requested_scope=doc_scope,
            requested_department=department,
            requested_subject=subject,
        )

        saved_path, file_name, file_size = await _store_upload(file)
        doc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await execute(
            """
            INSERT INTO documents
            (id, college_id, file_name, original_name, category, status, chunk_count, file_size,
             uploaded_by, uploaded_at, auto_refresh, version, department, subject, doc_scope, uploaded_role)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                college_id,
                file_name,
                file.filename or file_name,
                category,
                "processing",
                0,
                file_size,
                current_user["id"],
                now,
                False,
                1,
                resolved_department,
                resolved_subject,
                resolved_scope,
                current_user["role"],
            ),
        )

        background_tasks.add_task(
            _run_ingestion_and_update_document,
            doc_id,
            college_id,
            saved_path,
            file_name,
            file.filename or file_name,
            category,
            current_user["id"],
            "document_uploaded",
            resolved_department,
            resolved_subject,
            resolved_scope,
        )

        return DocumentCreateResponse(
            doc_id=doc_id,
            status="processing",
            message="Upload accepted. Document indexing started in background.",
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc


@router.get("/documents/status/{doc_id}", response_model=DocumentRecord)
async def get_document_status(
    doc_id: str,
    current_user: dict = Depends(require_role("admin", "hod", "dept_coordinator", "faculty")),
) -> DocumentRecord:
    try:
        row = await fetch_one(
            "SELECT * FROM documents WHERE id = ? AND college_id = ?",
            (doc_id, current_user["college_id"]),
        )
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
        if current_user["role"] in {"hod", "dept_coordinator", "faculty"}:
            profile = await _get_faculty_profile(current_user["id"])
            if not profile:
                raise HTTPException(status_code=404, detail="Faculty profile not found")
            if (row.get("department") or "").lower() != (profile["department"] or "").lower():
                raise HTTPException(status_code=403, detail="Cannot view documents outside your department")
            if current_user["role"] == "faculty" and row.get("uploaded_by") != current_user["id"]:
                raise HTTPException(status_code=403, detail="Faculty can view only their own documents")
        return DocumentRecord(**row)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to fetch status: {exc}") from exc


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    category: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
    current_user: dict = Depends(require_role("admin", "hod", "dept_coordinator", "faculty")),
) -> DocumentListResponse:
    try:
        clauses = ["college_id = ?"]
        params: list[object] = [current_user["college_id"]]

        if current_user["role"] in {"hod", "dept_coordinator", "faculty"}:
            profile = await _get_faculty_profile(current_user["id"])
            if not profile:
                raise HTTPException(status_code=404, detail="Faculty profile not found")
            clauses.append("lower(COALESCE(department, '')) = lower(?)")
            params.append(profile["department"])
            if current_user["role"] == "faculty":
                clauses.append("uploaded_by = ?")
                params.append(current_user["id"])

        if category:
            clauses.append("category = ?")
            params.append(category)
        if status_filter:
            clauses.append("status = ?")
            params.append(status_filter)
        if search:
            clauses.append("lower(original_name) LIKE lower(?)")
            params.append(f"%{search}%")

        where_sql = " AND ".join(clauses)
        rows = await fetch_all(
            f"SELECT * FROM documents WHERE {where_sql} ORDER BY datetime(uploaded_at) DESC",
            tuple(params),
        )
        return DocumentListResponse(
            items=[DocumentRecord(**row) for row in rows],
            total=len(rows),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {exc}") from exc


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    current_user: dict = Depends(require_role("admin", "hod", "dept_coordinator", "faculty")),
) -> dict:
    try:
        college_id = current_user["college_id"]
        doc = await fetch_one(
            "SELECT * FROM documents WHERE id = ? AND college_id = ?",
            (doc_id, college_id),
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        if current_user["role"] in {"hod", "dept_coordinator", "faculty"}:
            profile = await _get_faculty_profile(current_user["id"])
            if not profile:
                raise HTTPException(status_code=404, detail="Faculty profile not found")
            if (doc.get("department") or "").lower() != (profile["department"] or "").lower():
                raise HTTPException(status_code=403, detail="Cannot delete documents outside your department")
            if current_user["role"] == "faculty" and doc.get("uploaded_by") != current_user["id"]:
                raise HTTPException(status_code=403, detail="Faculty can delete only their own documents")

        vector_deleted = await delete_document_vectors(college_id=college_id, doc_id=doc_id)
        await execute("DELETE FROM documents WHERE id = ? AND college_id = ?", (doc_id, college_id))

        file_path = _resolve_upload_dir() / doc["file_name"]
        if file_path.exists():
            file_path.unlink(missing_ok=True)

        await log_audit(
            "document_deleted",
            json.dumps(
                {
                    "doc_id": doc_id,
                    "file_name": doc["original_name"],
                    "vectors_deleted": vector_deleted,
                }
            ),
            college_id=college_id,
            user_id=current_user["id"],
        )
        return {"success": True, "message": "Document deleted successfully"}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Delete failed: {exc}") from exc


@router.put("/documents/{doc_id}/replace", response_model=DocumentCreateResponse)
async def replace_document(
    doc_id: str,
    background_tasks: BackgroundTasks,
    category: str | None = Form(default=None),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("admin")),
) -> DocumentCreateResponse:
    try:
        college_id = current_user["college_id"]
        current_doc = await fetch_one(
            "SELECT * FROM documents WHERE id = ? AND college_id = ?",
            (doc_id, college_id),
        )
        if not current_doc:
            raise HTTPException(status_code=404, detail="Document not found")

        chosen_category = category or current_doc["category"]
        if chosen_category not in ALLOWED_CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category")

        saved_path, file_name, file_size = await _store_upload(file)
        old_file_path = _resolve_upload_dir() / current_doc["file_name"]
        await delete_document_vectors(college_id=college_id, doc_id=doc_id)

        await execute(
            """
            UPDATE documents
            SET file_name = ?, original_name = ?, category = ?, status = ?, chunk_count = ?,
                file_size = ?, uploaded_by = ?, uploaded_at = ?, uploaded_role = ?, version = version + 1
            WHERE id = ? AND college_id = ?
            """,
            (
                file_name,
                file.filename or file_name,
                chosen_category,
                "processing",
                0,
                file_size,
                current_user["id"],
                datetime.now(timezone.utc).isoformat(),
                current_user["role"],
                doc_id,
                college_id,
            ),
        )

        if old_file_path.exists():
            old_file_path.unlink(missing_ok=True)

        background_tasks.add_task(
            _run_ingestion_and_update_document,
            doc_id,
            college_id,
            saved_path,
            file_name,
            file.filename or file_name,
            chosen_category,
            current_user["id"],
            "document_replaced",
            current_doc.get("department"),
            current_doc.get("subject"),
            current_doc.get("doc_scope") or "college",
        )

        return DocumentCreateResponse(
            doc_id=doc_id,
            status="processing",
            message="Replacement uploaded. Re-indexing started in background.",
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Replace failed: {exc}") from exc


@router.post("/students/bulk-upload", response_model=BulkUploadResponse)
async def bulk_upload_students(
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("admin")),
) -> BulkUploadResponse:
    try:
        college_id = current_user["college_id"]
        if not college_id:
            raise HTTPException(status_code=400, detail="Admin is not linked to any college")
        if not (file.filename or "").lower().endswith(".csv"):
            raise HTTPException(status_code=400, detail="Only CSV files are allowed")

        raw = await file.read()
        if not raw:
            raise HTTPException(status_code=400, detail="Uploaded CSV is empty")

        try:
            decoded = raw.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=400, detail="CSV must be UTF-8 encoded") from exc

        csv_lines = [
            line
            for line in decoded.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        reader = csv.DictReader(io.StringIO("\n".join(csv_lines)))
        if not reader.fieldnames:
            raise HTTPException(status_code=400, detail="CSV header row is required")

        missing_columns = CSV_COLUMNS.difference(set(reader.fieldnames))
        if missing_columns:
            raise HTTPException(
                status_code=400,
                detail=f"Missing required columns: {', '.join(sorted(missing_columns))}",
            )

        total_rows = 0
        success = 0
        errors: list[str] = []

        for row_number, row in enumerate(reader, start=2):
            total_rows += 1
            cleaned = {key: (value.strip() if isinstance(value, str) else value) for key, value in row.items()}
            cleaned["is_hosteler"] = _parse_bool(cleaned.get("is_hosteler"))
            try:
                admitted = AdmittedStudentRow(**cleaned)
            except ValidationError as exc:
                errors.append(f"Row {row_number}: {exc.errors()[0]['msg']}")
                continue

            existing = await fetch_one(
                "SELECT id FROM admitted_students WHERE college_id = ? AND admission_no = ?",
                (college_id, admitted.admission_no),
            )
            if existing:
                errors.append(
                    f"Row {row_number}: admission number {admitted.admission_no} already exists for this college"
                )
                continue

            await execute(
                """
                INSERT INTO admitted_students
                (id, college_id, admission_no, name, department, course, year, semester,
                 section, session, batch, roll_no, phone, gender, category, is_hosteler,
                 is_registered, uploaded_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(uuid.uuid4()),
                    college_id,
                    admitted.admission_no,
                    admitted.name,
                    admitted.department,
                    admitted.course,
                    admitted.year,
                    admitted.semester,
                    admitted.section,
                    admitted.session,
                    admitted.batch,
                    admitted.roll_no,
                    admitted.phone,
                    admitted.gender,
                    admitted.category or "general",
                    bool(admitted.is_hosteler),
                    False,
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
            success += 1

        await log_audit(
            "admitted_students_uploaded",
            json.dumps({"total_rows": total_rows, "success": success, "failed": len(errors)}),
            college_id=college_id,
            user_id=current_user["id"],
        )

        return BulkUploadResponse(
            total_uploaded=total_rows,
            success=success,
            failed=len(errors),
            errors=errors,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Student CSV upload failed: {exc}") from exc


@router.get("/students/admitted")
async def list_admitted_students(
    department: str | None = Query(default=None),
    year: int | None = Query(default=None, ge=1, le=4),
    section: str | None = Query(default=None),
    is_registered: bool | None = Query(default=None),
    current_user: dict = Depends(require_role("admin")),
) -> dict:
    try:
        clauses = ["college_id = ?"]
        params: list[object] = [current_user["college_id"]]

        if department:
            clauses.append("department = ?")
            params.append(department)
        if year:
            clauses.append("year = ?")
            params.append(year)
        if section:
            clauses.append("section = ?")
            params.append(section)
        if is_registered is not None:
            clauses.append("is_registered = ?")
            params.append(bool(is_registered))

        rows = await fetch_all(
            f"""
            SELECT *
            FROM admitted_students
            WHERE {' AND '.join(clauses)}
            ORDER BY department ASC, year ASC, section ASC, name ASC
            """,
            tuple(params),
        )
        return {"items": rows, "total": len(rows)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to list admitted students: {exc}") from exc


@router.post("/faculty")
async def create_faculty(
    payload: CreateFacultyRequest,
    current_user: dict = Depends(require_role("admin")),
) -> dict:
    try:
        college_id = current_user["college_id"]
        if not college_id:
            raise HTTPException(status_code=400, detail="Admin is not linked to any college")

        existing_employee = await fetch_one(
            "SELECT id FROM faculty_profiles WHERE college_id = ? AND employee_id = ?",
            (college_id, payload.employee_id),
        )
        if existing_employee:
            raise HTTPException(status_code=400, detail="Employee ID already exists for this college")

        existing_email = await fetch_one("SELECT id FROM users WHERE lower(email) = lower(?)", (payload.email,))
        if existing_email:
            raise HTTPException(status_code=400, detail="Email already exists")

        temp_password = f"campus{uuid.uuid4().hex[:6]}"
        user_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()
        await execute(
            """
            INSERT INTO users (id, college_id, email, password_hash, role, name, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                college_id,
                payload.email,
                hash_password(temp_password),
                payload.role_type,
                payload.name,
                True,
                now,
            ),
        )
        await execute(
            """
            INSERT INTO faculty_profiles
            (id, user_id, college_id, employee_id, department, designation, role_type,
             subjects, employment_type, joining_date, phone, gender, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                user_id,
                college_id,
                payload.employee_id,
                payload.department,
                payload.designation,
                payload.role_type,
                json.dumps(payload.subjects, ensure_ascii=False),
                payload.employment_type,
                payload.joining_date,
                payload.phone,
                payload.gender,
                True,
                now,
            ),
        )

        if payload.role_type in {"hod", "dept_coordinator"}:
            column = "hod_user_id" if payload.role_type == "hod" else "coordinator_user_id"
            await execute(
                f"""
                UPDATE departments
                SET {column} = ?
                WHERE college_id = ? AND (lower(code) = lower(?) OR lower(name) = lower(?))
                """,
                (user_id, college_id, payload.department, payload.department),
            )

        await log_audit(
            "faculty_created",
            json.dumps(
                {
                    "user_id": user_id,
                    "email": payload.email,
                    "role": payload.role_type,
                    "employee_id": payload.employee_id,
                }
            ),
            college_id=college_id,
            user_id=current_user["id"],
        )
        return {
            "success": True,
            "message": "Faculty account created successfully",
            "user_id": user_id,
            "temp_password": temp_password,
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to create faculty: {exc}") from exc


@router.get("/faculty", response_model=list[FacultyProfileResponse])
async def list_faculty(
    current_user: dict = Depends(require_role("admin", "hod")),
) -> list[FacultyProfileResponse]:
    try:
        college_id = current_user["college_id"]
        clauses = ["fp.college_id = ?"]
        params: list[object] = [college_id]

        if current_user["role"] == "hod":
            profile = await _get_faculty_profile(current_user["id"])
            if not profile:
                raise HTTPException(status_code=404, detail="Faculty profile not found")
            clauses.append("lower(fp.department) = lower(?)")
            params.append(profile["department"])

        rows = await fetch_all(
            f"""
            SELECT fp.*, u.name, u.email, c.name AS college_name
            FROM faculty_profiles fp
            JOIN users u ON u.id = fp.user_id
            JOIN colleges c ON c.id = fp.college_id
            WHERE {' AND '.join(clauses)}
            ORDER BY fp.department ASC, u.name ASC
            """,
            tuple(params),
        )
        return [_faculty_response(row) for row in rows]
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to list faculty: {exc}") from exc


@router.delete("/faculty/{user_id}")
async def delete_faculty(
    user_id: str,
    current_user: dict = Depends(require_role("admin")),
) -> dict:
    try:
        college_id = current_user["college_id"]
        profile = await fetch_one(
            "SELECT id FROM faculty_profiles WHERE user_id = ? AND college_id = ?",
            (user_id, college_id),
        )
        if not profile:
            raise HTTPException(status_code=404, detail="Faculty member not found")

        await execute("UPDATE users SET is_active = 0 WHERE id = ? AND college_id = ?", (user_id, college_id))
        await execute(
            "UPDATE faculty_profiles SET is_active = 0 WHERE user_id = ? AND college_id = ?",
            (user_id, college_id),
        )
        await log_audit(
            "faculty_deactivated",
            json.dumps({"user_id": user_id}),
            college_id=college_id,
            user_id=current_user["id"],
        )
        return {"success": True, "message": "Faculty account deactivated"}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to deactivate faculty: {exc}") from exc


@router.post("/departments", response_model=DepartmentResponse)
async def create_department(
    payload: CreateDepartmentRequest,
    current_user: dict = Depends(require_role("admin")),
) -> DepartmentResponse:
    try:
        college_id = current_user["college_id"]
        existing = await fetch_one(
            "SELECT id FROM departments WHERE college_id = ? AND lower(code) = lower(?)",
            (college_id, payload.code),
        )
        if existing:
            raise HTTPException(status_code=400, detail="Department code already exists")

        dept_id = str(uuid.uuid4())
        await execute(
            """
            INSERT INTO departments (id, college_id, name, code, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                dept_id,
                college_id,
                payload.name,
                payload.code.upper(),
                True,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        row = await fetch_one(
            """
            SELECT d.*, hu.name AS hod_name, cu.name AS coordinator_name
            FROM departments d
            LEFT JOIN users hu ON hu.id = d.hod_user_id
            LEFT JOIN users cu ON cu.id = d.coordinator_user_id
            WHERE d.id = ? AND d.college_id = ?
            """,
            (dept_id, college_id),
        )
        await log_audit(
            "department_created",
            json.dumps({"department_id": dept_id, "code": payload.code}),
            college_id=college_id,
            user_id=current_user["id"],
        )
        return await _department_response(row)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to create department: {exc}") from exc


@router.get("/departments", response_model=list[DepartmentResponse])
async def list_departments(
    current_user: dict = Depends(require_role("admin", "hod", "dept_coordinator", "faculty")),
) -> list[DepartmentResponse]:
    try:
        college_id = current_user["college_id"]
        clauses = ["d.college_id = ?"]
        params: list[object] = [college_id]

        if current_user["role"] != "admin":
            profile = await _get_faculty_profile(current_user["id"])
            if not profile:
                raise HTTPException(status_code=404, detail="Faculty profile not found")
            clauses.append("(lower(d.code) = lower(?) OR lower(d.name) = lower(?))")
            params.extend([profile["department"], profile["department"]])

        rows = await fetch_all(
            f"""
            SELECT d.*, hu.name AS hod_name, cu.name AS coordinator_name
            FROM departments d
            LEFT JOIN users hu ON hu.id = d.hod_user_id
            LEFT JOIN users cu ON cu.id = d.coordinator_user_id
            WHERE {' AND '.join(clauses)}
            ORDER BY d.name ASC
            """,
            tuple(params),
        )
        return [await _department_response(row) for row in rows]
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to list departments: {exc}") from exc


@router.get("/analytics/summary", response_model=AdminAnalyticsSummary)
async def get_admin_analytics(
    current_user: dict = Depends(require_role("admin", "hod", "dept_coordinator")),
) -> AdminAnalyticsSummary:
    try:
        college_id = current_user["college_id"]
        month_total = await fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM query_logs
            WHERE college_id = ? AND datetime(created_at) >= datetime('now', 'start of month')
            """,
            (college_id,),
        )
        language_rows = await fetch_all(
            """
            SELECT language, COUNT(*) AS count
            FROM query_logs
            WHERE college_id = ?
            GROUP BY language
            """,
            (college_id,),
        )
        resolved = await fetch_one(
            """
            SELECT
                SUM(CASE WHEN escalated = 0 THEN 1 ELSE 0 END) AS resolved,
                COUNT(*) AS total
            FROM query_logs
            WHERE college_id = ?
            """,
            (college_id,),
        )
        daily_rows = await fetch_all(
            """
            SELECT date(created_at) AS day, COUNT(*) AS count
            FROM query_logs
            WHERE college_id = ? AND datetime(created_at) >= datetime('now', '-30 days')
            GROUP BY date(created_at)
            ORDER BY date(created_at) ASC
            """,
            (college_id,),
        )
        query_texts = await fetch_all(
            """
            SELECT query_text
            FROM query_logs
            WHERE college_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 500
            """,
            (college_id,),
        )
        docs = await fetch_all(
            "SELECT original_name, category FROM documents WHERE college_id = ?",
            (college_id,),
        )
        log_sources = await fetch_all(
            "SELECT sources FROM query_logs WHERE college_id = ?",
            (college_id,),
        )

        language_breakdown = {"hindi": 0, "english": 0}
        for row in language_rows:
            language_breakdown[row["language"]] = row["count"]

        resolved_count = int((resolved or {}).get("resolved", 0) or 0)
        total_count = int((resolved or {}).get("total", 0) or 0)
        resolution_rate = round((resolved_count / total_count) * 100, 2) if total_count else 0.0

        normalized_questions: Counter[str] = Counter()
        for row in query_texts:
            text = (row["query_text"] or "").strip().lower()
            if not text:
                continue
            text = re.sub(r"[^\w\s]", "", text)
            text = re.sub(r"\s+", " ", text).strip()
            if text:
                normalized_questions[text] += 1

        top_questions = [
            {"question": question, "count": count}
            for question, count in normalized_questions.most_common(10)
        ]

        doc_name_to_category = {row["original_name"]: row["category"] for row in docs}
        category_counts: Counter[str] = Counter()
        for row in log_sources:
            for source in json.loads(row["sources"] or "[]"):
                base_name = source.split(" (Page")[0].strip()
                category = doc_name_to_category.get(base_name)
                if category:
                    category_counts[category] += 1

        category_breakdown = [
            {"category": name, "count": count}
            for name, count in category_counts.most_common()
        ]

        return AdminAnalyticsSummary(
            total_queries_month=int((month_total or {}).get("total", 0) or 0),
            language_breakdown=language_breakdown,
            resolution_rate=resolution_rate,
            top_questions=top_questions,
            queries_per_day=[{"day": row["day"], "count": row["count"]} for row in daily_rows],
            category_breakdown=category_breakdown,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Analytics failed: {exc}") from exc


@router.get("/users", response_model=list[UserInfo])
async def list_students(current_user: dict = Depends(require_role("admin"))) -> list[UserInfo]:
    try:
        rows = await fetch_all(
            """
            SELECT u.id, u.college_id, c.name AS college_name, u.email, u.role, u.name, u.is_active
            FROM users u
            LEFT JOIN colleges c ON u.college_id = c.id
            WHERE u.college_id = ? AND u.role = 'student'
            ORDER BY datetime(u.created_at) DESC
            """,
            (current_user["college_id"],),
        )
        return [UserInfo(**row) for row in rows]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to list users: {exc}") from exc


@router.post("/users", response_model=UserInfo)
async def create_student(
    payload: CreateStudentRequest,
    current_user: dict = Depends(require_role("admin")),
) -> UserInfo:
    try:
        existing = await fetch_one("SELECT id FROM users WHERE lower(email) = lower(?)", (payload.email,))
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

        user_id = str(uuid.uuid4())
        await execute(
            """
            INSERT INTO users (id, college_id, email, password_hash, role, name, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_id,
                current_user["college_id"],
                payload.email,
                hash_password(payload.password),
                "student",
                payload.name,
                True,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        await log_audit(
            "user_created",
            json.dumps({"user_id": user_id, "email": payload.email, "role": "student"}),
            college_id=current_user["college_id"],
            user_id=current_user["id"],
        )

        created = await fetch_one(
            """
            SELECT u.id, u.college_id, c.name AS college_name, u.email, u.role, u.name, u.is_active
            FROM users u
            LEFT JOIN colleges c ON u.college_id = c.id
            WHERE u.id = ?
            """,
            (user_id,),
        )
        return UserInfo(**created)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to create student: {exc}") from exc
