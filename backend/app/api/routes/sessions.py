"""Sessions API — create session, trigger orchestration, list sessions."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import AuthContext, require_user_context
from app.models.base import Agent, AuditEvent, ProviderConnection, Session, Task
from app.services.audit import AuditService
from app.services.crypto import CredentialCryptoService
from app.services.job_queue import JOB_TYPE_SESSION_BOOTSTRAP, JobQueueService
from app.services.provider_connections import ProviderConnectionService
from app.services.vcs import RepoIdentity, VcsService

router = APIRouter(dependencies=[Depends(require_user_context)])
audit = AuditService()
crypto = CredentialCryptoService()
vcs = VcsService()
provider_connections = ProviderConnectionService()
job_queue = JobQueueService()


class CreateSessionRequest(BaseModel):
    repo_url: str
    prompt: str
    provider_connection_id: uuid.UUID | None = None
    repo_access_token: str | None = None
    repo_username: str | None = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    repo_url: str
    vcs_provider: str | None = None
    repo_owner: str | None = None
    repo_name: str | None = None
    base_branch: str | None = None
    prompt: str
    status: str
    error_message: str | None = None
    task_count: int
    agent_count: int = 0


class SessionAgentResponse(BaseModel):
    id: uuid.UUID
    taskId: uuid.UUID
    taskTitle: str
    scopeDir: str
    status: str
    port: int | None
    previewUrl: str | None


class AuditEventResponse(BaseModel):
    id: uuid.UUID
    action: str
    actor: str
    details: dict | None
    created_at: str


async def _resolve_provider_connection(
    *,
    payload: CreateSessionRequest,
    auth: AuthContext,
    db: AsyncSession,
    identity: RepoIdentity,
) -> ProviderConnection | None:
    if payload.provider_connection_id is None:
        return None

    result = await db.execute(
        select(ProviderConnection).where(
            ProviderConnection.id == payload.provider_connection_id,
            ProviderConnection.user_id == auth.user_id,
        )
    )
    connection = result.scalar_one_or_none()
    if connection is None:
        raise HTTPException(status_code=404, detail="Provider connection not found")
    return connection


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    payload: CreateSessionRequest,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new AeroSwarm session:
    1. Persist the session and prompt.
    2. Clone the target repository into the session workspace.
    3. Call Manager LLM to decompose into sub-tasks.
    4. Persist tasks and launch one agent per task.
    """
    # Validate repo_url is a safe string (basic injection guard)
    if not payload.repo_url.startswith(("https://", "http://", "git@")):
        raise HTTPException(status_code=400, detail="Invalid repo_url scheme")

    identity = vcs.parse_repo_identity(payload.repo_url)
    provider_connection = await _resolve_provider_connection(
        payload=payload,
        auth=auth,
        db=db,
        identity=identity,
    )

    session = Session(
        owner_user_id=auth.user_id,
        provider_connection_id=provider_connection.id if provider_connection else None,
        repo_url=payload.repo_url,
        vcs_provider=identity.provider,
        repo_owner=identity.owner,
        repo_name=identity.name,
        prompt=payload.prompt,
        status="queued",
        error_message=None,
    )
    db.add(session)
    await db.flush()
    await audit.record(
        db,
        "session.created",
        auth.actor,
        session_id=session.id,
        details={"repo_url": payload.repo_url, "prompt": payload.prompt},
    )
    await job_queue.enqueue(
        db,
        job_type=JOB_TYPE_SESSION_BOOTSTRAP,
        session_id=session.id,
        payload={
            "requested_by": auth.actor,
            "repo_username": payload.repo_username or "",
            "encrypted_repo_access_token": crypto.encrypt(payload.repo_access_token)
            if payload.repo_access_token
            else "",
        },
    )
    await audit.record(
        db,
        "session.bootstrap.queued",
        auth.actor,
        session_id=session.id,
        details={"repo_url": payload.repo_url},
    )
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.id,
        repo_url=session.repo_url,
        vcs_provider=session.vcs_provider,
        repo_owner=session.repo_owner,
        repo_name=session.repo_name,
        base_branch=session.base_branch,
        prompt=session.prompt,
        status=session.status,
        error_message=session.error_message,
        task_count=0,
        agent_count=0,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.owner_user_id == auth.user_id,
        )
    )
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    task_result = await db.execute(select(Task).where(Task.session_id == session_id))
    tasks = task_result.scalars().all()
    agent_result = (
        await db.execute(select(Agent).where(Agent.task_id.in_([task.id for task in tasks])))
        if tasks
        else None
    )
    agents = agent_result.scalars().all() if agent_result else []

    return SessionResponse(
        id=session.id,
        repo_url=session.repo_url,
        vcs_provider=session.vcs_provider,
        repo_owner=session.repo_owner,
        repo_name=session.repo_name,
        base_branch=session.base_branch,
        prompt=session.prompt,
        status=session.status,
        error_message=session.error_message,
        task_count=len(tasks),
        agent_count=len(agents),
    )


@router.get("/{session_id}/agents", response_model=list[SessionAgentResponse])
async def list_session_agents(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.owner_user_id == auth.user_id,
        )
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    tasks_result = await db.execute(select(Task).where(Task.session_id == session_id))
    tasks = tasks_result.scalars().all()

    task_ids = [task.id for task in tasks]
    if not task_ids:
        return []

    agents_result = await db.execute(select(Agent).where(Agent.task_id.in_(task_ids)))
    agents = agents_result.scalars().all()
    agents_by_task_id = {agent.task_id: agent for agent in agents}

    response = []
    for task in tasks:
        agent = agents_by_task_id.get(task.id)
        response.append(
            SessionAgentResponse(
                id=agent.id if agent else task.id,
                taskId=task.id,
                taskTitle=task.title,
                scopeDir=task.scope_dir,
                status=agent.status if agent else "initializing",
                port=agent.port if agent else None,
                previewUrl=f"http://localhost:{agent.port}" if agent and agent.port else None,
            )
        )

    return response


@router.get("/{session_id}/audit", response_model=list[AuditEventResponse])
async def list_session_audit_events(
    session_id: uuid.UUID,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    session_result = await db.execute(
        select(Session).where(
            Session.id == session_id,
            Session.owner_user_id == auth.user_id,
        )
    )
    session = session_result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    result = await db.execute(
        select(AuditEvent)
        .where(AuditEvent.session_id == session_id)
        .order_by(AuditEvent.created_at.desc())
    )
    events = result.scalars().all()

    return [
        AuditEventResponse(
            id=event.id,
            action=event.action,
            actor=event.actor,
            details=json.loads(event.details) if event.details else None,
            created_at=event.created_at.isoformat(),
        )
        for event in events
    ]
