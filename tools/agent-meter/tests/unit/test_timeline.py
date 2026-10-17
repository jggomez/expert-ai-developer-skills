"""Tests for the pure time metrics in ``agent_meter.timeline`` (ADR §3.6)."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from agent_meter.timeline import (
    RunSpan,
    active_intervals,
    critical_path,
    dev_hours,
    parallelism,
    retries,
    total_ms,
    union,
)

T0 = datetime(2026, 10, 16, 12, 0, 0, tzinfo=UTC)


def at(seconds: float) -> datetime:
    return T0 + timedelta(seconds=seconds)


def span(
    run_id: str, agent_type: str, start: float, end: float, active_s: float
) -> RunSpan:
    return RunSpan(
        agent_run_id=run_id,
        agent_type=agent_type,
        started_at=at(start),
        ended_at=at(end),
        active_ms=int(active_s * 1000),
    )


# --- union / total_ms -------------------------------------------------------------


def test_union_merges_overlapping_and_touching_intervals_and_sorts() -> None:
    intervals = [(at(50), at(60)), (at(0), at(10)), (at(5), at(20)), (at(20), at(30))]

    assert union(intervals) == [(at(0), at(30)), (at(50), at(60))]


def test_union_drops_empty_and_inverted_intervals() -> None:
    assert union([(at(5), at(5)), (at(9), at(3))]) == []


def test_total_ms_counts_overlap_once() -> None:
    assert total_ms([(at(0), at(10)), (at(5), at(15))]) == 15_000
    assert total_ms([]) == 0


# --- active_intervals (TK-03) ---------------------------------------------------------


def test_active_intervals_excludes_gaps_longer_than_threshold() -> None:
    events = [at(0), at(30), at(60), at(600), at(630)]

    result = active_intervals(events, idle_threshold_s=120)

    assert result == [(at(0), at(60)), (at(600), at(630))]
    assert total_ms(result) == 90_000


def test_active_intervals_gap_equal_to_threshold_is_active() -> None:
    assert active_intervals([at(0), at(120)], idle_threshold_s=120) == [
        (at(0), at(120))
    ]


def test_active_intervals_unsorted_events_and_extra_latency_intervals() -> None:
    events = [at(400), at(0), at(10)]
    extra = [(at(10), at(25)), (at(400), at(403))]

    result = active_intervals(events, idle_threshold_s=120, extra=extra)

    assert result == [(at(0), at(25)), (at(400), at(403))]


def test_active_intervals_single_event_is_zero_active_time() -> None:
    assert total_ms(active_intervals([at(0)], idle_threshold_s=120)) == 0


# --- critical path (TK-04) ------------------------------------------------------------


def test_critical_path_on_known_dag() -> None:
    runs = [
        span("pa", "product-analyst", 0, 100, 90),
        span("ae", "architect-engineer", 100, 200, 80),
        span("ci1", "code-implementer", 200, 500, 250),
        span("ci2", "code-implementer", 200, 400, 150),
        span("qa", "qa-tester", 500, 600, 60),
        span("cv", "compliance-verifier", 500, 560, 50),
    ]

    ms, path = critical_path(runs)

    assert path == [
        "product-analyst",
        "architect-engineer",
        "code-implementer",
        "qa-tester",
    ]
    assert ms == (90 + 80 + 250 + 60) * 1000


def test_critical_path_empty_and_single() -> None:
    assert critical_path([]) == (0, [])
    assert critical_path([span("m", "main", 0, 10, 7)]) == (7_000, ["main"])


def test_critical_path_tie_is_deterministic() -> None:
    runs = [span("b", "beta", 0, 10, 5), span("a", "alpha", 0, 10, 5)]

    assert critical_path(runs) == critical_path(list(reversed(runs)))


# --- retries (TK-05) ------------------------------------------------------------------


def test_code_implementer_after_failed_qa_counts_as_one_retry() -> None:
    runs = [
        span("m", "main", 0, 900, 100),
        span("ci1", "code-implementer", 10, 100, 80),
        span("qa", "qa-tester", 110, 200, 80),
        span("ci2", "code-implementer", 210, 300, 80),
    ]

    assert retries(runs) == (1, "qa-tester→code-implementer")


def test_retries_multiple_types_ordered_by_start() -> None:
    runs = [
        span("ci2", "code-implementer", 210, 300, 1),
        span("qa1", "qa-tester", 110, 200, 1),
        span("ci1", "code-implementer", 10, 100, 1),
        span("qa2", "qa-tester", 310, 400, 1),
    ]

    assert retries(runs) == (
        2,
        "qa-tester→code-implementer, code-implementer→qa-tester",
    )


def test_no_retries() -> None:
    assert retries([span("m", "main", 0, 1, 1)]) == (0, "")
    assert retries([]) == (0, "")


# --- parallelism (TK-02) --------------------------------------------------------------


def test_overlapping_runs_give_parallelism_above_one() -> None:
    run_a = active_intervals([at(0), at(60)], 120)
    run_b = active_intervals([at(30), at(90)], 120)
    task_active = total_ms(run_a + run_b)

    factor = parallelism([total_ms(run_a), total_ms(run_b)], task_active)

    assert factor == Decimal("1.33")
    assert factor is not None and factor > 1


def test_parallelism_none_for_single_run_or_zero_active() -> None:
    assert parallelism([1000], 1000) is None
    assert parallelism([0, 0], 0) is None


# --- dev hours (OQ-1) -----------------------------------------------------------------


def test_dev_hours_merges_small_gaps_and_splits_at_local_midnight() -> None:
    tz = ZoneInfo("America/Bogota")  # UTC-5, no DST
    # 23:00-23:30 local, then 23:45 -> 00:45 local next day (gap 15 min <= 30 → merged).
    s1 = datetime(2026, 10, 16, 23, 0, tzinfo=tz).astimezone(UTC)
    e1 = datetime(2026, 10, 16, 23, 30, tzinfo=tz).astimezone(UTC)
    s2 = datetime(2026, 10, 16, 23, 45, tzinfo=tz).astimezone(UTC)
    e2 = datetime(2026, 10, 17, 0, 45, tzinfo=tz).astimezone(UTC)
    # Far apart block on 17th: 10:00-10:20 (gap > 30 min → not merged).
    s3 = datetime(2026, 10, 17, 10, 0, tzinfo=tz).astimezone(UTC)
    e3 = datetime(2026, 10, 17, 10, 20, tzinfo=tz).astimezone(UTC)

    result = dev_hours([(s2, e2), (s1, e1), (s3, e3)], tz)

    assert result == {
        date(2026, 10, 16): Decimal("1.00"),
        date(2026, 10, 17): Decimal("1.08"),
    }


def test_dev_hours_union_of_overlapping_spans_across_hosts() -> None:
    tz = ZoneInfo("UTC")
    spans = [(at(0), at(3600)), (at(1800), at(5400))]

    assert dev_hours(spans, tz) == {date(2026, 10, 16): Decimal("1.50")}


def test_dev_hours_dst_day_uses_real_elapsed_time() -> None:
    tz = ZoneInfo("Europe/Madrid")  # clocks go back 03:00 → 02:00 on 2026-10-25
    start = datetime(2026, 10, 25, 0, 0, tzinfo=tz).astimezone(UTC)
    end = start + timedelta(hours=25)

    result = dev_hours([(start, end)], tz, merge_gap_s=0)

    assert result == {date(2026, 10, 25): Decimal("25.00")}


def test_dev_hours_empty() -> None:
    assert dev_hours([], ZoneInfo("UTC")) == {}
