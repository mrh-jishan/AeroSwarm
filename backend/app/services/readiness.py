"""Runtime readiness checks for infrastructure dependencies."""

from __future__ import annotations

import redis.asyncio as aioredis
from sqlalchemy import text

from app.core.config import settings
from app.core.database import engine


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

    async def run_checks(self) -> tuple[bool, dict[str, dict[str, bool | str]]]:
        database_ok, database_detail = await self.check_database()
        redis_ok, redis_detail = await self.check_redis()
        checks = {
            "database": {"ok": database_ok, "detail": database_detail},
            "redis": {"ok": redis_ok, "detail": redis_detail},
        }
        return database_ok and redis_ok, checks
