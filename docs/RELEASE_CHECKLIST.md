# Release Checklist

Use this before promoting AeroSwarm to a public environment.

## CI Gate

- GitHub Actions `CI` workflow passes on the target commit.
- Backend checks pass:
  - `poetry run ruff check app tests`
  - `poetry run python -m pytest tests -q`
  - `poetry run alembic upgrade head`
- Frontend checks pass:
  - `npm run lint`
  - `npm run build`

## Runtime Gate

- Backend API and worker are both deployed from the same revision.
- Database migrations are applied before serving traffic.
- `/health` returns `200`.
- `/ready` returns `200` after startup.
- Background worker can claim and execute jobs from `background_jobs`.

## Product Flow Gate

- Register/login/logout works in the deployed environment.
- Creating a session returns `queued`, then transitions to `running`.
- Agents appear in the dashboard after worker processing.
- Merge preflight returns queued/running states and eventually resolves.
- GitHub OAuth/App and PR sync work against a disposable repo.

## Operational Gate

- `COOKIE_SECURE=true` in non-local environments.
- `EXPOSE_DEV_TOKENS=false` in non-local environments.
- `SECRET_KEY`, GitHub secrets, and repo credentials are set from secret storage.
- Postgres backups and log retention are configured.
- Alerts exist for backend crash loops and worker crash loops.
