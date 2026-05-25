import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import aiosqlite
from dotenv import load_dotenv
from passlib.context import CryptContext


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.getenv("DATABASE_URL", "./chatdeva.db")
PASSWORD_CONTEXT = CryptContext(schemes=["sha256_crypt"], deprecated="auto")


def _resolve_db_path() -> str:
    raw_path = Path(DATABASE_URL)
    if raw_path.is_absolute():
        return str(raw_path)
    return str((BASE_DIR / raw_path).resolve())


DB_PATH = _resolve_db_path()


@asynccontextmanager
async def get_connection():
    conn = await aiosqlite.connect(DB_PATH)
    try:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    finally:
        await conn.close()


async def initialize_database() -> None:
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with get_connection() as conn:
        await conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS colleges (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                slug TEXT UNIQUE NOT NULL,
                api_key TEXT UNIQUE,
                plan TEXT DEFAULT 'starter',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                college_id TEXT,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('student', 'admin', 'super_admin')),
                name TEXT NOT NULL,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(college_id) REFERENCES colleges(id)
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                college_id TEXT NOT NULL,
                file_name TEXT NOT NULL,
                original_name TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                status TEXT DEFAULT 'processing',
                chunk_count INTEGER DEFAULT 0,
                file_size INTEGER,
                uploaded_by TEXT,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_indexed TIMESTAMP,
                auto_refresh BOOLEAN DEFAULT FALSE,
                version INTEGER DEFAULT 1,
                FOREIGN KEY(college_id) REFERENCES colleges(id),
                FOREIGN KEY(uploaded_by) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS query_logs (
                id TEXT PRIMARY KEY,
                college_id TEXT,
                user_id TEXT,
                query_text TEXT,
                response_text TEXT,
                language TEXT,
                confidence TEXT,
                escalated BOOLEAN DEFAULT FALSE,
                sources TEXT,
                response_time_ms INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(college_id) REFERENCES colleges(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                college_id TEXT,
                user_id TEXT,
                action TEXT,
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(college_id) REFERENCES colleges(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_college_id ON users(college_id);
            CREATE INDEX IF NOT EXISTS idx_documents_college_id ON documents(college_id);
            CREATE INDEX IF NOT EXISTS idx_query_logs_college_id ON query_logs(college_id);
            CREATE INDEX IF NOT EXISTS idx_query_logs_user_id ON query_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
            """
        )
        await conn.commit()

    await seed_demo_data()


async def seed_demo_data() -> None:
    admin_email = "admin@demo.com"
    student_email = "student@demo.com"
    super_email = "super@chatdeva.com"

    async with get_connection() as conn:
        await conn.execute(
            """
            INSERT OR IGNORE INTO colleges (id, name, slug, api_key, plan, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                "col_demo",
                "Demo College",
                "demo",
                "demo_api_key_col_demo",
                "starter",
                True,
                datetime.now(timezone.utc).isoformat(),
            ),
        )

        await _insert_user_if_missing(
            conn=conn,
            email=admin_email,
            password="admin123",
            role="admin",
            name="Demo Admin",
            college_id="col_demo",
        )
        await _insert_user_if_missing(
            conn=conn,
            email=student_email,
            password="student123",
            role="student",
            name="Demo Student",
            college_id="col_demo",
        )
        await _insert_user_if_missing(
            conn=conn,
            email=super_email,
            password="super123",
            role="super_admin",
            name="CampusAI Super Admin",
            college_id=None,
        )
        await conn.commit()


async def _insert_user_if_missing(
    conn: aiosqlite.Connection,
    email: str,
    password: str,
    role: str,
    name: str,
    college_id: str | None,
) -> None:
    existing = await conn.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = await existing.fetchone()
    await existing.close()
    if row:
        return

    await conn.execute(
        """
        INSERT INTO users (id, college_id, email, password_hash, role, name, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            college_id,
            email,
            PASSWORD_CONTEXT.hash(password),
            role,
            name,
            True,
            datetime.now(timezone.utc).isoformat(),
        ),
    )


async def fetch_one(query: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    async with get_connection() as conn:
        cursor = await conn.execute(query, params)
        row = await cursor.fetchone()
        await cursor.close()
        return dict(row) if row else None


async def fetch_all(query: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    async with get_connection() as conn:
        cursor = await conn.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()
        return [dict(row) for row in rows]


async def execute(query: str, params: tuple[Any, ...] = ()) -> int:
    async with get_connection() as conn:
        cursor = await conn.execute(query, params)
        await conn.commit()
        lastrowid = cursor.lastrowid
        await cursor.close()
        return lastrowid if lastrowid is not None else 0


async def execute_many(query: str, params_list: list[tuple[Any, ...]]) -> None:
    async with get_connection() as conn:
        await conn.executemany(query, params_list)
        await conn.commit()


async def log_audit(
    action: str,
    details: str,
    college_id: str | None = None,
    user_id: str | None = None,
) -> None:
    await execute(
        """
        INSERT INTO audit_logs (id, college_id, user_id, action, details, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            college_id,
            user_id,
            action,
            details,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
