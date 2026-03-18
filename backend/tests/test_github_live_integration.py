"""Live GitHub-backed integration test.

This test is skipped unless the required live environment variables are present.
It exercises the real backend over HTTP and is intended for staging/dev validation,
not for hermetic local unit-test runs.
"""

from __future__ import annotations

import asyncio
import os

import pytest

from scripts.github_live_smoke import load_live_config, run_live_smoke


REQUIRED_LIVE_ENV_VARS = [
    "AEROSWARM_EMAIL",
    "AEROSWARM_PASSWORD",
    "AEROSWARM_REPO_URL",
    "AEROSWARM_PROMPT",
]


def _missing_live_env() -> list[str]:
    return [name for name in REQUIRED_LIVE_ENV_VARS if not os.getenv(name)]


@pytest.mark.integration
def test_github_live_session_smoke() -> None:
    missing = _missing_live_env()
    if missing:
        pytest.skip(f"Missing live integration env vars: {', '.join(missing)}")

    payload = asyncio.run(run_live_smoke(load_live_config()))

    assert payload["id"]
    assert payload["repo_url"] == os.environ["AEROSWARM_REPO_URL"]
    assert payload["agent_count"] >= 1
    assert payload["status"] in {"planning", "running"}
