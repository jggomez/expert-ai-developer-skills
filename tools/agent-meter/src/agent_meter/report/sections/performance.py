"""Performance: task latency percentiles (P50/P95/P99) per host and per project (SM-05).

The three percentiles are ordered, so they wear the one-hue ordinal ramp (``o1``..``o3``)
rather than categorical hues.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Final

from agent_meter.report.charts import (
    BarGroup,
    Segment,
    Series,
    duration_scale,
    grouped_bars,
)
from agent_meter.report.data import LatencyRow, ReportData
from agent_meter.report.fmt import esc, format_duration_ms, format_int, host_label
from agent_meter.report.html import (
    card,
    chart_card,
    kpi,
    num_td,
    section,
    table,
    text_td,
)
from agent_meter.report.stats import LatencyStats

__all__ = ["render"]

_PERCENTILES: Final = (
    Series(key="p50", label="P50", tone="o1"),
    Series(key="p95", label="P95", tone="o2"),
    Series(key="p99", label="P99", tone="o3"),
)
_MAX_PROJECT_GROUPS: Final = 8


def _latency_cells(stats: LatencyStats) -> str:
    return (
        num_td(format_int(stats.tasks), stats.tasks)
        + num_td(format_duration_ms(stats.p50), stats.p50)
        + num_td(format_duration_ms(stats.p95), stats.p95)
        + num_td(format_duration_ms(stats.p99), stats.p99)
    )


def _label(row: LatencyRow, *, hosts: bool) -> str:
    return host_label(row.label) if hosts else row.label


def _latency_table(first: str, rows: Sequence[LatencyRow], *, hosts: bool) -> str:
    return table(
        [first, "Tasks", "P50", "P95", "P99"],
        (
            "<tr>" + text_td(_label(row, hosts=hosts)) + _latency_cells(row.stats) + "</tr>"
            for row in rows
        ),
    )


def _group(row: LatencyRow, *, hosts: bool) -> BarGroup:
    stats = row.stats
    values = tuple(
        Segment(series=key, value=value or Decimal(0), caption=format_duration_ms(value))
        for key, value in (("p50", stats.p50), ("p95", stats.p95), ("p99", stats.p99))
    )
    noun = "task" if stats.tasks == 1 else "tasks"
    return BarGroup(
        label=_label(row, hosts=hosts),
        note=f"P95 {format_duration_ms(stats.p95)} · {stats.tasks:,} {noun}",
        values=values,
    )


def _latency_card(
    title: str, subtitle: str, rows: Sequence[LatencyRow], *, hosts: bool, first: str
) -> str:
    finished = [row for row in rows if row.stats.tasks > 0]
    if not finished:
        return ""
    shown = finished if hosts else finished[:_MAX_PROJECT_GROUPS]
    maximum = max(
        (v for row in shown for v in (row.stats.p99, row.stats.p95, row.stats.p50) if v is not None),
        default=Decimal(0),
    )
    chart = grouped_bars(
        [_group(row, hosts=hosts) for row in shown],
        list(_PERCENTILES),
        title=title,
        scale=duration_scale(maximum),
    )
    return chart_card(title, subtitle, chart, _latency_table(first, rows, hosts=hosts))


def _monthly(data: ReportData) -> str:
    return card(
        "By month",
        table(
            ["Month", "Project", "Host", "Tasks", "P50", "P95", "P99"],
            (
                "<tr>"
                + text_td(row.local_month)
                + text_td(row.project_label)
                + text_td(host_label(row.host))
                + _latency_cells(LatencyStats(row.tasks, row.p50_ms, row.p95_ms, row.p99_ms))
                + "</tr>"
                for row in data.latency_monthly
            ),
        ),
    )


def render(data: ReportData) -> str:
    overall = data.latency_overall
    kpis = "".join(
        [
            kpi("Finished tasks", esc(format_int(overall.tasks))),
            kpi("P50", esc(format_duration_ms(overall.p50))),
            kpi("P95", esc(format_duration_ms(overall.p95))),
            kpi("P99", esc(format_duration_ms(overall.p99))),
        ]
    )
    charts = _latency_card(
        "Task latency by host",
        "P95 labelled; hover or open the table for P50 and P99",
        data.latency_by_host,
        hosts=True,
        first="Host",
    ) + _latency_card(
        "Task latency by project",
        f"Up to {_MAX_PROJECT_GROUPS} projects with the most finished tasks",
        data.latency_by_project,
        hosts=False,
        first="Project",
    )
    return section(
        "performance",
        "Performance",
        "Task latency percentiles over finished tasks (in-progress tasks excluded).",
        f'<div class="kpis kpis-compact">{kpis}</div>',
        f'<div class="grid">{charts}</div>',
        _monthly(data),
    )
