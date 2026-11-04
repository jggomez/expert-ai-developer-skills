"""Implements the pull request port on the GitHub REST API."""

from __future__ import annotations

from typing import Any

from pr_reviewer.adapters.github.client import GitHubClient, GitHubError
from pr_reviewer.adapters.github.markdown import (
    FINGERPRINT_PATTERN,
    SUMMARY_MARKER,
    format_inline_comment,
    format_summary,
)
from pr_reviewer.application.ports import ReviewOutcome
from pr_reviewer.domain.models import Finding

_UNPROCESSABLE = 422
_NOT_OURS = (403, 404)


def _is_bot(comment: dict[str, Any]) -> bool:
    return (comment.get("user") or {}).get("type") == "Bot"


class GitHubPullRequestGateway:
    def __init__(self, client: GitHubClient, repo: str, number: int):
        self._client = client
        self._repo = repo
        self._number = number

    def posted_fingerprints(self) -> set[str]:
        comments = self._client.list_all(f"/repos/{self._repo}/pulls/{self._number}/comments")
        return {match for c in comments if _is_bot(c) for match in FINGERPRINT_PATTERN.findall(c.get("body", ""))}

    def post_inline_review(self, commit: str, findings: list[Finding]) -> bool:
        payload = {
            "commit_id": commit,
            "event": "COMMENT",
            "body": f"Found {len(findings)} efficiency, optimality or cost issue(s).",
            "comments": [
                {"path": f.file, "line": f.line, "side": "RIGHT", "body": format_inline_comment(f)} for f in findings
            ],
        }
        try:
            self._client.request("POST", f"/repos/{self._repo}/pulls/{self._number}/reviews", json=payload)
        except GitHubError as error:
            if error.status != _UNPROCESSABLE:
                raise
            return False
        return True

    def upsert_summary(self, outcome: ReviewOutcome) -> None:
        body = format_summary(outcome)
        comments = self._client.list_all(f"/repos/{self._repo}/issues/{self._number}/comments")
        for comment in comments:
            if SUMMARY_MARKER in comment.get("body", "") and _is_bot(comment):
                try:
                    self._client.request(
                        "PATCH", f"/repos/{self._repo}/issues/comments/{comment['id']}", json={"body": body}
                    )
                except GitHubError as error:
                    if error.status not in _NOT_OURS:
                        raise
                    continue  # Another app wrote this comment, so this token cannot edit it.
                return
        self._client.request("POST", f"/repos/{self._repo}/issues/{self._number}/comments", json={"body": body})
