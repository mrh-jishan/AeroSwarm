"""
Agents API — spawn agents, stream logs via WebSocket, VFS (read/write files).
"""

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.models.base import Agent, Task
from app.services.docker_manager import DockerManagerService
from app.services.git_manager import GitManagerService
from app.services.redis_streamer import redis_streamer

router = APIRouter()
docker_mgr = DockerManagerService()
git_mgr = GitManagerService()


# ── Spawn ──────────────────────────────────────────────────────────────────────

class SpawnAgentRequest(BaseModel):
    task_id: uuid.UUID
    repo_path: str  # absolute path on the server to the cloned repo


@router.post("/", status_code=status.HTTP_201_CREATED)
async def spawn_agent(payload: SpawnAgentRequest, db: AsyncSession = Depends(get_db)):
    """Spawn a Docker container + Git worktree for a task."""
    result = await db.execute(select(Task).where(Task.id == payload.task_id))
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    agent_id = uuid.uuid4()

    # Create worktree
    worktree_path = git_mgr.create_worktree(
        session_id=task.session_id,
        agent_id=agent_id,
        repo_path=payload.repo_path,
    )

    # Assign port (simple range; production uses Redis INCR)
    port = settings.AGENT_PORT_RANGE_START + (int(agent_id) % (
        settings.AGENT_PORT_RANGE_END - settings.AGENT_PORT_RANGE_START
    ))

    # Spawn container
    container_id = await docker_mgr.spawn_agent(
        db=db,
        task_id=task.id,
        worktree_path=worktree_path,
        scope_dir=task.scope_dir,
        task_description=task.description or task.title,
        port=port,
        agent_id=agent_id,
    )

    # Update task + create Agent record
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
    await db.commit()

    return {"agent_id": str(agent_id), "port": port, "worktree_path": worktree_path}


# ── WebSocket log streaming ───────────────────────────────────────────────────

@router.websocket("/{agent_id}/logs")
async def stream_logs(agent_id: uuid.UUID, websocket: WebSocket):
    """Stream real-time agent terminal output to the browser."""
    await websocket.accept()
    try:
        async for log_line in redis_streamer.subscribe(str(agent_id)):
            await websocket.send_text(log_line)
    except WebSocketDisconnect:
        pass


# ── VFS (Virtual File System) ────────────────────────────────────────────────

def _safe_resolve(worktree_path: str, rel_path: str) -> Path:
    """Resolve a relative path inside the worktree and guard against path traversal."""
    base = Path(worktree_path).resolve()
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(base)):
        raise HTTPException(status_code=400, detail="Path traversal detected")
    return target


@router.get("/{agent_id}/files")
async def vfs_read(agent_id: uuid.UUID, path: str = "", db: AsyncSession = Depends(get_db)):
    """List directory or read file contents inside an agent's worktree."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None or agent.worktree_path is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    target = _safe_resolve(agent.worktree_path, path)

    if target.is_dir():
        entries = [
            {"name": e.name, "is_dir": e.is_dir()}
            for e in sorted(target.iterdir())
        ]
        return {"path": path, "entries": entries}
    elif target.is_file():
        content = target.read_text(encoding="utf-8", errors="replace")
        return {"path": path, "content": content}
    else:
        raise HTTPException(status_code=404, detail="Path not found")


class WriteFileRequest(BaseModel):
    content: str


@router.put("/{agent_id}/files")
async def vfs_write(
    agent_id: uuid.UUID,
    path: str,
    payload: WriteFileRequest,
    db: AsyncSession = Depends(get_db),
):
    """Write file content inside an agent's worktree (user manual edit)."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None or agent.worktree_path is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    target = _safe_resolve(agent.worktree_path, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"path": path, "bytes_written": len(payload.content.encode())}
