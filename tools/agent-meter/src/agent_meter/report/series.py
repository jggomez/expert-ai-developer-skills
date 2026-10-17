"""Shape report rows into chart series: tone assignment, top-N folding, time buckets.

Colour follows the entity, not its row number: tones are assigned once per chart from
a cost ranking, in the fixed categorical order (CVD-safe adjacency), and the tail past
seven slots folds into a neutral "Other" instead of cycling hues.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Final

from agent_meter.report.values import CostTotal

__all__ = [
    "CATEGORICAL_SLOTS",
    "DAILY_SPAN_LIMIT",
    "OTHER_LABEL",
    "OTHER_TONE",
    "DayCost",
    "TimeBucket",
    "assign_tones",
    "cost_buckets",
]

CATEGORICAL_SLOTS: Final = 7
OTHER_TONE: Final = "s-other"
OTHER_LABEL: Final = "Other"
DAILY_SPAN_LIMIT: Final = 62  # longer ranges are bucketed by ISO week


def assign_tones(ranked_keys: Sequence[str]) -> dict[str, str]:
    """``s1``..``s7`` in rank order; every key past the seventh shares ``s-other``."""
    return {
        key: f"s{index + 1}" if index < CATEGORICAL_SLOTS else OTHER_TONE
        for index, key in enumerate(ranked_keys)
    }


@dataclass(frozen=True, slots=True)
class TimeBucket:
    label: str
    cost: CostTotal | None  # None: no recorded calls in the bucket
    calls: int


@dataclass(frozen=True, slots=True)
class DayCost:
    day: date
    cost: CostTotal
    calls: int


def _combine(costs: Sequence[DayCost]) -> TimeBucket | None:
    if not costs:
        return None
    total = costs[0].cost
    for item in costs[1:]:
        total = total + item.cost
    return TimeBucket(label="", cost=total, calls=sum(item.calls for item in costs))


def cost_buckets(days: Sequence[DayCost]) -> tuple[str, tuple[TimeBucket, ...]]:
    """Daily buckets over the covered span (gaps included), weekly past 62 days."""
    if not days:
        return "Cost per day", ()
    by_day = {item.day: item for item in days}
    first, last = min(by_day), max(by_day)
    if (last - first).days + 1 <= DAILY_SPAN_LIMIT:
        buckets = []
        for offset in range((last - first).days + 1):
            day = first + timedelta(days=offset)
            item = by_day.get(day)
            buckets.append(
                TimeBucket(
                    label=day.isoformat(),
                    cost=item.cost if item is not None else None,
                    calls=item.calls if item is not None else 0,
                )
            )
        return "Cost per day", tuple(buckets)
    week = first - timedelta(days=first.weekday())
    weekly = []
    while week <= last:
        members = [
            by_day[d]
            for d in (week + timedelta(days=i) for i in range(7))
            if d in by_day
        ]
        combined = _combine(members)
        weekly.append(
            TimeBucket(
                label=f"Week of {week.isoformat()}",
                cost=combined.cost if combined is not None else None,
                calls=combined.calls if combined is not None else 0,
            )
        )
        week += timedelta(days=7)
    return "Cost per week", tuple(weekly)
