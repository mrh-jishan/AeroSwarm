"""Sessions API — create session, trigger orchestration, list sessions."""

import json
import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.core.security import AuthContext, require_user_context
from app.models.base import Agent, AuditEvent, BackgroundJob, ProviderConnection, Session, Task
from app.services.audit import AuditService
from app.services.crypto import CredentialCryptoService
from app.services.docker_manager import DockerManagerService
from app.services.job_queue import JOB_TYPE_SESSION_BOOTSTRAP, JobQueueService
from app.services.llm_factory import default_model_for_provider, normalize_llm_provider
from app.services.provider_connections import ProviderConnectionService
from app.services.vcs import RepoIdentity, VcsService

router = APIRouter(dependencies=[Depends(require_user_context)])
audit = AuditService()
crypto = CredentialCryptoService()
vcs = VcsService()
provider_connections = ProviderConnectionService()
job_queue = JobQueueService()
ACTIVE_SESSION_STATUSES = {"queued", "planning", "running", "merging"}
STOPPABLE_TASK_STATUSES = {"pending", "running", "merging"}
STOPPABLE_AGENT_STATUSES = {"initializing", "running", "idle", "error"}
CANCELLABLE_JOB_STATUSES = {"queued", "running"}


class CreateSessionRequest(BaseModel):
    repo_url: str
    prompt: str
    llm_provider: Literal["openai", "gemini"] = "gemini"
    manager_model: str | None = None
    agent_model: str | None = None
    provider_connection_id: uuid.UUID | None = None
    repo_access_token: str | None = None
    repo_username: str | None = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    provider_connection_id: uuid.UUID | None = None
    repo_url: str
    vcs_provider: str | None = None
    repo_owner: str | None = None
    repo_name: str | None = None
    base_branch: str | None = None
    llm_provider: str
    manager_model: str
    agent_model: str
    prompt: str
    status: str
    error_message: str | None = None
    task_count: int
    agent_count: int = 0
    created_at: str


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


async def _load_counts_for_sessions(
    db: AsyncSession,
    session_ids: list[uuid.UUID],
) -> tuple[dict[uuid.UUID, int], dict[uuid.UUID, int]]:
    if not session_ids:
        return {}, {}

    task_count_result = await db.execute(
        select(Task.session_id, func.count(Task.id))
        .where(Task.session_id.in_(session_ids))
        .group_by(Task.session_id)
    )
    task_counts = {
        session_id: int(count)
        for session_id, count in task_count_result.all()
    }

    agent_count_result = await db.execute(
        select(Task.session_id, func.count(Agent.id))
        .join(Agent, Agent.task_id == Task.id)
        .where(Task.session_id.in_(session_ids))
        .group_by(Task.session_id)
    )
    agent_counts = {
        session_id: int(count)
        for session_id, count in agent_count_result.all()
    }

    return task_counts, agent_counts


def _serialize_session(
    session: Session,
    *,
    task_count: int,
    agent_count: int,
) -> SessionResponse:
    return SessionResponse(
        id=session.id,
        provider_connection_id=session.provider_connection_id,
        repo_url=session.repo_url,
        vcs_provider=session.vcs_provider,
        repo_owner=session.repo_owner,
        repo_name=session.repo_name,
        base_branch=session.base_branch,
        llm_provider=session.llm_provider,
        manager_model=session.manager_model,
        agent_model=session.agent_model,
        prompt=session.prompt,
        status=session.status,
        error_message=session.error_message,
        task_count=task_count,
        agent_count=agent_count,
        created_at=session.created_at.isoformat(),
    )


def _build_agent_preview_url(port: int | None) -> str | None:
    if port is None:
        return None

    base_url = settings.AGENT_PREVIEW_BASE_URL.strip().rstrip("/")
    if not base_url:
        return None

    return f"{base_url}:{port}"


async def _queue_session_bootstrap(
    db: AsyncSession,
    *,
    session: Session,
    actor: str,
    repo_access_token: str | None = None,
    repo_username: str | None = None,
    source_session_id: uuid.UUID | None = None,
) -> None:
    await audit.record(
        db,
        "session.created",
        actor,
        session_id=session.id,
        details={"repo_url": session.repo_url, "prompt": session.prompt},
    )
    await job_queue.enqueue(
        db,
        job_type=JOB_TYPE_SESSION_BOOTSTRAP,
        session_id=session.id,
        payload={
            "requested_by": actor,
            "repo_username": repo_username or "",
            "encrypted_repo_access_token": crypto.encrypt(repo_access_token)
            if repo_access_token
            else "",
        },
    )
    audit_details: dict[str, str] = {"repo_url": session.repo_url}
    if source_session_id is not None:
        audit_details["source_session_id"] = str(source_session_id)
    await audit.record(
        db,
        "session.bootstrap.queued",
        actor,
        session_id=session.id,
        details=audit_details,
    )


