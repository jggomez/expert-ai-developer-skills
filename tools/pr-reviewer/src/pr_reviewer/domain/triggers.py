"""Decide from a GitHub event whether this workflow run should review a PR."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Event = dict[str, Any]
FetchPullRequest = Callable[[str, int], Event]

REVIEW_ACTIONS = frozenset({"opened", "reopened", "ready_for_review"})
MAINTAINERS = frozenset({"OWNER", "MEMBER", "COLLABORATOR"})
REVIEW_COMMAND = "/review"
DEPENDABOT = "dependabot[bot]"


@dataclass(frozen=True)
class ReviewContext:
    """Result of the gate. Empty fields mean there is nothing to review."""

    should_run: bool
    reason: str = ""
    repo: str = ""
    pr_number: int = 0
    base_sha: str = ""
    head_sha: str = ""


def _skip(reason: str) -> ReviewContext:
    return ReviewContext(should_run=False, reason=reason)


def _from_pull_request(pr: Event) -> ReviewContext:
    if (pr.get("user") or {}).get("login") == DEPENDABOT:
        return _skip("Dependabot runs have no access to secrets")
    base_repo = pr["base"]["repo"]["full_name"]
    head_repo = (pr["head"].get("repo") or {}).get("full_name")
    if head_repo != base_repo:
        return _skip("fork pull requests are not reviewed: their runs have no access to secrets")
    return ReviewContext(
        should_run=True,
        repo=base_repo,
        pr_number=pr["number"],
        base_sha=pr["base"]["sha"],
        head_sha=pr["head"]["sha"],
    )


def _is_review_command(body: str) -> bool:
    lines = body.strip().splitlines()
    return bool(lines) and lines[0].strip() == REVIEW_COMMAND


def resolve_context(event_name: str, event: Event, fetch_pr: FetchPullRequest) -> ReviewContext:
    """Apply the trigger rules. `fetch_pr` is only called for an authorised /review."""
    if event_name == "pull_request_target":
        return _skip("pull_request_target is not supported: it gives fork code access to secrets")

    if event_name == "pull_request":
        if event.get("action") not in REVIEW_ACTIONS:
            return _skip(f"action {event.get('action')!r} does not trigger a review")
        pr = event["pull_request"]
        if pr.get("draft"):
            return _skip("draft pull request")
        return _from_pull_request(pr)

    if event_name == "issue_comment":
        comment = event.get("comment", {})
        issue = event.get("issue", {})
        if event.get("action") != "created" or "pull_request" not in issue:
            return _skip("comment is not on a pull request")
        if not _is_review_command(comment.get("body", "")):
            return _skip("comment is not a /review command")
        if (comment.get("user") or {}).get("type") == "Bot":
            return _skip("comments from bots do not trigger a review")
        if comment.get("author_association") not in MAINTAINERS:
            return _skip("only maintainers can request a review")
        pr = fetch_pr(event["repository"]["full_name"], issue["number"])
        if pr.get("state") != "open":
            return _skip("pull request is closed")
        return _from_pull_request(pr)

    return _skip(f"event {event_name!r} does not trigger a review")
