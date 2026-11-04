"""Use case: publish what a review found."""

from __future__ import annotations

from dataclasses import dataclass

from pr_reviewer.application.ports import PullRequestGateway, ReviewOutcome
from pr_reviewer.domain.findings import PublishOptions, fingerprint, select_findings
from pr_reviewer.domain.models import DiffBundle, ReviewReport


@dataclass(frozen=True)
class PublishResult:
    inline_posted: int
    already_posted: int


def publish_review(
    gateway: PullRequestGateway,
    report: ReviewReport,
    bundle: DiffBundle,
    options: PublishOptions,
) -> PublishResult:
    """Post the findings not published yet, then create or update the summary."""
    selection = select_findings(report.findings, bundle, options)
    posted = gateway.posted_fingerprints()
    new = [f for f in selection.kept if fingerprint(f) not in posted]

    accepted = gateway.post_inline_review(bundle.head, new) if new else True

    inline_posted = len(new) if accepted else 0
    already_posted = len(selection.kept) - len(new)
    gateway.upsert_summary(
        ReviewOutcome(
            report=report,
            bundle=bundle,
            selection=selection,
            inline_posted=inline_posted,
            already_posted=already_posted,
            inline_rejected=not accepted,
        )
    )
    return PublishResult(inline_posted=inline_posted, already_posted=already_posted)
