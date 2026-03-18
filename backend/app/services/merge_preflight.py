"""Background merge preflight processing."""

from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Agent, MergeRequest, ProviderConnection, Session, Task
from app.services.audit import AuditService
from app.services.git_manager import GitManagerService
from app.services.github_provider import GitHubProviderService
from app.services.janitor import JanitorService
from app.services.provider_connections import ProviderConnectionService
from app.services.repo_manager import RepoManagerService


class MergePreflightService:
    def __init__(self) -> None:
        self._janitor = JanitorService()
        self._audit = AuditService()
        self._git_mgr = GitManagerService()
        self._repo_mgr = RepoManagerService()
        self._github = GitHubProviderService()
        self._provider_connections = ProviderConnectionService()

    async def run(
        self,
        db: AsyncSession,
        *,
        merge_request_id: uuid.UUID,
        actor: str,
    ) -> dict[str, object]:
        result = await db.execute(select(MergeRequest).where(MergeRequest.id == merge_request_id))
        mr = result.scalar_one_or_none()
        if mr is None:
            raise ValueError("Merge request not found")

        if mr.status == "rejected":
            return {"merge_request_id": str(mr.id), "status": mr.status}

        task = await db.get(Task, mr.task_id)
        if task is None or task.branch_name is None:
            raise ValueError("Task has no branch to merge")
        agent_result = await db.execute(select(Agent).where(Agent.task_id == task.id))
        agent = agent_result.scalar_one_or_none()
        if agent is None or agent.worktree_path is None or agent.container_id is None:
            raise ValueError("Task has no runnable agent worktree")
        session = await db.get(Session, task.session_id)
        if session is None:
            raise ValueError("Session not found")

        mr.status = "running"
        mr.error_message = None
        await db.commit()

        try:
            report = await self._janitor.run_preflight(agent.worktree_path, agent.container_id)
            mr.lint_passed = report.lint_passed
            mr.tests_passed = report.tests_passed
            mr.status = "pending" if report.ready_to_merge else "failed"
            mr.error_message = None
            mr.checks_json = json.dumps(
                [
                    {
                        "category": check.category,
                        "label": check.label,
                        "status": check.status,
                        "command": check.command,
                        "summary": check.summary,
                        "output": check.output,
                    }
                    for check in report.checks
                ]
            )
            task.status = "merging" if report.ready_to_merge else "done"
            await self._audit.record(
                db,
                "merge.preflight.completed",
                actor,
                session_id=task.session_id,
                task_id=task.id,
                agent_id=agent.id,
                details={
                    "ready_to_merge": report.ready_to_merge,
                    "lint_passed": report.lint_passed,
                    "tests_passed": report.tests_passed,
                },
            )

            provider_connection = await self._resolve_provider_connection(session, db)
            if session.vcs_provider == "github" and provider_connection is not None:
                access_token = await self._provider_connections.resolve_access_token(
                    provider_connection
                )
                await self._sync_github_pull_request(
                    session=session,
                    task=task,
                    mr=mr,
                    checks=json.loads(mr.checks_json),
                    access_token=access_token,
                    db=db,
                )

            await db.commit()
            return {
                "merge_request_id": str(mr.id),
                "status": mr.status,
                "ready_to_merge": report.ready_to_merge,
            }
        except Exception as exc:
            await db.rollback()
            failed_mr = await db.get(MergeRequest, merge_request_id)
            if failed_mr is not None:
                failed_mr.status = "failed"
                failed_mr.error_message = str(exc)
                await db.commit()
            raise

    async def _resolve_provider_connection(
        self,
        session: Session,
        db: AsyncSession,
    ) -> ProviderConnection | None:
        if session.provider_connection_id is None:
            return None
        return await self._provider_connections.get_connection_by_id(
            db=db,
            connection_id=session.provider_connection_id,
        )

    async def _sync_github_pull_request(
        self,
        *,
        session: Session,
        task: Task,
        mr: MergeRequest,
        checks: list[dict[str, str | None]],
        access_token: str,
        db: AsyncSession,
    ) -> None:
        if (
            not session.repo_owner
            or not session.repo_name
            or not session.base_branch
            or not task.branch_name
        ):
            raise ValueError("Session is missing GitHub repository metadata")

        repo_path = self._repo_mgr.get_repo_path(session.id)
        authenticated_url = self._repo_mgr.build_authenticated_repo_url(
            session.repo_url,
            access_token,
            "x-access-token",
        )
        self._git_mgr.push_branch(str(repo_path), authenticated_url, task.branch_name)

        comment_lines = [
            "AeroSwarm preflight results:",
            "",
        ]
        for check in checks:
            status_icon = {
                "passed": "PASS",
                "failed": "FAIL",
                "skipped": "SKIP",
            }.get(str(check["status"]), str(check["status"]).upper())
            comment_lines.append(f"- [{status_icon}] {check['label']}: {check['summary']}")
        comment_body = "\n".join(comment_lines)

        pr = await self._github.find_open_pull_request(
            owner=session.repo_owner,
            name=session.repo_name,
            head=f"{session.repo_owner}:{task.branch_name}",
            base=session.base_branch,
            access_token=access_token,
        )
        if pr is None:
            pr = await self._github.create_pull_request(
                owner=session.repo_owner,
                name=session.repo_name,
                title=task.title,
                body=task.description or f"AeroSwarm task: {task.title}",
                head=task.branch_name,
                base=session.base_branch,
                access_token=access_token,
            )

        await self._github.comment_on_pull_request(
            owner=session.repo_owner,
            name=session.repo_name,
            issue_number=pr.number,
            body=comment_body,
            access_token=access_token,
        )

        mr.provider_pr_number = pr.number
        mr.provider_pr_url = pr.html_url
        await self._audit.record(
            db,
            "merge.github_pr.synced",
            "system",
            session_id=session.id,
            task_id=task.id,
            details={"pr_number": pr.number, "pr_url": pr.html_url, "branch": task.branch_name},
        )
