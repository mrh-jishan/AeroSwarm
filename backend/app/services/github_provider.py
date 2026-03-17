"""GitHub API client for repository and pull request workflows."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import hmac
from urllib.parse import urlencode

import httpx

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
class GitHubPullRequest:
    number: int
    html_url: str
    state: str


class GitHubProviderService:
    BASE_URL = "https://api.github.com"
    AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
    OAUTH_TOKEN_URL = "https://github.com/login/oauth/access_token"

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
            raise ValueError(f"GitHub OAuth error: {data.get('error_description', 'missing access token')}")
        return str(access_token)

    def verify_webhook_signature(self, payload: bytes, signature_header: str | None) -> bool:
        secret = settings.GITHUB_WEBHOOK_SECRET
        if not secret:
            raise ValueError("GitHub webhook secret is not configured")
        if not signature_header or not signature_header.startswith("sha256="):
            return False

        digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
        expected = f"sha256={digest}"
        return hmac.compare_digest(expected, signature_header)

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
