"""User authentication helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings

JWT_ALGORITHM = "HS256"


@dataclass(slots=True)
class AuthClaims:
    user_id: uuid.UUID
    email: str


class AuthService:
    def hash_password(self, password: str) -> str:
        salt = os.urandom(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            100_000,
        )
        return (
            f"{base64.b64encode(salt).decode('ascii')}$"
            f"{base64.b64encode(digest).decode('ascii')}"
        )

    def verify_password(self, password: str, password_hash: str) -> bool:
        try:
            salt_b64, digest_b64 = password_hash.split("$", maxsplit=1)
        except ValueError:
            return False

        salt = base64.b64decode(salt_b64.encode("ascii"))
        expected = base64.b64decode(digest_b64.encode("ascii"))
        actual = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            100_000,
        )
        return hmac.compare_digest(actual, expected)

    def create_access_token(self, user_id: uuid.UUID, email: str) -> str:
        expires_at = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        payload = {
            "sub": str(user_id),
            "email": email,
            "type": "access",
            "exp": expires_at,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=JWT_ALGORITHM)

    def create_refresh_token(self) -> str:
        return secrets.token_urlsafe(48)

    def create_password_reset_token(self) -> str:
        return secrets.token_urlsafe(48)

    def hash_refresh_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def hash_password_reset_token(self, token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def refresh_token_expires_at(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    def password_reset_expires_at(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(
            minutes=settings.PASSWORD_RESET_EXPIRE_MINUTES
        )

    def decode_access_token(self, token: str) -> AuthClaims:
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[JWT_ALGORITHM])
        except JWTError as exc:
            raise ValueError("Invalid access token") from exc

        if payload.get("type") != "access":
            raise ValueError("Invalid token type")

        subject = payload.get("sub")
        email = payload.get("email")
        if not subject or not email:
            raise ValueError("Missing token subject")

        return AuthClaims(user_id=uuid.UUID(subject), email=str(email))
