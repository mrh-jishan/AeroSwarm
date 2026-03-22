"""
Agent launcher service.

Creates a worktree, assigns a port, starts the agent container, and persists the
Agent record without committing the transaction.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.base import Agent, Session, Task
from app.services.docker_manager import DockerManagerService
from app.services.git_manager import GitManagerService
from app.services.repo_manager import RepoManagerService


class AgentLauncherService:
    def __init__(self) -> None:
        self._docker_mgr = DockerManagerService()
        self._git_mgr = GitManagerService()
        self._repo_mgr = RepoManagerService()

    async def launch_for_task(
        self,
        db: AsyncSession,
        task: Task,
        session: Session,
    ) -> Agent:
        agent_id = uuid.uuid4()
        repo_path = self._repo_mgr.get_repo_path(task.session_id)

        worktree_path = self._git_mgr.create_worktree(
            session_id=task.session_id,
            agent_id=agent_id,
            repo_path=str(repo_path),
        )

        port = settings.AGENT_PORT_RANGE_START + (
            int(agent_id) % (settings.AGENT_PORT_RANGE_END - settings.AGENT_PORT_RANGE_START)
        )

        container_id = await self._docker_mgr.spawn_agent(
            task_id=task.id,
            worktree_path=worktree_path,
            scope_dir=task.scope_dir,
            task_description=task.description or task.title,
            llm_provider=session.llm_provider,
            agent_model=session.agent_model,
            port=port,
            agent_id=agent_id,
        )

        task.status = "running"
        task.branch_name = f"agent/{agent_id}"

        agent = Agent(
            id=agent_id,
            task_id=task.id,
            container_id=container_id,
            worktree_path=worktree_path,
            port=port,
            status="running",
            started_at=datetime.now(timezone.utc),
        )
        db.add(agent)
        return agent
