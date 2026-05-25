import json
import secrets
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from auth import hash_password, require_role
from database import execute, fetch_all, fetch_one, log_audit
from models import (
    CollegeCreateRequest,
    CollegeResponse,
    CollegeUpdateRequest,
    CreateCollegeAdminRequest,
    SuperStats,
    UserInfo,
)


router = APIRouter(tags=["Super Admin"])

PLAN_PRICING = {
    "starter": 15000,
    "growth": 60000,
    "university": 120000,
}


@router.get("/colleges", response_model=list[CollegeResponse])
async def list_colleges(_: dict = Depends(require_role("super_admin"))) -> list[CollegeResponse]:
    try:
        rows = await fetch_all(
            """
            SELECT
                c.id,
                c.name,
                c.slug,
                c.api_key,
                c.plan,
                c.is_active,
                c.created_at,
                (SELECT COUNT(*) FROM users u WHERE u.college_id = c.id) AS total_users,
                (SELECT COUNT(*) FROM documents d WHERE d.college_id = c.id) AS total_documents,
                (SELECT COUNT(*) FROM query_logs q WHERE q.college_id = c.id) AS total_queries
            FROM colleges c
            ORDER BY datetime(c.created_at) DESC
            """
        )
        return [CollegeResponse(**row) for row in rows]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to list colleges: {exc}") from exc


