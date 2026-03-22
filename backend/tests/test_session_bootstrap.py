"""Tests for session bootstrap failure handling."""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, Mock

from app.services.session_bootstrap import SessionBootstrapService


class _ExpiringSession:
    def __init__(self, session_id: uuid.UUID) -> None:
        self._id = session_id
        self._expired = False
        self.status = "queued"
        self.error_message: str | None = None
        self.repo_url = "https://github.com/mrh-jishan/syslog"
        self.vcs_provider = "github"
        self.repo_owner = "mrh-jishan"
        self.repo_name = "syslog"
        self.base_branch = None
        self.prompt = "add q/a page"
        self.llm_provider = "gemini"
        self.manager_model = "gemini-2.5-flash"
        self.agent_model = "gemini-2.5-flash"
        self.provider_connection_id = None

    @property
    def id(self) -> uuid.UUID:
        if self._expired:
            raise RuntimeError("expired ORM attribute access")
        return self._id

    def expire(self) -> None:
        self._expired = True


def test_run_marks_session_failed_without_touching_expired_session_ids() -> None:
    session_id = uuid.uuid4()
    initial_session = _ExpiringSession(session_id)
    failed_session = _ExpiringSession(session_id)

    async def exercise() -> None:
        service = SessionBootstrapService()
        service._cleanup_existing_tasks = AsyncMock()
        service._resolve_repo_credentials = AsyncMock(return_value=(None, None))
        service._cleanup_launched_agents = Mock()
        service._repo_mgr.cleanup_session_repo = Mock()
        service._repo_mgr.get_default_branch = Mock(return_value="main")
        service._repo_mgr.clone_repo = Mock(side_effect=RuntimeError("docker network missing"))
        service._audit.record = AsyncMock()

        db = AsyncMock()
        db.get = AsyncMock(side_effect=[initial_session, failed_session])

        async def rollback() -> None:
            initial_session.expire()
            failed_session.expire()

        db.rollback.side_effect = rollback

        try:
            await service.run(
                db,
                session_id=session_id,
                actor="r.hassan@gmail.com",
                payload={"requested_by": "r.hassan@gmail.com"},
            )
        except RuntimeError as exc:
            assert str(exc) == "docker network missing"
        else:
            raise AssertionError("expected bootstrap failure")

        assert failed_session.status == "failed"
        assert failed_session.error_message == "docker network missing"
        service._cleanup_launched_agents.assert_called_once_with(session_id, [])
        service._repo_mgr.cleanup_session_repo.assert_called_once_with(session_id)
        service._audit.record.assert_awaited_once_with(
            db,
            "session.bootstrap.failed",
            "r.hassan@gmail.com",
            session_id=session_id,
            details={"error": "docker network missing"},
        )

    asyncio.run(exercise())
