"""Tests for GitHub provider helpers."""

from __future__ import annotations

import hashlib
import hmac
from urllib.parse import parse_qs, urlparse

from app.core.config import settings
from app.services.github_provider import GitHubProviderService


def test_build_oauth_authorize_url() -> None:
    original_client_id = settings.GITHUB_OAUTH_CLIENT_ID
    original_redirect = settings.GITHUB_OAUTH_REDIRECT_URI
    settings.GITHUB_OAUTH_CLIENT_ID = "github-client-id"
    settings.GITHUB_OAUTH_REDIRECT_URI = "http://localhost:8000/api/vcs/github/oauth/callback"

    try:
        service = GitHubProviderService()
        url = service.build_oauth_authorize_url("opaque-state")
    finally:
        settings.GITHUB_OAUTH_CLIENT_ID = original_client_id
        settings.GITHUB_OAUTH_REDIRECT_URI = original_redirect

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.netloc == "github.com"
    assert params["client_id"] == ["github-client-id"]
    assert params["state"] == ["opaque-state"]


def test_build_app_install_url() -> None:
    original_slug = settings.GITHUB_APP_SLUG
    settings.GITHUB_APP_SLUG = "aeroswarm-bot"

    try:
        service = GitHubProviderService()
        url = service.build_app_install_url("install-state")
    finally:
        settings.GITHUB_APP_SLUG = original_slug

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    assert parsed.netloc == "github.com"
    assert parsed.path == "/apps/aeroswarm-bot/installations/new"
    assert params["state"] == ["install-state"]


def test_verify_webhook_signature() -> None:
    original_secret = settings.GITHUB_WEBHOOK_SECRET
    settings.GITHUB_WEBHOOK_SECRET = "webhook-secret"

    try:
        service = GitHubProviderService()
        payload = b'{"action":"closed"}'
        signature = "sha256=" + hmac.new(
            b"webhook-secret",
            payload,
            hashlib.sha256,
        ).hexdigest()
        assert service.verify_webhook_signature(payload, signature) is True
        assert service.verify_webhook_signature(payload, "sha256=bad") is False
    finally:
        settings.GITHUB_WEBHOOK_SECRET = original_secret
