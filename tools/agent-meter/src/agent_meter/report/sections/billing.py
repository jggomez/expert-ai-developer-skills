"""Billing: AI cost against billable value per client month, where a rate exists."""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Final

from agent_meter.report.charts import (
    BarGroup,
    Segment,
    Series,
    grouped_bars,
    money_scale,
)
from agent_meter.report.data import BillableRow, ReportData
from agent_meter.report.fmt import (
    DASH,
    esc,
    format_amount,
    format_cost,
    format_currency,
    format_percent,
    format_usd,
)
from agent_meter.report.html import (
    card,
    chart_card,
    cost_td,
    muted,
    num_td,
    section,
    table,
    text_td,
)
from agent_meter.report.values import DisplayCurrency

__all__ = ["render"]

_SERIES: Final = (
    Series(key="cost", label="AI cost", tone="s1"),
    Series(key="billable", label="Billable (USD)", tone="s2"),
)
_TITLE: Final = "Projects & clients"
_SUBTITLE: Final = (
    "Hourly: AI cost ÷ (rate × dev hours). Fixed: cumulative AI cost ÷ fixed price."
)


def _ratio_text(row: BillableRow) -> str:
    ratio = format_percent(row.ai_cost_ratio)
    if row.ai_cost_ratio is not None and row.cost.partial:
        ratio = f"≥ {ratio}"
    return ratio


def _billable_row(row: BillableRow, display: DisplayCurrency | None) -> str:
    billable = (
        format_currency(row.billable_value, row.rate_currency)
        if row.billable_value is not None and row.rate_currency is not None
        else DASH
    )
    hours = DASH if row.dev_hours is None else f"{format_amount(row.dev_hours, 1)} h"
    return (
        f'<tr data-project="{esc(row.project_id)}">'
        + text_td(row.local_month)
        + text_td(row.client or DASH)
        + text_td(row.project_label)
        + text_td(row.billing_model or DASH)
        + cost_td(row.cost, display)
        + num_td(hours, row.dev_hours)
        + num_td(billable, row.billable_value)
        + num_td(
            DASH if row.billable_usd is None else format_usd(row.billable_usd),
            row.billable_usd,
        )
        + num_td(_ratio_text(row), row.ai_cost_ratio)
        + "</tr>"
    )


def _comparison(rows: Sequence[BillableRow], display: DisplayCurrency | None) -> str:
    rated = [row for row in rows if row.billable_usd is not None]
    if not rated:
        return card(
            "",
            muted(
                "No billable rate in USD for these client months, so cost cannot be "
                "compared with billable value. Set a rate with agent-meter projects set."
            ),
            extra_class="card-empty",
        )
    groups = []
    for row in rated:
        billable = row.billable_usd if row.billable_usd is not None else Decimal(0)
        cost = row.cost.cost_usd if row.cost.cost_usd is not None else Decimal(0)
        groups.append(
            BarGroup(
                label=f"{row.local_month} · {row.project_label}",
                note=f"AI cost = {_ratio_text(row)} of billable",
                values=(
                    Segment("cost", cost, format_cost(row.cost)),
                    Segment("billable", billable, format_usd(billable)),
                ),
            )
        )
    maximum = max(max(v.value for v in g.values) for g in groups)
    chart = grouped_bars(
        groups, list(_SERIES), title="AI cost vs billable", scale=money_scale(maximum)
    )
    view = table(
        ["Month", "Project", "AI cost", "Billable (USD)", "AI cost / billable"],
        (
            "<tr>"
            + text_td(row.local_month)
            + text_td(row.project_label)
            + cost_td(row.cost, display)
            + num_td(
                format_usd(row.billable_usd) if row.billable_usd is not None else DASH,
                row.billable_usd,
            )
            + num_td(_ratio_text(row), row.ai_cost_ratio)
            + "</tr>"
            for row in rated
        ),
    )
    return chart_card(
        "AI cost vs billable",
        "Client months with a rate in USD (or convertible via the display currency)",
        chart,
        view,
        wide=True,
    )


def render(data: ReportData, display: DisplayCurrency | None) -> str:
    if not data.billable:
        return section(
            "billing",
            "Billing",
            _TITLE,
            card(
                "",
                muted(
                    "No client months in range. Set clients and rates with "
                    "agent-meter projects set."
                ),
                extra_class="card-empty",
            ),
        )
    headers = [
        "Month",
        "Client",
        "Project",
        "Billing",
        "AI cost",
        "Dev hours",
        "Billable",
        "Billable (USD)",
        "AI cost / billable",
    ]
    return section(
        "billing",
        "Billing",
        f"{_TITLE} · {_SUBTITLE} A project without a client or rate shows —.",
        f'<div class="grid">{_comparison(data.billable, display)}</div>',
        card(
            "Client months",
            table(headers, (_billable_row(row, display) for row in data.billable)),
        ),
    )
