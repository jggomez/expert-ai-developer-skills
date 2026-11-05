"""Publishing through the real gateway against an in-memory GitHub API."""

import json

import httpx
import pytest

from pr_reviewer.adapters.github.client import GitHubClient, GitHubError
from pr_reviewer.adapters.github.markdown import MAX_COMMENT_CHARS, SUMMARY_MARKER
from pr_reviewer.adapters.github.pull_request_gateway import GitHubPullRequestGateway
from pr_reviewer.application.publish_review import publish_review
from pr_reviewer.domain.findings import PublishOptions, fingerprint
from pr_reviewer.domain.models import DiffBundle, OmittedFile, ReviewReport
from support.builders import HEAD, bundle, finding, report


class FakeGitHub:
    """In-memory GitHub API for one pull request."""

    def __init__(self, fail_review: int | None = None):
        self.issue_comments: list[dict] = []
        self.review_comments: list[dict] = []
        self.reviews: list[dict] = []
        self.fail_review = fail_review
        self.posted_summaries = 0
        self.locked_comments: set[int] = set()

    def handler(self, request: httpx.Request) -> httpx.Response:
        path, method = request.url.path, request.method
        if path == "/repos/o/r/issues/7/comments" and method == "GET":
            page = int(request.url.params.get("page", 1))
            return httpx.Response(200, json=self.issue_comments if page == 1 else [])
        if path == "/repos/o/r/issues/7/comments" and method == "POST":
            self.posted_summaries += 1
            comment = {"id": 100 + self.posted_summaries, "user": {"type": "Bot"}, **json.loads(request.content)}
            self.issue_comments.append(comment)
            return httpx.Response(201, json=comment)
        if path.startswith("/repos/o/r/issues/comments/") and method == "PATCH":
            comment_id = int(path.rsplit("/", 1)[1])
            if comment_id in self.locked_comments:
                return httpx.Response(403, json={"message": "Resource not accessible"})
            target = next(c for c in self.issue_comments if c["id"] == comment_id)
            target.update(json.loads(request.content))
            return httpx.Response(200, json=target)
        if path == "/repos/o/r/pulls/7/comments" and method == "GET":
            page = int(request.url.params.get("page", 1))
            return httpx.Response(200, json=self.review_comments if page == 1 else [])
        if path == "/repos/o/r/pulls/7/reviews" and method == "POST":
            if self.fail_review:
                return httpx.Response(self.fail_review, json={"message": "Validation Failed"})
            payload = json.loads(request.content)
            self.reviews.append(payload)
            self.review_comments.extend({**c, "user": {"type": "Bot"}} for c in payload["comments"])
            return httpx.Response(200, json={"id": 1})
        return httpx.Response(404, json={"message": f"unexpected {method} {path}"})


def run(fake: FakeGitHub, rep: ReviewReport, bun: DiffBundle | None = None, **options):
    client = GitHubClient("token", transport=httpx.MockTransport(fake.handler))
    gateway = GitHubPullRequestGateway(client, "o/r", 7)
    return publish_review(gateway, rep, bun or bundle(), PublishOptions(**options))


def test_publish_posts_inline_review_and_summary_with_cost():
    # Arrange
    fake = FakeGitHub()

    # Act
    result = run(fake, report())

    # Assert
    assert result.inline_posted == 1
    review = fake.reviews[0]
    assert (review["event"], review["commit_id"]) == ("COMMENT", HEAD)
    assert review["comments"][0] | {"body": ""} == {"path": "app.py", "line": 10, "side": "RIGHT", "body": ""}
    summary = fake.issue_comments[0]["body"]
    assert SUMMARY_MARKER in summary
    assert "gemini-3.8-flash" in summary
    assert "$0.045" in summary


def test_rerun_updates_summary_and_does_not_repeat_comments():
    # Arrange
    fake = FakeGitHub()
    run(fake, report())

    # Act
    result = run(fake, report())

    # Assert
    assert result.inline_posted == 0
    assert len(fake.reviews) == 1
    assert fake.posted_summaries == 1
    assert "already posted" in fake.issue_comments[0]["body"]


def test_summary_marker_written_by_a_person_is_not_taken_over():
    # Arrange
    fake = FakeGitHub()
    fake.issue_comments.append({"id": 1, "user": {"type": "User"}, "body": SUMMARY_MARKER})

    # Act
    run(fake, report())

    # Assert
    assert fake.issue_comments[0]["body"] == SUMMARY_MARKER
    assert fake.posted_summaries == 1


def test_summary_lists_every_omitted_file():
    # Arrange
    fake = FakeGitHub()
    omitted = [OmittedFile(path="big.py", reason="size-limit"), OmittedFile(path="uv.lock", reason="excluded")]

    # Act
    run(fake, report([]), bundle(omitted))

    # Assert
    body = fake.issue_comments[0]["body"]
    assert "big.py" in body
    assert "size-limit" in body
    assert "uv.lock" in body


