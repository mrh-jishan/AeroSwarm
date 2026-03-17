# AeroSwarm — Initial Investigation Report
**Date:** March 17, 2026  
**Document Type:** Technical Investigation & Architecture Analysis  
**Source:** AeroSwarm SRS/PRD (March 17, 2026)

---

## 1. Product Summary

AeroSwarm is a **web-based, multi-agent parallel cloud IDE** — a "Parallel Software Factory" that allows a single Project Manager / Lead Developer to:

1. Submit a high-level feature prompt.
2. An **Orchestrator AI** decomposes it into independent sub-tasks.
3. **Multiple AI Worker Agents** execute those sub-tasks **concurrently** inside isolated Docker containers, each operating on a dedicated Git Worktree.
4. A **Grid Dashboard** lets the user monitor all agents in real-time (terminals, file system, live previews).
5. A **"Janitor" Merge Protocol** handles automated linting/testing, visual conflict resolution, and cleanup.

---

## 2. Functional Requirements Breakdown

| ID | Feature | Core Behaviour |
|----|---------|---------------|
| FR1 | AI Orchestration Engine | Manager LLM decomposes prompt → JSON sub-tasks → assigns one Worker Agent per task with a scoped directory |
| FR2 | Workspace Isolation | Each agent gets its own `git worktree` inside a Docker container; dependencies auto-installed at init |
| FR3 | Grid Dashboard (UI) | Browser-based grid — live terminal streaming, VFS code editor per agent |
| FR4 | Parallel Live Previews | Dynamic port/subdomain per container, side-by-side iframe/split comparison |
| FR5 | Janitor Merge Protocol | Automated linter + test pre-flight → visual 3-way Git diff/merge → container + worktree teardown |

---

## 3. Architecture Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                        Browser (Next.js)                           │
│   Grid Dashboard  │  VFS Code Editor  │  Live Preview iFrames      │
│   WebSocket terminal streams         │  Merge UI (3-way diff)      │
└──────────────────────────┬─────────────────────────────────────────┘
                           │  REST + WebSocket
┌──────────────────────────▼─────────────────────────────────────────┐
│               Backend API (FastAPI / Python)                        │
│  /orchestrate  /agents  /workspaces  /merge  /stream (WS)          │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────────────┐   │
│  │ Manager LLM  │   │  Docker Mgr  │   │  Redis Pub/Sub       │   │
│  │ (Decompose)  │   │  (Spawner)   │   │  (Log Streaming)     │   │
│  └──────────────┘   └──────────────┘   └──────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                    PostgreSQL                                 │  │
│  │    sessions | agents | tasks | worktrees | merge_requests    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────────────────────────┬─────────────────────────────────────────┘
                           │  Docker API
┌──────────────────────────▼─────────────────────────────────────────┐
│               Container Layer (Docker / K8s)                        │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐ │
│  │  Agent Container │  │  Agent Container │  │  Agent Container │ │
│  │  (Worker A)      │  │  (Worker B)      │  │  (Worker C)      │ │
│  │  git worktree/a  │  │  git worktree/b  │  │  git worktree/c  │ │
│  │  LangGraph loop  │  │  LangGraph loop  │  │  LangGraph loop  │ │
│  │  dev-server:3001 │  │  dev-server:3002 │  │  dev-server:3003 │ │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘ │
│                           Traefik Reverse Proxy                     │
│  agent-a.aeroswarm.dev → :3001  │  agent-b.aeroswarm.dev → :3002   │
└────────────────────────────────────────────────────────────────────┘
```

---

## 4. Recommended Technology Stack (from SRS)

| Layer | Technology | Why |
|-------|-----------|-----|
| Frontend | Next.js 14+, React, Tailwind CSS | SSR, WebSocket, fast DX |
| Backend API | Python 3.12 + FastAPI | Async, Docker SDK, easy LLM integration |
| Agent Logic | LangGraph (or CrewAI) | Stateful multi-agent graph workflows |
| Containers | Docker + Kubernetes | Full sandbox isolation per agent |
| Reverse Proxy | Traefik v3 | Dynamic subdomain routing via Docker labels |
| Database | PostgreSQL 16 | Persistent state, task/session metadata |
| Pub/Sub | Redis 7 | Real-time log streaming to frontend via WebSockets |
| Terminal Emulation | xterm.js (frontend) + PTY (backend) | Attach to container stdio |
| Code Editor (VFS) | Monaco Editor (frontend) | VS Code-grade editor in browser |
| Git Operations | GitPython / libgit2 (pygit2) | Worktree management, diffs, merges |

---

## 5. Execution Pipeline (Step-by-Step)

```
Step 1 — INIT
  User types prompt in Next.js UI
  → POST /api/orchestrate { prompt, repo_url }

Step 2 — PLAN
  FastAPI calls Manager LLM
  → Returns: [ { id, title, scope_dir, description }, ... ]
  → Persists plan to PostgreSQL (tasks table)

