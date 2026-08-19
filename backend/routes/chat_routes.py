import json
import re
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from auth import get_current_user, require_role
from database import execute, fetch_all, fetch_one
from models import (
    ChatQueryRequest,
    ChatQueryResponse,
    ConversationDetailResponse,
    ConversationResponse,
    MessageResponse,
    PaginatedQueryHistory,
    QueryLogResponse,
)
from rag_engine import get_answer, get_groq_client


router = APIRouter(tags=["Chat"])


class ConversationTitleRequest(BaseModel):
    title: str = Field(min_length=1, max_length=80)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _preview(value: str | None) -> str:
    text = " ".join((value or "").split())
    return text[:60]


def _message_response(row: dict) -> MessageResponse:
    return MessageResponse(
        id=row["id"],
        conversation_id=row["conversation_id"],
        role=row["role"],
        content=row["content"],
        sources=json.loads(row.get("sources") or "[]"),
        language=row.get("language") or "english",
        confidence=row.get("confidence") or "high",
        escalated=bool(row.get("escalated")),
        response_time_ms=int(row.get("response_time_ms") or 0),
        created_at=str(row["created_at"]),
    )


def _conversation_response(row: dict) -> ConversationResponse:
    return ConversationResponse(
        id=row["id"],
        title=row.get("title") or "New Chat",
        is_active=bool(row.get("is_active")),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        last_message=_preview(row.get("last_message")),
        message_count=int(row.get("message_count") or 0),
    )


