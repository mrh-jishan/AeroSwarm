"""
Merge Requests API — Janitor Protocol.
Handles: pre-flight lint/test, visual diff, HITL approval, merge + cleanup.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import AuthContext, require_user_context
from app.models.base import Agent, MergeRequest, Session, Task
from app.services.audit import AuditService
from app.services.docker_manager import DockerManagerService
from app.services.git_manager import GitManagerService
from app.services.janitor import JanitorService
from app.services.repo_manager import RepoManagerService

router = APIRouter(dependencies=[Depends(require_user_context)])
docker_mgr = DockerManagerService()
git_mgr = GitManagerService()
janitor = JanitorService()
repo_mgr = RepoManagerService()
audit = AuditService()


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
    checks: list[PreflightCheckResponse]


@router.post("/", response_model=MergeRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_merge_request(
    payload: CreateMergeRequestBody,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Mark a task as ready to merge — triggers Janitor pre-flight."""
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

    existing_result = await db.execute(select(MergeRequest).where(MergeRequest.task_id == task.id))
    mr = existing_result.scalar_one_or_none()
    if mr is None:
        mr = MergeRequest(task_id=task.id, status="pending")
        db.add(mr)
        await db.flush()

    if agent.container_id is None:
        raise HTTPException(status_code=400, detail="Agent container is not available for preflight")

    report = await janitor.run_preflight(agent.worktree_path, agent.container_id)
    mr.lint_passed = report.lint_passed
    mr.tests_passed = report.tests_passed
    mr.status = "pending" if report.ready_to_merge else "failed"
    task.status = "merging" if report.ready_to_merge else "done"
    await audit.record(
        db,
        "merge.preflight.completed",
        auth.actor,
        session_id=task.session_id,
        task_id=task.id,
        agent_id=agent.id,
        details={
            "ready_to_merge": report.ready_to_merge,
            "lint_passed": report.lint_passed,
            "tests_passed": report.tests_passed,
        },
    )

    await db.commit()
    await db.refresh(mr)

    return MergeRequestResponse(
        merge_request_id=mr.id,
        status=mr.status,
        ready_to_merge=report.ready_to_merge,
        lint_passed=report.lint_passed,
        tests_passed=report.tests_passed,
        checks=[
            PreflightCheckResponse(
                category=check.category,
                label=check.label,
                status=check.status,
                command=check.command,
                summary=check.summary,
                output=check.output,
            )
            for check in report.checks
        ],
    )


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

    repo_path = repo_mgr.get_repo_path(task.session_id)
    diff = git_mgr.get_diff(str(repo_path), task.branch_name)
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
        raise HTTPException(status_code=409, detail=f"Cannot approve a merge request in state '{mr.status}'")
    if not mr.lint_passed or not mr.tests_passed:
        raise HTTPException(status_code=409, detail="Preflight checks must pass before merge approval")

    task_result = await db.execute(select(Task).where(Task.id == mr.task_id))
    task = task_result.scalar_one_or_none()
    agent_result = await db.execute(select(Agent).where(Agent.task_id == mr.task_id))
    agent = agent_result.scalar_one_or_none()

    if task is None or task.branch_name is None:
        raise HTTPException(status_code=400, detail="Task has no branch")

    repo_path = repo_mgr.get_repo_path(task.session_id)

    # HITL merge — only possible with explicit human approval
    git_mgr.merge_branch(str(repo_path), task.branch_name, auth.actor)

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
    return {"status": "merged", "branch": task.branch_name}


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
