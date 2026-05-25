from fastapi import APIRouter, Depends, HTTPException, status

from auth import (
    TOKEN_EXPIRE_HOURS,
    authenticate_user,
    create_access_token,
    get_current_user,
)
from models import LoginRequest, LoginResponse, LogoutResponse, UserInfo


router = APIRouter(tags=["Auth"])


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


@router.post("/logout", response_model=LogoutResponse)
async def logout(_: dict = Depends(get_current_user)) -> LogoutResponse:
    try:
        return LogoutResponse(success=True, message="Logged out successfully")
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Logout failed: {exc}",
        ) from exc
