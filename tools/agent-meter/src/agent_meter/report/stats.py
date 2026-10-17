"""Exact percentile arithmetic for task latency (SM-05).

``percentile_cont`` uses the same linear interpolation as DuckDB ``quantile_cont`` and
BigQuery ``PERCENTILE_CONT``, carried out in ``Decimal`` so the result is deterministic.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

__all__ = ["LatencyStats", "latency_stats", "percentile_cont"]

_P50: Final = Decimal("0.50")
_P95: Final = Decimal("0.95")
_P99: Final = Decimal("0.99")


def percentile_cont(
    values: Sequence[int | Decimal], fraction: Decimal
) -> Decimal | None:
    """Continuous percentile with linear interpolation; ``None`` for no values."""
    if not Decimal(0) <= fraction <= Decimal(1):
        raise ValueError(f"fraction must be within [0, 1], got {fraction}")
    if not values:
        return None
    ordered = sorted(Decimal(v) for v in values)
    position = fraction * (len(ordered) - 1)
    lower = int(position)
    if lower + 1 >= len(ordered):
        return ordered[lower]
    weight = position - lower
    return ordered[lower] + (ordered[lower + 1] - ordered[lower]) * weight


@dataclass(frozen=True, slots=True)
class LatencyStats:
    tasks: int
    p50: Decimal | None
    p95: Decimal | None
    p99: Decimal | None


def latency_stats(values: Sequence[int | Decimal]) -> LatencyStats:
    return LatencyStats(
        tasks=len(values),
        p50=percentile_cont(values, _P50),
        p95=percentile_cont(values, _P95),
        p99=percentile_cont(values, _P99),
    )
