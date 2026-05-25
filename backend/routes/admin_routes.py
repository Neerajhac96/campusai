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

from auth import hash_password, require_role
from database import execute, fetch_all, fetch_one, log_audit
from ingest import delete_document_vectors, ingest_document
from models import (
    AdminAnalyticsSummary,
    CreateStudentRequest,
    DocumentCreateResponse,
    DocumentListResponse,
    DocumentRecord,
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


def _resolve_upload_dir() -> Path:
    path = Path(UPLOAD_DIR)
    if path.is_absolute():
        return path
    return (BASE_DIR / path).resolve()


def _sanitize_file_name(original_name: str) -> str:
    ext = Path(original_name).suffix.lower()
    return f"{uuid.uuid4().hex}{ext}"


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
) -> None:
    result = await ingest_document(
        file_path=file_path,
        college_id=college_id,
        doc_id=doc_id,
        doc_name=doc_name,
        category=category,
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
    file: UploadFile = File(...),
    current_user: dict = Depends(require_role("admin")),
) -> DocumentCreateResponse:
    try:
        college_id = current_user["college_id"]
        if not college_id:
            raise HTTPException(status_code=400, detail="Admin is not linked to any college")
        if category not in ALLOWED_CATEGORIES:
            raise HTTPException(status_code=400, detail="Invalid category")

        saved_path, file_name, file_size = await _store_upload(file)
        doc_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc).isoformat()

        await execute(
            """
            INSERT INTO documents
            (id, college_id, file_name, original_name, category, status, chunk_count, file_size,
             uploaded_by, uploaded_at, auto_refresh, version)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    current_user: dict = Depends(require_role("admin")),
) -> DocumentRecord:
    try:
        row = await fetch_one(
            "SELECT * FROM documents WHERE id = ? AND college_id = ?",
            (doc_id, current_user["college_id"]),
        )
        if not row:
            raise HTTPException(status_code=404, detail="Document not found")
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
    current_user: dict = Depends(require_role("admin")),
) -> DocumentListResponse:
    try:
        clauses = ["college_id = ?"]
        params: list[object] = [current_user["college_id"]]

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
    current_user: dict = Depends(require_role("admin")),
) -> dict:
    try:
        college_id = current_user["college_id"]
        doc = await fetch_one(
            "SELECT * FROM documents WHERE id = ? AND college_id = ?",
            (doc_id, college_id),
        )
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")

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
                file_size = ?, uploaded_by = ?, uploaded_at = ?, version = version + 1
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


@router.get("/analytics/summary", response_model=AdminAnalyticsSummary)
async def get_admin_analytics(
    current_user: dict = Depends(require_role("admin")),
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
