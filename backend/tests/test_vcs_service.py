"""Tests for repository provider parsing."""

from __future__ import annotations

from app.services.vcs import VcsService


def test_parse_github_https_url() -> None:
    service = VcsService()

    identity = service.parse_repo_identity("https://github.com/openai/aeroswarm.git")

    assert identity.provider == "github"
    assert identity.owner == "openai"
    assert identity.name == "aeroswarm"


def test_parse_github_ssh_url() -> None:
    service = VcsService()

    identity = service.parse_repo_identity("git@github.com:openai/aeroswarm.git")

    assert identity.provider == "github"
    assert identity.owner == "openai"
    assert identity.name == "aeroswarm"


def test_parse_unknown_provider_url() -> None:
    service = VcsService()

    identity = service.parse_repo_identity("https://gitlab.com/openai/aeroswarm.git")

    assert identity.provider is None
    assert identity.owner is None
    assert identity.name is None
