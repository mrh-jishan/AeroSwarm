"""Tests for orchestrator response parsing."""

import json

import pytest

from app.services.orchestrator import (
    _extract_json_payload,
    _normalize_response_content,
    _parse_subtasks,
)


def test_extract_json_payload_strips_markdown_fences() -> None:
    raw = """```json
[
  {
    "title": "Task",
    "description": "Desc",
    "scope_dir": "src/api"
  }
]
```"""

    payload = _extract_json_payload(raw)

    assert json.loads(payload)[0]["scope_dir"] == "src/api"


def test_extract_json_payload_handles_leading_text() -> None:
    raw = """Here is the plan:

```json
[
  {
    "title": "Task",
    "description": "Desc",
    "scope_dir": "src/api"
  }
]
```"""

    payload = _extract_json_payload(raw)

    assert json.loads(payload)[0]["title"] == "Task"


def test_normalize_response_content_joins_text_chunks() -> None:
    content = [
        {"type": "text", "text": "["},
        {"type": "text", "text": '{"title":"Task","description":"Desc","scope_dir":"src/api"}'},
        {"type": "text", "text": "]"},
    ]

    normalized = _normalize_response_content(content)

    assert normalized == '[\n{"title":"Task","description":"Desc","scope_dir":"src/api"}\n]'


def test_parse_subtasks_accepts_fenced_json() -> None:
    raw = """```json
[
  {
    "title": "Task",
    "description": "Desc",
    "scope_dir": "src/api"
  }
]
```"""

    tasks = _parse_subtasks(raw)

    assert len(tasks) == 1
    assert tasks[0].title == "Task"


def test_parse_subtasks_rejects_invalid_json() -> None:
    with pytest.raises(json.JSONDecodeError):
        _parse_subtasks("not valid json")
