import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from auth import (
    TOKEN_EXPIRE_HOURS,
    authenticate_user,
    create_access_token,
    get_current_user,
    hash_password,
)
from database import fetch_one, get_connection
from models import (
    AdmissionCheckResponse,
    LoginRequest,
    LoginResponse,
    LogoutResponse,
    StudentProfileResponse,
    StudentRegisterRequest,
    StudentRegisterResponse,
    UserInfo,
)


router = APIRouter(tags=["Auth"])


async def _fetch_student_profile(user_id: str) -> StudentProfileResponse | None:
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


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest) -> LoginResponse:
    try:
        user = await authenticate_user(payload.email, payload.password)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
            )

        token = create_access_token(user)
        user_info = UserInfo(
            id=user["id"],
            college_id=user["college_id"],
            college_name=user.get("college_name"),
            email=user["email"],
            role=user["role"],
            name=user["name"],
            is_active=bool(user["is_active"]),
        )

        return LoginResponse(
            access_token=token,
            expires_in_hours=TOKEN_EXPIRE_HOURS,
            user=user_info,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Login failed: {exc}",
        ) from exc


@router.get("/check-admission", response_model=AdmissionCheckResponse)
async def check_admission(college_id: str, admission_no: str) -> AdmissionCheckResponse:
    try:
        row = await fetch_one(
            """
            SELECT admission_no
            FROM admitted_students
            WHERE college_id = ? AND admission_no = ? AND is_registered = 0
            """,
            (college_id.strip(), admission_no.strip()),
        )
        if not row:
            return AdmissionCheckResponse(
                valid=False,
                message="Invalid admission number or already registered",
            )
        return AdmissionCheckResponse(
            valid=True,
            message="Admission number verified",
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Admission check failed: {exc}",
        ) from exc


@router.post("/register", response_model=StudentRegisterResponse)
async def register_student(payload: StudentRegisterRequest) -> StudentRegisterResponse:
    try:
        if payload.password != payload.confirm_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password and confirm password do not match",
            )

        college_id = payload.college_id.strip()
        admission_no = payload.admission_no.strip()
        email = payload.email.lower()

        async with get_connection() as conn:
            existing_cursor = await conn.execute(
                "SELECT id FROM users WHERE lower(email) = lower(?)",
                (email,),
            )
            existing_user = await existing_cursor.fetchone()
            await existing_cursor.close()
            if existing_user:
                raise HTTPException(status_code=400, detail="Email already exists")

            admitted_cursor = await conn.execute(
                """
                SELECT *
                FROM admitted_students
                WHERE college_id = ? AND admission_no = ? AND is_registered = 0
                """,
                (college_id, admission_no),
            )
            admitted_row = await admitted_cursor.fetchone()
            await admitted_cursor.close()
            if not admitted_row:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid admission number or already registered",
                )

            college_cursor = await conn.execute(
                "SELECT id FROM colleges WHERE id = ? AND is_active = 1",
                (college_id,),
            )
            college = await college_cursor.fetchone()
            await college_cursor.close()
            if not college:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid or inactive college",
                )

            user_id = str(uuid.uuid4())
            profile_id = str(uuid.uuid4())
            now = datetime.now(timezone.utc).isoformat()

            await conn.execute("BEGIN")
            await conn.execute(
                """
                INSERT INTO users (id, college_id, email, password_hash, role, name, is_active, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    college_id,
                    email,
                    hash_password(payload.password),
                    "student",
                    admitted_row["name"],
                    True,
                    now,
                ),
            )
            await conn.execute(
                """
                INSERT INTO student_profiles
                (id, user_id, college_id, admission_no, department, course, year, semester,
                 section, session, batch, roll_no, phone, gender, category, is_hosteler,
                 parent_phone, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    profile_id,
                    user_id,
                    college_id,
                    admission_no,
                    admitted_row["department"],
                    admitted_row["course"],
                    admitted_row["year"],
                    admitted_row["semester"],
                    admitted_row["section"],
                    admitted_row["session"],
                    admitted_row["batch"],
                    admitted_row["roll_no"],
                    admitted_row["phone"],
                    admitted_row["gender"],
                    admitted_row["category"] or "general",
                    bool(admitted_row["is_hosteler"]),
                    payload.parent_phone,
                    now,
                ),
            )
            update_cursor = await conn.execute(
                """
                UPDATE admitted_students
                SET is_registered = 1
                WHERE college_id = ? AND admission_no = ? AND is_registered = 0
                """,
                (college_id, admission_no),
            )
            if update_cursor.rowcount != 1:
                await conn.rollback()
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid admission number or already registered",
                )
            await conn.commit()

        return StudentRegisterResponse(
            success=True,
            message="Student account created successfully",
            user_id=user_id,
        )
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Registration failed: {exc}",
        ) from exc


@router.get("/me", response_model=UserInfo)
async def me(current_user: dict = Depends(get_current_user)) -> UserInfo:
    try:
        return UserInfo(
            id=current_user["id"],
            college_id=current_user["college_id"],
            college_name=current_user.get("college_name"),
            email=current_user["email"],
            role=current_user["role"],
            name=current_user["name"],
            is_active=bool(current_user["is_active"]),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch profile: {exc}",
        ) from exc


@router.get("/profile")
async def profile(current_user: dict = Depends(get_current_user)) -> StudentProfileResponse | UserInfo:
    try:
        if current_user["role"] == "student":
            student_profile = await _fetch_student_profile(current_user["id"])
            if student_profile:
                return student_profile

        return UserInfo(
            id=current_user["id"],
            college_id=current_user["college_id"],
            college_name=current_user.get("college_name"),
            email=current_user["email"],
            role=current_user["role"],
            name=current_user["name"],
            is_active=bool(current_user["is_active"]),
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Unable to fetch profile: {exc}",
        ) from exc


@router.post("/logout", response_model=LogoutResponse)
async def logout(_: dict = Depends(get_current_user)) -> LogoutResponse:
    try:
        return LogoutResponse(success=True, message="Logged out successfully")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {exc}",
        ) from exc