Step 3 — SPAWN
  For each task:
    → Docker daemon creates container (agent-worker image)
    → Mounts shared repo volume (read-only main + RW worktree)
    → Runs: git worktree add ./worktrees/<agent_id> -b branch/<agent_id>
    → Injects: TASK_DESCRIPTION, SCOPE_DIR, API_KEY as env vars
    → Opens PTY and subscribes output to Redis channel <agent_id>:logs

Step 4 — EXECUTE
  LangGraph agent loop inside container:
    → Reads files within SCOPE_DIR
    → Writes code / runs shell commands
    → Publishes stdout to Redis

Step 5 — STREAM
  FastAPI WebSocket endpoint subscribes to Redis channels
  → Pushes log chunks to Next.js via ws://
  → xterm.js renders live terminal output per agent

Step 6 — PREVIEW
  Agent starts dev server (e.g., `next dev -p 3001`)
  → Traefik maps agent-<id>.aeroswarm.dev → container:port
  → Frontend renders live preview in iFrame panel

Step 7 — MERGE (Janitor Protocol)
  Agent marks task "done"
  → Janitor runs: lint + unit tests inside container
  → Streams results to UI
  → On pass: presents 3-way visual diff (main vs agent branch)
  → User approves → git merge (no fast-forward)
  → Auto-cleanup: docker stop + rm container, git worktree remove
```

---

## 6. Key Technical Challenges & Risks

| # | Challenge | Severity | Proposed Mitigation |
|---|-----------|----------|---------------------|
| 1 | **Git Worktree race conditions** — multiple agents writing to shared repo volume | HIGH | Each agent strictly restricted to its own worktree directory via chroot/seccomp; only Janitor touches main branch |
| 2 | **Container cold-start latency** — spawning Docker containers adds delay | MEDIUM | Pre-warm a pool of base containers; mount worktrees at runtime |
| 3 | **LLM hallucination / scope creep** — agent writes outside designated `SCOPE_DIR` | HIGH | Filesystem seccomp profile + path-allow-list enforcement; agent prompt hardcodes boundaries |
| 4 | **Merge conflicts between agent branches** | MEDIUM | Orchestrator task decomposition must minimize overlapping file scopes; visual 3-way diff is mandatory HITL gate |
| 5 | **WebSocket bottleneck** — N agents × high log volume | MEDIUM | Redis pub/sub fan-out; per-agent WebSocket channel; backpressure + log buffering |
| 6 | **Secret leakage** — API keys in container env | HIGH | Use Docker secrets or K8s Secrets; never log env vars; restrict container network egress |
| 7 | **Unbounded container cost** — agents hang/loop | MEDIUM | Max execution time TTL per container; heartbeat ping from agent; auto-kill on timeout |
| 8 | **Port collision** — dynamic port assignment | LOW | Port registry with atomic auto-increment in Redis (INCR); range: 10000–20000 |

---

## 7. Security Requirements Analysis (from SRS §5)

- **Network Isolation:** Containers run in an isolated Docker network; only outbound to public package registries and the Orchestrator API endpoint. No VPC-internal access.
- **Directory Sandboxing:** Agents are restricted to `SCOPE_DIR` via read-only mounts and write-allow-listed paths. Consider seccomp + AppArmor profiles.
- **Secret Management:** At runtime, API keys injected via Docker `--env-file` (never baked into images). On K8s: use sealed secrets / Vault.
- **HITL Gate:** No agent branch can be merged to `main` without explicit human approval in the UI. The merge endpoint requires a signed approval token.

---

## 8. Database Schema (Initial Design)

```sql
-- Core entities

