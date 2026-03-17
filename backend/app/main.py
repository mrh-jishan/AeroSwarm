"""
AeroSwarm Backend — FastAPI Application Entry Point
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agents, auth, merge_requests, sessions, vcs
from app.core.config import settings
from app.models import base  # noqa: F401 — ensure models are imported before create_all


def _run_alembic_upgrade() -> None:
    from alembic import command
    from alembic.config import Config

    alembic_ini = Path(__file__).resolve().parents[1] / "alembic.ini"
    config = Config(str(alembic_ini))
    command.upgrade(config, "head")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    if settings.RUN_MIGRATIONS_ON_STARTUP:
        await asyncio.to_thread(_run_alembic_upgrade)
    yield


app = FastAPI(
    title="AeroSwarm API",
    description="Multi-agent parallel cloud IDE — orchestration backend",
    version="0.1.0",
    lifespan=lifespan,
)

# ── CORS (restrict in production via settings) ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(merge_requests.router, prefix="/api/merge-requests", tags=["merge"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(vcs.router, prefix="/api/vcs", tags=["vcs"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "aeroswarm-backend"}
