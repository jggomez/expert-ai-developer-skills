"""Minimal GitHub REST client."""

from __future__ import annotations

import os
from typing import Any

import httpx

DEFAULT_API_URL = "https://api.github.com"
PAGE_SIZE = 100


class GitHubError(RuntimeError):
    """A GitHub API call failed."""

    def __init__(self, status: int, message: str):
        super().__init__(f"GitHub API returned {status}: {message}")
        self.status = status


class GitHubClient:
    def __init__(self, token: str, *, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(
            base_url=os.environ.get("GITHUB_API_URL", DEFAULT_API_URL),
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "pr-reviewer",
            },
            timeout=30.0,
            transport=transport,
        )

    def request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self._client.request(method, path, **kwargs)
        if response.is_error:
            raise GitHubError(response.status_code, response.text[:300])
        return response.json()

    def list_all(self, path: str) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        page = 1
        while True:
            batch = self.request("GET", path, params={"per_page": PAGE_SIZE, "page": page})
            items.extend(batch)
            if len(batch) < PAGE_SIZE:
                return items
            page += 1

    def pull_request(self, repo: str, number: int) -> dict[str, Any]:
        result: dict[str, Any] = self.request("GET", f"/repos/{repo}/pulls/{number}")
        return result
