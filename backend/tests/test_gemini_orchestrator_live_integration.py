"""Live Gemini-backed integration test for orchestrator parsing."""

from __future__ import annotations

import asyncio

import pytest

from app.core.config import settings
from scripts.gemini_orchestrator_live_smoke import load_live_config, run_live_smoke


@pytest.mark.integration
def test_gemini_orchestrator_live_smoke() -> None:
    if not settings.GEMINI_API_KEY:
        pytest.skip("Missing live Gemini configuration")

    payload = asyncio.run(run_live_smoke(load_live_config()))

    assert payload["raw"]
    assert payload["task_count"] >= 1
    assert isinstance(payload["tasks"], list)
    first_task = payload["tasks"][0]
    assert first_task["title"]
    assert first_task["description"]
    assert first_task["scope_dir"]
