# GitHub Live Validation

This runbook validates the GitHub OAuth, GitHub App installation, PR sync, webhook reconciliation, and live session flow against a disposable GitHub repository.

## Prerequisites

- A disposable GitHub repository you can modify.
- A GitHub OAuth app configured with:
  - callback URL `http://localhost:8000/api/vcs/github/oauth/callback`
- A GitHub App configured with:
  - permissions for repository contents, pull requests, and issues/comments
  - setup URL `http://localhost:8000/api/vcs/github-app/install/callback`
  - webhook URL `http://localhost:8000/api/vcs/github/webhooks`
- Backend env configured from [`backend/.env.example`](/Users/robin-hassan/Desktop/AeroSwarm/backend/.env.example)
- Local backend, frontend, Redis, Postgres, and agent image running

## Bring Up The Stack

1. Start infra:

```bash
cd infra/docker
docker compose up -d
```

2. Apply migrations:

```bash
cd backend
poetry install
poetry run alembic upgrade head
```

3. Start backend:

```bash
cd backend
poetry run uvicorn app.main:app --reload
```

4. Start frontend:

```bash
cd frontend
npm install
npm run dev
```

5. Build the agent image if needed:

```bash
cd agent-engine
docker build -t aeroswarm-agent:latest .
```

## Browser Validation

1. Open `http://localhost:3000`.
2. Register or log in.
3. Click `Connect With GitHub OAuth`.
4. Confirm the callback returns to the dashboard and a saved connection appears.
5. Click `Install GitHub App`.
6. Install the app on the disposable repo owner.
7. Confirm the callback returns and a `github_app` saved connection appears.
8. Create a session against the disposable repo using the GitHub App connection.
9. Wait for an agent to become `idle`.
10. Click `Merge`.
11. Confirm:
   - a GitHub PR is created
   - preflight comment appears on the PR
   - merge approval completes

## Smoke Script Validation

If you want a non-browser session smoke run, export:

```bash
export AEROSWARM_BASE_URL=http://localhost:8000
export AEROSWARM_EMAIL=you@example.com
export AEROSWARM_PASSWORD=your-password
export AEROSWARM_REPO_URL=https://github.com/<owner>/<repo>
export AEROSWARM_PROMPT="Make a tiny repo change and prepare a PR"
export AEROSWARM_PROVIDER_CONNECTION_ID=<saved-provider-connection-id>
```

Then run:

```bash
cd backend
python3 scripts/github_live_smoke.py
```

You can also omit `AEROSWARM_PROVIDER_CONNECTION_ID` and provide `AEROSWARM_GITHUB_PAT` for PAT-based fallback.

## Pytest Integration Entry Point

The repo also includes a live integration test that wraps the same flow and skips automatically if the live env is incomplete:

```bash
cd backend
python3 -m pytest tests/test_github_live_integration.py -m integration -q
```

This is the preferred command for CI or staging validation because it produces normal pytest pass/skip/fail output.

## Webhook Validation

1. Merge or close the PR directly in GitHub.
2. Confirm the webhook reaches `/api/vcs/github/webhooks`.
3. Confirm local state updates:
   - merged PR sets merge request to `merged`
   - closed-unmerged PR sets merge request to `rejected`
   - merged PR stops the agent container and removes the worktree
4. Review the session audit feed for:
   - `merge.github_pr.synced`
   - `merge.github_webhook.synced`

## Expected Failures To Investigate

- OAuth callback error:
  - verify `GITHUB_OAUTH_CLIENT_ID`, `GITHUB_OAUTH_CLIENT_SECRET`, and callback URL
- GitHub App install callback error:
  - verify `GITHUB_APP_ID`, `GITHUB_APP_SLUG`, private key, and setup URL
- PR creation fails:
  - verify repo permissions and the selected saved connection mode
- Webhook 401:
  - verify `GITHUB_WEBHOOK_SECRET`
- Session clone fails:
  - verify the saved provider connection can access the repo and the repo URL matches the installed owner/repo
