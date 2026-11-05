"""Where to cut: the deterministic insights, first in the report because they lead to an action."""

from __future__ import annotations

from agent_meter.insights import OVERLAP_NOTE, Insight
from agent_meter.report.data import ReportData
from agent_meter.report.fmt import format_usd
from agent_meter.report.html import card, muted, section, table, text_td

__all__ = ["render"]


def _row(insight: Insight) -> str:
    saving = "—" if insight.saving_usd is None else f"≈ {format_usd(insight.saving_usd)}"
    return (
        "<tr>"
        + text_td(insight.title)
        + text_td(saving)
        + text_td(insight.saving_basis)
        + text_td(insight.action)
        + "</tr>"
    )


def render(data: ReportData) -> str:
    report = data.insights
    if report is None or not report.insights:
        return ""
    rows = table(["Finding", "Estimated saving", "How it is estimated", "Action"], (_row(i) for i in report.insights))
    return section(
        "where-to-cut",
        "Where to cut",
        f"Fixed rules over {report.date_from} → {report.date_to}. The findings are measured, the savings are estimates.",
        card("", rows, muted(OVERLAP_NOTE)),
    )
