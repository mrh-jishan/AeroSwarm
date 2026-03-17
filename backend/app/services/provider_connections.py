"""Helpers for resolving stored provider connections into usable credentials."""

from __future__ import annotations

import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.models.base import ProviderConnection
from app.services.crypto import CredentialCryptoService
from app.services.github_provider import GitHubProviderService


class ProviderConnectionService:
    def __init__(self) -> None:
        self._crypto = CredentialCryptoService()
        self._github = GitHubProviderService()

    async def get_connection_for_user(
        self,
        *,
        db: AsyncSession,
        connection_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> ProviderConnection | None:
        result = await db.execute(
            select(ProviderConnection).where(
                ProviderConnection.id == connection_id,
                ProviderConnection.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_connection_by_id(
        self,
        *,
        db: AsyncSession,
        connection_id: uuid.UUID,
    ) -> ProviderConnection | None:
        result = await db.execute(
            select(ProviderConnection).where(ProviderConnection.id == connection_id)
        )
        return result.scalar_one_or_none()

    async def resolve_access_token(self, connection: ProviderConnection) -> str:
        if connection.provider != "github":
            raise ValueError(f"Unsupported provider: {connection.provider}")

        if connection.auth_mode in {"token", "oauth"}:
            if not connection.encrypted_access_token:
                raise ValueError("Stored GitHub token is missing")
            return self._crypto.decrypt(connection.encrypted_access_token)

        if connection.auth_mode == "github_app":
            if connection.installation_id is None:
                raise ValueError("GitHub App installation is missing an installation ID")
            return await self._github.create_installation_access_token(connection.installation_id)

        raise ValueError(f"Unsupported auth mode: {connection.auth_mode}")

    def require_token_username(self, connection: ProviderConnection | None) -> str | None:
        if connection and connection.provider == "github":
            return "x-access-token"
        return None

    def ensure_connection(self, connection: ProviderConnection | None) -> ProviderConnection:
        if connection is None:
            raise HTTPException(status_code=404, detail="Provider connection not found")
        return connection
