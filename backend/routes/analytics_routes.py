from fastapi import APIRouter, Depends, HTTPException, Query

from auth import require_role
from database import fetch_all


router = APIRouter(tags=["Analytics"])


@router.get("/analytics/recent")
async def recent_queries(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_role("admin")),
) -> dict:
    try:
        rows = await fetch_all(
            """
            SELECT id, query_text, language, confidence, escalated, response_time_ms, created_at
            FROM query_logs
            WHERE college_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT ?
            """,
            (current_user["college_id"], limit),
        )
        return {"items": rows, "total": len(rows)}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Unable to fetch recent analytics: {exc}") from exc
