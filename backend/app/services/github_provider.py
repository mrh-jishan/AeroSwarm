"""GitHub API client for repository and pull request workflows."""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from jose import jwt

from app.core.config import settings


@dataclass(slots=True)
class GitHubUser:
    login: str


@dataclass(slots=True)
class GitHubRepo:
    owner: str
    name: str
    default_branch: str
    html_url: str


@dataclass(slots=True)
class GitHubRepoSuggestion:
    owner: str
    name: str
    full_name: str
    default_branch: str
    html_url: str
    private: bool


@dataclass(slots=True)
class GitHubPullRequest:
    number: int
    html_url: str
    state: str


@dataclass(slots=True)
class GitHubInstallation:
    id: int
    account_login: str


class GitHubProviderService:
    BASE_URL = "https://api.github.com"
    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"
    APP_INSTALL_URL = "https://github.com/apps/{slug}/installations/new"

    def build_oauth_authorize_url(self, state: str) -> str:
        if not settings.GITHUB_OAUTH_CLIENT_ID:
            raise ValueError("GitHub OAuth is not configured")

        query = urlencode(
            {
                "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
                "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
                "scope": "repo read:user",
                "state": state,
            }
        )
        return f"{self.AUTHORIZE_URL}?{query}"

    async def exchange_code_for_access_token(self, code: str) -> str:
        if not settings.GITHUB_OAUTH_CLIENT_ID or not settings.GITHUB_OAUTH_CLIENT_SECRET:
            raise ValueError("GitHub OAuth is not configured")

        headers = {"Accept": "application/json"}
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                self.OAUTH_TOKEN_URL,
                headers=headers,
                data={
                    "client_id": settings.GITHUB_OAUTH_CLIENT_ID,
                    "client_secret": settings.GITHUB_OAUTH_CLIENT_SECRET,
                    "code": code,
                    "redirect_uri": settings.GITHUB_OAUTH_REDIRECT_URI,
                },
            )

        if response.status_code >= 400:
            raise ValueError(f"GitHub OAuth error: {response.text}")

        data = response.json()
        access_token = data.get("access_token")
        if not access_token:
            raise ValueError(
                "GitHub OAuth error: "
                f"{data.get('error_description', 'missing access token')}"
            )
        return str(access_token)

    def build_app_install_url(self, state: str) -> str:
        if not settings.GITHUB_APP_SLUG:
            raise ValueError("GitHub App is not configured")
        query = urlencode({"state": state})
        return f"{self.APP_INSTALL_URL.format(slug=settings.GITHUB_APP_SLUG)}?{query}"

    async def get_installation(self, installation_id: int) -> GitHubInstallation:
        data = await self._request_as_app("GET", f"/app/installations/{installation_id}")
        account = data.get("account") or {}
        return GitHubInstallation(
            id=int(data["id"]),
            account_login=str(account.get("login", "")),
        )

    async def create_installation_access_token(self, installation_id: int) -> str:
        data = await self._request_as_app(
            "POST",
            f"/app/installations/{installation_id}/access_tokens",
        )
        token = data.get("token")
        if not token:
            raise ValueError("GitHub App installation token response was missing a token")
        return str(token)

    def verify_webhook_signature(self, payload: bytes, signature_header: str | None) -> bool:
        secret = settings.GITHUB_WEBHOOK_SECRET
        if not secret:
            raise ValueError("GitHub webhook secret is not configured")
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        return hmac.compare_digest(expected, signature_header)

    def _create_app_jwt(self) -> str:
        if not settings.GITHUB_APP_ID or not settings.GITHUB_APP_PRIVATE_KEY:
            raise ValueError("GitHub App is not configured")

        now = datetime.now(timezone.utc)
        payload = {
            "iat": int((now - timedelta(seconds=30)).timestamp()),
            "exp": int((now + timedelta(minutes=9)).timestamp()),
            "iss": settings.GITHUB_APP_ID,
        }
        private_key = settings.GITHUB_APP_PRIVATE_KEY.replace("\\n", "\n")
        return jwt.encode(payload, private_key, algorithm="RS256")

    async def get_authenticated_user(self, access_token: str) -> GitHubUser:
        data = await self._request("GET", "/user", access_token)
        return GitHubUser(login=str(data["login"]))

    async def get_repo(self, owner: str, name: str, access_token: str) -> GitHubRepo:
        data = await self._request("GET", f"/repos/{owner}/{name}", access_token)
        return GitHubRepo(
            owner=str(data["owner"]["login"]),
            name=str(data["name"]),
            default_branch=str(data["default_branch"]),
            html_url=str(data["html_url"]),
        )

    async def list_repositories(
        self,
        *,
        access_token: str,
        auth_mode: str,
        query: str | None = None,
        limit: int = 20,
    ) -> list[GitHubRepoSuggestion]:
        if auth_mode == "github_app":
            data = await self._request(
                "GET",
                "/installation/repositories",
                access_token,
                params={"per_page": "100"},
            )
            repositories = (data if isinstance(data, dict) else {}).get("repositories", [])
        else:
            data = await self._request(
                "GET",
                "/user/repos",
                access_token,
                params={
                    "per_page": "100",
                    "sort": "updated",
                    "affiliation": "owner,collaborator,organization_member",
                },
            )
            repositories = data if isinstance(data, list) else []

        normalized_query = self._normalize_repo_query(query)
        suggestions: list[GitHubRepoSuggestion] = []
        for repo in repositories:
            owner = str((repo.get("owner") or {}).get("login", ""))
            name = str(repo.get("name", ""))
            full_name = str(repo.get("full_name") or f"{owner}/{name}")
            html_url = str(repo.get("html_url", ""))
            default_branch = str(repo.get("default_branch", ""))
            if normalized_query:
                haystack = " ".join(
                    part.lower()
                    for part in [owner, name, full_name, html_url]
                    if part
                )
                if normalized_query not in haystack:
                    continue
            suggestions.append(
                GitHubRepoSuggestion(
                    owner=owner,
                    name=name,
                    full_name=full_name,
                    default_branch=default_branch,
                    html_url=html_url,
                    private=bool(repo.get("private", False)),
                )
            )
            if len(suggestions) >= limit:
                break

        return suggestions

    def _normalize_repo_query(self, query: str | None) -> str:
        normalized = (query or "").strip().lower()
        if normalized.startswith("https://github.com/"):
            normalized = normalized.removeprefix("https://github.com/")
        elif normalized.startswith("http://github.com/"):
            normalized = normalized.removeprefix("http://github.com/")
        elif normalized.startswith("git@github.com:"):
            normalized = normalized.removeprefix("git@github.com:")
        return normalized.strip("/")

    async def find_open_pull_request(
        self,
        *,
        owner: str,
        name: str,
        head: str,
        base: str,
        access_token: str,
    ) -> GitHubPullRequest | None:
        data = await self._request(
            "GET",
            f"/repos/{owner}/{name}/pulls",
            access_token,
            params={"state": "open", "head": head, "base": base},
        )
        if not data:
            return None
        pr = data[0]
        return GitHubPullRequest(
            number=int(pr["number"]),
            html_url=str(pr["html_url"]),
            state=str(pr["state"]),
        )

    async def create_pull_request(
        self,
        *,
        owner: str,
        name: str,
        title: str,
        body: str,
        head: str,
        base: str,
        access_token: str,
    ) -> GitHubPullRequest:
        data = await self._request(
            "POST",
            f"/repos/{owner}/{name}/pulls",
            access_token,
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
            },
        )
        return GitHubPullRequest(
            number=int(data["number"]),
            html_url=str(data["html_url"]),
            state=str(data["state"]),
        )

    async def comment_on_pull_request(
        self,
        *,
        owner: str,
        name: str,
        issue_number: int,
        body: str,
        access_token: str,
    ) -> None:
        await self._request(
            "POST",
            f"/repos/{owner}/{name}/issues/{issue_number}/comments",
            access_token,
            json={"body": body},
        )

    async def merge_pull_request(
        self,
        *,
        owner: str,
        name: str,
        number: int,
        commit_title: str,
        access_token: str,
    ) -> None:
        await self._request(
            "PUT",
            f"/repos/{owner}/{name}/pulls/{number}/merge",
            access_token,
            json={
                "merge_method": "squash",
                "commit_title": commit_title,
            },
        )

    async def _request(
        self,
        method: str,
        path: str,
        access_token: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> dict | list:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {access_token}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=20.0) as client:
            response = await client.request(
                method,
                path,
                headers=headers,
                params=params,
                json=json,
            )

        if response.status_code >= 400:
            message = response.text
            try:
                payload = response.json()
                message = str(payload.get("message", message))
            except ValueError:
                pass
            raise ValueError(f"GitHub API error: {message}")

        return response.json()

    async def _request_as_app(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, str] | None = None,
        json: dict[str, object] | None = None,
    ) -> dict | list:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._create_app_jwt()}",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient(base_url=self.BASE_URL, timeout=20.0) as client:
            response = await client.request(
                method,
                path,
                headers=headers,
                params=params,
                json=json,
            )

        if response.status_code >= 400:
            message = response.text
            try:
                payload = response.json()
                message = str(payload.get("message", message))
            except ValueError:
                pass
            raise ValueError(f"GitHub App API error: {message}")

        return response.json()
