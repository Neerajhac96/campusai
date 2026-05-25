import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status

from auth import require_role
from database import execute, fetch_all, fetch_one
from models import PaginatedQueryHistory, QueryLogResponse, QueryRequest, QueryResponse
from rag_engine import get_answer


router = APIRouter(tags=["Chat"])


@router.post("/query", response_model=QueryResponse)
async def query_chat(
    payload: QueryRequest,
    current_user: dict = Depends(require_role("student", "admin")),
) -> QueryResponse:
    try:
        college_id = current_user["college_id"]
        if not college_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not mapped to a college",
            )

        result = await get_answer(
            query=payload.query,
            college_id=college_id,
            college_name=current_user.get("college_name") or "Your College",
        )

        await execute(
            """
            INSERT INTO query_logs
            (id, college_id, user_id, query_text, response_text, language, confidence,
             escalated, sources, response_time_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                college_id,
                current_user["id"],
                payload.query,
                result["answer"],
                result["language"],
                result["confidence"],
                bool(result["escalate"]),
                json.dumps(result["sources"], ensure_ascii=False),
                int(result["response_time_ms"]),
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        return QueryResponse(**result)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {exc}",
        ) from exc


@router.get("/history", response_model=PaginatedQueryHistory)
async def get_chat_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(require_role("student", "admin")),
) -> PaginatedQueryHistory:
    try:
        offset = (page - 1) * limit
        count_row = await fetch_one(
            "SELECT COUNT(*) AS total FROM query_logs WHERE user_id = ?",
            (current_user["id"],),
        )
        rows = await fetch_all(
            """
            SELECT id, query_text, response_text, language, confidence, escalated, sources,
                   response_time_ms, created_at
            FROM query_logs
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC
            LIMIT ? OFFSET ?
            """,
            (current_user["id"], limit, offset),
        )

        items = [
            QueryLogResponse(
                id=row["id"],
                query_text=row["query_text"],
                response_text=row["response_text"],
                language=row["language"],
                confidence=row["confidence"],
                escalated=bool(row["escalated"]),
                sources=json.loads(row["sources"] or "[]"),
                response_time_ms=row["response_time_ms"] or 0,
                created_at=row["created_at"],
            )
            for row in rows
        ]
        return PaginatedQueryHistory(
            page=page,
            limit=limit,
            total=(count_row or {}).get("total", 0),
            items=items,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {exc}",
        ) from exc
