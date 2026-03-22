"""Tests for Docker manager host discovery."""

from pathlib import Path

from app.services import docker_manager


def test_docker_host_candidates_prefers_explicit_env(monkeypatch) -> None:
    monkeypatch.setenv("DOCKER_HOST", "unix:///custom/docker.sock")

    assert docker_manager._docker_host_candidates() == ["unix:///custom/docker.sock"]


def test_docker_host_candidates_uses_docker_desktop_socket_when_present(
    monkeypatch,
    tmp_path: Path,
) -> None:
    desktop_socket = tmp_path / "docker.sock"
    desktop_socket.touch()
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(
        docker_manager,
        "_docker_desktop_socket_path",
        lambda: desktop_socket,
    )

    assert docker_manager._docker_host_candidates() == [
        f"unix://{desktop_socket}",
        "unix:///var/run/docker.sock",
    ]


def test_docker_host_candidates_falls_back_to_var_run_socket(monkeypatch) -> None:
    missing_socket = Path("/tmp/non-existent-aeroswarm-docker.sock")
    monkeypatch.delenv("DOCKER_HOST", raising=False)
    monkeypatch.setattr(
        docker_manager,
        "_docker_desktop_socket_path",
        lambda: missing_socket,
    )

    assert docker_manager._docker_host_candidates() == ["unix:///var/run/docker.sock"]
