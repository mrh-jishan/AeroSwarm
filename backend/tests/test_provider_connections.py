"""Tests for provider connection resolution helpers."""

from __future__ import annotations

import asyncio
import uuid

from app.models.base import ProviderConnection
from app.services.crypto import CredentialCryptoService
from app.services.provider_connections import ProviderConnectionService


def test_require_token_username_for_github() -> None:
    service = ProviderConnectionService()
    connection = ProviderConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="github",
        auth_mode="token",
        account_login="octocat",
        installation_id=None,
        encrypted_access_token="ciphertext",
    )

    assert service.require_token_username(connection) == "x-access-token"


def test_resolve_access_token_from_stored_token() -> None:
    service = ProviderConnectionService()
    encrypted = CredentialCryptoService().encrypt("ghp_example_token")
    connection = ProviderConnection(
        id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        provider="github",
        auth_mode="token",
        account_login="octocat",
        installation_id=None,
        encrypted_access_token=encrypted,
    )

    token = asyncio.run(service.resolve_access_token(connection))

    assert token == "ghp_example_token"
