"""What the use cases need from the outside world."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pr_reviewer.domain.findings import Selection
from pr_reviewer.domain.models import (
    DiffBundle,
    Finding,
    ReviewReport,
    ReviewResult,
    ReviewUsage,
)

DEFAULT_MAX_TOKENS = 200_000
DEFAULT_BUDGET_USD = "1.00"


@dataclass(frozen=True)
class ReviewRequest:
    bundle: DiffBundle
    workspace: Path
    model: str | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS
    budget_usd: str = DEFAULT_BUDGET_USD
    rubric: str | None = None


@dataclass(frozen=True)
class ProviderOutput:
    result: ReviewResult
    usage: ReviewUsage
    model: str


class ProviderError(RuntimeError):
    """The review did not finish. `usage` keeps the tokens already spent."""

    def __init__(self, message: str, *, usage: ReviewUsage | None = None, model: str = ""):
        super().__init__(message)
        self.usage = usage or ReviewUsage()
        self.model = model


class ReviewProvider(Protocol):
    name: str

    def review(self, request: ReviewRequest) -> ProviderOutput:
        """Run the review. Raises ProviderError when it cannot finish."""
        ...


class DiffReader(Protocol):
    def read(self, base: str, head: str) -> str:
        """Return the unified diff between two commits."""
        ...


@dataclass(frozen=True)
class ReviewOutcome:
    """Everything needed to report a finished review."""

    report: ReviewReport
    bundle: DiffBundle
    selection: Selection
    inline_posted: int = 0
    already_posted: int = 0
    inline_rejected: bool = False


class PullRequestGateway(Protocol):
    def posted_fingerprints(self) -> set[str]:
        """Fingerprints of the findings already published on this pull request."""
        ...

    def post_inline_review(self, commit: str, findings: list[Finding]) -> bool:
        """Publish inline comments. Returns False when the platform rejects them."""
        ...

    def upsert_summary(self, outcome: ReviewOutcome) -> None:
        """Create or update the single summary comment."""
        ...
