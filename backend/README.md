# AeroSwarm Backend

FastAPI backend for AeroSwarm.

## Local Checks

Install dependencies with Poetry, then run:

```bash
poetry run ruff check app tests alembic
poetry run python -m pytest tests -q
poetry run alembic upgrade head
```
