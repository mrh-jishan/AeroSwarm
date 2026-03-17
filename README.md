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

This starts: **PostgreSQL**, **Redis**, **Traefik**, and the **FastAPI backend**.

### 2. Run database migrations

```bash
cd backend
poetry install
poetry run alembic upgrade head
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
├── frontend/         # Next.js 14 — Grid Dashboard, Terminal panels, VFS editor
├── backend/          # FastAPI — Orchestrator, Docker Manager, Git Manager, WebSocket streaming
├── agent-engine/     # LangGraph worker — runs inside each Docker container
├── infra/
│   ├── docker/       # docker-compose.yml for local dev
│   ├── k8s/          # Kubernetes manifests (Phase 3)
│   └── traefik/      # Traefik dynamic routing config
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

See [docs/INITIAL_INVESTIGATION.md](docs/INITIAL_INVESTIGATION.md) for the full technical investigation.

---

## Security

- Agent containers are network-isolated (no VPC access)
- File operations restricted to `SCOPE_DIR` (path traversal blocked)
- API keys injected at runtime via environment (never in images)
- **Human-in-the-Loop (HITL):** no code reaches `main` without explicit human approval
