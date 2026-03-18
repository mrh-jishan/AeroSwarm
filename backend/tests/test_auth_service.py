"""Unit tests for authentication helpers."""

from __future__ import annotations

import uuid

from app.services.auth import AuthService


def test_password_hash_round_trip() -> None:
    service = AuthService()
    password = "correct horse battery staple"

    password_hash = service.hash_password(password)

    assert password_hash != password
    assert service.verify_password(password, password_hash) is True
    assert service.verify_password("wrong password", password_hash) is False


def test_access_token_round_trip() -> None:
    service = AuthService()
    user_id = uuid.uuid4()
    email = "user@example.com"

    token = service.create_access_token(user_id, email)
    claims = service.decode_access_token(token)

    assert claims.user_id == user_id
    assert claims.email == email


def test_refresh_and_reset_tokens_hash_consistently() -> None:
    service = AuthService()
    refresh_token = service.create_refresh_token()
    reset_token = service.create_password_reset_token()

    assert service.hash_refresh_token(refresh_token) == service.hash_refresh_token(
        refresh_token
    )
    assert service.hash_password_reset_token(
        reset_token
    ) == service.hash_password_reset_token(reset_token)
    assert service.hash_refresh_token(
        refresh_token
    ) != service.hash_password_reset_token(reset_token)


def test_expiry_helpers_return_future_timestamps() -> None:
    service = AuthService()

    assert service.refresh_token_expires_at() > service.password_reset_expires_at()
