"""
AeroSwarm Backend — FastAPI Application Entry Point
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import agents, merge_requests, sessions
from app.core.config import settings
from app.core.database import engine
from app.models import base  # noqa: F401 — ensure models are imported before create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Nothing blocking here; Alembic handles migrations separately.
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


@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "aeroswarm-backend"}
