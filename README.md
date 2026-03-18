# AeroSwarm

> **Multi-Agent Parallel Cloud IDE** — A "Parallel Software Factory" that spawns concurrent AI coding agents in isolated Docker containers, each working on a dedicated Git Worktree of your codebase.

---

## Architecture at a Glance

```
Browser (Next.js Grid Dashboard)
        ↕  REST + WebSocket
FastAPI Backend (Orchestrator + Docker Manager + Git Manager)
        ↕  Docker API
Agent Containers (LangGraph Workers × N)
        ↕  Traefik Dynamic Routing
Live Preview URLs (agent-<id>.aeroswarm.dev)
```

## Quick Start (Local Dev)

### Prerequisites
- Docker Desktop
- Python 3.12+ with Poetry
- Node.js 20+

### 1. Start all infrastructure services

```bash
cd infra/docker
docker compose up -d
```

This starts: **PostgreSQL**, **Redis**, **Traefik**, the **FastAPI backend**, and the **background worker**.

### 2. Run database migrations

```bash
cd backend
poetry install
poetry run alembic upgrade head
```

Copy the backend env template before running live GitHub integrations:

```bash
cd backend
cp .env.example .env
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000)

### 4. Build the agent container image

```bash
cd agent-engine
docker build -t aeroswarm-agent:latest .
```

---

## Project Structure

```
AeroSwarm/
├── AeroSwarm PRD.md          # ← Product Requirements Document (source of truth)
├── frontend/                 # Next.js 16 — Grid Dashboard, Terminal panels, VFS editor
├── backend/                  # FastAPI — Orchestrator, Docker Manager, Git Manager, WebSocket streaming
├── agent-engine/             # LangGraph worker — runs inside each Docker container
├── infra/
│   ├── docker/               # docker-compose.yml for local dev
│   ├── k8s/                  # Kubernetes manifests (Phase 3)
│   └── traefik/              # Traefik dynamic routing config
└── docs/
    └── INITIAL_INVESTIGATION.md   # Full architecture investigation & phase plan
```

---

## Delivery Phases

| Phase | Weeks | Goal |
|-------|-------|------|
| 1 — Core Engine | 1–4 | Backend proves parallel agents write code without file corruption |
| 2 — Web Interface | 5–8 | Next.js Grid Dashboard with live terminal streaming |
| 3 — Previews & Merge | 9–12 | Traefik live previews + visual 3-way merge UI + K8s deployment |

See [AeroSwarm PRD.md](AeroSwarm%20PRD.md) for the full product requirements and [docs/INITIAL_INVESTIGATION.md](docs/INITIAL_INVESTIGATION.md) for the technical investigation.

For live GitHub OAuth, GitHub App installation, PR sync, and webhook validation, use [docs/GITHUB_LIVE_VALIDATION.md](docs/GITHUB_LIVE_VALIDATION.md).

For deployment and go-live checks, use [docs/RELEASE_CHECKLIST.md](docs/RELEASE_CHECKLIST.md).

For a production-like local or staging stack with frontend, backend, worker, Postgres, and Redis, use [docs/STAGING_DEPLOYMENT.md](docs/STAGING_DEPLOYMENT.md).

For GitHub Actions deployment to your own SSH-accessible machine, use [docs/GITHUB_SSH_DEPLOY.md](docs/GITHUB_SSH_DEPLOY.md).

## Shared AI Context

To keep context consistent across computers, this repo now includes:

- `CLAUDE.md` — project context and working rules for Claude-based agents.
- `.github/copilot-instructions.md` — repo-specific instructions for VS Code Copilot.
- `.vscode/settings.json` — shared VS Code workspace settings.
- `.vscode/extensions.json` — recommended extensions for this project.
- `.vscode/tasks.json` — common run tasks for backend/frontend/infra.

---

## Security

- Agent containers are network-isolated (no VPC access)
- File operations restricted to `SCOPE_DIR` (path traversal blocked)
- API keys injected at runtime via environment (never in images)
- **Human-in-the-Loop (HITL):** no code reaches `main` without explicit human approval
