# GitHub SSH Deploy

This workflow deploys AeroSwarm to a machine you control over SSH.

## Required GitHub Secrets

- `DEPLOY_HOST`: server hostname or IP
- `DEPLOY_USER`: SSH username
- `DEPLOY_PORT`: optional SSH port, defaults to `22`
- `DEPLOY_PATH`: absolute path on the server, for example `/opt/aeroswarm`
- `DEPLOY_SSH_PRIVATE_KEY`: private key matching the public key installed on the server

Install the matching public key into `~/.ssh/authorized_keys` for `DEPLOY_USER` on the target machine.

## Files Required On The Server

The workflow intentionally does **not** overwrite these secret-bearing files:

- `${DEPLOY_PATH}/backend/.env`
- `${DEPLOY_PATH}/infra/docker/.env`
- `${DEPLOY_PATH}/frontend/.env.local` (optional for local-only frontend use)

Use these templates:

- [backend/.env.example](../backend/.env.example)
- [infra/docker/.env.staging.example](../infra/docker/.env.staging.example)
- [frontend/.env.example](../frontend/.env.example)

## What The Workflow Does

1. Runs backend tests and migration validation.
2. Runs frontend lint and native `next build`.
3. Syncs the repo to the target machine via `rsync`.
4. Builds the agent image on the server.
5. Runs `docker compose -f infra/docker/docker-compose.staging.yml up --build -d`.

## Triggering Deploy

- Automatic on push to `main`
- Manual from the GitHub Actions UI via `workflow_dispatch`
