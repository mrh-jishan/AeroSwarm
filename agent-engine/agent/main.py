"""
AeroSwarm Worker Agent — LangGraph state machine.

Runs inside an isolated Docker container.
Reads TASK_DESCRIPTION and SCOPE_DIR from environment.
Publishes all output to Redis channel logs:<AGENT_ID>.
"""

import asyncio
import logging
import os
import sys

import redis.asyncio as aioredis

from agent.graph import build_graph

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def main() -> None:
    agent_id = os.environ["AGENT_ID"]
    task_description = os.environ["TASK_DESCRIPTION"]
    scope_dir = os.environ.get("SCOPE_DIR", "/workspace")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")

    # Redis connection for log streaming
    r = await aioredis.from_url(redis_url, decode_responses=True)

    async def publish(msg: str) -> None:
        await r.publish(f"logs:{agent_id}", msg)
        print(msg, flush=True)  # also log to container stdout

    await publish(f"[AeroSwarm Agent {agent_id}] Starting...")
    await publish(f"[Task] {task_description}")
    await publish(f"[Scope] {scope_dir}")

    graph = build_graph()

    initial_state = {
        "agent_id": agent_id,
        "task_description": task_description,
        "scope_dir": scope_dir,
        "messages": [],
        "completed": False,
    }

    async for event in graph.astream(initial_state):
        for node_name, node_output in event.items():
            log_line = f"[{node_name}] {node_output.get('last_output', '')}"
            await publish(log_line)

    await publish(f"[AeroSwarm Agent {agent_id}] Task complete.")
    await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
