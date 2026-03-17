# Copilot Instructions For AeroSwarm

## Requirements Source
Use `AeroSwarm PRD.md` as the primary product requirements document.
Use `docs/INITIAL_INVESTIGATION.md` for architecture details and implementation planning.

## Project Context
- Monorepo with `frontend/`, `backend/`, `agent-engine/`, `infra/`.
- Goal: multi-agent parallel cloud IDE with isolated Git worktrees and Docker containers.

## Engineering Priorities
1. Correctness and safety over speed.
2. Isolation boundaries for agent workspaces.
3. Human-in-the-loop merge approval.
4. Clear observability and failure handling.

## Coding Guidelines
- Keep edits small and targeted.
- Do not reformat unrelated files.
- Preserve public API contracts unless requirements change.
- Add concise comments only where logic is non-obvious.
- Add or update tests when behavior changes.

## Backend Guidelines
- FastAPI routes live in `backend/app/api/routes/`.
- Business logic lives in `backend/app/services/`.
- DB models live in `backend/app/models/`.
- Prefer async I/O patterns and explicit error handling.

## Frontend Guidelines
- Keep UI modular under `frontend/src/components/`.
- Use typed interfaces from `frontend/src/lib/types.ts`.
- Keep data access in `frontend/src/lib/api.ts` and hooks.

## Security Guardrails
- Never expose secrets in logs or committed files.
- Restrict filesystem operations to scoped directories.
- Keep runtime permissions minimal.
