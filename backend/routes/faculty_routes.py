import json
from collections import Counter
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_role
from database import execute, fetch_all, fetch_one
from models import (
    DepartmentResponse,
    FacultyDashboardResponse,
    FacultyProfileResponse,
    FacultyProfileUpdateRequest,
)


router = APIRouter(tags=["Faculty"])


def _parse_subjects(value: str | None) -> list[str]:
    if not value:
        return []
    try:
        decoded = json.loads(value)
        return decoded if isinstance(decoded, list) else []
    except json.JSONDecodeError:
        return []


def _faculty_response(row: dict) -> FacultyProfileResponse:
    payload = dict(row)
    payload["subjects"] = _parse_subjects(payload.get("subjects"))
    payload["is_active"] = bool(payload.get("is_active"))
    return FacultyProfileResponse(**payload)


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


async def _department_response(college_id: str, department: str) -> DepartmentResponse:
    row = await fetch_one(
        """
        SELECT d.*, hu.name AS hod_name, cu.name AS coordinator_name
        FROM departments d
        LEFT JOIN users hu ON hu.id = d.hod_user_id
        LEFT JOIN users cu ON cu.id = d.coordinator_user_id
        WHERE d.college_id = ? AND (lower(d.code) = lower(?) OR lower(d.name) = lower(?))
        """,
        (college_id, department, department),
    )
    if not row:
        row = {
            "id": "",
            "college_id": college_id,
            "name": department,
            "code": department,
            "hod_name": None,
            "coordinator_name": None,
            "is_active": True,
        }

    total_faculty = await fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM faculty_profiles
        WHERE college_id = ? AND lower(department) = lower(?) AND is_active = 1
        """,
        (college_id, department),
    )
    total_students = await fetch_one(
        """
        SELECT COUNT(*) AS total
        FROM student_profiles
        WHERE college_id = ?
          AND (lower(department) = lower(?) OR lower(department) = lower(?))
        """,
        (college_id, row["code"], row["name"]),
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


@router.get("/profile", response_model=FacultyProfileResponse)
async def get_faculty_profile(
    current_user: dict = Depends(require_role("hod", "dept_coordinator", "faculty")),
) -> FacultyProfileResponse:
    try:
        profile = await _get_faculty_profile(current_user["id"])
        if not profile:
            raise HTTPException(status_code=404, detail="Faculty profile not found")
        return _faculty_response(profile)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to fetch faculty profile: {exc}") from exc


@router.put("/profile", response_model=FacultyProfileResponse)
async def update_faculty_profile(
    payload: FacultyProfileUpdateRequest,
    current_user: dict = Depends(require_role("hod", "dept_coordinator", "faculty")),
) -> FacultyProfileResponse:
    try:
        profile = await _get_faculty_profile(current_user["id"])
        if not profile:
            raise HTTPException(status_code=404, detail="Faculty profile not found")

        await execute(
            """
            UPDATE faculty_profiles
            SET phone = COALESCE(?, phone),
                gender = COALESCE(?, gender),
                subjects = COALESCE(?, subjects)
            WHERE user_id = ? AND college_id = ?
            """,
            (
                payload.phone,
                payload.gender,
                json.dumps(payload.subjects, ensure_ascii=False) if payload.subjects is not None else None,
                current_user["id"],
                current_user["college_id"],
            ),
        )
        updated = await _get_faculty_profile(current_user["id"])
        return _faculty_response(updated)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to update faculty profile: {exc}") from exc


@router.get("/students")
async def get_department_students(
    year: int | None = Query(default=None, ge=1, le=4),
    semester: int | None = Query(default=None, ge=1, le=8),
    section: str | None = Query(default=None),
    current_user: dict = Depends(require_role("hod", "dept_coordinator", "faculty")),
) -> dict:
    try:
        profile = await _get_faculty_profile(current_user["id"])
        if not profile:
            raise HTTPException(status_code=404, detail="Faculty profile not found")
        department = await _department_response(profile["college_id"], profile["department"])

        clauses = [
            "sp.college_id = ?",
            "(lower(sp.department) = lower(?) OR lower(sp.department) = lower(?))",
        ]
        params: list[object] = [profile["college_id"], department.code, department.name]
        if year:
            clauses.append("sp.year = ?")
            params.append(year)
        if semester:
            clauses.append("sp.semester = ?")
            params.append(semester)
        if section:
            clauses.append("lower(sp.section) = lower(?)")
            params.append(section)

        rows = await fetch_all(
            f"""
            SELECT sp.admission_no, sp.department, sp.course, sp.year, sp.semester,
                   sp.section, sp.roll_no, u.name, u.email
            FROM student_profiles sp
            JOIN users u ON u.id = sp.user_id
            WHERE {' AND '.join(clauses)}
            ORDER BY sp.year ASC, sp.semester ASC, sp.section ASC, u.name ASC
            """,
            tuple(params),
        )
        return {"items": rows, "total": len(rows)}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to fetch department students: {exc}") from exc


@router.get("/dashboard", response_model=FacultyDashboardResponse)
async def get_faculty_dashboard(
    current_user: dict = Depends(require_role("hod", "dept_coordinator", "faculty")),
) -> FacultyDashboardResponse:
    try:
        profile_row = await _get_faculty_profile(current_user["id"])
        if not profile_row:
            raise HTTPException(status_code=404, detail="Faculty profile not found")
        profile = _faculty_response(profile_row)
        department_info = await _department_response(profile.college_id, profile.department)

        my_documents = await fetch_all(
            """
            SELECT id, original_name, category, status, chunk_count, uploaded_at,
                   department, subject, doc_scope
            FROM documents
            WHERE college_id = ? AND uploaded_by = ?
            ORDER BY datetime(uploaded_at) DESC
            LIMIT 10
            """,
            (profile.college_id, profile.user_id),
        )
        total_docs = await fetch_one(
            "SELECT COUNT(*) AS total FROM documents WHERE college_id = ? AND uploaded_by = ?",
            (profile.college_id, profile.user_id),
        )
        today_queries = await fetch_all(
            """
            SELECT q.query_text
            FROM query_logs q
            JOIN student_profiles sp ON sp.user_id = q.user_id
            WHERE q.college_id = ?
              AND date(q.created_at) = date('now')
              AND (lower(sp.department) = lower(?) OR lower(sp.department) = lower(?))
            """,
            (profile.college_id, department_info.code, department_info.name),
        )
        normalized = Counter(
            (row["query_text"] or "").strip().lower()
            for row in today_queries
            if (row["query_text"] or "").strip()
        )

        return FacultyDashboardResponse(
            profile=profile,
            department_info=department_info,
            my_documents=my_documents,
            total_documents=int((total_docs or {}).get("total", 0) or 0),
            student_queries_today=len(today_queries),
            top_queries=[question for question, _ in normalized.most_common(5)],
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to fetch faculty dashboard: {exc}") from exc
