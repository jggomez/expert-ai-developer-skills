"""Overview: KPI tiles, cost over time, cost by project and month, host comparison."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Final

from agent_meter.report.charts import (
    BarPoint,
    Segment,
    Series,
    StackColumn,
    bar_list,
    column_chart,
    money_scale,
    stacked_columns,
)
from agent_meter.report.data import ReportData, UsageRow
from agent_meter.report.fmt import (
    DASH,
    esc,
    format_cost,
    format_cost_compact,
    format_duration_ms,
    format_int,
    format_percent,
    format_tokens,
    host_label,
)
from agent_meter.report.html import (
    card,
    chart_card,
    cost_html,
    cost_td,
    kpi,
    num_td,
    section,
    table,
    text_td,
)
from agent_meter.report.series import (
    CATEGORICAL_SLOTS,
    OTHER_LABEL,
    OTHER_TONE,
    DayCost,
    assign_tones,
    cost_buckets,
)
from agent_meter.report.values import CostTotal, DisplayCurrency

__all__ = ["FLAG_FOOTNOTE", "render"]

FLAG_FOOTNOTE: Final = "* includes an inferred model or an estimated price"
API_EQUIVALENT_NOTE: Final = (
    "All costs are API-equivalent (≈): tokens × the public API price for the model on the "
    "call date. Subscription plans (Claude Pro/Max, Gemini plans) are not billed per token, "
    "so this is not what a subscriber actually paid."
)
_OTHER_KEY: Final = "(other)"
_NO_CALLS: Final = "no recorded calls"


def _value(total: CostTotal) -> Decimal:
    return total.cost_usd if total.cost_usd is not None else Decimal(0)


# ------------------------------------------------------------------ KPI tiles


def _month_tile(data: ReportData, display: DisplayCurrency | None) -> str:
    months = [row.key for row in data.by_month]
    if not months:
        return kpi("This month", esc(DASH), _NO_CALLS)
    current = data.options.generated_at.strftime("%Y-%m")
    label, key = ("This month", current) if current in months else ("Latest month", months[-1])
    rows = {row.key: row for row in data.by_month}
    index = months.index(key)
    sub = key
    if index > 0:
        sub += f" · previous {format_cost(rows[months[index - 1]].cost)}"
    return kpi(label, cost_html(rows[key].cost, display), sub)


def _token_tile(totals: UsageRow) -> str:
    parts = (
        totals.input_tokens,
        totals.output_tokens,
        totals.cache_write_tokens,
        totals.cache_read_tokens,
    )
    known = [part for part in parts if part is not None]
    total = sum(known) if known else None
    sub = (
        f"{format_tokens(totals.input_tokens)} in · "
        f"{format_tokens(totals.output_tokens)} out · "
        f"{format_tokens(totals.cache_read_tokens)} cache read"
    )
    return kpi("Tokens", esc(format_tokens(total)), sub)


def _kpis(data: ReportData, display: DisplayCurrency | None) -> str:
    totals = data.totals
    latency = data.latency_overall
    tiles = [
        kpi(
            "Total cost",
            cost_html(totals.cost, display, data.unpriced_models_in_scope),
            f"API-equivalent · {format_int(totals.calls)} calls",
            hero=True,
        ),
        _month_tile(data, display),
        _token_tile(totals),
        kpi(
            "Cache hit",
            esc(format_percent(totals.cache_hit_ratio)),
            "cache-read share of prompt tokens",
        ),
        kpi(
            "Tasks",
            esc(format_int(data.task_count)),
            f"{format_int(data.session_count)} sessions · "
            f"{format_percent(totals.error_rate)} call errors",
        ),
        kpi(
            "P95 task time",
            esc(format_duration_ms(latency.p95)),
            f"P50 {format_duration_ms(latency.p50)} · P99 {format_duration_ms(latency.p99)}",
        ),
    ]
    return f'<div class="kpis">{"".join(tiles)}</div>'


# --------------------------------------------------------------------- charts


def _cost_over_time(data: ReportData, display: DisplayCurrency | None) -> str:
    days = [
        DayCost(day=date.fromisoformat(row.key), cost=row.cost, calls=row.calls)
        for row in data.by_day
    ]
    title, buckets = cost_buckets(days)
    if not buckets:
        return ""
    points = [
        BarPoint(
            label=bucket.label,
            value=_value(bucket.cost) if bucket.cost is not None else Decimal(0),
            caption=format_cost(bucket.cost) if bucket.cost is not None else _NO_CALLS,
        )
        for bucket in buckets
    ]
    chart = column_chart(
        points, title=title, scale=money_scale(max(p.value for p in points))
    )
    rows = [
        "<tr>"
        + text_td(bucket.label)
        + num_td(format_int(bucket.calls), bucket.calls)
        + cost_td(bucket.cost, display)
        + "</tr>"
        for bucket in buckets
        if bucket.cost is not None
    ]
    first = data.by_day[0].key
    last = data.by_day[-1].key
    subtitle = f"{first} → {last} · peak labelled" if first != last else first
    return chart_card(
        title,
        subtitle,
        chart,
        table(["Day" if title.endswith("day") else "Week", "Calls", "Cost"], rows),
        wide=True,
    )


def _project_series(data: ReportData) -> tuple[list[Series], dict[str, str]]:
    """Legend series (top seven projects + Other) and each project's series key."""
    ranked = [row.key for row in data.by_project]
    ranked += sorted({r.key for r in data.by_project_month} - set(ranked))
    tones = assign_tones(ranked)
    labels = {row.key: row.label for row in data.by_project_month}
    labels.update({row.key: row.label for row in data.by_project})
    series = [
        Series(key=key, label=labels.get(key, key), tone=tones[key])
        for key in ranked[:CATEGORICAL_SLOTS]
    ]
    if len(ranked) > CATEGORICAL_SLOTS:
        series.append(Series(key=_OTHER_KEY, label=OTHER_LABEL, tone=OTHER_TONE))
    owner = {key: key if tones[key] != OTHER_TONE else _OTHER_KEY for key in ranked}
    return series, owner


