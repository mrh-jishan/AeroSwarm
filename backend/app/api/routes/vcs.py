"""VCS provider connection APIs."""

from __future__ import annotations

from datetime import datetime, timezone
import json
from urllib.parse import urlencode
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import get_db
from app.core.security import AuthContext, require_user_context
from app.models.base import Agent, MergeRequest, ProviderConnection, Session, Task, User
from app.services.audit import AuditService
from app.services.crypto import CredentialCryptoService
from app.services.docker_manager import DockerManagerService
from app.services.git_manager import GitManagerService
from app.services.github_provider import GitHubProviderService
from app.services.repo_manager import RepoManagerService

router = APIRouter()
crypto = CredentialCryptoService()
github = GitHubProviderService()
audit = AuditService()
docker_mgr = DockerManagerService()
git_mgr = GitManagerService()
repo_mgr = RepoManagerService()


class GitHubConnectRequest(BaseModel):
    access_token: str = Field(min_length=1)


class ProviderConnectionResponse(BaseModel):
    id: uuid.UUID
    provider: str
    account_login: str


def _build_frontend_redirect(path: str, params: dict[str, str] | None = None) -> str:
    safe_path = path if path.startswith("/") else "/"
    base = f"{settings.FRONTEND_URL.rstrip('/')}{safe_path}"
    if not params:
        return base
    return f"{base}?{urlencode(params)}"


async def _upsert_github_connection(
    *,
    db: AsyncSession,
    user_id: uuid.UUID,
    account_login: str,
    access_token: str,
) -> ProviderConnection:
    result = await db.execute(
        select(ProviderConnection).where(
            ProviderConnection.user_id == user_id,
            ProviderConnection.provider == "github",
            ProviderConnection.account_login == account_login,
        )
    )
    connection = result.scalar_one_or_none()
    encrypted_token = crypto.encrypt(access_token)

    if connection is None:
        connection = ProviderConnection(
            user_id=user_id,
            provider="github",
            account_login=account_login,
            encrypted_access_token=encrypted_token,
        )
        db.add(connection)
        await db.flush()
    else:
        connection.encrypted_access_token = encrypted_token

    return connection


