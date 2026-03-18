#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(pwd)"

if [[ ! -f "$ROOT_DIR/backend/.env" ]]; then
  echo "Missing backend/.env on deploy target"
  exit 1
fi

if [[ ! -f "$ROOT_DIR/infra/docker/.env" ]]; then
  echo "Missing infra/docker/.env on deploy target"
  exit 1
fi

source "$ROOT_DIR/infra/docker/.env"

AGENT_IMAGE="${DOCKER_AGENT_IMAGE:-aeroswarm-agent:staging}"

docker build -t "$AGENT_IMAGE" "$ROOT_DIR/agent-engine"

cd "$ROOT_DIR/infra/docker"
docker compose -f docker-compose.staging.yml up --build -d
docker compose -f docker-compose.staging.yml ps
