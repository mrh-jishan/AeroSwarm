"""Tests for readiness aggregation helpers."""

from __future__ import annotations

import asyncio

from app.services.readiness import ReadinessService


class ReadyService(ReadinessService):
    async def check_database(self) -> tuple[bool, str]:
        return True, "ok"

    async def check_redis(self) -> tuple[bool, str]:
        return True, "ok"


class DegradedService(ReadinessService):
    async def check_database(self) -> tuple[bool, str]:
        return False, "database unavailable"

    async def check_redis(self) -> tuple[bool, str]:
        return True, "ok"


def test_run_checks_returns_ready_summary() -> None:
    ready, checks = asyncio.run(ReadyService().run_checks())

    assert ready is True
    assert checks == {
        "database": {"ok": True, "detail": "ok"},
        "redis": {"ok": True, "detail": "ok"},
    }


def test_run_checks_returns_degraded_summary() -> None:
    ready, checks = asyncio.run(DegradedService().run_checks())

    assert ready is False
    assert checks == {
        "database": {"ok": False, "detail": "database unavailable"},
        "redis": {"ok": True, "detail": "ok"},
    }
