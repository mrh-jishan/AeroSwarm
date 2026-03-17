"""
Orchestrator Service — calls the Manager LLM to decompose a user prompt
into a structured list of independent sub-tasks.
"""

import json
import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a senior software architect acting as a Task Orchestrator.
Your job is to decompose a high-level feature request into a list of independent,
non-overlapping sub-tasks that can be worked on concurrently by separate AI agents.

Rules:
- Each task must touch a DIFFERENT part of the codebase (no overlapping files/directories).
- scope_dir must be a relative path (e.g. "src/api", "src/components/checkout").
- Aim for 2–6 tasks. Do not create tasks that depend on each other's output.
- Output ONLY valid JSON — no markdown fences, no extra text.

Output schema:
[
  {
    "title": "short task title",
    "description": "detailed instructions for the AI agent",
    "scope_dir": "relative/path/to/directory"
  },
  ...
]
"""


class SubTask(BaseModel):
    title: str
    description: str
    scope_dir: str = Field(..., description="Directory the agent is restricted to")


class OrchestratorService:
    def __init__(self) -> None:
        self._llm = ChatOpenAI(
            model=settings.MANAGER_MODEL,
            temperature=0.2,
            api_key=settings.OPENAI_API_KEY,
        )

    async def decompose(self, prompt: str) -> list[SubTask]:
        """Call the Manager LLM and return a validated list of sub-tasks."""
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Feature request: {prompt}"),
        ]
        response = await self._llm.ainvoke(messages)
        raw: str = response.content  # type: ignore[assignment]

        try:
            data: list[dict[str, Any]] = json.loads(raw)
            return [SubTask(**item) for item in data]
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("LLM returned invalid JSON: %s\nRaw: %s", exc, raw)
            raise ValueError(f"Orchestrator LLM returned invalid response: {exc}") from exc
