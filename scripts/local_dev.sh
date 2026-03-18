#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
FRONTEND_DIR="$ROOT_DIR/frontend"
AGENT_DIR="$ROOT_DIR/agent-engine"
COMPOSE_DIR="$ROOT_DIR/infra/docker"
COMPOSE_FILE="$COMPOSE_DIR/docker-compose.yml"
AGENT_IMAGE="${DOCKER_AGENT_IMAGE:-aeroswarm-agent:latest}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    exit 1
  fi
}

compose() {
  docker compose -f "$COMPOSE_FILE" "$@"
}

ensure_env_files() {
  if [[ ! -f "$BACKEND_DIR/.env" ]]; then
    cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
    echo "Created backend/.env from example"
  fi

  if [[ ! -f "$FRONTEND_DIR/.env.local" ]]; then
    cp "$FRONTEND_DIR/.env.example" "$FRONTEND_DIR/.env.local"
    echo "Created frontend/.env.local from example"
  fi
}

install_dependencies() {
  require_cmd poetry
  require_cmd npm

  (
    cd "$BACKEND_DIR"
    poetry install --with dev
  )

  (
    cd "$FRONTEND_DIR"
    npm install
  )
}

build_agent_image() {
  require_cmd docker
  docker build -t "$AGENT_IMAGE" "$AGENT_DIR"
}

start_infra() {
  require_cmd docker
  compose up -d postgres redis backend worker traefik
}

run_migrations() {
  compose exec -T backend alembic upgrade head
}

show_status() {
  compose ps
  echo
  echo "Frontend: http://localhost:3000"
  echo "Backend:  http://localhost:8000"
  echo "Health:   http://localhost:8000/health"
  echo "Ready:    http://localhost:8000/ready"
  echo "Traefik:  http://localhost:8080"
}

start_frontend_dev() {
  require_cmd npm
  (
    cd "$FRONTEND_DIR"
    npm run dev
  )
}

setup() {
  ensure_env_files
  install_dependencies
  build_agent_image
  start_infra
  run_migrations
  show_status
}

up() {
  ensure_env_files
  build_agent_image
  start_infra
  run_migrations
  show_status
}

down() {
  compose down
}

reset() {
  compose down -v
}

logs() {
  compose logs -f "${2:-backend}" "${@:3}"
}

usage() {
  cat <<'EOF'
Usage: scripts/local_dev.sh <command>

Commands:
  setup      Copy env files, install local deps, build agent image, start infra, run migrations
  up         Start docker services, build the agent image, run migrations
  frontend   Start the Next.js frontend dev server on localhost:3000
  down       Stop local docker services
  reset      Stop services and remove docker volumes
  status     Show local docker service status
  logs       Tail docker compose logs (default service: backend)

Examples:
  ./scripts/local_dev.sh setup
  ./scripts/local_dev.sh frontend
  ./scripts/local_dev.sh logs worker
EOF
}

main() {
  local command="${1:-}"

  case "$command" in
    setup)
      setup
      ;;
    up)
      up
      ;;
    frontend)
      start_frontend_dev
      ;;
    down)
      down
      ;;
    reset)
      reset
      ;;
    status)
      show_status
      ;;
    logs)
      logs "$@"
      ;;
    *)
      usage
      exit 1
      ;;
  esac
}

main "$@"
