"""
Janitor service for merge preflight checks.

The janitor detects supported lint/test commands from the repo contents,
runs them inside the agent worktree, and returns a structured report that
the merge gate can enforce.
"""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from pathlib import Path

import tomllib

from app.core.config import settings
from app.services.docker_manager import DockerManagerService


@dataclass(slots=True)
class CheckSpec:
    category: str
    label: str
    command: str | None
    summary: str


@dataclass(slots=True)
class CheckResult:
    category: str
    label: str
    status: str
    command: str | None
    summary: str
    output: str | None


@dataclass(slots=True)
class PreflightReport:
    lint_passed: bool
    tests_passed: bool
    checks: list[CheckResult]

    @property
    def ready_to_merge(self) -> bool:
        return self.lint_passed and self.tests_passed


class JanitorService:
    def __init__(self) -> None:
        self._docker_mgr = DockerManagerService()

    async def run_preflight(self, worktree_path: str, container_id: str) -> PreflightReport:
        root = Path(worktree_path)
        specs = self._detect_checks(root)
        checks: list[CheckResult] = []

        for command in self._detect_install_steps(root):
            install_result = await self._run_command(container_id, command, "Dependency install")
            if install_result.status == "failed":
                return PreflightReport(
                    lint_passed=False,
                    tests_passed=False,
                    checks=[install_result],
                )
            checks.append(install_result)

        for spec in specs:
            if spec.command is None:
                checks.append(
                    CheckResult(
                        category=spec.category,
                        label=spec.label,
                        status="skipped",
                        command=None,
                        summary=spec.summary,
                        output=None,
                    )
                )
                continue

            checks.append(await self._run_check(spec, container_id))

        lint_passed = all(
            check.status != "failed" for check in checks if check.category == "lint"
        )
        tests_passed = all(
            check.status != "failed" for check in checks if check.category == "tests"
        )

        return PreflightReport(
            lint_passed=lint_passed,
            tests_passed=tests_passed,
            checks=checks,
        )

    def _detect_checks(self, root: Path) -> list[CheckSpec]:
        checks: list[CheckSpec] = []
        checks.extend(self._detect_node_checks(root))
        checks.extend(self._detect_python_checks(root))

        if not any(check.category == "lint" for check in checks):
            checks.append(
                CheckSpec(
                    category="lint",
                    label="Lint",
                    command=None,
                    summary="No supported lint command detected.",
                )
            )

        if not any(check.category == "tests" for check in checks):
            checks.append(
                CheckSpec(
                    category="tests",
                    label="Tests",
                    command=None,
                    summary="No supported test command detected.",
                )
            )

        return checks

    def _detect_install_steps(self, root: Path) -> list[str]:
        commands: list[str] = []
        package_json = root / "package.json"
        pyproject = root / "pyproject.toml"

        if package_json.exists():
            manager = self._detect_node_package_manager(root)
            install_command = {
                "npm": "npm install",
                "pnpm": "pnpm install",
                "yarn": "yarn install",
            }[manager]
            commands.append(install_command)

        if pyproject.exists():
            data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
            if "poetry" in data.get("tool", {}):
                commands.append("poetry install --no-interaction")

        return commands

    def _detect_node_checks(self, root: Path) -> list[CheckSpec]:
        package_json = root / "package.json"
        if not package_json.exists():
            return []

        data = json.loads(package_json.read_text(encoding="utf-8"))
        scripts = data.get("scripts", {})
        manager = self._detect_node_package_manager(root)
        runner = {
            "npm": "npm run",
            "pnpm": "pnpm",
            "yarn": "yarn",
        }[manager]

        checks: list[CheckSpec] = []

        if "lint" in scripts:
            checks.append(
                CheckSpec(
                    category="lint",
                    label="Node lint",
                    command=f"{runner} lint",
                    summary="Run the frontend/backend JavaScript lint script.",
                )
            )

        if "test" in scripts:
            checks.append(
                CheckSpec(
                    category="tests",
                    label="Node tests",
                    command=f"{runner} test",
                    summary="Run the JavaScript test suite from package.json.",
                )
            )

        return checks

    def _detect_python_checks(self, root: Path) -> list[CheckSpec]:
        pyproject = root / "pyproject.toml"
        if not pyproject.exists():
            return []

        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        tool_config = data.get("tool", {})
        checks: list[CheckSpec] = []

        if "ruff" in tool_config and "poetry" in tool_config:
            checks.append(
                CheckSpec(
                    category="lint",
                    label="Python lint",
                    command="poetry run ruff check .",
                    summary="Run Ruff against the Python project.",
                )
            )

        if "poetry" in tool_config and self._has_python_tests(root):
            checks.append(
                CheckSpec(
                    category="tests",
                    label="Python tests",
                    command="poetry run pytest",
                    summary="Run the Python test suite.",
                )
            )

        return checks

    def _detect_node_package_manager(self, root: Path) -> str:
        if (root / "pnpm-lock.yaml").exists():
            return "pnpm"
        if (root / "yarn.lock").exists():
            return "yarn"
        return "npm"

    def _has_python_tests(self, root: Path) -> bool:
        if (root / "tests").exists():
            return True
        return any(root.rglob("test_*.py"))

    async def _run_check(self, spec: CheckSpec, container_id: str) -> CheckResult:
        assert spec.command is not None

        result = await self._run_command(container_id, spec.command, spec.label)
        result.category = spec.category
        result.summary = spec.summary if result.status == "passed" else f"{spec.label} failed."
        return result

    async def _run_command(self, container_id: str, command: str, label: str) -> CheckResult:
        try:
            exit_code, output = await asyncio.wait_for(
                asyncio.to_thread(
                    self._docker_mgr.exec_command,
                    container_id,
                    ["/bin/sh", "-lc", command],
                    "/workspace",
                ),
                timeout=settings.JANITOR_COMMAND_TIMEOUT_SECONDS,
            )
        except asyncio.TimeoutError:
            return CheckResult(
                category="setup",
                label=label,
                status="failed",
                command=command,
                summary=f"{label} timed out after {settings.JANITOR_COMMAND_TIMEOUT_SECONDS}s.",
                output=None,
            )
        except Exception as exc:
            return CheckResult(
                category="setup",
                label=label,
                status="failed",
                command=command,
                summary=f"{label} failed to execute.",
                output=str(exc),
            )

        return CheckResult(
            category="setup",
            label=label,
            status="passed" if exit_code == 0 else "failed",
            command=command,
            summary=f"{label} completed.",
            output=output[:6000] or None,
        )
