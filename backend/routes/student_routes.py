import json

from fastapi import APIRouter, Depends, HTTPException

from auth import require_role
from database import execute, fetch_all, fetch_one
from models import StudentProfileResponse, StudentProfileUpdateRequest


router = APIRouter(tags=["Student"])


async def _get_student_profile(user_id: str) -> StudentProfileResponse | None:
    row = await fetch_one(
        """
        SELECT
            sp.id,
            sp.user_id,
            sp.college_id,
            sp.admission_no,
            sp.department,
            sp.course,
            sp.year,
            sp.semester,
            sp.section,
            sp.session,
            sp.batch,
            sp.roll_no,
            sp.phone,
            sp.gender,
            sp.category,
            sp.is_hosteler,
            sp.parent_phone,
            sp.created_at,
            u.name,
            u.email,
            c.name AS college_name
        FROM student_profiles sp
        JOIN users u ON u.id = sp.user_id
        JOIN colleges c ON c.id = sp.college_id
        WHERE sp.user_id = ?
        """,
        (user_id,),
    )
    return StudentProfileResponse(**row) if row else None


@router.get("/profile", response_model=StudentProfileResponse)
async def get_student_profile(
    current_user: dict = Depends(require_role("student")),
) -> StudentProfileResponse:
    try:
        profile = await _get_student_profile(current_user["id"])
        if not profile:
            raise HTTPException(status_code=404, detail="Student profile not found")
        return profile
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to fetch student profile: {exc}") from exc


@router.put("/profile", response_model=StudentProfileResponse)
async def update_student_profile(
    payload: StudentProfileUpdateRequest,
    current_user: dict = Depends(require_role("student")),
) -> StudentProfileResponse:
    try:
        profile = await _get_student_profile(current_user["id"])
        if not profile:
            raise HTTPException(status_code=404, detail="Student profile not found")

        updates = payload.model_dump(exclude_none=True)
        allowed_fields = {"phone", "parent_phone", "gender", "is_hosteler"}
        updates = {key: value for key, value in updates.items() if key in allowed_fields}

        if updates:
            clauses = ", ".join(f"{field} = ?" for field in updates)
            params = list(updates.values()) + [current_user["id"]]
            await execute(
                f"UPDATE student_profiles SET {clauses} WHERE user_id = ?",
                tuple(params),
            )

        updated = await _get_student_profile(current_user["id"])
        if not updated:
            raise HTTPException(status_code=404, detail="Student profile not found")
        return updated
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to update student profile: {exc}") from exc


@router.get("/dashboard")
async def get_student_dashboard(
    current_user: dict = Depends(require_role("student")),
) -> dict:
    try:
        profile = await _get_student_profile(current_user["id"])
        if not profile:
            raise HTTPException(status_code=404, detail="Student profile not found")

        recent_queries = await fetch_all(
            """
            SELECT id, query_text, response_text, language, confidence, escalated,
                   sources, response_time_ms, created_at
            FROM query_logs
            WHERE user_id = ? AND college_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT 5
            """,
            (current_user["id"], current_user["college_id"]),
        )
        total_queries = await fetch_one(
            "SELECT COUNT(*) AS total FROM query_logs WHERE user_id = ? AND college_id = ?",
            (current_user["id"], current_user["college_id"]),
        )
        documents_available = await fetch_one(
            "SELECT COUNT(*) AS total FROM documents WHERE college_id = ? AND status = 'active'",
            (current_user["college_id"],),
        )

        for query in recent_queries:
            query["sources"] = json.loads(query["sources"] or "[]")
            query["escalated"] = bool(query["escalated"])

        return {
            "student": profile,
            "recent_queries": recent_queries,
            "total_queries": int((total_queries or {}).get("total", 0) or 0),
            "college_name": profile.college_name,
            "quick_stats": {
                "documents_available": int((documents_available or {}).get("total", 0) or 0),
            },
        }
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to load student dashboard: {exc}") from exc
