"""Sessions API — create session, trigger orchestration, list sessions."""

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.core.security import AuthContext, require_user_context
from app.models.base import Agent, AuditEvent, Session, Task
from app.services.agent_launcher import AgentLauncherService
from app.services.audit import AuditService
from app.services.orchestrator import OrchestratorService
from app.services.repo_manager import RepoManagerService

router = APIRouter(dependencies=[Depends(require_user_context)])
orchestrator = OrchestratorService()
launcher = AgentLauncherService()
audit = AuditService()
repo_mgr = RepoManagerService()


class CreateSessionRequest(BaseModel):
    repo_url: str
    prompt: str
    repo_access_token: str | None = None
    repo_username: str | None = None


class SessionResponse(BaseModel):
    id: uuid.UUID
    repo_url: str
    prompt: str
    status: str
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

    session = Session(
        owner_user_id=auth.user_id,
        repo_url=payload.repo_url,
        prompt=payload.prompt,
        status="planning",
    )
    db.add(session)
    await db.flush()  # get session.id without committing
    await audit.record(
        db,
        "session.created",
        auth.actor,
        session_id=session.id,
        details={"repo_url": payload.repo_url, "prompt": payload.prompt},
    )

    try:
        repo_mgr.clone_repo(
            session.id,
            payload.repo_url,
            repo_access_token=payload.repo_access_token,
            repo_username=payload.repo_username,
        )
    except Exception as exc:
        await db.rollback()
        repo_mgr.cleanup_session_repo(session.id)
        raise HTTPException(status_code=502, detail="Failed to clone repository") from exc
    await audit.record(
        db,
        "repo.cloned",
        auth.actor,
        session_id=session.id,
        details={"repo_url": payload.repo_url},
    )

    # Decompose prompt into sub-tasks
    try:
        sub_tasks = await orchestrator.decompose(payload.prompt)
    except ValueError as exc:
        await db.rollback()
        repo_mgr.cleanup_session_repo(session.id)
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    tasks = []
    for st in sub_tasks:
        task = Task(
            session_id=session.id,
            title=st.title,
            description=st.description,
            scope_dir=st.scope_dir,
            status="pending",
            branch_name=None,
        )
        db.add(task)
        tasks.append(task)

    await db.flush()

    try:
        for task in tasks:
            agent = await launcher.launch_for_task(db, task)
            await audit.record(
                db,
                "agent.launched",
                auth.actor,
                session_id=session.id,
                task_id=task.id,
                agent_id=agent.id,
                details={"task_title": task.title, "scope_dir": task.scope_dir, "port": agent.port},
            )
    except Exception as exc:
        await db.rollback()
        repo_mgr.cleanup_session_repo(session.id)
        raise HTTPException(status_code=502, detail=f"Failed to launch agents: {exc}") from exc

    session.status = "running"
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.id,
        repo_url=session.repo_url,
        prompt=session.prompt,
        status=session.status,
        task_count=len(tasks),
        agent_count=len(tasks),
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
    agent_result = await db.execute(
        select(Agent).where(Agent.task_id.in_([task.id for task in tasks]))
    ) if tasks else None
    agents = agent_result.scalars().all() if agent_result else []

    return SessionResponse(
        id=session.id,
        repo_url=session.repo_url,
        prompt=session.prompt,
        status=session.status,
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
