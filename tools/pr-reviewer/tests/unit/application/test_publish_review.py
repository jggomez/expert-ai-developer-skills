"""Publishing rules, with the pull request port replaced by an in-memory double."""

from pr_reviewer.application.ports import ReviewOutcome
from pr_reviewer.application.publish_review import publish_review
from pr_reviewer.domain.findings import PublishOptions, fingerprint
from pr_reviewer.domain.models import Finding
from support.builders import HEAD, bundle, finding, report


class FakeGateway:
    def __init__(self, posted: set[str] | None = None, accept_inline: bool = True):
        self.posted = posted or set()
        self.accept_inline = accept_inline
        self.inline_calls: list[tuple[str, list[Finding]]] = []
        self.summaries: list[ReviewOutcome] = []

    def posted_fingerprints(self) -> set[str]:
        return self.posted

    def post_inline_review(self, commit: str, findings: list[Finding]) -> bool:
        self.inline_calls.append((commit, findings))
        return self.accept_inline

    def upsert_summary(self, outcome: ReviewOutcome) -> None:
        self.summaries.append(outcome)


def test_new_findings_are_posted_for_the_reviewed_commit():
    # Arrange
    gateway = FakeGateway()

    # Act
    result = publish_review(gateway, report(), bundle(), PublishOptions())

    # Assert
    assert result.inline_posted == 1
    assert gateway.inline_calls[0][0] == HEAD
    assert gateway.summaries[0].inline_posted == 1


def test_published_findings_are_not_posted_again():
    # Arrange
    gateway = FakeGateway(posted={fingerprint(finding())})

    # Act
    result = publish_review(gateway, report(), bundle(), PublishOptions())

    # Assert
    assert (result.inline_posted, result.already_posted) == (0, 1)
    assert gateway.inline_calls == []


def test_rejected_inline_review_is_reported_in_the_outcome():
    # Arrange
    gateway = FakeGateway(accept_inline=False)

    # Act
    result = publish_review(gateway, report(), bundle(), PublishOptions())

    # Assert
    assert result.inline_posted == 0
    assert gateway.summaries[0].inline_rejected is True


def test_summary_is_always_updated_even_with_no_findings():
    # Arrange
    gateway = FakeGateway()

    # Act
    publish_review(gateway, report([]), bundle(), PublishOptions())

    # Assert
    assert gateway.inline_calls == []
    assert len(gateway.summaries) == 1
