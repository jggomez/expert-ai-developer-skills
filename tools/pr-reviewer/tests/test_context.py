"""Decides whether a workflow event should trigger a review."""

import pytest

from pr_reviewer.context import resolve_context

BASE, HEAD = "a" * 40, "b" * 40


def pr_event(action: str = "opened", draft: bool = False, fork: bool = False, author: str = "dev") -> dict:
    return {
        "action": action,
        "pull_request": {
            "number": 7,
            "draft": draft,
            "user": {"login": author},
            "base": {"sha": BASE, "repo": {"full_name": "o/r"}},
            "head": {"sha": HEAD, "repo": {"full_name": "x/r" if fork else "o/r"}},
        },
    }


def comment_event(body: str = "/review", association: str = "MEMBER", user_type: str = "User", on_pr: bool = True) -> dict:
    issue: dict = {"number": 7}
    if on_pr:
        issue["pull_request"] = {"url": "https://api.github.com/repos/o/r/pulls/7"}
    return {
        "action": "created",
        "repository": {"full_name": "o/r"},
        "issue": issue,
        "comment": {"body": body, "author_association": association, "user": {"type": user_type}},
    }


def fetch_pr(*, draft: bool = False, fork: bool = False, state: str = "open"):
    def _fetch(repo: str, number: int) -> dict:
        assert (repo, number) == ("o/r", 7)
        return {**pr_event(draft=draft, fork=fork)["pull_request"], "state": state}

    return _fetch


@pytest.mark.parametrize("action", ["opened", "reopened", "ready_for_review"])
def test_pull_request_review_actions_run(action: str):
    # Act
    ctx = resolve_context("pull_request", pr_event(action), fetch_pr())

    # Assert
    assert (ctx.should_run, ctx.pr_number, ctx.base_sha, ctx.head_sha) == (True, 7, BASE, HEAD)
    assert ctx.repo == "o/r"


@pytest.mark.parametrize(
    ("event", "reason"),
    [
        (pr_event("synchronize"), "action"),
        (pr_event(draft=True), "draft"),
        (pr_event(fork=True), "fork"),
        (pr_event(author="dependabot[bot]"), "Dependabot"),
    ],
)
def test_pull_request_skips(event: dict, reason: str):
    # Act
    ctx = resolve_context("pull_request", event, fetch_pr())

    # Assert
    assert ctx.should_run is False
    assert reason in ctx.reason


def test_pull_request_target_is_refused_because_it_exposes_secrets_to_forks():
    # Act
    ctx = resolve_context("pull_request_target", pr_event(), fetch_pr())

    # Assert
    assert ctx.should_run is False
    assert "pull_request_target" in ctx.reason


@pytest.mark.parametrize("association", ["OWNER", "MEMBER", "COLLABORATOR"])
def test_review_command_runs_for_maintainers(association: str):
    # Act
    ctx = resolve_context("issue_comment", comment_event(association=association), fetch_pr())

    # Assert
    assert (ctx.should_run, ctx.pr_number, ctx.head_sha) == (True, 7, HEAD)


@pytest.mark.parametrize(
    "event",
    [
        comment_event(association="CONTRIBUTOR"),
        comment_event(association="NONE"),
        comment_event(body="please /review this"),
        comment_event(body="/reviewer"),
        comment_event(user_type="Bot"),
        comment_event(on_pr=False),
    ],
)
def test_review_command_is_ignored_when_not_authorised_or_not_exact(event: dict):
    # Act
    ctx = resolve_context("issue_comment", event, fetch_pr())

    # Assert
    assert ctx.should_run is False


def test_review_command_allows_text_after_the_command_line():
    # Act
    ctx = resolve_context("issue_comment", comment_event(body="  /review\nthanks"), fetch_pr())

    # Assert
    assert ctx.should_run is True


@pytest.mark.parametrize(("kwargs", "reason"), [({"fork": True}, "fork"), ({"state": "closed"}, "closed")])
def test_review_command_skips_forks_and_closed_prs(kwargs: dict, reason: str):
    # Act
    ctx = resolve_context("issue_comment", comment_event(), fetch_pr(**kwargs))

    # Assert
    assert ctx.should_run is False
    assert reason in ctx.reason


def test_unknown_events_are_skipped():
    # Act
    ctx = resolve_context("push", {}, fetch_pr())

    # Assert
    assert ctx.should_run is False


def test_deleted_author_account_does_not_crash_the_gate():
    # Arrange
    event = pr_event()
    event["pull_request"]["user"] = None

    # Act
    ctx = resolve_context("pull_request", event, fetch_pr())

    # Assert
    assert ctx.should_run is True


def test_comment_with_null_user_is_treated_as_unauthorised():
    # Arrange
    event = comment_event(association="NONE")
    event["comment"]["user"] = None

    # Act
    ctx = resolve_context("issue_comment", event, fetch_pr())

    # Assert
    assert ctx.should_run is False
