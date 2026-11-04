"""A review always ends in a report, with the provider replaced by doubles."""

from pathlib import Path

import pytest

from pr_reviewer.application.ports import ProviderError, ProviderOutput, ReviewRequest
from pr_reviewer.application.run_review import (
    MAX_ERROR_CHARS,
    ReviewSettings,
    run_review,
)
from pr_reviewer.domain.models import DiffBundle, ReviewResult, ReviewUsage
from support.builders import bundle, finding

SETTINGS = ReviewSettings(provider="stub", model="stub-model", max_tokens=123)


class StubProvider:
    name = "stub"

    def __init__(self, error: Exception | None = None):
        self.error = error
        self.request: ReviewRequest | None = None

    def review(self, request: ReviewRequest) -> ProviderOutput:
        self.request = request
        if self.error:
            raise self.error
        result = ReviewResult(findings=[finding()])
        return ProviderOutput(result=result, usage=ReviewUsage(input_tokens=5), model="served-model")


def run(provider: StubProvider, workspace=lambda: Path("/clean")):
    return run_review(bundle(), SETTINGS, load_provider=lambda: provider, build_workspace=workspace)


def test_successful_review_carries_findings_usage_and_the_served_model():
    # Arrange
    provider = StubProvider()

    # Act
    report = run(provider)

    # Assert
    assert (report.status, report.model, report.usage.input_tokens) == ("ok", "served-model", 5)
    assert len(report.findings) == 1
    assert (provider.request.workspace, provider.request.model, provider.request.max_tokens) == (Path("/clean"), "stub-model", 123)


def test_nothing_to_review_never_creates_the_provider_or_the_workspace():
    # Arrange
    def fail():
        raise AssertionError("must not be called")

    empty = DiffBundle(base="a" * 40, head="b" * 40)

    # Act
    report = run_review(empty, SETTINGS, load_provider=fail, build_workspace=fail)

    # Assert
    assert (report.status, report.findings) == ("ok", [])


def test_provider_error_keeps_the_tokens_already_spent():
    # Arrange
    error = ProviderError("over budget", usage=ReviewUsage(input_tokens=9), model="m")

    # Act
    report = run(StubProvider(error))

    # Assert
    assert (report.status, report.model, report.usage.input_tokens, report.error) == ("failed", "m", 9, "over budget")


@pytest.mark.parametrize("stage", ["provider", "workspace"])
def test_unexpected_failures_become_a_failed_report(stage: str):
    # Arrange
    def boom():
        raise OSError("disk full")

    provider = StubProvider(OSError("disk full")) if stage == "provider" else StubProvider()
    workspace = boom if stage == "workspace" else (lambda: Path("/clean"))

    # Act
    report = run(provider, workspace)

    # Assert
    assert report.status == "failed"
    assert report.error == "OSError: disk full"


def test_long_error_text_is_clipped():
    # Act
    report = run(StubProvider(RuntimeError("x" * 5000)))

    # Assert
    assert len(report.error) == MAX_ERROR_CHARS