def _month_column(
    month: str, rows: Sequence[tuple[str, CostTotal]], series: Sequence[Series]
) -> StackColumn:
    costs: dict[str, CostTotal] = {}
    for key, cost in rows:
        costs[key] = costs[key] + cost if key in costs else cost
    total = CostTotal(None)
    for cost in costs.values():
        total = total + cost
    segments = tuple(
        Segment(series=s.key, value=_value(costs[s.key]), caption=format_cost(costs[s.key]))
        for s in series
        if s.key in costs
    )
    return StackColumn(label=month, caption=format_cost_compact(total), segments=segments)


def _project_months(data: ReportData, display: DisplayCurrency | None) -> str:
    if not data.by_project_month:
        return ""
    series, owner = _project_series(data)
    months = sorted({row.local_month for row in data.by_project_month})
    columns = [
        _month_column(
            month,
            [
                (owner[row.key], row.cost)
                for row in data.by_project_month
                if row.local_month == month
            ],
            series,
        )
        for month in months
    ]
    maximum = max(sum((s.value for s in c.segments), Decimal(0)) for c in columns)
    chart = stacked_columns(
        columns, series, title="Cost by project and month", scale=money_scale(maximum)
    )
    ordered = sorted(
        data.by_project_month, key=lambda r: (r.local_month, -_value(r.cost), r.label)
    )
    rows = [
        "<tr>"
        + text_td(row.local_month)
        + text_td(row.label)
        + cost_td(row.cost, display)
        + "</tr>"
        for row in ordered
    ]
    subtitle = (
        f"Top {CATEGORICAL_SLOTS} projects by cost; the rest folded into Other"
        if any(s.key == _OTHER_KEY for s in series)
        else "Month totals on each column"
    )
    return chart_card(
        "Cost by project and month",
        subtitle,
        chart,
        table(["Month", "Project", "Cost"], rows),
        wide=True,
    )


def _host_points(data: ReportData) -> list[tuple[str, str]]:
    latency = {row.key: row.stats for row in data.latency_by_host}
    hosts = data.by_host
    p95 = [latency[h.key].p95 if h.key in latency else None for h in hosts]
    multiples = [
        (
            "Cost",
            bar_list(
                [
                    BarPoint(host_label(h.key), _value(h.cost), format_cost(h.cost))
                    for h in hosts
                ],
                title="Cost by host",
            ),
        ),
        (
            "Calls",
            bar_list(
                [
                    BarPoint(host_label(h.key), Decimal(h.calls), format_int(h.calls))
                    for h in hosts
                ],
                title="Calls by host",
            ),
        ),
        (
            "Cache hit",
            bar_list(
                [
                    BarPoint(
                        host_label(h.key),
                        h.cache_hit_ratio or Decimal(0),
                        format_percent(h.cache_hit_ratio),
                    )
                    for h in hosts
                ],
                title="Cache hit by host",
                top=Decimal(1),
            ),
        ),
        (
            "Task P95",
            bar_list(
                [
                    BarPoint(host_label(h.key), value or Decimal(0), format_duration_ms(value))
                    for h, value in zip(hosts, p95, strict=True)
                ],
                title="Task P95 by host",
            ),
        ),
    ]
    return multiples


