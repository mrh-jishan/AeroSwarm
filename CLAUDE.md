# CLAUDE.md

This file provides shared project context for Claude-based coding agents.

## Project Source Of Truth
- Product requirements: `AeroSwarm PRD.md`
- Technical investigation: `docs/INITIAL_INVESTIGATION.md`

## Product Summary
AeroSwarm is a multi-agent parallel cloud IDE where an orchestrator decomposes a feature prompt into sub-tasks and runs workers concurrently in isolated Docker containers and Git worktrees.

## Current Architecture (Phase 1 foundation)
- Frontend: Next.js (`frontend/`)
- Backend: FastAPI (`backend/`)
- Agent runtime: LangGraph worker (`agent-engine/`)
- Infra: Docker Compose + Traefik + Postgres + Redis (`infra/docker/`)

## Core Requirements To Preserve
1. Strict per-agent workspace isolation with Git worktrees.
2. Human-in-the-loop approval before merges to `main`.
3. Real-time terminal log streaming via Redis + WebSocket.
4. Dynamic live preview routing per agent container.
5. Security controls: sandboxing, least privilege, runtime secrets.

## Development Conventions
- Keep changes minimal and scoped.
- Avoid unrelated refactors.
- Preserve API contracts unless requested.
- Add tests when behavior changes.
- Prefer explicit error handling over silent failure.

## Important Paths
- Backend entrypoint: `backend/app/main.py`
- Orchestrator service: `backend/app/services/orchestrator.py`
- Docker manager: `backend/app/services/docker_manager.py`
- Git manager: `backend/app/services/git_manager.py`
- Agent graph: `agent-engine/agent/graph.py`
- Agent tools: `agent-engine/agent/tools.py`

## Runbook
- Start infra: `cd infra/docker && docker compose up -d`
- Backend (local): `cd backend && poetry install && poetry run uvicorn app.main:app --reload`
- Frontend: `cd frontend && npm install && npm run dev`

## Notes For AI Agents
- Use `AeroSwarm PRD.md` as requirements source.
- If requirements conflict with implementation, prioritize PRD and flag mismatch.
- Never bypass approval gates in merge flow.
