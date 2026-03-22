"""Tests for readiness aggregation helpers."""

from __future__ import annotations

import asyncio

from app.services.readiness import ReadinessService


class ReadyService(ReadinessService):
    async def check_database(self) -> tuple[bool, str]:
        return True, "ok"

    async def check_redis(self) -> tuple[bool, str]:
        return True, "ok"

    async def check_docker(self) -> tuple[bool, str]:
        return True, "unix:///tmp/docker.sock"

    async def check_repo_base_path(self) -> tuple[bool, str]:
        return True, "/tmp/repos"


class DegradedService(ReadinessService):
    async def check_database(self) -> tuple[bool, str]:
        return False, "database unavailable"

    async def check_redis(self) -> tuple[bool, str]:
        return True, "ok"

    async def check_docker(self) -> tuple[bool, str]:
        return True, "unix:///tmp/docker.sock"

    async def check_repo_base_path(self) -> tuple[bool, str]:
        return True, "/tmp/repos"


class DockerDegradedService(ReadinessService):
    async def check_database(self) -> tuple[bool, str]:
        return True, "ok"

    async def check_redis(self) -> tuple[bool, str]:
        return True, "ok"

    async def check_docker(self) -> tuple[bool, str]:
        return False, "docker unavailable"

    async def check_repo_base_path(self) -> tuple[bool, str]:
        return True, "/tmp/repos"


def test_run_checks_returns_ready_summary() -> None:
    ready, checks = asyncio.run(ReadyService().run_checks())

    assert ready is True
    assert checks == {
        "database": {"ok": True, "detail": "ok"},
        "redis": {"ok": True, "detail": "ok"},
        "docker": {"ok": True, "detail": "unix:///tmp/docker.sock"},
        "repo_base_path": {"ok": True, "detail": "/tmp/repos"},
    }


def test_run_checks_returns_degraded_summary() -> None:
    ready, checks = asyncio.run(DegradedService().run_checks())

    assert ready is False
    assert checks == {
        "database": {"ok": False, "detail": "database unavailable"},
        "redis": {"ok": True, "detail": "ok"},
        "docker": {"ok": True, "detail": "unix:///tmp/docker.sock"},
        "repo_base_path": {"ok": True, "detail": "/tmp/repos"},
    }


def test_run_checks_returns_degraded_when_docker_is_unavailable() -> None:
    ready, checks = asyncio.run(DockerDegradedService().run_checks())

    assert ready is False
    assert checks == {
        "database": {"ok": True, "detail": "ok"},
        "redis": {"ok": True, "detail": "ok"},
        "docker": {"ok": False, "detail": "docker unavailable"},
        "repo_base_path": {"ok": True, "detail": "/tmp/repos"},
    }
