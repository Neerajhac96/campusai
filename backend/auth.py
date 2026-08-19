import os
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from database import fetch_one


load_dotenv()

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if os.getenv("ENV", "development").lower() == "production":
        raise RuntimeError("SECRET_KEY environment variable is missing in production!")
    SECRET_KEY = "chatdeva_dev_fallback_secret_key_change_in_production"

ALGORITHM = "HS256"
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))
PASSWORD_CONTEXT = CryptContext(
    schemes=["pbkdf2_sha256", "sha256_crypt"],
    deprecated="auto",
    pbkdf2_sha256__default_rounds=29000,
)
AUTH_SCHEME = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return PASSWORD_CONTEXT.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    return PASSWORD_CONTEXT.verify(plain_password, password_hash)


async def authenticate_user(email: str, password: str) -> dict[str, Any] | None:
    user = await fetch_one(
        """
        SELECT
            u.id,
            u.college_id,
            u.email,
            u.password_hash,
            u.role,
            u.name,
            u.is_active,
            c.name AS college_name,
            c.is_active AS college_active
        FROM users u
        LEFT JOIN colleges c ON u.college_id = c.id
        WHERE lower(u.email) = lower(?)
        """,
        (email,),
    )

    if not user:
        return None
    if not user["is_active"]:
        return None
    if user["role"] != "super_admin" and not user["college_active"]:
        return None
    if not verify_password(password, user["password_hash"]):
        return None
    return user


def create_access_token(user: dict[str, Any]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "user_id": user["id"],
        "email": user["email"],
        "role": user["role"],
        "college_id": user["college_id"],
        "name": user["name"],
        "exp": now + timedelta(hours=TOKEN_EXPIRE_HOURS),
        "iat": now,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(AUTH_SCHEME),
) -> dict[str, Any]:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    user = await fetch_one(
        """
        SELECT
            u.id,
            u.college_id,
            u.email,
            u.role,
            u.name,
            u.is_active,
            c.name AS college_name,
            c.is_active AS college_active
        FROM users u
        LEFT JOIN colleges c ON u.college_id = c.id
        WHERE u.id = ?
        """,
        (user_id,),
    )

    if not user or not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    if user["role"] != "super_admin" and not user["college_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="College account is deactivated",
        )

    return user


def require_role(*roles: str) -> Callable[..., Any]:
    async def role_checker(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
        if user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions for this resource",
            )
        return user

    return role_checker
