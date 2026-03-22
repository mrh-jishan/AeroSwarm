"""Tests for stopping sessions."""

from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

from app.api.routes import sessions as sessions_route
from app.core.security import AuthContext


class _ScalarResult:
    def __init__(self, value) -> None:
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class _Scalars:
    def __init__(self, values) -> None:
        self._values = values

    def all(self):
        return list(self._values)


class _ManyResult:
    def __init__(self, values) -> None:
        self._values = values

    def scalars(self):
        return _Scalars(self._values)


def test_stop_session_marks_runtime_stopped_and_cancels_jobs() -> None:
    session_id = uuid.uuid4()
    task_id = uuid.uuid4()
    agent_id = uuid.uuid4()
    user_id = uuid.uuid4()
    created_at = datetime.now(timezone.utc)

    session = SimpleNamespace(
        id=session_id,
        owner_user_id=user_id,
        provider_connection_id=None,
        repo_url="https://github.com/mrh-jishan/syslog",
        vcs_provider="github",
        repo_owner="mrh-jishan",
        repo_name="syslog",
        base_branch="main",
        llm_provider="gemini",
        manager_model="gemini-2.5-flash",
        agent_model="gemini-2.5-flash",
        prompt="add q/a page",
        status="running",
        error_message=None,
        created_at=created_at,
    )
    task = SimpleNamespace(id=task_id, status="running")
    agent = SimpleNamespace(
        id=agent_id,
        task_id=task_id,
        container_id="container-123",
        status="running",
        stopped_at=None,
    )
    job = SimpleNamespace(
        status="queued",
        error_message=None,
        locked_at=created_at,
        locked_by="worker-1",
    )

    db = AsyncMock()
    db.execute = AsyncMock(
        side_effect=[
            _ScalarResult(session),
            _ManyResult([task]),
            _ManyResult([agent]),
            _ManyResult([job]),
        ]
    )
    db.commit = AsyncMock()
    db.refresh = AsyncMock()

    audit_record = AsyncMock()
    docker_mgr = Mock()

    async def exercise() -> None:
        auth = AuthContext(actor="r.hassan@gmail.com", user_id=user_id, auth_type="user")
        with (
            patch.object(sessions_route, "_load_counts_for_sessions", AsyncMock(return_value=({session_id: 1}, {session_id: 1}))),
            patch.object(sessions_route, "audit", SimpleNamespace(record=audit_record)),
            patch.object(sessions_route, "DockerManagerService", return_value=docker_mgr),
        ):
            response = await sessions_route.stop_session(session_id=session_id, auth=auth, db=db)

        assert response.status == "stopped"
        assert response.error_message == "Stopped by user"
        assert task.status == "stopped"
        assert agent.status == "stopped"
        assert agent.stopped_at is not None
        assert job.status == "cancelled"
        assert job.error_message == "Stopped by user"
        assert job.locked_at is None
        assert job.locked_by is None
        docker_mgr.stop_and_remove.assert_called_once_with("container-123")
        audit_record.assert_awaited_once()
        db.commit.assert_awaited_once()
        db.refresh.assert_awaited_once_with(session)

    asyncio.run(exercise())
