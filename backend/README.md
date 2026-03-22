# AeroSwarm Backend

FastAPI backend for AeroSwarm.

## Recommended Local Startup

The shortest path for running the full app locally is from the repo root with the shared startup script:

```bash
./scripts/local_dev.sh setup
./scripts/local_dev.sh frontend
```

That script:

1. copies `backend/.env` and `frontend/.env.local` from examples
2. installs backend and frontend dependencies
3. builds the `aeroswarm-agent:latest` image
4. starts Postgres, Redis, backend, worker, and Traefik
5. runs `alembic upgrade head`

Full guide: [docs/LOCAL_STARTUP.md](/Users/robin-hassan/Desktop/AeroSwarm/docs/LOCAL_STARTUP.md)

## Backend-Only Startup

If you only want to work on the backend, use this path.

### 1. Create env file

```bash
cd backend
cp .env.example .env
```

Important backend envs:

- `DATABASE_URL`
- `REDIS_URL`
- `SECRET_KEY`
- `CORS_ORIGIN_REGEX`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`
- `GEMINI_DEFAULT_MODEL`
- `OPENAI_DEFAULT_MODEL`

Defaults live in [backend/.env.example](/Users/robin-hassan/Desktop/AeroSwarm/backend/.env.example).

### 2. Install dependencies

```bash
cd backend
poetry install --with dev
```

### 3. Start local infra

From the repo root:

```bash
docker compose -f infra/docker/docker-compose.yml up -d postgres redis
```

### 4. Run migrations

```bash
cd backend
poetry run alembic upgrade head
```

### 5. Start the API

```bash
cd backend
poetry run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 6. Optional: start the background worker

In a second terminal:

```bash
cd backend
poetry run python -m app.worker
```

## Health Checks

Once the API is up:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/ready
```

## Local Checks

Install dependencies with Poetry, then run:

```bash
poetry run ruff check app tests alembic
poetry run python -m pytest tests -q
poetry run alembic upgrade head
```
