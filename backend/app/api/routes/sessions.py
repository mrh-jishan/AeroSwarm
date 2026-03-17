"""Sessions API — create session, trigger orchestration, list sessions."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.database import get_db
from app.models.base import Agent, Session, Task
from app.services.orchestrator import OrchestratorService

router = APIRouter()
orchestrator = OrchestratorService()


class CreateSessionRequest(BaseModel):
    repo_url: str
    prompt: str


class SessionResponse(BaseModel):
    id: uuid.UUID
    repo_url: str
    prompt: str
    status: str
    task_count: int


@router.post("/", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(payload: CreateSessionRequest, db: AsyncSession = Depends(get_db)):
    """
    Create a new AeroSwarm session:
    1. Persist the session and prompt.
    2. Call Manager LLM to decompose into sub-tasks.
    3. Persist all sub-tasks (agents are spawned separately).
    """
    # Validate repo_url is a safe string (basic injection guard)
    if not payload.repo_url.startswith(("https://", "http://", "git@")):
        raise HTTPException(status_code=400, detail="Invalid repo_url scheme")

    session = Session(repo_url=payload.repo_url, prompt=payload.prompt, status="planning")
    db.add(session)
    await db.flush()  # get session.id without committing

    # Decompose prompt into sub-tasks
    try:
        sub_tasks = await orchestrator.decompose(payload.prompt)
    except ValueError as exc:
        await db.rollback()
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

    session.status = "planning_complete"
    await db.commit()
    await db.refresh(session)

    return SessionResponse(
        id=session.id,
        repo_url=session.repo_url,
        prompt=session.prompt,
        status=session.status,
        task_count=len(tasks),
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(session_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    task_result = await db.execute(select(Task).where(Task.session_id == session_id))
    tasks = task_result.scalars().all()

    return SessionResponse(
        id=session.id,
        repo_url=session.repo_url,
        prompt=session.prompt,
        status=session.status,
        task_count=len(tasks),
    )
