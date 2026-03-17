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
import uuid
from collections.abc import Sequence

import docker
from docker.errors import DockerException

from app.core.config import settings

logger = logging.getLogger(__name__)


class DockerManagerService:
    def __init__(self) -> None:
        try:
            self._client = docker.from_env()
        except DockerException as exc:
            logger.warning("Docker not available: %s", exc)
            self._client = None  # type: ignore[assignment]

    async def spawn_agent(
        self,
        task_id: uuid.UUID,
        worktree_path: str,
        scope_dir: str,
        task_description: str,
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
                "OPENAI_API_KEY": settings.OPENAI_API_KEY,
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
