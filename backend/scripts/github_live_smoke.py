"""Live smoke harness for a real GitHub-backed AeroSwarm session.

Environment:
  AEROSWARM_BASE_URL=http://localhost:8000
  AEROSWARM_EMAIL=...
  AEROSWARM_PASSWORD=...
  AEROSWARM_REPO_URL=https://github.com/<owner>/<repo>
  AEROSWARM_PROMPT=...

Optional:
  AEROSWARM_PROVIDER_CONNECTION_ID=...
  AEROSWARM_GITHUB_PAT=...
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

import httpx


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def load_live_config() -> dict[str, str | None]:
    return {
        "base_url": os.getenv("AEROSWARM_BASE_URL", "http://localhost:8000").rstrip("/"),
        "email": require_env("AEROSWARM_EMAIL"),
        "password": require_env("AEROSWARM_PASSWORD"),
        "repo_url": require_env("AEROSWARM_REPO_URL"),
        "prompt": require_env("AEROSWARM_PROMPT"),
        "provider_connection_id": os.getenv("AEROSWARM_PROVIDER_CONNECTION_ID"),
        "github_pat": os.getenv("AEROSWARM_GITHUB_PAT"),
    }


async def run_live_smoke(config: dict[str, str | None]) -> dict[str, Any]:
    async with httpx.AsyncClient(
        base_url=str(config["base_url"]),
        follow_redirects=True,
        timeout=60.0,
    ) as client:
        login = await client.post(
            "/api/auth/login",
            json={"email": config["email"], "password": config["password"]},
        )
        login.raise_for_status()

        provider_connection_id = config.get("provider_connection_id")
        github_pat = config.get("github_pat")

        if not provider_connection_id and github_pat:
            connect = await client.post(
                "/api/vcs/github/connect",
                json={"access_token": github_pat},
            )
            connect.raise_for_status()
            provider_connection_id = connect.json()["id"]

        session = await client.post(
            "/api/sessions/",
            json={
                "repo_url": config["repo_url"],
                "prompt": config["prompt"],
                "provider_connection_id": provider_connection_id,
            },
        )
        session.raise_for_status()
        return session.json()


async def main() -> int:
    payload = await run_live_smoke(load_live_config())
    print("Created session:", payload["id"])
    print("Repo:", payload.get("repo_owner"), payload.get("repo_name"))
    print("Base branch:", payload.get("base_branch"))
    print("Agent count:", payload.get("agent_count"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:  # noqa: BLE001
        print(f"Smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
