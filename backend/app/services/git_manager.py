"""
Git Manager Service — manages Git worktrees for agent isolation.

Each agent gets:
  - A dedicated branch: agent/<agent_id>
  - A dedicated worktree directory: <REPO_BASE_PATH>/<session_id>/worktrees/<agent_id>
"""

import logging
import os
import shutil
import uuid
from pathlib import Path

import git

from app.core.config import settings

logger = logging.getLogger(__name__)


class GitManagerService:
    def create_worktree(
        self,
        session_id: uuid.UUID,
        agent_id: uuid.UUID,
        repo_path: str,
    ) -> str:
        """
        Create a new Git worktree + branch for an agent.
        Returns the absolute path to the worktree directory.
        """
        repo = git.Repo(repo_path)
        branch_name = f"agent/{agent_id}"
        worktree_path = str(
            Path(settings.REPO_BASE_PATH) / str(session_id) / "worktrees" / str(agent_id)
        )

        os.makedirs(worktree_path, exist_ok=True)

        # Create worktree on a new branch based on HEAD
        repo.git.worktree("add", "-b", branch_name, worktree_path, "HEAD")
        logger.info("Created worktree at %s (branch: %s)", worktree_path, branch_name)
        return worktree_path

    def remove_worktree(self, repo_path: str, worktree_path: str) -> None:
        """
        Remove a Git worktree and delete its directory.
        Called by Janitor after a successful merge.
        """
        repo = git.Repo(repo_path)
        try:
            repo.git.worktree("remove", "--force", worktree_path)
            logger.info("Removed worktree at %s", worktree_path)
        except git.GitCommandError as exc:
            logger.error("git worktree remove failed: %s", exc)
            # Fallback: prune stale worktrees
            repo.git.worktree("prune")
            if Path(worktree_path).exists():
                shutil.rmtree(worktree_path, ignore_errors=True)

    def get_diff(self, repo_path: str, branch_name: str) -> str:
        """Return the unified diff between the agent branch and main."""
        repo = git.Repo(repo_path)
        return repo.git.diff("main", branch_name)

    def merge_branch(self, repo_path: str, branch_name: str, approved_by: str) -> None:
        """
        Merge an agent branch into main (no fast-forward, HITL-approved).
        NEVER called without explicit human approval token.
        """
        repo = git.Repo(repo_path)
        repo.git.checkout("main")
        repo.git.merge(
            "--no-ff",
            branch_name,
            "-m",
            f"feat: merge {branch_name} — approved by {approved_by}",
        )
        logger.info("Merged %s into main (approved by %s)", branch_name, approved_by)
