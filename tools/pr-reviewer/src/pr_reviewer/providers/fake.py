"""Deterministic provider for tests and for trying the Action without an API key."""

from __future__ import annotations

from pathlib import Path

from pr_reviewer.models import ReviewResult, ReviewUsage
from pr_reviewer.providers.base import ProviderOutput, ReviewRequest


class FakeProvider:
    name = "fake"

    def __init__(self, findings_path: Path | None):
        self._findings_path = findings_path

    def review(self, request: ReviewRequest) -> ProviderOutput:
        result = ReviewResult()
        if self._findings_path is not None:
            result = ReviewResult.model_validate_json(self._findings_path.read_text(encoding="utf-8"))
        return ProviderOutput(result=result, usage=ReviewUsage(), model="fake")
