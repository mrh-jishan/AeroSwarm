"""Tests for provider credential encryption."""

from __future__ import annotations

from app.services.crypto import CredentialCryptoService


def test_encrypt_and_decrypt_round_trip() -> None:
    service = CredentialCryptoService()

    ciphertext = service.encrypt("ghp_example_token")

    assert ciphertext != "ghp_example_token"
    assert service.decrypt(ciphertext) == "ghp_example_token"


def test_encrypt_and_decrypt_json_round_trip() -> None:
    service = CredentialCryptoService()

    ciphertext = service.encrypt_json({"user_id": "123", "redirect_path": "/"})

    assert service.decrypt_json(ciphertext)["user_id"] == "123"
