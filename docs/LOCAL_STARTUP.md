# Local Startup Guide

This is the shortest full local development path for AeroSwarm.

## What Runs Locally

- `frontend`: Next.js app on `http://localhost:3000`
- `backend`: FastAPI API on `http://localhost:8000`
- `worker`: background job processor
- `postgres`: primary database on `localhost:5432`
- `redis`: cache / pub-sub on `localhost:6379`
- `traefik`: local reverse proxy on `http://localhost:8081`
- `traefik dashboard`: `http://localhost:8080`
- `aeroswarm-agent:latest`: worker image launched dynamically for task execution

## Prerequisites

- Docker Desktop with Compose
- Python 3.12+
- Poetry
- Node.js 20+
- npm

## One-Time Setup

From the repo root:

```bash
chmod +x scripts/local_dev.sh
./scripts/local_dev.sh setup
```

What `setup` does:

1. creates `backend/.env` from [backend/.env.example](/Users/robin-hassan/Desktop/AeroSwarm/backend/.env.example)
2. creates `frontend/.env.local` from [frontend/.env.example](/Users/robin-hassan/Desktop/AeroSwarm/frontend/.env.example)
3. installs backend dependencies with Poetry
4. installs frontend dependencies with npm
5. builds the local agent image
6. starts Postgres, Redis, backend, worker, and Traefik
7. runs `alembic upgrade head`

## Daily Startup

Start the local backend stack:

```bash
./scripts/local_dev.sh up
```

Start the frontend dev server in a separate terminal:

```bash
./scripts/local_dev.sh frontend
```

## Local URLs

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Health: `http://localhost:8000/health`
- Ready: `http://localhost:8000/ready`
- Traefik proxy: `http://localhost:8081`
- Traefik dashboard: `http://localhost:8080`

## Useful Commands

Show status:

```bash
./scripts/local_dev.sh status
```

Tail backend logs:

```bash
./scripts/local_dev.sh logs backend
```

Tail worker logs:

```bash
./scripts/local_dev.sh logs worker
```

Stop local services:

```bash
./scripts/local_dev.sh down
```

Stop and wipe local Docker volumes:

```bash
./scripts/local_dev.sh reset
```

## First Validation Pass

After startup:

1. open `http://localhost:3000`
2. register a user
3. log in
4. create a session against a disposable repo
5. confirm backend readiness at `http://localhost:8000/ready`
6. confirm agents appear after the worker picks up the bootstrap job

## Environment Files

Backend env defaults live in [backend/.env.example](/Users/robin-hassan/Desktop/AeroSwarm/backend/.env.example).

Frontend env defaults live in [frontend/.env.example](/Users/robin-hassan/Desktop/AeroSwarm/frontend/.env.example).

For local development, the generated defaults are enough to boot the stack. Add OpenAI and GitHub credentials only when you want live model or GitHub integration paths.

## Port Overrides

If `8081` or `8080` are also occupied on your machine, override them when starting the stack:

```bash
TRAEFIK_WEB_PORT=8091 TRAEFIK_DASHBOARD_PORT=8092 ./scripts/local_dev.sh up
```

## Common Problems

### `poetry: command not found`

Install Poetry first, then rerun:

```bash
./scripts/local_dev.sh setup
```

### Agent launch fails

Rebuild the agent image:

```bash
docker build -t aeroswarm-agent:latest agent-engine
```

### `bind: address already in use`

The local reverse proxy no longer uses port `80` by default. It uses `8081`.

If that still conflicts on your machine, start with custom ports:

```bash
TRAEFIK_WEB_PORT=8091 TRAEFIK_DASHBOARD_PORT=8092 ./scripts/local_dev.sh up
```

### Migrations fail

Check that Postgres is healthy:

```bash
./scripts/local_dev.sh status
./scripts/local_dev.sh logs backend
```

Then rerun:

```bash
./scripts/local_dev.sh up
```
