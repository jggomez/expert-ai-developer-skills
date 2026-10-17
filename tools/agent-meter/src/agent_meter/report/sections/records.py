"""Sessions and Data quality: the record-level tables behind the charts."""

from __future__ import annotations

from collections.abc import Sequence

from agent_meter.report.data import (
    HealthRow,
    ReportData,
    SessionRow,
    UnpricedModelRow,
    UntrackedRow,
)
from agent_meter.report.fmt import (
    DASH,
    esc,
    format_duration_ms,
    format_int,
    format_percent,
    host_label,
)
from agent_meter.report.html import (
    card,
    cost_td,
    muted,
    num_td,
    section,
    table,
    td,
    text_td,
    timestamp,
)
from agent_meter.report.values import DisplayCurrency

__all__ = ["render_data_quality", "render_sessions"]


def _session_row(row: SessionRow, display: DisplayCurrency | None) -> str:
    return (
        "<tr>"
        + td(esc(row.local_date.isoformat()), sort=row.started_at.isoformat())
        + text_td(row.project_label)
        + text_td(host_label(row.host))
        + text_td(row.status)
        + num_td(format_duration_ms(row.wall_clock_ms), row.wall_clock_ms)
        + num_td(format_duration_ms(row.active_ms), row.active_ms)
        + num_td(format_int(row.tasks), row.tasks)
        + num_td(format_int(row.calls), row.calls)
        + num_td(format_percent(row.cache_hit_ratio), row.cache_hit_ratio)
        + num_td(format_duration_ms(row.task_p50_ms), row.task_p50_ms)
        + num_td(format_duration_ms(row.task_p95_ms), row.task_p95_ms)
        + cost_td(row.cost, display)
        + "</tr>"
    )


def render_sessions(data: ReportData, display: DisplayCurrency | None) -> str:
    headers = [
        "Date",
        "Project",
        "Host",
        "Status",
        "Wall-clock",
        "Active",
        "Tasks",
        "Calls",
        "Cache hit",
        "Task P50",
        "Task P95",
        "Cost",
    ]
    shown = f"Showing {len(data.sessions):,} most recent of {data.session_count:,} sessions."
    return section(
        "sessions",
        "Sessions",
        shown,
        card("", table(headers, (_session_row(row, display) for row in data.sessions))),
    )


def _health_row(row: HealthRow) -> str:
    earliest = (
        DASH if row.earliest_call_ts is None else row.earliest_call_ts.date().isoformat()
    )
    return (
        "<tr>"
        + text_td(host_label(row.host))
        + text_td(timestamp(row.last_ingested_at))
        + num_td(format_int(row.units), row.units)
        + num_td(format_int(row.unknown_formats), row.unknown_formats)
        + num_td(format_int(row.diagnostics_7d), row.diagnostics_7d)
        + text_td(earliest)
        + "</tr>"
    )


def _unpriced_models_table(rows: Sequence[UnpricedModelRow]) -> str:
    if not rows:
        return muted("All models are priced.")
    return table(
        ["Host", "Model", "Calls", "First seen", "Last seen"],
        (
            "<tr>"
            + text_td(host_label(row.host))
            + text_td(row.model)
            + num_td(format_int(row.calls), row.calls)
            + text_td(timestamp(row.first_ts))
            + text_td(timestamp(row.last_ts))
            + "</tr>"
            for row in rows
        ),
    )


def _untracked_table(rows: Sequence[UntrackedRow]) -> str:
    if not rows:
        return muted("No untracked history.")
    return table(
        ["Host", "Reason", "Conversations", "Observed from", "Observed to"],
        (
            "<tr>"
            + text_td(host_label(row.host))
            + text_td(row.reason)
            + num_td(format_int(row.conversations), row.conversations)
            + text_td(row.observed_from.isoformat() if row.observed_from else DASH)
            + text_td(row.observed_to.isoformat() if row.observed_to else DASH)
            + "</tr>"
            for row in rows
        ),
    )


def _health_table(rows: Sequence[HealthRow]) -> str:
    headers = [
        "Host",
        "Last ingest",
        "Units",
        "Unknown formats",
        "Diagnostics (7 d)",
        "Earliest call",
    ]
    return table(headers, (_health_row(row) for row in rows))


def render_data_quality(data: ReportData) -> str:
    totals = data.totals.cost
    return section(
        "data-quality",
        "Data quality",
        f"In this report: {totals.unpriced_calls:,} unpriced calls, "
        f"{totals.estimated_calls:,} with an estimated price, "
        f"{totals.inferred_calls:,} with an inferred model.",
        card("Unpriced models (store-wide)", _unpriced_models_table(data.unpriced_models)),
        card(
            "Untracked history",
            muted("Untracked conversations are never estimated and never shown as zero usage."),
            _untracked_table(data.untracked),
        ),
        card("Collection health", _health_table(data.health)),
    )
