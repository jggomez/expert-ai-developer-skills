"""Cost estimates."""

import pytest

from pr_reviewer.domain.models import ReviewUsage
from pr_reviewer.domain.pricing import estimate_cost


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        ("gemini-3.8-flash", 0.045),
        ("gemini-3.8-flash-experimental", None),
        ("claude-opus-5-5", 0.24),
    ],
)
def test_estimate_cost_uses_list_prices_and_admits_unknown_models(model: str, expected: float | None):
    # Arrange
    usage = ReviewUsage(input_tokens=40_000, output_tokens=4_000)

    # Act
    cost = estimate_cost(model, usage)

    # Assert
    assert cost == pytest.approx(expected) if expected else cost is None


def test_estimate_cost_applies_cached_rate():
    # Arrange
    usage = ReviewUsage(input_tokens=1_000_000, cached_input_tokens=1_000_000)

    # Act / Assert
    assert estimate_cost("gemini-3.8-flash", usage) == pytest.approx(0.075)