def _host_table(data: ReportData, display: DisplayCurrency | None) -> str:
    latency = {row.key: row.stats for row in data.latency_by_host}
    body = []
    for row in data.by_host:
        stats = latency.get(row.key)
        p50 = stats.p50 if stats else None
        p95 = stats.p95 if stats else None
        body.append(
            "<tr>"
            + text_td(host_label(row.key))
            + num_td(format_int(row.calls), row.calls)
            + num_td(format_tokens(row.input_tokens), row.input_tokens)
            + num_td(format_tokens(row.output_tokens), row.output_tokens)
            + num_td(format_percent(row.cache_hit_ratio), row.cache_hit_ratio)
            + num_td(format_percent(row.error_rate), row.error_rate)
            + num_td(format_duration_ms(p50), p50)
            + num_td(format_duration_ms(p95), p95)
            + cost_td(row.cost, display)
            + "</tr>"
        )
    headers = [
        "Host",
        "Calls",
        "Input",
        "Output",
        "Cache hit",
        "Errors",
        "Task P50",
        "Task P95",
        "Cost",
    ]
    return table(headers, body)


def _hosts(data: ReportData, display: DisplayCurrency | None) -> str:
    if not data.by_host:
        return ""
    multiples = "".join(
        f'<div class="multiple"><h4>{esc(title)}</h4>{chart}</div>'
        for title, chart in _host_points(data)
    )
    return chart_card(
        "Claude Code vs Antigravity",
        "Per host: cost, calls, cache hit and task P95",
        f'<div class="multiples">{multiples}</div>',
        _host_table(data, display),
        wide=True,
    )


# --------------------------------------------------------------------- tables


def _usage_table(
    rows: Sequence[UsageRow],
    first: str,
    display: DisplayCurrency | None,
    *,
    with_client: bool = False,
) -> str:
    headers = [
        first,
        *(["Client"] if with_client else []),
        "Calls",
        "Input",
        "Output",
        "Cache read",
        "Cache hit",
        "Errors",
        "Cost",
    ]
    body = []
    for row in rows:
        cells = [text_td(row.label)]
        if with_client:
            cells.append(text_td(row.client or DASH))
        cells += [
            num_td(format_int(row.calls), row.calls),
            num_td(format_tokens(row.input_tokens), row.input_tokens),
            num_td(format_tokens(row.output_tokens), row.output_tokens),
            num_td(format_tokens(row.cache_read_tokens), row.cache_read_tokens),
            num_td(format_percent(row.cache_hit_ratio), row.cache_hit_ratio),
            num_td(format_percent(row.error_rate), row.error_rate),
            cost_td(row.cost, display),
        ]
        body.append(f"<tr>{''.join(cells)}</tr>")
    return table(headers, body)


def _breakdowns(data: ReportData, display: DisplayCurrency | None) -> str:
    more = "".join(
        f'<details class="breakdown"><summary>{esc(title)}</summary>{body}</details>'
        for title, body in (
            ("By client", _usage_table(data.by_client, "Client", display)),
            ("By month", _usage_table(data.by_month, "Month", display)),
            ("By model", _usage_table(data.by_model, "Model", display)),
        )
    )
    return card(
        "By project",
        _usage_table(data.by_project, "Project", display, with_client=True),
        more,
    )


def render(data: ReportData, display: DisplayCurrency | None) -> str:
    footnote = (
        f'<p class="footnote">{esc(FLAG_FOOTNOTE)}</p>' if data.totals.cost.flagged else ""
    )
    charts = "".join(
        (
            _cost_over_time(data, display),
            _project_months(data, display),
            _hosts(data, display),
        )
    )
    return section(
        "overview",
        "Overview",
        "Spend, volume and cache efficiency for the selected scope.",
        _kpis(data, display),
        footnote,
        f'<p class="note-line">{esc(API_EQUIVALENT_NOTE)}</p>',
        f'<div class="grid">{charts}</div>',
        _breakdowns(data, display),
    )
