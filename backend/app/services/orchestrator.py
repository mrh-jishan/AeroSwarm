"""
Orchestrator Service — calls the Manager LLM to decompose a user prompt
into a structured list of independent sub-tasks.
"""

import json
import logging
import re
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.services.llm_factory import create_chat_model

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


def _normalize_response_content(content: Any) -> str:
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        chunks: list[str] = []
        for item in content:
            if isinstance(item, str):
                chunks.append(item)
            elif isinstance(item, dict):
                text = item.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks).strip()

    return str(content).strip()


def _extract_json_payload(raw: str) -> str:
    text = raw.strip()
    fenced_match = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.IGNORECASE | re.DOTALL)
    if fenced_match:
        text = fenced_match.group(1).strip()

    if text.startswith("[") or text.startswith("{"):
        return text

    for opening, closing in (("[", "]"), ("{", "}")):
        start = text.find(opening)
        end = text.rfind(closing)
        if start != -1 and end != -1 and start < end:
            return text[start : end + 1].strip()

    return text


def _parse_subtasks(raw: str) -> list[SubTask]:
    payload = _extract_json_payload(raw)
    data: list[dict[str, Any]] = json.loads(payload)
    return [SubTask(**item) for item in data]


class OrchestratorService:
    async def decompose(
        self,
        prompt: str,
        *,
        provider: str,
        model: str,
    ) -> list[SubTask]:
        """Call the Manager LLM and return a validated list of sub-tasks."""
        llm = create_chat_model(
            provider=provider,
            model=model,
            temperature=0.2,
        )
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=f"Feature request: {prompt}"),
        ]
        response = await llm.ainvoke(messages)
        raw = _normalize_response_content(response.content)

        try:
            return _parse_subtasks(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            logger.error("LLM returned invalid JSON: %s\nRaw: %s", exc, raw)
            raise ValueError(f"Orchestrator LLM returned invalid response: {exc}") from exc
