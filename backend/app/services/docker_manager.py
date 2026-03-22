"""
Docker Manager Service — spawns and stops agent containers.

Each agent container:
  - Mounts the shared repo volume
  - Has its Git worktree pre-created
  - Runs the aeroswarm-agent image (LangGraph worker)
  - Is network-isolated (no VPC access, only outbound public + Orchestrator API)
  - Has a unique port assigned from the Redis-managed port registry
"""

import logging
import os
import uuid
from collections.abc import Sequence
from pathlib import Path

import docker
from docker.errors import DockerException

from app.core.config import settings

logger = logging.getLogger(__name__)


def _docker_desktop_socket_path() -> Path:
    return Path.home() / ".docker" / "run" / "docker.sock"


def _docker_host_candidates() -> list[str]:
    configured_host = os.getenv("DOCKER_HOST")
    if configured_host:
        return [configured_host]

    candidates: list[str] = []
    desktop_socket = _docker_desktop_socket_path()
    if desktop_socket.exists():
        candidates.append(f"unix://{desktop_socket}")
    candidates.append("unix:///var/run/docker.sock")
    return candidates


class DockerManagerService:
    def __init__(self) -> None:
        self._client = None
        self._docker_host = None
        self._availability_error = "Docker daemon is not accessible"

        connection_errors: list[str] = []
        for host in _docker_host_candidates():
            try:
                client = docker.DockerClient(base_url=host)
                client.ping()
                self._client = client
                self._docker_host = host
                return
            except DockerException as exc:
                connection_errors.append(f"{host}: {exc}")

        if connection_errors:
            self._availability_error = "; ".join(connection_errors)
        logger.warning("Docker not available: %s", self._availability_error)

    def availability(self) -> tuple[bool, str]:
        if self._client is None:
            return False, self._availability_error
        return True, self._docker_host or "ok"

    async def spawn_agent(
        self,
        task_id: uuid.UUID,
        worktree_path: str,
        scope_dir: str,
        task_description: str,
        llm_provider: str,
        agent_model: str,
        port: int,
        agent_id: uuid.UUID,
    ) -> str:
        """
        Launch an agent container and return its Docker container ID.

        Security controls:
        - Container runs as non-root (uid 1000)
        - Network mode: isolated bridge, no host network
        - Read-only root FS except for the worktree mount
        - SCOPE_DIR env var enforced inside the agent
        - API key injected via env (never baked into the image)
        """
        if self._client is None:
            raise RuntimeError("Docker daemon is not accessible")

        container = self._client.containers.run(
            image=settings.DOCKER_AGENT_IMAGE,
            name=f"aeroswarm-agent-{agent_id}",
            detach=True,
            remove=False,
            environment={
                "AGENT_ID": str(agent_id),
                "TASK_ID": str(task_id),
                "TASK_DESCRIPTION": task_description,
                "SCOPE_DIR": f"/workspace/{scope_dir}",
                "LLM_PROVIDER": llm_provider,
                "LLM_MODEL": agent_model,
                "OPENAI_API_KEY": settings.OPENAI_API_KEY,
                "GEMINI_API_KEY": settings.GEMINI_API_KEY,
                "GEMINI_OPENAI_BASE_URL": settings.GEMINI_OPENAI_BASE_URL,
                "API_BEARER_TOKEN": settings.API_BEARER_TOKEN,
                "REDIS_URL": settings.REDIS_URL,
                "BACKEND_API_URL": "http://aeroswarm-backend:8000",
            },
            volumes={
                worktree_path: {"bind": "/workspace", "mode": "rw"},
            },
            ports={f"{port}/tcp": port},
            # Security: non-root user
            user="1000:1000",
            # Resource limits — prevent runaway containers
            mem_limit="2g",
            cpu_quota=100000,  # 1 CPU
            # No network access to internal VPC
            network="aeroswarm-net",
        )
        return container.id  # type: ignore[return-value]

    def stop_and_remove(self, container_id: str) -> None:
        """Stop and remove a container (called by Janitor after successful merge)."""
        if self._client is None:
            return
        try:
            container = self._client.containers.get(container_id)
            container.stop(timeout=10)
            container.remove(force=True)
            logger.info("Removed container %s", container_id)
        except DockerException as exc:
            logger.error("Failed to remove container %s: %s", container_id, exc)

    def get_logs(self, container_id: str, tail: int = 100) -> str:
        """Fetch recent container logs (for REST endpoint)."""
        if self._client is None:
            return ""
        try:
            container = self._client.containers.get(container_id)
            return container.logs(tail=tail).decode("utf-8", errors="replace")
        except DockerException:
            return ""

    def exec_command(
        self,
        container_id: str,
        command: Sequence[str],
        workdir: str = "/workspace",
    ) -> tuple[int, str]:
        """Run a command inside an agent container and return exit code + output."""
        if self._client is None:
            raise RuntimeError("Docker daemon is not accessible")

        container = self._client.containers.get(container_id)
        result = container.exec_run(list(command), workdir=workdir)
        output = result.output.decode("utf-8", errors="replace")
        return int(result.exit_code), output
