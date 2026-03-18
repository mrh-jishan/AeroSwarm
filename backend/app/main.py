"""
AeroSwarm Backend — FastAPI Application Entry Point
"""

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import agents, auth, merge_requests, sessions, vcs
from app.core.config import settings
from app.core.security import validate_csrf_request
from app.models import base  # noqa: F401 — ensure models are imported before create_all
from app.services.readiness import ReadinessService


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
readiness = ReadinessService()

# ── CORS (restrict in production via settings) ────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def csrf_protection_middleware(request: Request, call_next):
    try:
        validate_csrf_request(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(merge_requests.router, prefix="/api/merge-requests", tags=["merge"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(vcs.router, prefix="/api/vcs", tags=["vcs"])


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "aeroswarm-backend"}


@app.get("/ready")
async def readiness_check():
    ready, checks = await readiness.run_checks()
    if not ready:
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "service": "aeroswarm-backend", "checks": checks},
        )

    return {"status": "ok", "service": "aeroswarm-backend", "checks": checks}
