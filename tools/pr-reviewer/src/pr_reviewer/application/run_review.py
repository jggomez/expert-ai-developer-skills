"""Use case: review a diff and always produce a report."""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from pr_reviewer.application.ports import (
    DEFAULT_BUDGET_USD,
    DEFAULT_MAX_TOKENS,
    ProviderError,
    ReviewProvider,
    ReviewRequest,
)
from pr_reviewer.domain.findings import fingerprint
from pr_reviewer.domain.models import DiffBundle, Finding, ReviewReport, ReviewUsage
from pr_reviewer.domain.pricing import estimate_cost

logger = logging.getLogger(__name__)

MAX_ERROR_CHARS = 300


@dataclass(frozen=True)
class ReviewSettings:
    provider: str
    model: str | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS
    budget_usd: str = DEFAULT_BUDGET_USD
    fallback_model: str | None = None


def run_review(
    bundle: DiffBundle,
    settings: ReviewSettings,
    *,
    load_provider: Callable[[], ReviewProvider],
    build_workspace: Callable[[], Path],
    load_rubric: Callable[[], str | None] = lambda: None,
) -> ReviewReport:
    """A failed review becomes a report, because it must never block the pull request.

    The provider and workspace are created here, and only when there is
    something to review, so that their failures are reported the same way.
    """
    if not bundle.files:
        return ReviewReport(status="ok", provider=settings.provider)
    try:
        provider = load_provider()
        request = ReviewRequest(
            bundle=bundle,
            workspace=build_workspace(),
            model=settings.model,
            max_tokens=settings.max_tokens,
            budget_usd=settings.budget_usd,
            rubric=load_rubric(),
            fallback_model=settings.fallback_model,
        )
        output = provider.review(request)
    except ProviderError as error:
        logger.exception("The review did not finish")
        return ReviewReport(
            status="failed",
            provider=settings.provider,
            model=error.model,
            usage=error.usage,
            error=str(error)[:MAX_ERROR_CHARS],
        )
    except Exception as error:
        logger.exception("The review failed unexpectedly")
        return ReviewReport(
            status="failed",
            provider=settings.provider,
            error=f"{type(error).__name__}: {error}"[:MAX_ERROR_CHARS],
        )
    return ReviewReport(
        status="ok",
        provider=settings.provider,
        model=output.model,
        findings=output.result.findings,
        usage=output.usage,
    )


def _total_cost(reports: list[ReviewReport]) -> float | None:
    costs = [estimate_cost(report.model, report.usage) for report in reports]
    return None if any(cost is None for cost in costs) else sum(c for c in costs if c is not None)


def merge_reports(reports: list[ReviewReport], shards: list[DiffBundle]) -> ReviewReport:
    """Combine one report per group. Each model's cost is computed here, while the model is known."""
    if len(reports) == 1:
        return reports[0]
    failed = [(report, shard) for report, shard in zip(reports, shards, strict=True) if report.status != "ok"]
    unique: dict[str, Finding] = {}
    for report in reports:
        for finding in report.findings:
            unique.setdefault(fingerprint(finding), finding)
    usage = ReviewUsage(
        input_tokens=sum(r.usage.input_tokens for r in reports),
        cached_input_tokens=sum(r.usage.cached_input_tokens for r in reports),
        output_tokens=sum(r.usage.output_tokens for r in reports),
        reported_cost_usd=_total_cost(reports),
    )
    return ReviewReport(
        status="failed" if len(failed) == len(reports) else "partial" if failed else "ok",
        provider=reports[0].provider,
        model=", ".join(dict.fromkeys(r.model for r in reports if r.model)),
        findings=list(unique.values()),
        usage=usage,
        error=failed[0][0].error if failed else "",
        unreviewed=[file.path for _, shard in failed for file in shard.files],
    )