async def _get_conversation_for_user(conversation_id: str, user_id: str) -> dict:
    conversation = await fetch_one(
        """
        SELECT *
        FROM conversations
        WHERE id = ? AND user_id = ? AND is_active = 1
        """,
        (conversation_id, user_id),
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


async def _conversation_with_summary(conversation_id: str, user_id: str) -> ConversationResponse:
    row = await fetch_one(
        """
        SELECT c.*,
               (
                   SELECT m.content
                   FROM messages m
                   WHERE m.conversation_id = c.id
                   ORDER BY datetime(m.created_at) DESC
                   LIMIT 1
               ) AS last_message,
               (
                   SELECT COUNT(*)
                   FROM messages m
                   WHERE m.conversation_id = c.id
               ) AS message_count
        FROM conversations c
        WHERE c.id = ? AND c.user_id = ? AND c.is_active = 1
        """,
        (conversation_id, user_id),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conversation_response(row)


async def _create_conversation(user_id: str, college_id: str, title: str = "New Chat") -> str:
    conversation_id = str(uuid.uuid4())
    now = _now()
    await execute(
        """
        INSERT INTO conversations (id, user_id, college_id, title, is_active, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (conversation_id, user_id, college_id, title, True, now, now),
    )
    return conversation_id


async def _fetch_conversation_history(conversation_id: str) -> list[dict[str, str]]:
    rows = await fetch_all(
        """
        SELECT role, content
        FROM messages
        WHERE conversation_id = ?
        ORDER BY datetime(created_at) DESC
        LIMIT 6
        """,
        (conversation_id,),
    )
    return [
        {"role": row["role"], "content": row["content"]}
        for row in reversed(rows)
        if row["role"] in {"user", "assistant"}
    ]


def _fallback_title(first_message: str) -> str:
    words = re.findall(r"[\w']+", first_message.strip())
    title = " ".join(words[:5]).strip()
    return title or "New Chat"


def _generate_conversation_title(first_message: str) -> str:
    client = get_groq_client()
    if client is None:
        return _fallback_title(first_message)
    try:
        completion = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            temperature=0.2,
            max_tokens=24,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Generate a short 4-5 word title for a conversation that starts with: "
                        f"'{first_message}'. Return ONLY the title, no quotes, no punctuation at end."
                    ),
                }
            ],
        )
        title = (completion.choices[0].message.content or "").strip().strip("\"'")
        title = re.sub(r"[.!?]+$", "", title).strip()
        return title[:80] or _fallback_title(first_message)
    except Exception:  # noqa: BLE001
        return _fallback_title(first_message)


@router.post("/query", response_model=ChatQueryResponse)
async def query_chat(
    payload: ChatQueryRequest,
    current_user: dict = Depends(require_role("student", "admin", "faculty", "hod", "dept_coordinator")),
) -> ChatQueryResponse:
    try:
        college_id = current_user["college_id"]
        if not college_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not mapped to a college",
            )

        if payload.conversation_id:
            conversation = await _get_conversation_for_user(payload.conversation_id, current_user["id"])
            conversation_id = conversation["id"]
        else:
            conversation_id = await _create_conversation(current_user["id"], college_id)
            conversation = await _get_conversation_for_user(conversation_id, current_user["id"])

        message_count_row = await fetch_one(
            "SELECT COUNT(*) AS total FROM messages WHERE conversation_id = ?",
            (conversation_id,),
        )
        is_first_message = int((message_count_row or {}).get("total", 0) or 0) == 0
        conversation_history = await _fetch_conversation_history(conversation_id)

        now = _now()
        user_message_id = str(uuid.uuid4())
        await execute(
            """
            INSERT INTO messages
            (id, conversation_id, user_id, role, content, sources, language, confidence,
             escalated, response_time_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user_message_id,
                conversation_id,
                current_user["id"],
                "user",
                payload.query,
                "[]",
                "english",
                "high",
                False,
                0,
                now,
            ),
        )

        result = await get_answer(
            query=payload.query,
            college_id=college_id,
            college_name=current_user.get("college_name") or "Your College",
            user_id=current_user["id"],
            conversation_history=conversation_history,
        )

        assistant_message_id = str(uuid.uuid4())
        await execute(
            """
            INSERT INTO messages
            (id, conversation_id, user_id, role, content, sources, language, confidence,
             escalated, response_time_ms, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                assistant_message_id,
                conversation_id,
                current_user["id"],
                "assistant",
                result["answer"],
                json.dumps(result["sources"], ensure_ascii=False),
                result["language"],
                result["confidence"],
                bool(result["escalate"]),
                int(result["response_time_ms"]),
                _now(),
            ),
        )

        conversation_title = conversation["title"] or "New Chat"
        if is_first_message:
            conversation_title = _generate_conversation_title(payload.query)

        await execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (conversation_title, _now(), conversation_id, current_user["id"]),
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
                _now(),
            ),
        )

        return ChatQueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            language=result["language"],
            confidence=result["confidence"],
            escalate=bool(result["escalate"]),
            response_time_ms=int(result["response_time_ms"]),
            conversation_id=conversation_id,
            message_id=assistant_message_id,
            conversation_title=conversation_title,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process query: {exc}",
        ) from exc


@router.get("/conversations", response_model=list[ConversationResponse])
async def list_conversations(current_user: dict = Depends(get_current_user)) -> list[ConversationResponse]:
    try:
        rows = await fetch_all(
            """
            SELECT c.*,
                   (
                       SELECT m.content
                       FROM messages m
                       WHERE m.conversation_id = c.id
                       ORDER BY datetime(m.created_at) DESC
                       LIMIT 1
                   ) AS last_message,
                   (
                       SELECT COUNT(*)
                       FROM messages m
                       WHERE m.conversation_id = c.id
                   ) AS message_count
            FROM conversations c
            WHERE c.user_id = ? AND c.is_active = 1
            ORDER BY datetime(c.updated_at) DESC
            """,
            (current_user["id"],),
        )
        return [_conversation_response(row) for row in rows]
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to list conversations: {exc}") from exc


@router.post("/conversations/new", response_model=ConversationResponse)
async def create_new_conversation(current_user: dict = Depends(get_current_user)) -> ConversationResponse:
    try:
        college_id = current_user["college_id"]
        if not college_id:
            raise HTTPException(status_code=400, detail="User is not mapped to a college")
        conversation_id = await _create_conversation(current_user["id"], college_id)
        return await _conversation_with_summary(conversation_id, current_user["id"])
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to create conversation: {exc}") from exc


@router.get("/conversations/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
) -> ConversationDetailResponse:
    try:
        conversation = await _get_conversation_for_user(conversation_id, current_user["id"])
        rows = await fetch_all(
            """
            SELECT *
            FROM messages
            WHERE conversation_id = ?
            ORDER BY datetime(created_at) ASC
            """,
            (conversation_id,),
        )
        return ConversationDetailResponse(
            id=conversation["id"],
            title=conversation["title"],
            messages=[_message_response(row) for row in rows],
            created_at=str(conversation["created_at"]),
            updated_at=str(conversation["updated_at"]),
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to fetch conversation: {exc}") from exc


@router.delete("/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    try:
        await _get_conversation_for_user(conversation_id, current_user["id"])
        await execute(
            "UPDATE conversations SET is_active = 0, updated_at = ? WHERE id = ? AND user_id = ?",
            (_now(), conversation_id, current_user["id"]),
        )
        return {"success": True, "message": "Conversation deleted"}
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {exc}") from exc


@router.put("/conversations/{conversation_id}/title", response_model=ConversationResponse)
async def update_conversation_title(
    conversation_id: str,
    payload: ConversationTitleRequest,
    current_user: dict = Depends(get_current_user),
) -> ConversationResponse:
    try:
        await _get_conversation_for_user(conversation_id, current_user["id"])
        await execute(
            "UPDATE conversations SET title = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (payload.title.strip(), _now(), conversation_id, current_user["id"]),
        )
        return await _conversation_with_summary(conversation_id, current_user["id"])
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=f"Failed to update title: {exc}") from exc


@router.get("/history", response_model=PaginatedQueryHistory)
async def get_chat_history(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
) -> PaginatedQueryHistory:
    try:
        offset = (page - 1) * limit
        count_row = await fetch_one(
            """
            SELECT COUNT(*) AS total
            FROM messages m
            JOIN conversations c ON c.id = m.conversation_id
            WHERE m.user_id = ? AND m.role = 'assistant' AND c.is_active = 1
            """,
            (current_user["id"],),
        )
        rows = await fetch_all(
            """
            SELECT
                a.id,
                COALESCE(
                    (
                        SELECT u.content
                        FROM messages u
                        WHERE u.conversation_id = a.conversation_id
                          AND u.role = 'user'
                          AND datetime(u.created_at) <= datetime(a.created_at)
                        ORDER BY datetime(u.created_at) DESC
                        LIMIT 1
                    ),
                    ''
                ) AS query_text,
                a.content AS response_text,
                a.language,
                a.confidence,
                a.escalated,
                a.sources,
                a.response_time_ms,
                a.created_at
            FROM messages a
            JOIN conversations c ON c.id = a.conversation_id
            WHERE a.user_id = ? AND a.role = 'assistant' AND c.is_active = 1
            ORDER BY datetime(a.created_at) DESC
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
            total=int((count_row or {}).get("total", 0) or 0),
            items=items,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch history: {exc}",
        ) from exc