@router.get("/", response_model=list[SessionResponse])
async def list_sessions(
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Session)
        .where(Session.owner_user_id == auth.user_id)
        .order_by(Session.created_at.desc())
    )
    sessions = result.scalars().all()
    session_ids = [session.id for session in sessions]
    task_counts, agent_counts = await _load_counts_for_sessions(db, session_ids)

    return [
        _serialize_session(
            session,
            task_count=task_counts.get(session.id, 0),
            agent_count=agent_counts.get(session.id, 0),
        )
        for session in sessions
    ]


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
    llm_provider = normalize_llm_provider(payload.llm_provider)
    manager_model = payload.manager_model or default_model_for_provider(llm_provider)
    agent_model = payload.agent_model or default_model_for_provider(llm_provider)
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
        llm_provider=llm_provider,
        manager_model=manager_model,
        agent_model=agent_model,
        prompt=payload.prompt,
        status="queued",
        error_message=None,
    )
    db.add(session)
    await db.flush()
    await _queue_session_bootstrap(
        db,
        session=session,
        actor=auth.actor,
        repo_access_token=payload.repo_access_token,
        repo_username=payload.repo_username,
    )
    await db.commit()
    await db.refresh(session)

    return _serialize_session(
        session,
        task_count=0,
        agent_count=0,
    )


@router.post("/{session_id}/retry", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def retry_session(
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
    source_session = result.scalar_one_or_none()
    if source_session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    retried_session = Session(
        owner_user_id=source_session.owner_user_id,
        provider_connection_id=source_session.provider_connection_id,
        repo_url=source_session.repo_url,
        vcs_provider=source_session.vcs_provider,
        repo_owner=source_session.repo_owner,
        repo_name=source_session.repo_name,
        base_branch=source_session.base_branch,
        llm_provider=source_session.llm_provider,
        manager_model=source_session.manager_model,
        agent_model=source_session.agent_model,
        prompt=source_session.prompt,
        status="queued",
        error_message=None,
    )
    db.add(retried_session)
    await db.flush()
    await audit.record(
        db,
        "session.retried",
        auth.actor,
        session_id=retried_session.id,
        details={"source_session_id": str(source_session.id)},
    )
    await _queue_session_bootstrap(
        db,
        session=retried_session,
        actor=auth.actor,
        source_session_id=source_session.id,
    )
    await db.commit()
    await db.refresh(retried_session)

    return _serialize_session(
        retried_session,
        task_count=0,
        agent_count=0,
    )


@router.post("/{session_id}/stop", response_model=SessionResponse)
async def stop_session(
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

    task_counts, agent_counts = await _load_counts_for_sessions(db, [session_id])
    if session.status not in ACTIVE_SESSION_STATUSES and session.status != "stopped":
        return _serialize_session(
            session,
            task_count=task_counts.get(session_id, 0),
            agent_count=agent_counts.get(session_id, 0),
        )

    task_result = await db.execute(select(Task).where(Task.session_id == session_id))
    tasks = task_result.scalars().all()
    task_ids = [task.id for task in tasks]

    agents: list[Agent] = []
    if task_ids:
        agent_result = await db.execute(select(Agent).where(Agent.task_id.in_(task_ids)))
        agents = agent_result.scalars().all()

    job_result = await db.execute(
        select(BackgroundJob).where(
            BackgroundJob.session_id == session_id,
            BackgroundJob.status.in_(CANCELLABLE_JOB_STATUSES),
        )
    )
    jobs = job_result.scalars().all()

    docker_mgr = DockerManagerService()
    stopped_at = datetime.now(timezone.utc)

    for agent in agents:
        if agent.container_id and agent.status in STOPPABLE_AGENT_STATUSES:
            docker_mgr.stop_and_remove(agent.container_id)
        agent.status = "stopped"
        agent.stopped_at = stopped_at

    for task in tasks:
        if task.status in STOPPABLE_TASK_STATUSES:
            task.status = "stopped"

    for job in jobs:
        job.status = "cancelled"
        job.error_message = "Stopped by user"
        job.locked_at = None
        job.locked_by = None

    if session.status != "stopped":
        session.status = "stopped"
        session.error_message = "Stopped by user"
        await audit.record(
            db,
            "session.stopped",
            auth.actor,
            session_id=session.id,
            details={
                "stopped_agent_count": len(agents),
                "cancelled_job_count": len(jobs),
            },
        )

    await db.commit()
    await db.refresh(session)

    return _serialize_session(
        session,
        task_count=task_counts.get(session_id, 0),
        agent_count=agent_counts.get(session_id, 0),
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

    task_counts, agent_counts = await _load_counts_for_sessions(db, [session_id])

    return _serialize_session(
        session,
        task_count=task_counts.get(session_id, 0),
        agent_count=agent_counts.get(session_id, 0),
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
                previewUrl=_build_agent_preview_url(agent.port if agent else None),
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
