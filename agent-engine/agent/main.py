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

import httpx
import redis.asyncio as aioredis

from agent.graph import build_graph

logging.basicConfig(level=logging.INFO, stream=sys.stdout)
logger = logging.getLogger(__name__)


async def main() -> None:
    agent_id = os.environ["AGENT_ID"]
    task_description = os.environ["TASK_DESCRIPTION"]
    scope_dir = os.environ.get("SCOPE_DIR", "/workspace")
    redis_url = os.environ.get("REDIS_URL", "redis://localhost:6379")
    backend_api_url = os.environ.get("BACKEND_API_URL", "http://localhost:8000")
    api_bearer_token = os.environ.get("API_BEARER_TOKEN", "")

    # Redis connection for log streaming
    r = await aioredis.from_url(redis_url, decode_responses=True)

    async def publish(msg: str) -> None:
        await r.publish(f"logs:{agent_id}", msg)
        print(msg, flush=True)  # also log to container stdout

    async def update_status(status: str) -> None:
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                await client.post(
                    f"{backend_api_url}/api/agents/{agent_id}/status",
                    headers={
                        "Authorization": f"Bearer {api_bearer_token}",
                    } if api_bearer_token else None,
                    json={"status": status},
                )
        except Exception as exc:
            await publish(f"[warning] Failed to update agent status to {status}: {exc}")

    await publish(f"[AeroSwarm Agent {agent_id}] Starting...")
    await publish(f"[Task] {task_description}")
    await publish(f"[Scope] {scope_dir}")
    await update_status("running")

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
    await update_status("idle")
    await r.aclose()


if __name__ == "__main__":
    asyncio.run(main())
