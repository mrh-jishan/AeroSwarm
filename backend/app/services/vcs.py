"""Helpers for provider-backed repository workflows."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(slots=True)
class RepoIdentity:
    provider: str | None
    owner: str | None
    name: str | None


class VcsService:
    _GITHUB_HTTPS = re.compile(r"^https?://github\.com/(?P<owner>[^/]+)/(?P<name>[^/.]+?)(?:\.git)?/?$")
    _GITHUB_SSH = re.compile(r"^git@github\.com:(?P<owner>[^/]+)/(?P<name>[^/.]+?)(?:\.git)?$")

    def parse_repo_identity(self, repo_url: str) -> RepoIdentity:
        for pattern in (self._GITHUB_HTTPS, self._GITHUB_SSH):
            match = pattern.match(repo_url)
            if match:
                return RepoIdentity(
                    provider="github",
                    owner=match.group("owner"),
                    name=match.group("name"),
                )
        return RepoIdentity(provider=None, owner=None, name=None)
