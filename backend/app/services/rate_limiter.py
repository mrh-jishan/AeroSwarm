"""Redis-backed auth rate limiting helpers."""

from __future__ import annotations

import logging

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiterService:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def _client(self) -> aioredis.Redis:
        if self._redis is None:
            self._redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        return self._redis

    async def is_limited(self, key: str, limit: int) -> bool:
        try:
            client = await self._client()
            value = await client.get(key)
            return int(value or 0) >= limit
        except Exception as exc:
            logger.warning("Rate limiter unavailable: %s", exc)
            return False

    async def increment(self, key: str, window_seconds: int) -> int:
        try:
            client = await self._client()
            count = await client.incr(key)
            if count == 1:
                await client.expire(key, window_seconds)
            return int(count)
        except Exception as exc:
            logger.warning("Rate limiter unavailable: %s", exc)
            return 0

    async def reset(self, key: str) -> None:
        try:
            client = await self._client()
            await client.delete(key)
        except Exception as exc:
            logger.warning("Rate limiter unavailable: %s", exc)
