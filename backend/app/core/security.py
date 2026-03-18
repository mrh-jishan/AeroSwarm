"""Authentication helpers for the AeroSwarm API."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from http import HTTPMethod

from fastapi import Depends, HTTPException, Request, WebSocket, WebSocketException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import settings
from app.services.auth import AuthService

bearer_scheme = HTTPBearer(auto_error=False)
auth_service = AuthService()
SAFE_METHODS = {
    HTTPMethod.GET,
    HTTPMethod.HEAD,
    HTTPMethod.OPTIONS,
}


@dataclass(slots=True)
class AuthContext:
    actor: str
    user_id: uuid.UUID | None
    auth_type: str

    @property
    def is_user(self) -> bool:
        return self.user_id is not None


async def get_auth_context(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthContext:
    """
    Accept either a user JWT or the internal API bearer token.
    Local development can leave both unset to disable auth enforcement.
    """
    if not settings.API_BEARER_TOKEN and not settings.SECRET_KEY:
        return AuthContext(actor="anonymous", user_id=None, auth_type="none")

    token = credentials.credentials if credentials is not None else request.cookies.get(
        settings.ACCESS_COOKIE_NAME
    )

    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    if settings.API_BEARER_TOKEN and token == settings.API_BEARER_TOKEN:
        return AuthContext(actor="system", user_id=None, auth_type="internal")

    try:
        claims = auth_service.decode_access_token(token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        ) from exc

    return AuthContext(actor=claims.email, user_id=claims.user_id, auth_type="user")


def _has_bearer_authorization(request: Request) -> bool:
    auth_header = request.headers.get("authorization", "")
    return auth_header.startswith("Bearer ")


def _has_cookie_authenticated_session(request: Request) -> bool:
    return bool(
        request.cookies.get(settings.ACCESS_COOKIE_NAME)
        or request.cookies.get(settings.REFRESH_COOKIE_NAME)
    )


def should_enforce_csrf(request: Request) -> bool:
    if request.method.upper() in SAFE_METHODS:
        return False
    if _has_bearer_authorization(request):
        return False
    return _has_cookie_authenticated_session(request)


def validate_csrf_request(request: Request) -> None:
    if not should_enforce_csrf(request):
        return

    cookie_token = request.cookies.get(settings.CSRF_COOKIE_NAME)
    header_token = request.headers.get(settings.CSRF_HEADER_NAME)
    if not cookie_token or not header_token or cookie_token != header_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="CSRF validation failed",
        )


async def require_api_token() -> AuthContext:
    raise RuntimeError("This dependency should not be called directly")


async def require_user_context(
    auth: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    if not auth.is_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User authentication required",
        )
    return auth


async def require_internal_context(
    auth: AuthContext = Depends(get_auth_context),
) -> AuthContext:
    if not settings.API_BEARER_TOKEN:
        return AuthContext(actor="system", user_id=None, auth_type="internal")
    if auth.auth_type != "internal":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Internal authentication required",
        )
    return auth


async def get_websocket_auth_context(websocket: WebSocket) -> AuthContext:
    if not settings.API_BEARER_TOKEN and not settings.SECRET_KEY:
        return AuthContext(actor="anonymous", user_id=None, auth_type="none")

    auth_header = websocket.headers.get("authorization", "")
    query_token = websocket.query_params.get("token")
    header_token = (
        auth_header.removeprefix("Bearer ").strip()
        if auth_header.startswith("Bearer ")
        else None
    )
    cookie_token = websocket.cookies.get(settings.ACCESS_COOKIE_NAME)
    token = query_token or header_token or cookie_token

    if not token:
        raise WebSocketException(code=1008, reason="Unauthorized")

    if settings.API_BEARER_TOKEN and token == settings.API_BEARER_TOKEN:
        return AuthContext(actor="system", user_id=None, auth_type="internal")

    try:
        claims = auth_service.decode_access_token(token)
    except ValueError as exc:
        raise WebSocketException(code=1008, reason="Unauthorized") from exc

    return AuthContext(actor=claims.email, user_id=claims.user_id, auth_type="user")
