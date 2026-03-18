"""
Merge Requests API — Janitor Protocol.
Handles: pre-flight lint/test, visual diff, HITL approval, merge + cleanup.
"""

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import AuthContext, require_user_context
from app.models.base import Agent, MergeRequest, ProviderConnection, Session, Task
from app.services.audit import AuditService
from app.services.docker_manager import DockerManagerService
from app.services.git_manager import GitManagerService
from app.services.github_provider import GitHubProviderService
from app.services.job_queue import JOB_TYPE_MERGE_PREFLIGHT, JobQueueService
from app.services.provider_connections import ProviderConnectionService
from app.services.repo_manager import RepoManagerService

router = APIRouter(dependencies=[Depends(require_user_context)])
docker_mgr = DockerManagerService()
git_mgr = GitManagerService()
repo_mgr = RepoManagerService()
audit = AuditService()
github = GitHubProviderService()
provider_connections = ProviderConnectionService()
job_queue = JobQueueService()


class CreateMergeRequestBody(BaseModel):
    task_id: uuid.UUID


class PreflightCheckResponse(BaseModel):
    category: str
    label: str
    status: str
    command: str | None
    summary: str
    output: str | None


class MergeRequestResponse(BaseModel):
    merge_request_id: uuid.UUID
    status: str
    ready_to_merge: bool
    lint_passed: bool
    tests_passed: bool
    provider_pr_number: int | None = None
    provider_pr_url: str | None = None
    error_message: str | None = None
    checks: list[PreflightCheckResponse]


async def _resolve_provider_connection(
    session: Session,
    db: AsyncSession,
) -> ProviderConnection | None:
    if session.provider_connection_id is None:
        return None

    result = await db.execute(
        select(ProviderConnection).where(ProviderConnection.id == session.provider_connection_id)
    )
    return result.scalar_one_or_none()


def _deserialize_checks(raw_checks: str | None) -> list[PreflightCheckResponse]:
    if not raw_checks:
        return []
    try:
        data = json.loads(raw_checks)
    except json.JSONDecodeError:
        return []
    return [
        PreflightCheckResponse(
            category=item["category"],
            label=item["label"],
            status=item["status"],
            command=item.get("command"),
            summary=item["summary"],
            output=item.get("output"),
        )
        for item in data
    ]


def _build_merge_request_response(mr: MergeRequest) -> MergeRequestResponse:
    return MergeRequestResponse(
        merge_request_id=mr.id,
        status=mr.status,
        ready_to_merge=bool(mr.lint_passed and mr.tests_passed),
        lint_passed=bool(mr.lint_passed),
        tests_passed=bool(mr.tests_passed),
        provider_pr_number=mr.provider_pr_number,
        provider_pr_url=mr.provider_pr_url,
        error_message=mr.error_message,
        checks=_deserialize_checks(mr.checks_json),
    )


