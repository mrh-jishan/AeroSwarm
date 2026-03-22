"""Live Gemini-backed smoke harness for orchestrator response parsing.

This script exercises the same Gemini chat-model path used by the orchestrator,
captures the raw response, normalizes it, parses it into subtasks, and prints
the result for manual inspection.

Environment:
  GEMINI_API_KEY=...

Optional:
  GEMINI_ORCHESTRATOR_MODEL=gemini-2.5-flash
  GEMINI_ORCHESTRATOR_PROMPT=add q/a page
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.config import settings
from app.services.llm_factory import create_chat_model
from app.services.orchestrator import SYSTEM_PROMPT, _normalize_response_content, _parse_subtasks


def load_live_config() -> dict[str, str]:
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("Missing Gemini configuration: GEMINI_API_KEY")

    return {
        "provider": "gemini",
        "model": os.getenv("GEMINI_ORCHESTRATOR_MODEL", settings.GEMINI_DEFAULT_MODEL),
        "prompt": os.getenv("GEMINI_ORCHESTRATOR_PROMPT", "add q/a page"),
    }


async def run_live_smoke(config: dict[str, str]) -> dict[str, Any]:
    llm = create_chat_model(
        provider=config["provider"],
        model=config["model"],
        temperature=0.2,
    )
    response = await llm.ainvoke(
        [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Feature request: {config['prompt']}"),
        ]
    )
    raw = _normalize_response_content(response.content)
    parsed = _parse_subtasks(raw)

    return {
        "model": config["model"],
        "prompt": config["prompt"],
        "raw": raw,
        "task_count": len(parsed),
        "tasks": [task.model_dump() for task in parsed],
    }


async def main() -> int:
    payload = await run_live_smoke(load_live_config())
    print(json.dumps(payload, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(main()))
    except Exception as exc:  # noqa: BLE001
        print(f"Gemini orchestrator smoke test failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
