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
from pr_reviewer.domain.models import DiffBundle, ReviewReport

logger = logging.getLogger(__name__)

MAX_ERROR_CHARS = 300


@dataclass(frozen=True)
class ReviewSettings:
    provider: str
    model: str | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS
    budget_usd: str = DEFAULT_BUDGET_USD


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
