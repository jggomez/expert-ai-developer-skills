"""Efficiency: cache hit rate, context size per call and output per task, by host."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import Decimal

from agent_meter.report.charts import BarPoint, bar_list
from agent_meter.report.data import EfficiencyRow, ReportData
from agent_meter.report.fmt import format_percent, format_token_average, host_label
from agent_meter.report.html import card, chart_card, num_td, section, table, text_td

__all__ = ["render"]

Metric = Callable[[EfficiencyRow], Decimal | None]


def _label(row: EfficiencyRow, *, hosts: bool) -> str:
    return host_label(row.label) if hosts else row.label


def _efficiency_table(first: str, rows: Sequence[EfficiencyRow], *, hosts: bool) -> str:
    return table(
        [first, "Cache hit", "Context / call", "Output / task", "Error rate"],
        (
            "<tr>"
            + text_td(_label(row, hosts=hosts))
            + num_td(format_percent(row.cache_hit_ratio), row.cache_hit_ratio)
            + num_td(format_token_average(row.avg_context_tokens), row.avg_context_tokens)
            + num_td(format_token_average(row.output_per_task), row.output_per_task)
            + num_td(format_percent(row.error_rate), row.error_rate)
            + "</tr>"
            for row in rows
        ),
    )


def _metric_card(
    title: str,
    subtitle: str,
    rows: Sequence[EfficiencyRow],
    metric: Metric,
    formatter: Callable[[Decimal | None], str],
    *,
    top: Decimal | None = None,
) -> str:
    points = [
        BarPoint(
            label=host_label(row.label),
            value=metric(row) or Decimal(0),
            caption=formatter(metric(row)),
        )
        for row in rows
    ]
    values = table(
        ["Host", title],
        (
            "<tr>" + text_td(p.label) + num_td(p.caption, metric(row)) + "</tr>"
            for p, row in zip(points, rows, strict=True)
        ),
    )
    return chart_card(title, subtitle, bar_list(points, title=title, top=top), values)


def render(data: ReportData) -> str:
    rows = data.efficiency_by_host
    charts = (
        _metric_card(
            "Cache hit rate",
            "Cache-read tokens ÷ prompt tokens · 0–100% scale",
            rows,
            lambda r: r.cache_hit_ratio,
            format_percent,
            top=Decimal(1),
        )
        + _metric_card(
            "Context per call",
            "Mean prompt tokens per call with known usage",
            rows,
            lambda r: r.avg_context_tokens,
            format_token_average,
        )
        + _metric_card(
            "Output per task",
            "Mean output tokens per task",
            rows,
            lambda r: r.output_per_task,
            format_token_average,
        )
        if rows
        else ""
    )
    return section(
        "efficiency",
        "Efficiency",
        "Cache hit = cache-read tokens ÷ prompt tokens (input + cache write + cache read). "
        "Context / call = mean prompt tokens per call with known usage.",
        f'<div class="grid grid-3">{charts}</div>',
        card("By host", _efficiency_table("Host", rows, hosts=True)),
        card(
            "By project",
            _efficiency_table("Project", data.efficiency_by_project, hosts=False),
        ),
    )