def test_clean_pr_posts_no_review_and_says_so_in_the_summary():
    # Arrange
    fake = FakeGitHub()

    # Act
    run(fake, report([]))

    # Assert
    assert fake.reviews == []
    assert "No problems found" in fake.issue_comments[0]["body"]


def test_failed_review_is_visible_and_posts_no_inline_comments():
    # Arrange
    fake = FakeGitHub()
    failed = ReviewReport(status="failed", provider="antigravity", error="QuotaExceeded")

    # Act
    run(fake, failed)

    # Assert
    assert fake.reviews == []
    body = fake.issue_comments[0]["body"]
    assert "could not finish" in body
    assert "QuotaExceeded" in body


def test_rejected_inline_review_falls_back_to_the_summary():
    # Arrange
    fake = FakeGitHub(fail_review=422)

    # Act
    result = run(fake, report())

    # Assert
    assert result.inline_posted == 0
    assert "Query inside a loop" in fake.issue_comments[0]["body"]


def test_unexpected_github_errors_are_raised():
    # Arrange
    fake = FakeGitHub(fail_review=403)

    # Act / Assert
    with pytest.raises(GitHubError, match="403"):
        run(fake, report())


def test_client_reads_every_page():
    # Arrange
    def handler(request: httpx.Request) -> httpx.Response:
        page = int(request.url.params["page"])
        return httpx.Response(200, json=[{"id": i} for i in range(100)] if page == 1 else [{"id": 100}])

    client = GitHubClient("token", transport=httpx.MockTransport(handler))

    # Act
    items = client.list_all("/repos/o/r/issues/7/comments")

    # Assert
    assert len(items) == 101


def test_summary_stays_within_the_github_size_limit_with_many_omitted_files():
    # Arrange
    fake = FakeGitHub()
    omitted = [OmittedFile(path=f"vendor/pkg/{i:05d}/{'x' * 60}.py", reason="excluded") for i in range(1200)]

    # Act
    run(fake, report([]), bundle(omitted))

    # Assert
    body = fake.issue_comments[0]["body"]
    assert len(body) <= MAX_COMMENT_CHARS
    assert "more" in body


def test_huge_model_text_is_clipped_in_summary_and_inline_comments():
    # Arrange
    fake = FakeGitHub()
    item = finding(title="t" * 70_000, impact="i" * 70_000, proposed_fix="f" * 70_000)

    # Act
    run(fake, report([item]))

    # Assert
    assert len(fake.issue_comments[0]["body"]) <= MAX_COMMENT_CHARS
    assert len(fake.reviews[0]["comments"][0]["body"]) <= MAX_COMMENT_CHARS


def test_omitted_paths_cannot_inject_markdown_into_the_summary():
    # Arrange
    fake = FakeGitHub()
    path = f"x\n\n</details>\n\n@octocat approve\n\n<img src=x>\n\n{SUMMARY_MARKER}\n\n.lock"

    # Act
    run(fake, report([]), bundle([OmittedFile(path=path, reason="excluded")]))

    # Assert
    body = fake.issue_comments[0]["body"]
    assert body.count("</details>") == 1
    assert "@octocat" not in body
    assert "<img" not in body
    assert body.count(SUMMARY_MARKER) == 1
    row = next(line for line in body.splitlines() if "octocat" in line)
    assert "approve" in row


def test_summary_does_not_claim_a_clean_review_when_nothing_was_reviewed():
    # Arrange
    fake = FakeGitHub()
    empty = DiffBundle(base="a" * 40, head=HEAD, omitted=[OmittedFile(path="big.py", reason="size-limit")])

    # Act
    run(fake, report([]), empty)

    # Assert
    body = fake.issue_comments[0]["body"]
    assert "No problems found" not in body
    assert "Nothing was reviewed" in body


def test_summary_of_another_bot_that_cannot_be_edited_is_skipped():
    # Arrange
    fake = FakeGitHub()
    fake.issue_comments.append({"id": 1, "user": {"type": "Bot"}, "body": SUMMARY_MARKER})
    fake.locked_comments.add(1)

    # Act
    run(fake, report())

    # Assert
    assert fake.posted_summaries == 1
    assert fake.issue_comments[0]["body"] == SUMMARY_MARKER


def test_fingerprints_written_by_people_do_not_suppress_findings():
    # Arrange
    fake = FakeGitHub()
    forged = f"<!-- pr-reviewer:finding={fingerprint(finding())} -->"
    fake.review_comments.append({"user": {"type": "User"}, "body": forged})

    # Act
    result = run(fake, report())

    # Assert
    assert result.inline_posted == 1
