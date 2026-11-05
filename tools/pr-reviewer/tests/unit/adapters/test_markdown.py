"""Hostile model text must render inert."""

import pytest

from pr_reviewer.adapters.github.markdown import (
    SUMMARY_MARKER,
    format_inline_comment,
    format_summary,
    sanitize,
)
from pr_reviewer.application.ports import ReviewOutcome
from pr_reviewer.domain.findings import Selection, fingerprint
from pr_reviewer.domain.models import ReviewReport
from support.builders import bundle, finding


@pytest.mark.parametrize(
    ("raw", "forbidden"),
    [
        ("leak ghp_" + "a" * 36, "ghp_"),
        ("leak github_pat_" + "a" * 40, "github_pat_"),
        ("leak AIza" + "b" * 35, "AIza"),
        ("leak sk-ant-api03-" + "c" * 40, "sk-ant-"),
        ("leak AKIA" + "D" * 16, "AKIA"),
        ("-----BEGIN RSA PRIVATE KEY-----\nabc\n-----END RSA PRIVATE KEY-----", "abc"),
        ("hello @octocat", "@octocat"),
        (".@octocat", "@octocat"),
        ("-@octocat", "@octocat"),
        ("/@octocat", "@octocat"),
        ("` @octocat `", "@octocat"),
        ("\\`<img src=https://evil.example/p.png>\\`", "<img"),
        ("``` <img src=x> `", "<img"),
        ("leak ASIA" + "D" * 16, "ASIA"),
        ("leak glpat-" + "e" * 20, "glpat-"),
        ("leak xoxb-" + "1" * 20, "xoxb-"),
        ("![track](https://evil.example/x.png)", "!["),
        (f"{SUMMARY_MARKER} fake", SUMMARY_MARKER),
    ],
)
def test_sanitize_removes_secrets_mentions_images_and_markers(raw: str, forbidden: str):
    # Act
    clean = sanitize(raw)

    # Assert
    assert forbidden not in clean


def test_email_addresses_are_left_alone():
    # Act / Assert
    assert sanitize("write to dev@example.com") == "write to dev@example.com"


def test_inline_comment_keeps_fence_intact_when_the_fix_contains_backticks():
    # Arrange
    item = finding(proposed_fix="```py\nx = 1\n```")

    # Act
    body = format_inline_comment(item)

    # Assert
    assert "````" in body
    assert fingerprint(item) in body


def test_a_partial_review_shows_the_findings_and_lists_the_files_it_missed():
    # Arrange
    selected = finding(file="a.py", line=1)
    report = ReviewReport(
        status="partial", provider="p", findings=[selected], error="model overloaded", unreviewed=["payments/charge.py"]
    )
    data = bundle()
    selection = Selection(kept=[selected], outside_diff=0, filtered=0, over_limit=0)

    # Act
    text = format_summary(ReviewOutcome(report, data, selection, inline_posted=1, already_posted=0, inline_rejected=False))

    # Assert
    assert "1 file(s) could not be reviewed" in text
    assert "payments/charge.py" in text
    assert "1 new inline comment(s) posted" in text


def test_a_partial_review_with_no_findings_never_claims_the_code_is_clean():
    # Arrange
    report = ReviewReport(status="partial", provider="p", error="x", unreviewed=["a.py"])
    selection = Selection(kept=[], outside_diff=0, filtered=0, over_limit=0)

    # Act
    text = format_summary(ReviewOutcome(report, bundle(), selection, inline_posted=0, already_posted=0, inline_rejected=False))

    # Assert
    assert "✅" not in text
