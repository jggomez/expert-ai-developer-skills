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
    if name == "claude":
        from pr_reviewer.adapters.providers.claude_managed import ClaudeManagedProvider

        return ClaudeManagedProvider(
            agent_id=os.environ.get("CLAUDE_AGENT_ID"),
            environment_id=os.environ.get("CLAUDE_ENVIRONMENT_ID"),
        )
    raise ValueError(f"Unknown provider {name!r}")


def setup_claude() -> tuple[str, str]:
    """Create the persistent Managed Agents resources. Reads ANTHROPIC_API_KEY."""
    from pr_reviewer.adapters.providers.claude_managed import create_reviewer_resources

    return create_reviewer_resources()


def github_client() -> GitHubClient:
    return GitHubClient(os.environ["GITHUB_TOKEN"])


def pull_request_gateway(repo: str, number: int) -> PullRequestGateway:
    return GitHubPullRequestGateway(github_client(), repo, number)
