"""
Agents API — spawn agents, stream logs via WebSocket, VFS (read/write files).
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    WebSocket,
    WebSocketDisconnect,
    WebSocketException,
    status,
)
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal, get_db
from app.core.security import (
    AuthContext,
    get_websocket_auth_context,
    require_internal_context,
    require_user_context,
)
from app.models.base import Agent, Session, Task
from app.services.agent_launcher import AgentLauncherService
from app.services.redis_streamer import redis_streamer

router = APIRouter()
launcher = AgentLauncherService()


# ── Spawn ──────────────────────────────────────────────────────────────────────

class SpawnAgentRequest(BaseModel):
    task_id: uuid.UUID


class AgentResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    task_id: uuid.UUID
    task_title: str
    scope_dir: str
    status: str
    port: int | None


class AgentLogsResponse(BaseModel):
    lines: list[str]
    next_before: int | None


@router.post("/", status_code=status.HTTP_201_CREATED)
async def spawn_agent(
    payload: SpawnAgentRequest,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Spawn a Docker container + Git worktree for a task."""
    result = await db.execute(
        select(Task)
        .join(Session, Session.id == Task.session_id)
        .where(Task.id == payload.task_id, Session.owner_user_id == auth.user_id)
    )
    task = result.scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    agent = await launcher.launch_for_task(db, task)
    await db.commit()

    return {
        "agent_id": str(agent.id),
        "port": agent.port,
        "worktree_path": agent.worktree_path,
    }


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: uuid.UUID,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent, Task, Session)
        .join(Task, Task.id == Agent.task_id)
        .join(Session, Session.id == Task.session_id)
        .where(Agent.id == agent_id, Session.owner_user_id == auth.user_id)
    )
    row = result.one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent, task, session = row
    return AgentResponse(
        id=agent.id,
        session_id=session.id,
        task_id=task.id,
        task_title=task.title,
        scope_dir=task.scope_dir,
        status=agent.status,
        port=agent.port,
    )


@router.get("/{agent_id}/logs", response_model=AgentLogsResponse)
async def get_agent_logs(
    agent_id: uuid.UUID,
    before: int = Query(0, ge=0),
    limit: int = Query(200, ge=1, le=500),
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Agent)
        .join(Task, Task.id == Agent.task_id)
        .join(Session, Session.id == Task.session_id)
        .where(Agent.id == agent_id, Session.owner_user_id == auth.user_id)
    )
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not agent.container_id:
        return AgentLogsResponse(lines=[], next_before=None)

    logs = launcher.docker_manager.get_logs(agent.container_id, tail=10_000)
    all_lines = logs.splitlines()
    end = max(len(all_lines) - before, 0)
    start = max(end - limit, 0)
    next_before = len(all_lines) - start if start > 0 else None
    return AgentLogsResponse(
        lines=all_lines[start:end],
        next_before=next_before,
    )


# ── WebSocket log streaming ───────────────────────────────────────────────────

@router.websocket("/{agent_id}/logs")
async def stream_logs(agent_id: uuid.UUID, websocket: WebSocket):
    """Stream real-time agent terminal output to the browser."""
    auth = await get_websocket_auth_context(websocket)
    if auth.is_user:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Agent)
                .join(Task, Task.id == Agent.task_id)
                .join(Session, Session.id == Task.session_id)
                .where(Agent.id == agent_id, Session.owner_user_id == auth.user_id)
            )
            if result.scalar_one_or_none() is None:
                raise WebSocketException(code=1008, reason="Agent not found")
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
async def vfs_read(
    agent_id: uuid.UUID,
    path: str = "",
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    """List directory or read file contents inside an agent's worktree."""
    result = await db.execute(
        select(Agent)
        .join(Task, Task.id == Agent.task_id)
        .join(Session, Session.id == Task.session_id)
        .where(Agent.id == agent_id, Session.owner_user_id == auth.user_id)
    )
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
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    """Write file content inside an agent's worktree (user manual edit)."""
    result = await db.execute(
        select(Agent)
        .join(Task, Task.id == Agent.task_id)
        .join(Session, Session.id == Task.session_id)
        .where(Agent.id == agent_id, Session.owner_user_id == auth.user_id)
    )
    agent = result.scalar_one_or_none()
    if agent is None or agent.worktree_path is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    target = _safe_resolve(agent.worktree_path, path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload.content, encoding="utf-8")
    return {"path": path, "bytes_written": len(payload.content.encode())}


class UpdateAgentStatusRequest(BaseModel):
    status: str


@router.post("/{agent_id}/status")
async def update_agent_status(
    agent_id: uuid.UUID,
    payload: UpdateAgentStatusRequest,
    _auth: AuthContext = Depends(require_internal_context),
    db: AsyncSession = Depends(get_db),
):
    """Internal worker callback used to transition the dashboard state."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent.status = payload.status
    if payload.status == "idle":
        task_result = await db.execute(select(Task).where(Task.id == agent.task_id))
        task = task_result.scalar_one_or_none()
        if task:
            task.status = "done"
    if payload.status == "stopped":
        agent.stopped_at = datetime.now(timezone.utc)

    await db.commit()
    return {"agent_id": str(agent.id), "status": agent.status}
