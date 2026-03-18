# Staging Deployment

This document describes the shortest production-like path for validating AeroSwarm before a public launch.

## Components

- `frontend`: Next.js dashboard
- `backend`: FastAPI API
- `worker`: background job processor for session bootstrap and merge preflight
- `postgres`: primary database
- `redis`: pub/sub and rate limiting
- `aeroswarm-agent` image: spawned dynamically by the backend for task execution

## Prerequisites

- Docker with Compose
- A populated `backend/.env`
- OpenAI and GitHub credentials configured where needed

## 1. Prepare Environment

Create backend env if it does not exist:

```bash
cd backend
cp .env.example .env
```

Recommended staging additions in `backend/.env`:

```env
COOKIE_SECURE=false
EXPOSE_DEV_TOKENS=false
RUN_MIGRATIONS_ON_STARTUP=true
DOCKER_AGENT_IMAGE=aeroswarm-agent:staging
FRONTEND_URL=http://localhost:3000
```

For the frontend, create:

```bash
cd frontend
cp .env.example .env.local
```

## 2. Build Agent Image

The backend launches agent containers by image name, so build that image first:

```bash
cd agent-engine
docker build -t aeroswarm-agent:staging .
```

## 3. Start Staging Stack

```bash
cd infra/docker
docker compose -f docker-compose.staging.yml up --build -d
```

Services:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

## 4. Verify Runtime

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
docker compose -f infra/docker/docker-compose.staging.yml ps
```

Confirm both `backend` and `worker` are healthy/running.

## 5. Run Product Validation

1. Register and log in through the frontend.
2. Create a session against a disposable repo.
3. Confirm the session enters `queued`, then `planning`, then `running`.
4. Confirm agents appear in the grid.
5. Let one agent reach `idle`, then trigger merge.
6. Confirm preflight queues, completes, and either blocks or merges correctly.

For GitHub live validation, follow [GITHUB_LIVE_VALIDATION.md](./GITHUB_LIVE_VALIDATION.md).

## 6. Tear Down

```bash
cd infra/docker
docker compose -f docker-compose.staging.yml down
```

To wipe data too:

```bash
docker compose -f docker-compose.staging.yml down -v
```
