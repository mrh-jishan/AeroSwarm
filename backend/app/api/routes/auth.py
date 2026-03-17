"""Authentication API routes."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import AuthContext, require_user_context
from app.models.base import AuthSession, PasswordResetToken, User
from app.services.auth import AuthService
from app.services.rate_limiter import RateLimiterService

router = APIRouter()
auth_service = AuthService()
rate_limiter = RateLimiterService()


def _normalize_email(value: str) -> str:
    email = value.strip().lower()
    if "@" not in email or "." not in email.rsplit("@", maxsplit=1)[-1]:
        raise HTTPException(status_code=400, detail="Invalid email address")
    return email


class RegisterRequest(BaseModel):
    email: str
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str


class AuthResponse(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str | None = None


class LogoutRequest(BaseModel):
    refresh_token: str | None = None


class PasswordResetRequestBody(BaseModel):
    email: str


class PasswordResetConfirmRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class PasswordResetRequestResponse(BaseModel):
    accepted: bool = True
    reset_token: str | None = None


def _client_host(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    response.set_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        value=access_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/",
    )
    response.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(
        key=settings.ACCESS_COOKIE_NAME,
        path="/",
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )
    response.delete_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        path="/",
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
    )


def _resolve_refresh_token(request: Request, payload_token: str | None) -> str | None:
    return payload_token or request.cookies.get(settings.REFRESH_COOKIE_NAME)


def _build_auth_response(user: User, access_token: str, refresh_token: str) -> AuthResponse:
    if settings.EXPOSE_DEV_TOKENS:
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=UserResponse(id=user.id, email=user.email),
        )
    return AuthResponse(user=UserResponse(id=user.id, email=user.email))


async def _issue_auth_response(
    db: AsyncSession,
    user: User,
    request: Request,
    response: Response,
    *,
    replace_session: AuthSession | None = None,
) -> AuthResponse:
    refresh_token = auth_service.create_refresh_token()
    refresh_hash = auth_service.hash_refresh_token(refresh_token)
    access_token = auth_service.create_access_token(user.id, user.email)

    if replace_session is not None:
        replace_session.revoked_at = datetime.now(timezone.utc)

    auth_session = AuthSession(
        user_id=user.id,
        refresh_token_hash=refresh_hash,
        user_agent=request.headers.get("user-agent"),
        ip_address=_client_host(request),
        expires_at=auth_service.refresh_token_expires_at(),
    )
    db.add(auth_session)
    await db.commit()

    _set_auth_cookies(response, access_token, refresh_token)
    return _build_auth_response(user, access_token, refresh_token)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(
    payload: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    email = _normalize_email(payload.email)
    rate_key = f"auth:register:{_client_host(request)}:{email}"
    if await rate_limiter.is_limited(rate_key, settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS):
        raise HTTPException(status_code=429, detail="Too many registration attempts")

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none() is not None:
        await rate_limiter.increment(rate_key, settings.AUTH_RATE_LIMIT_WINDOW_SECONDS)
        raise HTTPException(status_code=409, detail="User already exists")

    user = User(
        email=email,
        password_hash=auth_service.hash_password(payload.password),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    await rate_limiter.reset(rate_key)
    return await _issue_auth_response(db, user, request, response)


@router.post("/login", response_model=AuthResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    email = _normalize_email(payload.email)
    rate_key = f"auth:login:{_client_host(request)}:{email}"
    if await rate_limiter.is_limited(rate_key, settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS):
        raise HTTPException(status_code=429, detail="Too many login attempts")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None or not auth_service.verify_password(payload.password, user.password_hash):
        await rate_limiter.increment(rate_key, settings.AUTH_RATE_LIMIT_WINDOW_SECONDS)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    await rate_limiter.reset(rate_key)
    return await _issue_auth_response(db, user, request, response)


@router.post("/refresh", response_model=AuthResponse)
async def refresh(
    request: Request,
    response: Response,
    payload: RefreshRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = _resolve_refresh_token(request, payload.refresh_token if payload else None)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")

    token_hash = auth_service.hash_refresh_token(refresh_token)
    result = await db.execute(
        select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
    )
    auth_session = result.scalar_one_or_none()
    if auth_session is None or auth_session.revoked_at is not None:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    if auth_session.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Refresh token expired")

    user_result = await db.execute(select(User).where(User.id == auth_session.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return await _issue_auth_response(db, user, request, response, replace_session=auth_session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    response: Response,
    payload: LogoutRequest | None = None,
    db: AsyncSession = Depends(get_db),
):
    refresh_token = _resolve_refresh_token(request, payload.refresh_token if payload else None)
    if refresh_token:
        token_hash = auth_service.hash_refresh_token(refresh_token)
        result = await db.execute(
            select(AuthSession).where(AuthSession.refresh_token_hash == token_hash)
        )
        auth_session = result.scalar_one_or_none()
        if auth_session is not None and auth_session.revoked_at is None:
            auth_session.revoked_at = datetime.now(timezone.utc)
            await db.commit()

    _clear_auth_cookies(response)
    return None


@router.post("/password-reset/request", response_model=PasswordResetRequestResponse)
async def request_password_reset(
    payload: PasswordResetRequestBody,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    email = _normalize_email(payload.email)
    rate_key = f"auth:password-reset:{_client_host(request)}:{email}"
    if await rate_limiter.is_limited(rate_key, settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS):
        raise HTTPException(status_code=429, detail="Too many password reset attempts")

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if user is None:
        await rate_limiter.increment(rate_key, settings.AUTH_RATE_LIMIT_WINDOW_SECONDS)
        return PasswordResetRequestResponse()

    reset_token = auth_service.create_password_reset_token()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=auth_service.hash_password_reset_token(reset_token),
            expires_at=auth_service.password_reset_expires_at(),
        )
    )
    await db.commit()
    await rate_limiter.reset(rate_key)

    if settings.EXPOSE_DEV_TOKENS:
        return PasswordResetRequestResponse(reset_token=reset_token)
    return PasswordResetRequestResponse()


@router.post("/password-reset/confirm", status_code=status.HTTP_204_NO_CONTENT)
async def confirm_password_reset(
    payload: PasswordResetConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    token_hash = auth_service.hash_password_reset_token(payload.token)
    result = await db.execute(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )
    reset_token = result.scalar_one_or_none()
    if reset_token is None or reset_token.used_at is not None:
        raise HTTPException(status_code=400, detail="Invalid password reset token")
    if reset_token.expires_at <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Password reset token expired")

    user_result = await db.execute(select(User).where(User.id == reset_token.user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.password_hash = auth_service.hash_password(payload.new_password)
    reset_token.used_at = datetime.now(timezone.utc)
    await db.execute(
        update(AuthSession)
        .where(AuthSession.user_id == user.id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await db.commit()
    return None


@router.get("/me", response_model=UserResponse)
async def me(
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == auth.user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    return UserResponse(id=user.id, email=user.email)
