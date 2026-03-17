"""
Repository manager for session-scoped source checkouts.

Each session gets its own cloned source tree under:
  <REPO_BASE_PATH>/<session_id>/source
"""

import shutil
import uuid
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import git

from app.core.config import settings


class RepoManagerService:
    def get_session_root(self, session_id: uuid.UUID) -> Path:
        return Path(settings.REPO_BASE_PATH) / str(session_id)

    def get_repo_path(self, session_id: uuid.UUID) -> Path:
        return self.get_session_root(session_id) / "source"

    def clone_repo(
        self,
        session_id: uuid.UUID,
        repo_url: str,
        repo_access_token: str | None = None,
        repo_username: str | None = None,
    ) -> str:
        repo_path = self.get_repo_path(session_id)
        repo_path.parent.mkdir(parents=True, exist_ok=True)

        if repo_path.exists():
            shutil.rmtree(repo_path)

        clone_url = self._build_clone_url(repo_url, repo_access_token, repo_username)
        git.Repo.clone_from(clone_url, repo_path)
        return str(repo_path)

    def cleanup_session_repo(self, session_id: uuid.UUID) -> None:
        session_root = self.get_session_root(session_id)
        if session_root.exists():
            shutil.rmtree(session_root, ignore_errors=True)

    def _build_clone_url(
        self,
        repo_url: str,
        repo_access_token: str | None,
        repo_username: str | None,
    ) -> str:
        if not repo_access_token:
            return repo_url

        parsed = urlsplit(repo_url)
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("Token-based cloning currently requires an http(s) repository URL")

        username = quote(repo_username or "x-access-token", safe="")
        password = quote(repo_access_token, safe="")
        netloc = f"{username}:{password}@{parsed.netloc}"
        return urlunsplit((parsed.scheme, netloc, parsed.path, parsed.query, parsed.fragment))