@router.post("/", response_model=MergeRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_merge_request(
    payload: CreateMergeRequestBody,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Mark a task as ready to merge — queues Janitor pre-flight."""
    result = await db.execute(
        select(Task)
        .join(Session, Session.id == Task.session_id)
        .where(Task.id == payload.task_id, Session.owner_user_id == auth.user_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.branch_name is None:
        raise HTTPException(status_code=400, detail="Task has no branch to merge")

    agent_result = await db.execute(select(Agent).where(Agent.task_id == task.id))
    agent = agent_result.scalar_one_or_none()
    if agent is None or agent.worktree_path is None:
        raise HTTPException(status_code=400, detail="Task has no agent worktree")
    session_result = await db.execute(select(Session).where(Session.id == task.session_id))
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    existing_result = await db.execute(select(MergeRequest).where(MergeRequest.task_id == task.id))
    mr = existing_result.scalar_one_or_none()
    if mr is None:
        mr = MergeRequest(task_id=task.id, status="pending")
        db.add(mr)
        await db.flush()
    elif mr.status in {"queued", "running", "pending"}:
        return _build_merge_request_response(mr)

    if agent.container_id is None:
        raise HTTPException(
            status_code=400,
            detail="Agent container is not available for preflight",
        )

    mr.status = "queued"
    mr.lint_passed = None
    mr.tests_passed = None
    mr.checks_json = None
    mr.error_message = None
    task.status = "merging"
    await job_queue.enqueue(
        db,
        job_type=JOB_TYPE_MERGE_PREFLIGHT,
        merge_request_id=mr.id,
        payload={"requested_by": auth.actor},
    )
    await audit.record(
        db,
        "merge.preflight.queued",
        auth.actor,
        session_id=task.session_id,
        task_id=task.id,
        agent_id=agent.id,
        details={"merge_request_id": str(mr.id)},
    )

    await db.commit()
    await db.refresh(mr)

    return _build_merge_request_response(mr)


@router.get("/{mr_id}", response_model=MergeRequestResponse)
async def get_merge_request(
    mr_id: uuid.UUID,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(MergeRequest)
        .join(Task, Task.id == MergeRequest.task_id)
        .join(Session, Session.id == Task.session_id)
        .where(MergeRequest.id == mr_id, Session.owner_user_id == auth.user_id)
    )
    mr = result.scalar_one_or_none()
    if mr is None:
        raise HTTPException(status_code=404, detail="Merge request not found")
    return _build_merge_request_response(mr)


@router.get("/{mr_id}/diff")
async def get_diff(
    mr_id: uuid.UUID,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Return the unified diff for the visual merge UI."""
    result = await db.execute(
        select(MergeRequest)
        .join(Task, Task.id == MergeRequest.task_id)
        .join(Session, Session.id == Task.session_id)
        .where(MergeRequest.id == mr_id, Session.owner_user_id == auth.user_id)
    )
    mr = result.scalar_one_or_none()
    if mr is None:
        raise HTTPException(status_code=404, detail="Merge request not found")

    task_result = await db.execute(select(Task).where(Task.id == mr.task_id))
    task = task_result.scalar_one_or_none()
    if task is None or task.branch_name is None:
        raise HTTPException(status_code=400, detail="Task has no branch")
    session_result = await db.execute(select(Session).where(Session.id == task.session_id))
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    repo_path = repo_mgr.get_repo_path(task.session_id)
    base_branch = session.base_branch or "main"
    diff = git_mgr.get_diff(str(repo_path), base_branch, task.branch_name)
    return {"branch": task.branch_name, "diff": diff}


class ApproveBody(BaseModel):
    approved_by: str  # username / identifier of the human approver


class RejectBody(BaseModel):
    rejected_by: str = "dashboard-user"


@router.post("/{mr_id}/approve")
async def approve_merge(
    mr_id: uuid.UUID,
    payload: ApproveBody,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Human approves the merge.
    - Merges agent branch into main
    - Stops + removes Docker container
    - Removes Git worktree
    """
    result = await db.execute(
        select(MergeRequest)
        .join(Task, Task.id == MergeRequest.task_id)
        .join(Session, Session.id == Task.session_id)
        .where(MergeRequest.id == mr_id, Session.owner_user_id == auth.user_id)
    )
    mr = result.scalar_one_or_none()
    if mr is None:
        raise HTTPException(status_code=404, detail="Merge request not found")
    if mr.status != "pending":
        raise HTTPException(
            status_code=409,
            detail=f"Cannot approve a merge request in state '{mr.status}'",
        )
    if not mr.lint_passed or not mr.tests_passed:
        raise HTTPException(
            status_code=409,
            detail="Preflight checks must pass before merge approval",
        )

    task_result = await db.execute(select(Task).where(Task.id == mr.task_id))
    task = task_result.scalar_one_or_none()
    agent_result = await db.execute(select(Agent).where(Agent.task_id == mr.task_id))
    agent = agent_result.scalar_one_or_none()
    session_result = (
        await db.execute(select(Session).where(Session.id == task.session_id))
        if task
        else None
    )
    session = session_result.scalar_one_or_none() if session_result else None

    if task is None or task.branch_name is None or session is None:
        raise HTTPException(status_code=400, detail="Task has no branch")
    repo_path = repo_mgr.get_repo_path(task.session_id)
    base_branch = session.base_branch or "main"

    provider_connection = await _resolve_provider_connection(session, db)
    if (
        session.vcs_provider == "github"
        and provider_connection is not None
        and mr.provider_pr_number is not None
        and session.repo_owner
        and session.repo_name
    ):
        try:
            access_token = await provider_connections.resolve_access_token(provider_connection)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        try:
            await github.merge_pull_request(
                owner=session.repo_owner,
                name=session.repo_name,
                number=mr.provider_pr_number,
                commit_title=f"AeroSwarm: {task.title}",
                access_token=access_token,
            )
        except ValueError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
    else:
        # HITL merge — only possible with explicit human approval
        git_mgr.merge_branch(str(repo_path), base_branch, task.branch_name, auth.actor)

    # Cleanup
    if agent and agent.container_id:
        docker_mgr.stop_and_remove(agent.container_id)
        agent.status = "stopped"
        agent.stopped_at = datetime.now(timezone.utc)

    if agent and agent.worktree_path:
        git_mgr.remove_worktree(str(repo_path), agent.worktree_path)

    mr.status = "merged"
    mr.approved_by = auth.actor
    mr.approved_at = datetime.now(timezone.utc)
    mr.merged_at = datetime.now(timezone.utc)
    task.status = "done"
    await audit.record(
        db,
        "merge.approved",
        auth.actor,
        session_id=task.session_id,
        task_id=task.id,
        agent_id=agent.id if agent else None,
        details={"branch": task.branch_name},
    )

    await db.commit()
    return {
        "status": "merged",
        "branch": task.branch_name,
        "provider_pr_number": mr.provider_pr_number,
        "provider_pr_url": mr.provider_pr_url,
    }


@router.post("/{mr_id}/reject")
async def reject_merge(
    mr_id: uuid.UUID,
    payload: RejectBody,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Human rejects — agent keeps working."""
    result = await db.execute(
        select(MergeRequest)
        .join(Task, Task.id == MergeRequest.task_id)
        .join(Session, Session.id == Task.session_id)
        .where(MergeRequest.id == mr_id, Session.owner_user_id == auth.user_id)
    )
    mr = result.scalar_one_or_none()
    if mr is None:
        raise HTTPException(status_code=404, detail="Merge request not found")

    mr.status = "rejected"
    task_result = await db.execute(select(Task).where(Task.id == mr.task_id))
    if task_result:
        task = task_result.scalar_one_or_none()
        if task:
            task.status = "running"
            agent_result = await db.execute(select(Agent).where(Agent.task_id == task.id))
            agent = agent_result.scalar_one_or_none()
            if agent:
                agent.status = "running"
            await audit.record(
                db,
                "merge.rejected",
                auth.actor,
                session_id=task.session_id,
                task_id=task.id,
                agent_id=agent.id if agent else None,
                details={"merge_request_id": str(mr.id)},
            )

    await db.commit()
    return {"status": "rejected"}
