"""Background session bootstrap processing."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import datetime, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Agent, MergeRequest, Session, Task
from app.services.agent_launcher import AgentLauncherService
from app.services.audit import AuditService
from app.services.crypto import CredentialCryptoService
from app.services.github_provider import GitHubProviderService
from app.services.orchestrator import OrchestratorService
from app.services.provider_connections import ProviderConnectionService
from app.services.repo_manager import RepoManagerService


class SessionBootstrapService:
    def __init__(self) -> None:
        self._orchestrator = OrchestratorService()
        self._launcher = AgentLauncherService()
        self._audit = AuditService()
        self._repo_mgr = RepoManagerService()
        self._provider_connections = ProviderConnectionService()
        self._crypto = CredentialCryptoService()
        self._github = GitHubProviderService()

    async def run(
        self,
        db: AsyncSession,
        *,
        session_id: uuid.UUID,
        actor: str,
        payload: dict[str, str],
    ) -> dict[str, object]:
        session = await db.get(Session, session_id)
        if session is None:
            raise ValueError("Session not found")

        if session.status == "stopped":
            return {"session_id": str(session.id), "status": session.status}

        if session.status == "running":
            return {"session_id": str(session.id), "status": session.status}

        session.status = "planning"
        session.error_message = None
        await db.commit()

        launched_agents: list[Agent] = []
        tasks: list[Task] = []
        try:
            await self._cleanup_existing_tasks(db, session)

            repo_access_token, repo_username = await self._resolve_repo_credentials(
                db,
                session,
                payload,
            )

            self._repo_mgr.clone_repo(
                session.id,
                session.repo_url,
                repo_access_token=repo_access_token,
                repo_username=repo_username,
            )
            session.base_branch = self._repo_mgr.get_default_branch(session.id)
            if (
                session.vcs_provider == "github"
                and session.repo_owner
                and session.repo_name
                and repo_access_token
            ):
                try:
                    repo_info = await self._github.get_repo(
                        session.repo_owner,
                        session.repo_name,
                        repo_access_token,
                    )
                    session.base_branch = repo_info.default_branch
                except ValueError:
                    pass
            await self._audit.record(
                db,
                "repo.cloned",
                actor,
                session_id=session.id,
                details={
                    "repo_url": session.repo_url,
                    "provider": session.vcs_provider,
                    "repo_owner": session.repo_owner,
                    "repo_name": session.repo_name,
                    "base_branch": session.base_branch,
                },
            )
            await db.commit()

            sub_tasks = await self._orchestrator.decompose(
                session.prompt,
                provider=session.llm_provider,
                model=session.manager_model,
            )
            for sub_task in sub_tasks:
                task = Task(
                    session_id=session.id,
                    title=sub_task.title,
                    description=sub_task.description,
                    scope_dir=sub_task.scope_dir,
                    status="pending",
                )
                db.add(task)
                tasks.append(task)
            await db.flush()

            if await self._stop_requested(db, session.id):
                return await self._finalize_stopped_session(
                    db,
                    session=session,
                    tasks=tasks,
                    launched_agents=launched_agents,
                )

            for task in tasks:
                if await self._stop_requested(db, session.id):
                    return await self._finalize_stopped_session(
                        db,
                        session=session,
                        tasks=tasks,
                        launched_agents=launched_agents,
                    )
                agent = await self._launcher.launch_for_task(db, task, session)
                launched_agents.append(agent)
                await self._audit.record(
                    db,
                    "agent.launched",
                    actor,
                    session_id=session.id,
                    task_id=task.id,
                    agent_id=agent.id,
                    details={
                        "task_title": task.title,
                        "scope_dir": task.scope_dir,
                        "port": agent.port,
                    },
                )

            if await self._stop_requested(db, session.id):
                return await self._finalize_stopped_session(
                    db,
                    session=session,
                    tasks=tasks,
                    launched_agents=launched_agents,
                )

            session.status = "running"
            session.error_message = None
            await db.commit()
            return {
                "session_id": str(session.id),
                "status": session.status,
                "task_count": len(tasks),
                "agent_count": len(launched_agents),
            }
        except Exception as exc:
            await db.rollback()
            self._cleanup_launched_agents(session_id, launched_agents)
            self._repo_mgr.cleanup_session_repo(session_id)

            failed_session = await db.get(Session, session_id)
            if failed_session is not None:
                failed_session.status = "failed"
                failed_session.error_message = str(exc)
                await self._audit.record(
                    db,
                    "session.bootstrap.failed",
                    actor,
                    session_id=session_id,
                    details={"error": str(exc)},
                )
                await db.commit()
            raise

    async def _resolve_repo_credentials(
        self,
        db: AsyncSession,
        session: Session,
        payload: dict[str, str],
    ) -> tuple[str | None, str | None]:
        encrypted_token = payload.get("encrypted_repo_access_token")
        repo_access_token = self._crypto.decrypt(encrypted_token) if encrypted_token else None
        repo_username = payload.get("repo_username") or None

        if repo_access_token is None and session.provider_connection_id is not None:
            connection = await self._provider_connections.get_connection_by_id(
                db=db,
                connection_id=session.provider_connection_id,
            )
            if connection is None:
                raise ValueError("Stored provider connection was not found")
            repo_access_token = await self._provider_connections.resolve_access_token(connection)
            repo_username = self._provider_connections.require_token_username(connection)

        return repo_access_token, repo_username

    async def _cleanup_existing_tasks(self, db: AsyncSession, session: Session) -> None:
        task_result = await db.execute(select(Task).where(Task.session_id == session.id))
        tasks = task_result.scalars().all()
        if not tasks:
            return

        task_ids = [task.id for task in tasks]
        agent_result = await db.execute(select(Agent).where(Agent.task_id.in_(task_ids)))
        agents = agent_result.scalars().all()
        self._cleanup_launched_agents(session.id, agents)

        await db.execute(delete(MergeRequest).where(MergeRequest.task_id.in_(task_ids)))
        await db.execute(delete(Agent).where(Agent.task_id.in_(task_ids)))
        await db.execute(delete(Task).where(Task.id.in_(task_ids)))
        await db.commit()

    async def _stop_requested(self, db: AsyncSession, session_id: uuid.UUID) -> bool:
        result = await db.execute(select(Session.status).where(Session.id == session_id))
        return result.scalar_one_or_none() == "stopped"

    async def _finalize_stopped_session(
        self,
        db: AsyncSession,
        *,
        session: Session,
        tasks: list[Task],
        launched_agents: list[Agent],
    ) -> dict[str, object]:
        stopped_at = datetime.now(timezone.utc)

        self._cleanup_launched_agents(session.id, launched_agents)
        self._repo_mgr.cleanup_session_repo(session.id)

        for task in tasks:
            if task.status not in {"done", "failed", "stopped"}:
                task.status = "stopped"

        for agent in launched_agents:
            agent.status = "stopped"
            agent.stopped_at = stopped_at

        session.status = "stopped"
        session.error_message = "Stopped by user"
        await db.commit()

        return {
            "session_id": str(session.id),
            "status": session.status,
            "task_count": len(tasks),
            "agent_count": len(launched_agents),
        }

    def _cleanup_launched_agents(self, session_id: uuid.UUID, agents: Iterable[Agent]) -> None:
        repo_path = self._repo_mgr.get_repo_path(session_id)
        git_mgr = self._launcher._git_mgr
        docker_mgr = self._launcher._docker_mgr
        for agent in agents:
            if agent.container_id:
                docker_mgr.stop_and_remove(agent.container_id)
            if agent.worktree_path and repo_path.exists():
                git_mgr.remove_worktree(str(repo_path), agent.worktree_path)
