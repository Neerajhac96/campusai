import os
import json
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
PASSWORD_CONTEXT = CryptContext(
    schemes=["sha256_crypt"],
    deprecated="auto",
    sha256_crypt__default_rounds=5000,
)


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
                role TEXT NOT NULL CHECK(role IN ('student', 'admin', 'super_admin', 'hod', 'dept_coordinator', 'faculty')),
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
                department TEXT DEFAULT NULL,
                subject TEXT DEFAULT NULL,
                doc_scope TEXT DEFAULT 'college',
                uploaded_role TEXT DEFAULT 'admin',
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

            CREATE TABLE IF NOT EXISTS admitted_students (
                id TEXT PRIMARY KEY,
                college_id TEXT NOT NULL,
                admission_no TEXT NOT NULL,
                name TEXT NOT NULL,
                department TEXT NOT NULL,
                course TEXT NOT NULL,
                year INTEGER NOT NULL,
                semester INTEGER NOT NULL,
                section TEXT NOT NULL,
                session TEXT NOT NULL,
                batch TEXT NOT NULL,
                roll_no TEXT,
                phone TEXT,
                gender TEXT,
                category TEXT DEFAULT 'general',
                is_hosteler BOOLEAN DEFAULT FALSE,
                is_registered BOOLEAN DEFAULT FALSE,
                uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(college_id, admission_no),
                FOREIGN KEY(college_id) REFERENCES colleges(id)
            );

            CREATE TABLE IF NOT EXISTS student_profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                college_id TEXT NOT NULL,
                admission_no TEXT NOT NULL,
                department TEXT NOT NULL,
                course TEXT NOT NULL,
                year INTEGER NOT NULL,
                semester INTEGER NOT NULL,
                section TEXT NOT NULL,
                session TEXT NOT NULL,
                batch TEXT NOT NULL,
                roll_no TEXT,
                phone TEXT,
                gender TEXT,
                category TEXT DEFAULT 'general',
                is_hosteler BOOLEAN DEFAULT FALSE,
                parent_phone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(college_id) REFERENCES colleges(id)
            );

            CREATE TABLE IF NOT EXISTS faculty_profiles (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL UNIQUE,
                college_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                department TEXT NOT NULL,
                designation TEXT NOT NULL,
                role_type TEXT NOT NULL CHECK(role_type IN ('hod', 'dept_coordinator', 'faculty')),
                subjects TEXT DEFAULT '[]',
                employment_type TEXT DEFAULT 'full_time',
                joining_date TEXT,
                phone TEXT,
                gender TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(college_id, employee_id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(college_id) REFERENCES colleges(id)
            );

            CREATE TABLE IF NOT EXISTS departments (
                id TEXT PRIMARY KEY,
                college_id TEXT NOT NULL,
                name TEXT NOT NULL,
                code TEXT NOT NULL,
                hod_user_id TEXT,
                coordinator_user_id TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(college_id, code),
                FOREIGN KEY(college_id) REFERENCES colleges(id),
                FOREIGN KEY(hod_user_id) REFERENCES users(id),
                FOREIGN KEY(coordinator_user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS conversations (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                college_id TEXT NOT NULL,
                title TEXT DEFAULT 'New Chat',
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(college_id) REFERENCES colleges(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                user_id TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user','assistant')),
                content TEXT NOT NULL,
                sources TEXT DEFAULT '[]',
                language TEXT DEFAULT 'english',
                confidence TEXT DEFAULT 'high',
                escalated BOOLEAN DEFAULT FALSE,
                response_time_ms INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(conversation_id) REFERENCES conversations(id),
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE INDEX IF NOT EXISTS idx_users_college_id ON users(college_id);
            CREATE INDEX IF NOT EXISTS idx_documents_college_id ON documents(college_id);
            CREATE INDEX IF NOT EXISTS idx_documents_uploaded_by ON documents(uploaded_by);
            CREATE INDEX IF NOT EXISTS idx_query_logs_college_id ON query_logs(college_id);
            CREATE INDEX IF NOT EXISTS idx_query_logs_user_id ON query_logs(user_id);
            CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at);
            CREATE INDEX IF NOT EXISTS idx_documents_status ON documents(status);
            CREATE INDEX IF NOT EXISTS idx_admitted_students_college_id ON admitted_students(college_id);
            CREATE INDEX IF NOT EXISTS idx_student_profiles_user_id ON student_profiles(user_id);
            CREATE INDEX IF NOT EXISTS idx_student_profiles_college_id ON student_profiles(college_id);
            CREATE INDEX IF NOT EXISTS idx_faculty_profiles_college_id ON faculty_profiles(college_id);
            CREATE INDEX IF NOT EXISTS idx_faculty_profiles_user_id ON faculty_profiles(user_id);
            CREATE INDEX IF NOT EXISTS idx_faculty_profiles_department ON faculty_profiles(department);
            CREATE INDEX IF NOT EXISTS idx_departments_college_id ON departments(college_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
            CREATE INDEX IF NOT EXISTS idx_conversations_updated ON conversations(updated_at);
            CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
            CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);
            """
        )
        await _add_documents_column_if_missing(conn, "department", "TEXT DEFAULT NULL")
        await _add_documents_column_if_missing(conn, "subject", "TEXT DEFAULT NULL")
        await _add_documents_column_if_missing(conn, "doc_scope", "TEXT DEFAULT 'college'")
        await _add_documents_column_if_missing(conn, "uploaded_role", "TEXT DEFAULT 'admin'")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_department ON documents(department)")
        await conn.commit()

    await seed_demo_data()


async def _add_documents_column_if_missing(
    conn: aiosqlite.Connection,
    column_name: str,
    column_definition: str,
) -> None:
    try:
        await conn.execute(f"ALTER TABLE documents ADD COLUMN {column_name} {column_definition}")
    except aiosqlite.OperationalError as exc:
        if "duplicate column name" not in str(exc).lower():
            raise


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
        await _seed_demo_departments(conn)
        await _seed_demo_faculty(conn)
        await _seed_demo_student_profile(conn, student_email)
        await conn.commit()


async def _insert_user_if_missing(
    conn: aiosqlite.Connection,
    email: str,
    password: str,
    role: str,
    name: str,
    college_id: str | None,
) -> str:
    existing = await conn.execute("SELECT id FROM users WHERE email = ?", (email,))
    row = await existing.fetchone()
    await existing.close()
    if row:
        return row["id"]

    user_id = str(uuid.uuid4())
    await conn.execute(
        """
        INSERT INTO users (id, college_id, email, password_hash, role, name, is_active, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            college_id,
            email,
            PASSWORD_CONTEXT.hash(password),
            role,
            name,
            True,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    return user_id


async def _seed_demo_departments(conn: aiosqlite.Connection) -> None:
    now = datetime.now(timezone.utc).isoformat()
    departments = [
        ("dept_cse_demo", "col_demo", "Computer Science", "CSE"),
        ("dept_mca_demo", "col_demo", "MCA", "MCA"),
        ("dept_it_demo", "col_demo", "Information Technology", "IT"),
    ]
    for dept_id, college_id, name, code in departments:
        await conn.execute(
            """
            INSERT OR IGNORE INTO departments
            (id, college_id, name, code, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (dept_id, college_id, name, code, True, now),
        )


async def _seed_demo_faculty(conn: aiosqlite.Connection) -> None:
    demo_faculty = [
        {
            "email": "hod.cse@demo.com",
            "password": "hod123",
            "role": "hod",
            "name": "Dr. Rajesh Kumar",
            "department": "CSE",
            "designation": "HOD",
            "employee_id": "EMP001",
            "subjects": [],
        },
        {
            "email": "coord.cse@demo.com",
            "password": "coord123",
            "role": "dept_coordinator",
            "name": "Prof. Anita Sharma",
            "department": "CSE",
            "designation": "Assistant Professor",
            "employee_id": "EMP002",
            "subjects": [],
        },
        {
            "email": "faculty.cse@demo.com",
            "password": "faculty123",
            "role": "faculty",
            "name": "Prof. Suresh Verma",
            "department": "CSE",
            "designation": "Assistant Professor",
            "employee_id": "EMP003",
            "subjects": ["Operating Systems", "Computer Networks"],
        },
    ]
    now = datetime.now(timezone.utc).isoformat()
    seeded_user_ids: dict[str, str] = {}
    for item in demo_faculty:
        user_id = await _insert_user_if_missing(
            conn=conn,
            email=item["email"],
            password=item["password"],
            role=item["role"],
            name=item["name"],
            college_id="col_demo",
        )
        seeded_user_ids[item["role"]] = user_id
        await conn.execute(
            """
            INSERT OR IGNORE INTO faculty_profiles
            (id, user_id, college_id, employee_id, department, designation, role_type,
             subjects, employment_type, joining_date, phone, gender, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(uuid.uuid4()),
                user_id,
                "col_demo",
                item["employee_id"],
                item["department"],
                item["designation"],
                item["role"],
                json.dumps(item["subjects"], ensure_ascii=False),
                "full_time",
                None,
                None,
                None,
                True,
                now,
            ),
        )

    await conn.execute(
        """
        UPDATE departments
        SET hod_user_id = COALESCE(hod_user_id, ?),
            coordinator_user_id = COALESCE(coordinator_user_id, ?)
        WHERE college_id = ? AND code = ?
        """,
        (
            seeded_user_ids.get("hod"),
            seeded_user_ids.get("dept_coordinator"),
            "col_demo",
            "CSE",
        ),
    )


async def _seed_demo_student_profile(conn: aiosqlite.Connection, student_email: str) -> None:
    cursor = await conn.execute("SELECT id FROM users WHERE email = ?", (student_email,))
    student = await cursor.fetchone()
    await cursor.close()
    if not student:
        return

    now = datetime.now(timezone.utc).isoformat()
    admission_no = "DEMO2024001"
    await conn.execute(
        """
        INSERT OR IGNORE INTO admitted_students
        (id, college_id, admission_no, name, department, course, year, semester,
         section, session, batch, roll_no, phone, gender, category, is_hosteler,
         is_registered, uploaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            "col_demo",
            admission_no,
            "Demo Student",
            "Computer Science",
            "BTech CSE",
            3,
            6,
            "A",
            "2021-25",
            "2021",
            "21CS000",
            "9876500000",
            "Other",
            "General",
            False,
            True,
            now,
        ),
    )
    await conn.execute(
        """
        INSERT OR IGNORE INTO student_profiles
        (id, user_id, college_id, admission_no, department, course, year, semester,
         section, session, batch, roll_no, phone, gender, category, is_hosteler,
         parent_phone, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            str(uuid.uuid4()),
            student["id"],
            "col_demo",
            admission_no,
            "Computer Science",
            "BTech CSE",
            3,
            6,
            "A",
            "2021-25",
            "2021",
            "21CS000",
            "9876500000",
            "Other",
            "General",
            False,
            None,
            now,
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
