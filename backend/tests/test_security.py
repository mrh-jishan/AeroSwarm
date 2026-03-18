"""Tests for auth context resolution."""

from __future__ import annotations

import asyncio
import uuid

from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request
from starlette.websockets import WebSocket

from app.core.config import settings
from app.core.security import get_auth_context, get_websocket_auth_context, validate_csrf_request
from app.services.auth import AuthService


def _http_request(
    *,
    method: str = "GET",
    cookie_header: str = "",
    headers: list[tuple[bytes, bytes]] | None = None,
) -> Request:
    combined_headers = list(headers or [])
    if cookie_header:
        combined_headers.append((b"cookie", cookie_header.encode("utf-8")))
    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": combined_headers,
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
    }
    return Request(scope)


def _websocket_with_cookie(cookie_header: str) -> WebSocket:
    async def receive() -> dict[str, object]:
        return {"type": "websocket.disconnect"}

    async def send(message: dict[str, object]) -> None:
        return None

    scope = {
        "type": "websocket",
        "asgi": {"version": "3.0"},
        "scheme": "ws",
        "path": "/ws/agents/test/logs",
        "raw_path": b"/ws/agents/test/logs",
        "query_string": b"",
        "headers": [(b"cookie", cookie_header.encode("utf-8"))],
        "client": ("127.0.0.1", 12345),
        "server": ("testserver", 80),
        "root_path": "",
        "subprotocols": [],
    }
    return WebSocket(scope, receive=receive, send=send)


def test_http_cookie_access_token_is_accepted() -> None:
    service = AuthService()
    token = service.create_access_token(uuid.uuid4(), "user@example.com")
    request = _http_request(cookie_header=f"{settings.ACCESS_COOKIE_NAME}={token}")

    auth = asyncio.run(get_auth_context(request=request, credentials=None))

    assert auth.is_user is True
    assert auth.actor == "user@example.com"


def test_websocket_cookie_access_token_is_accepted() -> None:
    service = AuthService()
    token = service.create_access_token(uuid.uuid4(), "user@example.com")
    websocket = _websocket_with_cookie(f"{settings.ACCESS_COOKIE_NAME}={token}")

    auth = asyncio.run(get_websocket_auth_context(websocket))

    assert auth.is_user is True
    assert auth.actor == "user@example.com"


def test_internal_bearer_token_is_accepted() -> None:
    original_token = settings.API_BEARER_TOKEN
    settings.API_BEARER_TOKEN = "internal-test-token"
    request = _http_request()
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="internal-test-token",
    )

    try:
        auth = asyncio.run(get_auth_context(request=request, credentials=credentials))
    finally:
        settings.API_BEARER_TOKEN = original_token

    assert auth.auth_type == "internal"
    assert auth.actor == "system"


def test_csrf_required_for_cookie_authenticated_post_requests() -> None:
    request = _http_request(
        method="POST",
        cookie_header=(
            f"{settings.ACCESS_COOKIE_NAME}=access-token; "
            f"{settings.CSRF_COOKIE_NAME}=cookie-token"
        ),
    )

    try:
        validate_csrf_request(request)
    except Exception as exc:  # pragma: no cover - assertion handles type
        assert str(exc) == "403: CSRF validation failed"
    else:  # pragma: no cover - explicit failure path
        raise AssertionError("Expected CSRF validation to fail")


def test_csrf_accepts_matching_header_and_cookie() -> None:
    request = _http_request(
        method="POST",
        cookie_header=(
            f"{settings.ACCESS_COOKIE_NAME}=access-token; "
            f"{settings.CSRF_COOKIE_NAME}=cookie-token"
        ),
        headers=[(b"x-csrf-token", b"cookie-token")],
    )

    validate_csrf_request(request)


def test_csrf_not_required_for_bearer_authenticated_post_requests() -> None:
    request = _http_request(
        method="POST",
        headers=[(b"authorization", b"Bearer user-token")],
    )

    validate_csrf_request(request)
