"""Runtime readiness checks for infrastructure dependencies."""

from __future__ import annotations

import asyncio
from pathlib import Path

import redis.asyncio as aioredis
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine
from app.services.docker_manager import DockerManagerService


class ReadinessService:
    async def check_database(self) -> tuple[bool, str]:
        try:
            async with engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True, "ok"
        except Exception as exc:
            return False, str(exc)

    async def check_redis(self) -> tuple[bool, str]:
        client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            await client.ping()
            return True, "ok"
        except Exception as exc:
            return False, str(exc)
        finally:
            await client.aclose()

    async def check_docker(self) -> tuple[bool, str]:
        return await asyncio.to_thread(DockerManagerService().availability)

    async def check_repo_base_path(self) -> tuple[bool, str]:
        repo_base_path = Path(settings.REPO_BASE_PATH)
        try:
            repo_base_path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            return False, str(exc)
        return True, str(repo_base_path)

    async def run_checks(self) -> tuple[bool, dict[str, dict[str, bool | str]]]:
        database_ok, database_detail = await self.check_database()
        redis_ok, redis_detail = await self.check_redis()
        docker_ok, docker_detail = await self.check_docker()
        repo_base_path_ok, repo_base_path_detail = await self.check_repo_base_path()
        checks = {
            "database": {"ok": database_ok, "detail": database_detail},
            "redis": {"ok": redis_ok, "detail": redis_detail},
            "docker": {"ok": docker_ok, "detail": docker_detail},
            "repo_base_path": {"ok": repo_base_path_ok, "detail": repo_base_path_detail},
        }
        return database_ok and redis_ok and docker_ok and repo_base_path_ok, checks
