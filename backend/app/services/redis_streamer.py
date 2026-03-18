"""
Redis Streaming Service — publishes agent container logs to frontend via WebSockets.

Each agent writes to channel:  logs:<agent_id>
Frontend subscribes via:       WS /ws/agents/<agent_id>/logs
"""

import logging
from collections.abc import AsyncGenerator

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)


class RedisStreamer:
    def __init__(self) -> None:
        self._redis: aioredis.Redis | None = None

    async def connect(self) -> None:
        self._redis = await aioredis.from_url(settings.REDIS_URL, decode_responses=True)

    async def publish(self, agent_id: str, message: str) -> None:
        if self._redis is None:
            await self.connect()
        await self._redis.publish(f"logs:{agent_id}", message)  # type: ignore[union-attr]

    async def subscribe(self, agent_id: str) -> AsyncGenerator[str, None]:
        """Async generator that yields log lines for an agent."""
        if self._redis is None:
            await self.connect()

        pubsub = self._redis.pubsub()  # type: ignore[union-attr]
        await pubsub.subscribe(f"logs:{agent_id}")
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    yield message["data"]
        finally:
            await pubsub.unsubscribe(f"logs:{agent_id}")
            await pubsub.close()

    async def close(self) -> None:
        if self._redis:
            await self._redis.aclose()


# Singleton
redis_streamer = RedisStreamer()