CREATE TABLE sessions (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  repo_url    TEXT NOT NULL,
  prompt      TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'planning', -- planning|running|merging|done
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE tasks (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id  UUID REFERENCES sessions(id) ON DELETE CASCADE,
  title       TEXT NOT NULL,
  description TEXT,
  scope_dir   TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'pending', -- pending|running|done|failed
  branch_name TEXT,
  created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agents (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id       UUID REFERENCES tasks(id) ON DELETE CASCADE,
  container_id  TEXT,           -- Docker container ID
  worktree_path TEXT,
  port          INT,
  status        TEXT NOT NULL DEFAULT 'initializing', -- initializing|running|idle|stopped
  started_at    TIMESTAMPTZ,
  stopped_at    TIMESTAMPTZ
);

CREATE TABLE merge_requests (
  id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  task_id     UUID REFERENCES tasks(id),
  lint_passed BOOLEAN,
  tests_passed BOOLEAN,
  approved_by TEXT,
  approved_at TIMESTAMPTZ,
  merged_at   TIMESTAMPTZ,
  status      TEXT NOT NULL DEFAULT 'pending' -- pending|approved|rejected|merged
);
```

---

## 9. API Surface (Initial Design)

```
POST   /api/sessions                         — Create session, trigger orchestration
GET    /api/sessions/:id                     — Get session + tasks status
GET    /api/sessions/:id/agents              — List all agents for session
POST   /api/agents/:id/start                 — Start agent execution
DELETE /api/agents/:id                       — Stop + cleanup agent

WS     /ws/agents/:id/logs                   — Stream agent terminal output
WS     /ws/sessions/:id/status               — Full session status updates

GET    /api/agents/:id/files?path=...        — VFS: list/read files
PUT    /api/agents/:id/files?path=...        — VFS: write file

GET    /api/merge-requests/:id/diff          — Get 3-way diff
POST   /api/merge-requests/:id/approve       — Human approves merge
POST   /api/merge-requests/:id/reject        — Human rejects, agent keeps working
```

---

## 10. Delivery Phases (from SRS §6)

### Phase 1 — Core Engine & CLI (Weeks 1–4)
**Goal:** Prove backend works end-to-end.
- [ ] Backend FastAPI project setup (Poetry, Dockerfile)
- [ ] PostgreSQL + Redis Docker Compose setup
- [ ] Manager LLM integration (task decomposition)
- [ ] Docker SDK: spawn/stop agent containers
- [ ] `git worktree` creation/deletion (GitPython)
- [ ] LangGraph worker agent scaffolding (tool: read_file, write_file, run_command)
- [ ] Redis pub/sub log streaming
- [ ] CLI script: input prompt → two parallel agents → verify no file corruption

### Phase 2 — Web Interface & Real-Time Sync (Weeks 5–8)
**Goal:** Full browser-based experience.
- [ ] Next.js project setup (App Router, Tailwind)
- [ ] Grid Dashboard with Kanban-style agent cards
- [ ] xterm.js terminal panels wired to WebSocket
- [ ] Monaco Editor VFS integration
- [ ] Session creation flow (UI → API)

### Phase 3 — Proxy Previews & Merge Resolution (Weeks 9–12)
**Goal:** Complete "Cloud IDE" experience.
- [ ] Traefik / Nginx dynamic subdomain routing
- [ ] Live Preview iFrame panel (side-by-side comparison)
- [ ] Visual 3-way Git merge UI
- [ ] CI Janitor loop (lint + test runner)
- [ ] Kubernetes Helm charts + Terraform deployment scripts

---

## 11. Monorepo Structure

```
AeroSwarm/
├── frontend/               # Next.js 14 App (FR3, FR4 UI)
│   ├── src/
│   │   ├── app/            # App Router pages
│   │   ├── components/     # Grid, Terminal, Editor, PreviewPane, MergeUI
│   │   └── lib/            # WebSocket client, API hooks
│   └── package.json
│
├── backend/                # FastAPI Python API
│   ├── app/
│   │   ├── api/            # Route handlers (sessions, agents, merge)
│   │   ├── services/       # Orchestrator, DockerManager, GitManager, RedisStreamer
│   │   ├── models/         # SQLAlchemy ORM models
│   │   └── main.py
│   ├── pyproject.toml
│   └── Dockerfile
│
├── agent-engine/           # LangGraph worker agent (runs inside container)
│   ├── agent/
│   │   ├── graph.py        # LangGraph state machine
│   │   ├── tools.py        # read_file, write_file, run_shell, list_dir
│   │   └── prompts.py
│   ├── pyproject.toml
│   └── Dockerfile
│
├── infra/
│   ├── docker/
│   │   └── docker-compose.yml   # Local dev: API + DB + Redis + Traefik
│   ├── k8s/                     # Kubernetes manifests
│   │   ├── backend-deployment.yaml
│   │   ├── frontend-deployment.yaml
│   │   └── traefik-ingress.yaml
│   └── traefik/
│       └── traefik.yml
│
└── docs/
    ├── INITIAL_INVESTIGATION.md  ← this file
    ├── ARCHITECTURE.md
    └── CONTRIBUTING.md
```

---

## 12. Next Immediate Steps (Phase 1 Kickoff)

1. **Initialize Git repository** with the monorepo structure above.
2. **Backend:** Bootstrap FastAPI with Poetry, define SQLAlchemy models, Alembic migrations.
3. **Infrastructure:** Create `docker-compose.yml` for local dev (FastAPI + PostgreSQL + Redis + Traefik).
4. **Agent Engine:** Scaffold LangGraph agent with three tools: `read_file`, `write_file`, `run_shell`.
5. **Manager LLM:** Implement task-decomposition prompt + structured JSON output parsing.
6. **Docker Manager service:** Wrap `docker` Python SDK to spawn/stop agent containers.
7. **Git Manager service:** Wrap `gitpython` for `worktree add`, `worktree remove`, branch creation.
8. **Smoke test:** Two agents writing to separate worktrees simultaneously — verify no corruption.
