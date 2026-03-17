"""Symmetric encryption helpers for provider credentials."""

from __future__ import annotations

import base64
import hashlib
import json
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings


class CredentialCryptoService:
    def __init__(self) -> None:
        digest = hashlib.sha256(settings.SECRET_KEY.encode("utf-8")).digest()
        self._fernet = Fernet(base64.urlsafe_b64encode(digest))

    def encrypt(self, plaintext: str) -> str:
        return self._fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

    def decrypt(self, ciphertext: str) -> str:
        try:
            return self._fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Failed to decrypt credential") from exc

    def encrypt_json(self, payload: dict[str, Any]) -> str:
        return self.encrypt(json.dumps(payload))

    def decrypt_json(self, ciphertext: str, *, ttl: int | None = None) -> dict[str, Any]:
        try:
            plaintext = self._fernet.decrypt(
                ciphertext.encode("utf-8"),
                ttl=ttl,
            ).decode("utf-8")
        except InvalidToken as exc:
            raise ValueError("Failed to decrypt credential") from exc
        return json.loads(plaintext)
