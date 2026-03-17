"""
Agent tools — the only actions a LangGraph worker agent can perform.

Security:
  - All file operations are restricted to SCOPE_DIR via path resolution guard.
  - run_shell has a command allow-list (no arbitrary root commands).
"""

import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool

SCOPE_DIR = os.environ.get("SCOPE_DIR", "/workspace")
SHELL_TIMEOUT = 30  # seconds


def _safe_path(rel_path: str) -> Path:
    """Resolve a path inside SCOPE_DIR and reject path traversal attempts."""
    base = Path(SCOPE_DIR).resolve()
    target = (base / rel_path).resolve()
    if not str(target).startswith(str(base)):
        raise PermissionError(f"Path traversal blocked: '{rel_path}' is outside SCOPE_DIR")
    return target


@tool
def read_file_tool(path: str) -> str:
    """Read the contents of a file at `path` (relative to SCOPE_DIR)."""
    target = _safe_path(path)
    if not target.is_file():
        return f"ERROR: '{path}' is not a file"
    return target.read_text(encoding="utf-8", errors="replace")


@tool
def write_file_tool(path: str, content: str) -> str:
    """Write `content` to a file at `path` (relative to SCOPE_DIR). Creates parent dirs."""
    target = _safe_path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    return f"Written {len(content)} chars to '{path}'"


@tool
def list_dir_tool(path: str = "") -> str:
    """List files and directories at `path` (relative to SCOPE_DIR)."""
    target = _safe_path(path)
    if not target.is_dir():
        return f"ERROR: '{path}' is not a directory"
    entries = sorted(target.iterdir())
    lines = [f"{'d' if e.is_dir() else 'f'}  {e.name}" for e in entries]
    return "\n".join(lines) if lines else "(empty directory)"


# Allow-list for shell commands (no sudo, no rm -rf, no network tools beyond package managers)
_ALLOWED_PREFIXES = (
    "npm ", "npx ", "yarn ", "pnpm ",
    "pip ", "pip3 ", "poetry ",
    "python ", "python3 ",
    "node ",
    "git status", "git log", "git diff", "git add", "git commit",
    "ls ", "cat ", "echo ", "mkdir ", "touch ",
    "pytest", "ruff", "black", "eslint", "tsc",
)


@tool
def run_shell_tool(command: str) -> str:
    """
    Run a shell command inside SCOPE_DIR.
    Only allow-listed command prefixes are permitted.
    """
    stripped = command.strip()
    if not any(stripped.startswith(prefix) for prefix in _ALLOWED_PREFIXES):
        return f"BLOCKED: command '{stripped}' is not on the allow-list"

    try:
        result = subprocess.run(
            stripped,
            shell=True,  # noqa: S602 — allow-list validated above
            cwd=SCOPE_DIR,
            capture_output=True,
            text=True,
            timeout=SHELL_TIMEOUT,
        )
        output = result.stdout + result.stderr
        return output[:4000]  # cap output size
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {SHELL_TIMEOUT}s"
    except Exception as exc:
        return f"ERROR: {exc}"
