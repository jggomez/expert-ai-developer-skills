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


def _summary_outcome(summary, files=("api/clients.py", "web/page.tsx"), findings=None, status="ok"):
    from pr_reviewer.domain.models import DiffBundle, FileDiff

    diff = DiffBundle(base="a" * 40, head="b" * 40, files=[
        FileDiff(path=path, patch="+++ b/x\n+one\n+two\n-old\n", commentable_lines=[1, 2]) for path in files])
    kept = findings or []
    report = ReviewReport(status=status, provider="antigravity", model="gemini-3.8-flash", findings=kept,
                          summary=summary, error="boom" if status == "failed" else "")
    return ReviewOutcome(report, diff, Selection(kept=kept))


def _mermaid(text: str) -> str:
    return text.split("```mermaid\n", 1)[1].split("\n```", 1)[0]


def test_the_summary_shows_the_overview_and_a_change_map():
    # Arrange
    from pr_reviewer.domain.models import AreaChange, AreaLink, PullRequestSummary

    summary = PullRequestSummary(
        overview="Adds the Clients to Review page backed by Firestore.",
        changes=[AreaChange(path="api", what="new /clients endpoint"), AreaChange(path="web", what="new page")],
        links=[AreaLink(source="web", target="api")])
    findings = [finding(file="api/clients.py", line=1, severity="high")]

    # Act
    text = format_summary(_summary_outcome(summary, findings=findings))

    # Assert
    assert "### What changed" in text
    assert "Adds the Clients to Review page backed by Firestore." in text
    graph = _mermaid(text)
    assert graph.startswith("flowchart LR")
    assert 'a1["api/ · +2 -1<br/>new /clients endpoint"]' in graph
    assert "a2 --> a1" in graph
    assert "class a1 high" in graph
    assert text.index("### What changed") < text.index("| Severity |")


@pytest.mark.parametrize("hostile", [
    'x"]; click a1 href "https://evil.example"',
    "`code` <script>alert(1)</script>",
    "ping @octocat",
    SUMMARY_MARKER,
    "line\nbreak]]\n```\n## fake heading",
    "%%{init: {'theme':'dark'}}%%",
])
def test_hostile_summary_text_cannot_escape_the_diagram(hostile):
    # Arrange
    from pr_reviewer.domain.models import AreaChange, PullRequestSummary

    summary = PullRequestSummary(overview=hostile, changes=[AreaChange(path="api", what=hostile)])

    # Act
    text = format_summary(_summary_outcome(summary))

    # Assert
    graph = _mermaid(text)
    for line in graph.splitlines()[1:]:
        assert line.startswith(("  a", "  classDef ", "  class ")), line
    assert '"' not in graph.replace('["', "").replace('"]', "")
    assert "%%" not in graph and ";" not in graph
    assert "<script" not in text and "@octocat" not in text
    assert text.count(SUMMARY_MARKER) == 1
    assert text.count("```") == 2


def test_no_summary_means_no_section():
    # Act
    text = format_summary(_summary_outcome(None))

    # Assert
    assert "What changed" not in text
    assert "```mermaid" not in text


def test_a_failed_review_shows_no_summary():
    # Arrange
    from pr_reviewer.domain.models import PullRequestSummary

    # Act
    text = format_summary(_summary_outcome(PullRequestSummary(overview="x"), status="failed"))

    # Assert
    assert "What changed" not in text


def test_a_single_area_still_gets_the_overview_but_no_diagram():
    # Arrange
    from pr_reviewer.domain.models import PullRequestSummary

    # Act
    text = format_summary(_summary_outcome(PullRequestSummary(overview="Fixes a typo."), files=("README.md",)))

    # Assert
    assert "Fixes a typo." in text
    assert "```mermaid" not in text