@router.post("/colleges", response_model=CollegeResponse)
async def create_college(
    payload: CollegeCreateRequest,
    current_user: dict = Depends(require_role("super_admin")),
) -> CollegeResponse:
    try:
        existing = await fetch_one("SELECT id FROM colleges WHERE id = ? OR slug = ?", (payload.id, payload.slug))
        if existing:
            raise HTTPException(status_code=400, detail="College id or slug already exists")

        api_key = payload.api_key or f"campusai_{payload.slug}_{secrets.token_hex(8)}"
        now = datetime.now(timezone.utc).isoformat()
        await execute(
            """
            INSERT INTO colleges (id, name, slug, api_key, plan, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (payload.id, payload.name, payload.slug, api_key, payload.plan, True, now),
        )

        await log_audit(
            "college_created",
            json.dumps(payload.model_dump(), ensure_ascii=False),
            college_id=payload.id,
            user_id=current_user["id"],
        )
        created = await fetch_one(
            """
            SELECT id, name, slug, api_key, plan, is_active, created_at,
                   0 AS total_users, 0 AS total_documents, 0 AS total_queries
            FROM colleges
            WHERE id = ?
            """,
            (payload.id,),
        )
        return CollegeResponse(**created)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to create college: {exc}") from exc


@router.put("/colleges/{college_id}", response_model=CollegeResponse)
async def update_college(
    college_id: str,
    payload: CollegeUpdateRequest,
    current_user: dict = Depends(require_role("super_admin")),
) -> CollegeResponse:
    try:
        existing = await fetch_one("SELECT * FROM colleges WHERE id = ?", (college_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="College not found")

        updates = payload.model_dump(exclude_none=True)
        if updates:
            clauses = ", ".join([f"{field} = ?" for field in updates.keys()])
            params = list(updates.values()) + [college_id]
            await execute(f"UPDATE colleges SET {clauses} WHERE id = ?", tuple(params))
            await log_audit(
                "college_updated",
                json.dumps({"college_id": college_id, "changes": updates}, ensure_ascii=False),
                college_id=college_id,
                user_id=current_user["id"],
            )

        updated = await fetch_one(
            """
            SELECT
                c.id,
                c.name,
                c.slug,
                c.api_key,
                c.plan,
                c.is_active,
                c.created_at,
                (SELECT COUNT(*) FROM users u WHERE u.college_id = c.id) AS total_users,
                (SELECT COUNT(*) FROM documents d WHERE d.college_id = c.id) AS total_documents,
                (SELECT COUNT(*) FROM query_logs q WHERE q.college_id = c.id) AS total_queries
            FROM colleges c
            WHERE c.id = ?
            """,
            (college_id,),
        )
        return CollegeResponse(**updated)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to update college: {exc}") from exc


@router.delete("/colleges/{college_id}")
async def deactivate_college(
    college_id: str,
    current_user: dict = Depends(require_role("super_admin")),
) -> dict:
    try:
        existing = await fetch_one("SELECT id FROM colleges WHERE id = ?", (college_id,))
        if not existing:
            raise HTTPException(status_code=404, detail="College not found")

        await execute("UPDATE colleges SET is_active = 0 WHERE id = ?", (college_id,))
        await log_audit(
            "college_deactivated",
            json.dumps({"college_id": college_id}),
            college_id=college_id,
            user_id=current_user["id"],
        )
        return {"success": True, "message": "College deactivated"}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to deactivate college: {exc}") from exc


@router.get("/users", response_model=list[UserInfo])
async def list_all_users(_: dict = Depends(require_role("super_admin"))) -> list[UserInfo]:
    try:
        rows = await fetch_all(
            """
            SELECT u.id, u.college_id, c.name AS college_name, u.email, u.role, u.name, u.is_active
            FROM users u
            LEFT JOIN colleges c ON u.college_id = c.id
            ORDER BY datetime(u.created_at) DESC
            """
        )
        return [UserInfo(**row) for row in rows]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to list users: {exc}") from exc


@router.post("/users", response_model=UserInfo)
async def create_college_admin(
    payload: CreateCollegeAdminRequest,
    current_user: dict = Depends(require_role("super_admin")),
) -> UserInfo:
    try:
        college = await fetch_one("SELECT id, name FROM colleges WHERE id = ?", (payload.college_id,))
        if not college:
            raise HTTPException(status_code=404, detail="College not found")
        existing = await fetch_one("SELECT id FROM users WHERE lower(email) = lower(?)", (payload.email,))
        if existing:
            raise HTTPException(status_code=400, detail="Email already exists")

        new_user_id = str(uuid.uuid4())
        await execute(
            """
            INSERT INTO users (id, college_id, email, password_hash, role, name, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_user_id,
                payload.college_id,
                payload.email,
                hash_password(payload.password),
                "admin",
                payload.name,
                True,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        await log_audit(
            "user_created",
            json.dumps({"user_id": new_user_id, "email": payload.email, "role": "admin"}),
            college_id=payload.college_id,
            user_id=current_user["id"],
        )

        user = await fetch_one(
            """
            SELECT u.id, u.college_id, c.name AS college_name, u.email, u.role, u.name, u.is_active
            FROM users u
            LEFT JOIN colleges c ON u.college_id = c.id
            WHERE u.id = ?
            """,
            (new_user_id,),
        )
        return UserInfo(**user)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to create admin: {exc}") from exc


@router.get("/stats", response_model=SuperStats)
async def get_super_stats(_: dict = Depends(require_role("super_admin"))) -> SuperStats:
    try:
        total_colleges = await fetch_one("SELECT COUNT(*) AS total FROM colleges WHERE is_active = 1")
        total_students = await fetch_one(
            "SELECT COUNT(*) AS total FROM users WHERE role = 'student' AND is_active = 1"
        )
        today = await fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM query_logs
            WHERE datetime(created_at) >= datetime('now', 'start of day')
            """
        )
        week = await fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM query_logs
            WHERE datetime(created_at) >= datetime('now', '-7 days')
            """
        )
        month = await fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM query_logs
            WHERE datetime(created_at) >= datetime('now', 'start of month')
            """
        )

        plan_rows = await fetch_all("SELECT plan, COUNT(*) AS count FROM colleges WHERE is_active = 1 GROUP BY plan")
        revenue = 0
        for row in plan_rows:
            revenue += PLAN_PRICING.get(row["plan"], PLAN_PRICING["starter"]) * row["count"]

        active_colleges = await fetch_all(
            """
            SELECT c.id, c.name, COUNT(q.id) AS queries
            FROM colleges c
            LEFT JOIN query_logs q ON q.college_id = c.id
            WHERE c.is_active = 1
            GROUP BY c.id, c.name
            ORDER BY queries DESC
            LIMIT 10
            """
        )

        return SuperStats(
            total_colleges=int((total_colleges or {}).get("total", 0) or 0),
            total_students=int((total_students or {}).get("total", 0) or 0),
            total_queries_today=int((today or {}).get("total", 0) or 0),
            total_queries_week=int((week or {}).get("total", 0) or 0),
            total_queries_month=int((month or {}).get("total", 0) or 0),
            revenue_estimate_inr=int(revenue),
            most_active_colleges=[
                {"college_id": row["id"], "college_name": row["name"], "queries": row["queries"]}
                for row in active_colleges
            ],
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to fetch stats: {exc}") from exc
