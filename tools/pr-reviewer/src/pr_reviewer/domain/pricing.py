"""List prices used to report what a review cost. Checked on 2026-11-04."""

from __future__ import annotations

from typing import NamedTuple

from pr_reviewer.domain.models import ReviewUsage


class Price(NamedTuple):
    """USD per million tokens."""

    input: float
    output: float
    cached_input: float


PRICES: dict[str, Price] = {
    "gemini-3.8-flash": Price(0.75, 3.75, 0.075),
    "gemini-3.6-flash": Price(0.75, 3.75, 0.075),
    "gemini-3.5-flash-lite": Price(0.30, 2.50, 0.03),
    "gemini-3.1-flash-lite": Price(0.25, 1.50, 0.025),
    "claude-opus-5-5": Price(4.00, 20.00, 0.20),
    "claude-sonnet-5-5": Price(2.00, 10.00, 0.20),
}


def estimate_cost(model: str, usage: ReviewUsage) -> float | None:
    """Estimated USD cost, or None for a model without a known price."""
    price = PRICES.get(model)
    if price is None:
        return None
    uncached = max(usage.input_tokens - usage.cached_input_tokens, 0)
    total = uncached * price.input + usage.cached_input_tokens * price.cached_input + usage.output_tokens * price.output
    return total / 1_000_000
