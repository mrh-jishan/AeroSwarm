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
from app.models.base import Agent, MergeRequest, Task
from app.services.docker_manager import DockerManagerService
from app.services.git_manager import GitManagerService

router = APIRouter()
docker_mgr = DockerManagerService()
git_mgr = GitManagerService()


class CreateMergeRequestBody(BaseModel):
    task_id: uuid.UUID
    repo_path: str


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_merge_request(payload: CreateMergeRequestBody, db: AsyncSession = Depends(get_db)):
    """Mark a task as ready to merge — triggers Janitor pre-flight."""
    result = await db.execute(select(Task).where(Task.id == payload.task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    mr = MergeRequest(task_id=task.id, status="pending")
    db.add(mr)
    task.status = "merging"
    await db.commit()
    await db.refresh(mr)

    return {"merge_request_id": str(mr.id), "status": mr.status}


@router.get("/{mr_id}/diff")
async def get_diff(mr_id: uuid.UUID, repo_path: str, db: AsyncSession = Depends(get_db)):
    """Return the unified diff for the visual merge UI."""
    result = await db.execute(select(MergeRequest).where(MergeRequest.id == mr_id))
    mr = result.scalar_one_or_none()
    if mr is None:
        raise HTTPException(status_code=404, detail="Merge request not found")

    task_result = await db.execute(select(Task).where(Task.id == mr.task_id))
    task = task_result.scalar_one_or_none()
    if task is None or task.branch_name is None:
        raise HTTPException(status_code=400, detail="Task has no branch")

    diff = git_mgr.get_diff(repo_path, task.branch_name)
    return {"branch": task.branch_name, "diff": diff}


class ApproveBody(BaseModel):
    approved_by: str  # username / identifier of the human approver
    repo_path: str


@router.post("/{mr_id}/approve")
async def approve_merge(mr_id: uuid.UUID, payload: ApproveBody, db: AsyncSession = Depends(get_db)):
    """
    Human approves the merge.
    - Merges agent branch into main
    - Stops + removes Docker container
    - Removes Git worktree
    """
    result = await db.execute(select(MergeRequest).where(MergeRequest.id == mr_id))
    mr = result.scalar_one_or_none()
    if mr is None:
        raise HTTPException(status_code=404, detail="Merge request not found")
    if mr.status != "pending":
        raise HTTPException(status_code=409, detail=f"Cannot approve a merge request in state '{mr.status}'")

    task_result = await db.execute(select(Task).where(Task.id == mr.task_id))
    task = task_result.scalar_one_or_none()
    agent_result = await db.execute(select(Agent).where(Agent.task_id == mr.task_id))
    agent = agent_result.scalar_one_or_none()

    if task is None or task.branch_name is None:
        raise HTTPException(status_code=400, detail="Task has no branch")

    # HITL merge — only possible with explicit human approval
    git_mgr.merge_branch(payload.repo_path, task.branch_name, payload.approved_by)

    # Cleanup
    if agent and agent.container_id:
        docker_mgr.stop_and_remove(agent.container_id)
        agent.status = "stopped"
        agent.stopped_at = datetime.now(timezone.utc)

    if agent and agent.worktree_path:
        git_mgr.remove_worktree(payload.repo_path, agent.worktree_path)

    mr.status = "merged"
    mr.approved_by = payload.approved_by
    mr.approved_at = datetime.now(timezone.utc)
    mr.merged_at = datetime.now(timezone.utc)
    task.status = "done"

    await db.commit()
    return {"status": "merged", "branch": task.branch_name}


@router.post("/{mr_id}/reject")
async def reject_merge(mr_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Human rejects — agent keeps working."""
    result = await db.execute(select(MergeRequest).where(MergeRequest.id == mr_id))
    mr = result.scalar_one_or_none()
    if mr is None:
        raise HTTPException(status_code=404, detail="Merge request not found")

    mr.status = "rejected"
    task_result = await db.execute(select(Task).where(Task.id == mr.task_id))
    if task_result:
        task = task_result.scalar_one_or_none()
        if task:
            task.status = "running"

    await db.commit()
    return {"status": "rejected"}
