"""Contract every review provider implements."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from pr_reviewer.models import DiffBundle, ReviewResult, ReviewUsage

DEFAULT_MAX_TOKENS = 200_000


@dataclass(frozen=True)
class ReviewRequest:
    bundle: DiffBundle
    workspace: Path
    model: str | None = None
    max_tokens: int = DEFAULT_MAX_TOKENS


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
