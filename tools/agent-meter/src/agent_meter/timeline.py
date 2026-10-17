"""Host-independent, pure time metrics (ADR §3.6, contracts §3.3).

All datetimes are timezone-aware. Durations are computed on absolute instants
(converted to UTC before subtracting) so DST transitions never distort them.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_UP, Decimal
from itertools import pairwise
from zoneinfo import ZoneInfo

__all__ = [
    "Interval",
    "RunSpan",
    "active_intervals",
    "critical_path",
    "dev_hours",
    "parallelism",
    "retries",
    "total_ms",
    "union",
]

Interval = tuple[datetime, datetime]

_TWO_PLACES = Decimal("0.01")
_MICROS_PER_HOUR = Decimal(3_600_000_000)


@dataclass(frozen=True, slots=True)
class RunSpan:
    agent_run_id: str
    agent_type: str
    started_at: datetime
    ended_at: datetime
    active_ms: int


def _ms(delta: timedelta) -> int:
    return delta // timedelta(milliseconds=1)


def union(intervals: Iterable[Interval]) -> list[Interval]:
    """Merge overlapping or touching intervals; empty or inverted intervals are dropped."""
    ordered = sorted((s, e) for s, e in intervals if e > s)
    merged: list[Interval] = []
    for start, end in ordered:
        if merged and start <= merged[-1][1]:
            if end > merged[-1][1]:
                merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def total_ms(intervals: Iterable[Interval]) -> int:
    """Milliseconds covered by the union of ``intervals`` (overlaps count once)."""
    return sum(_ms(end - start) for start, end in union(intervals))


def active_intervals(
    events: Sequence[datetime], idle_threshold_s: int, extra: Sequence[Interval] = ()
) -> list[Interval]:
    """Active time of one run: consecutive events at most ``idle_threshold_s`` apart.

    ``extra`` intervals (e.g. Antigravity call latency ``[ts, ts + latency]``) are
    always active. The result is a sorted, non-overlapping interval list.
    """
    threshold = timedelta(seconds=idle_threshold_s)
    ordered = sorted(events)
    segments: list[Interval] = [
        (prev, cur) for prev, cur in pairwise(ordered) if cur - prev <= threshold
    ]
    return union([*segments, *extra])


def critical_path(runs: Sequence[RunSpan]) -> tuple[int, list[str]]:
    """Longest chain of runs with ``a.ended_at <= b.started_at``, weighted by ``active_ms``.

    O(n²) dynamic programming; ties resolve deterministically by
    ``(started_at, ended_at, agent_run_id)`` order.
    """
    if not runs:
        return 0, []
    ordered = sorted(runs, key=lambda r: (r.started_at, r.ended_at, r.agent_run_id))
    best: list[int] = []
    previous: list[int | None] = []
    for index, run in enumerate(ordered):
        best_weight, best_prev = run.active_ms, None
        for candidate in range(index):
            if ordered[candidate].ended_at <= run.started_at:
                weight = best[candidate] + run.active_ms
                if weight > best_weight:
                    best_weight, best_prev = weight, candidate
        best.append(best_weight)
        previous.append(best_prev)
    end_index = max(range(len(ordered)), key=lambda i: (best[i], -i))
    chain: list[str] = []
    cursor: int | None = end_index
    while cursor is not None:
        chain.append(ordered[cursor].agent_type)
        cursor = previous[cursor]
    chain.reverse()
    return best[end_index], chain


def retries(runs: Sequence[RunSpan]) -> tuple[int, str]:
    """BR-13: each second-or-later run of an ``agent_type`` is a retry.

    The summary lists ``"<previous agent_type>→<agent_type>"`` in start order, where the
    previous type is the run that started immediately before the retried run.
    """
    ordered = sorted(runs, key=lambda r: (r.started_at, r.ended_at, r.agent_run_id))
    seen: Counter[str] = Counter()
    transitions: list[str] = []
    for index, run in enumerate(ordered):
        if seen[run.agent_type] and index > 0:
            transitions.append(f"{ordered[index - 1].agent_type}→{run.agent_type}")
        seen[run.agent_type] += 1
    return len(transitions), ", ".join(transitions)


def _merge_with_gap(spans: Iterable[Interval], merge_gap: timedelta) -> list[Interval]:
    merged: list[Interval] = []
    for start, end in union(spans):
        if merged and start - merged[-1][1] <= merge_gap:
            merged[-1] = (merged[-1][0], end)
        else:
            merged.append((start, end))
    return merged


def _local_midnight_after(instant: datetime, tz: ZoneInfo) -> datetime:
    local_day = instant.astimezone(tz).date()
    return datetime.combine(
        local_day + timedelta(days=1), time(0), tzinfo=tz
    ).astimezone(UTC)


def dev_hours(
    spans: Sequence[Interval], tz: ZoneInfo, merge_gap_s: int = 1800
) -> dict[date, Decimal]:
    """Derived developer hours per local day (OQ-1), rounded half-up to 2 decimals.

    Spans are united, blocks separated by at most ``merge_gap_s`` are merged (the gap
    counts as worked time), and each block is split at local midnight.
    """
    micros_per_day: Counter[date] = Counter()
    for start, end in _merge_with_gap(spans, timedelta(seconds=merge_gap_s)):
        cursor = start.astimezone(UTC)
        stop = end.astimezone(UTC)
        while cursor < stop:
            boundary = min(_local_midnight_after(cursor, tz), stop)
            micros_per_day[cursor.astimezone(tz).date()] += (
                boundary - cursor
            ) // timedelta(microseconds=1)
            cursor = boundary
    return {
        day: (Decimal(micros) / _MICROS_PER_HOUR).quantize(
            _TWO_PLACES, rounding=ROUND_HALF_UP
        )
        for day, micros in sorted(micros_per_day.items())
    }


def parallelism(run_active_ms: Sequence[int], task_active_ms: int) -> Decimal | None:
    """Σ run active time ÷ task active time (2 dp); ``None`` for < 2 runs or zero time."""
    if len(run_active_ms) < 2 or task_active_ms <= 0:
        return None
    return (Decimal(sum(run_active_ms)) / Decimal(task_active_ms)).quantize(
        _TWO_PLACES, rounding=ROUND_HALF_UP
    )
