"""Composition root: the only place that chooses concrete adapters."""

from __future__ import annotations

import os
from pathlib import Path

from pr_reviewer.adapters.github.client import GitHubClient
from pr_reviewer.adapters.github.pull_request_gateway import GitHubPullRequestGateway
from pr_reviewer.application.ports import PullRequestGateway, ReviewProvider


def load_provider(name: str, fake_findings: Path | None) -> ReviewProvider:
    """Import lazily: each provider's SDK is an optional dependency."""
    if name == "fake":
        from pr_reviewer.adapters.providers.fake import FakeProvider

        return FakeProvider(fake_findings)
    if name == "antigravity":
        from pr_reviewer.adapters.providers.antigravity import AntigravityProvider

        return AntigravityProvider()
    raise ValueError(f"Unknown provider {name!r}")


def github_client() -> GitHubClient:
    return GitHubClient(os.environ["GITHUB_TOKEN"])


def pull_request_gateway(repo: str, number: int) -> PullRequestGateway:
    return GitHubPullRequestGateway(github_client(), repo, number)