@router.post("/github/connect", response_model=ProviderConnectionResponse, status_code=status.HTTP_201_CREATED)
async def connect_github(
    payload: GitHubConnectRequest,
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    try:
        gh_user = await github.get_authenticated_user(payload.access_token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    connection = await _upsert_github_connection(
        db=db,
        user_id=auth.user_id,
        account_login=gh_user.login,
        access_token=payload.access_token,
    )

    await audit.record(
        db,
        "vcs.github.connected",
        auth.actor,
        details={"account_login": gh_user.login, "method": "token"},
    )
    await db.commit()
    await db.refresh(connection)

    return ProviderConnectionResponse(
        id=connection.id,
        provider=connection.provider,
        account_login=connection.account_login,
    )


@router.get("/github/oauth/start")
async def start_github_oauth(
    redirect_path: str = "/",
    auth: AuthContext = Depends(require_user_context),
):
    state = crypto.encrypt_json(
        {
            "user_id": str(auth.user_id),
            "redirect_path": redirect_path if redirect_path.startswith("/") else "/",
        }
    )
    try:
        authorize_url = github.build_oauth_authorize_url(state)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse(authorize_url, status_code=status.HTTP_307_TEMPORARY_REDIRECT)


@router.get("/github/oauth/callback")
async def github_oauth_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    if error:
        return RedirectResponse(
            _build_frontend_redirect("/", {"github_oauth": "error", "message": error}),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )
    if not code or not state:
        return RedirectResponse(
            _build_frontend_redirect("/", {"github_oauth": "error", "message": "missing callback parameters"}),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    try:
        state_payload = crypto.decrypt_json(
            state,
            ttl=settings.GITHUB_OAUTH_STATE_TTL_SECONDS,
        )
        user_id = uuid.UUID(str(state_payload["user_id"]))
        redirect_path = str(state_payload.get("redirect_path", "/"))
        access_token = await github.exchange_code_for_access_token(code)
        gh_user = await github.get_authenticated_user(access_token)
    except (KeyError, ValueError) as exc:
        return RedirectResponse(
            _build_frontend_redirect("/", {"github_oauth": "error", "message": str(exc)}),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if user is None:
        return RedirectResponse(
            _build_frontend_redirect("/", {"github_oauth": "error", "message": "user not found"}),
            status_code=status.HTTP_307_TEMPORARY_REDIRECT,
        )

    connection = await _upsert_github_connection(
        db=db,
        user_id=user.id,
        account_login=gh_user.login,
        access_token=access_token,
    )
    await audit.record(
        db,
        "vcs.github.connected",
        user.email,
        details={"account_login": gh_user.login, "method": "oauth"},
    )
    await db.commit()

    return RedirectResponse(
        _build_frontend_redirect(
            redirect_path,
            {"github_oauth": "connected", "account": connection.account_login},
        ),
        status_code=status.HTTP_307_TEMPORARY_REDIRECT,
    )


@router.get("/connections", response_model=list[ProviderConnectionResponse])
async def list_connections(
    auth: AuthContext = Depends(require_user_context),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(ProviderConnection).where(ProviderConnection.user_id == auth.user_id)
    )
    connections = result.scalars().all()
    return [
        ProviderConnectionResponse(
            id=connection.id,
            provider=connection.provider,
            account_login=connection.account_login,
        )
        for connection in connections
    ]


@router.post("/github/webhooks")
async def github_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    try:
        payload = await request.body()
        if not github.verify_webhook_signature(
            payload,
            request.headers.get("x-hub-signature-256"),
        ):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    event_name = request.headers.get("x-github-event", "")
    body = json.loads(payload.decode("utf-8"))

    if event_name == "ping":
        return {"status": "ok"}

    if event_name != "pull_request":
        return {"status": "ignored", "event": event_name}

    pull_request = body.get("pull_request", {})
    repository = body.get("repository", {})
    owner = repository.get("owner", {}).get("login")
    repo_name = repository.get("name")
    number = pull_request.get("number")
    action = body.get("action")
    merged = bool(pull_request.get("merged"))

    if not owner or not repo_name or number is None:
        raise HTTPException(status_code=400, detail="Invalid pull_request payload")

    result = await db.execute(
        select(MergeRequest, Task, Session)
        .join(Task, Task.id == MergeRequest.task_id)
        .join(Session, Session.id == Task.session_id)
        .where(
            MergeRequest.provider_pr_number == int(number),
            Session.vcs_provider == "github",
            Session.repo_owner == str(owner),
            Session.repo_name == str(repo_name),
        )
    )
    row = result.first()
    if row is None:
        return {"status": "ignored", "reason": "merge request not found"}

    mr, task, session = row
    mr.provider_pr_url = str(pull_request.get("html_url")) if pull_request.get("html_url") else mr.provider_pr_url

    if action == "closed":
        if merged:
            mr.status = "merged"
            task.status = "done"
            merged_at = pull_request.get("merged_at")
            if merged_at:
                mr.merged_at = datetime.fromisoformat(str(merged_at).replace("Z", "+00:00"))
            else:
                mr.merged_at = datetime.now(timezone.utc)

            agent_result = await db.execute(select(Agent).where(Agent.task_id == task.id))
            agent = agent_result.scalar_one_or_none()
            if agent and agent.container_id:
                docker_mgr.stop_and_remove(agent.container_id)
                agent.status = "stopped"
                agent.stopped_at = datetime.now(timezone.utc)
            if agent and agent.worktree_path:
                repo_path = repo_mgr.get_repo_path(session.id)
                git_mgr.remove_worktree(str(repo_path), agent.worktree_path)
        else:
            mr.status = "rejected"
            task.status = "running"
    elif action in {"opened", "reopened", "synchronize", "ready_for_review"}:
        if mr.status != "merged":
            mr.status = "pending"
            task.status = "merging"

    await audit.record(
        db,
        "merge.github_webhook.synced",
        "github-webhook",
        session_id=session.id,
        task_id=task.id,
        details={
            "action": action,
            "pr_number": int(number),
            "merged": merged,
            "status": mr.status,
        },
    )
    await db.commit()
    return {"status": "ok", "merge_request_id": str(mr.id)}
