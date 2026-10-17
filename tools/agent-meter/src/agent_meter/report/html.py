"""HTML building blocks shared by the report sections.

Every helper takes *already escaped* HTML for its ``content`` / ``body`` arguments and
escapes the plain-text arguments (titles, labels) itself.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final

from agent_meter.report.fmt import DASH, esc, format_cost, unpriced_note
from agent_meter.report.values import CostTotal, DisplayCurrency

__all__ = [
    "callout",
    "card",
    "chart_card",
    "cost_html",
    "cost_td",
    "h3",
    "kpi",
    "muted",
    "num_td",
    "section",
    "table",
    "table_view",
    "td",
    "text_td",
    "timestamp",
]

_ICONS: Final = {
    "warning": (
        '<svg class="callout-icon" aria-hidden="true" viewBox="0 0 20 20" focusable="false">'
        '<path class="icon-fill" d="M10 2.2 18.6 17.3a.8.8 0 0 1-.7 1.2H2.1a.8.8 0 0 1-.7-1.2Z"/>'
        '<path class="icon-ink" d="M10 7.4v5"/><circle class="icon-dot" cx="10" cy="15.2" r="1.05"/>'
        "</svg>"
    ),
    "info": (
        '<svg class="callout-icon" aria-hidden="true" viewBox="0 0 20 20" focusable="false">'
        '<circle class="icon-ring" cx="10" cy="10" r="8"/>'
        '<path class="icon-ink" d="M10 9v5"/><circle class="icon-dot" cx="10" cy="6.2" r="1.05"/>'
        "</svg>"
    ),
}


def _sort_key(value: Decimal | int | str | None) -> str:
    return "" if value is None else str(value)


def td(content: str, *, sort: Decimal | int | str | None = None, num: bool = False) -> str:
    """A cell; ``content`` must already be escaped HTML."""
    cls = ' class="num"' if num else ""
    data = f' data-sort="{esc(_sort_key(sort))}"' if sort is not None else ""
    return f"<td{cls}{data}>{content}</td>"


def text_td(text: str) -> str:
    return td(esc(text))


def num_td(text: str, sort: Decimal | int | None) -> str:
    return td(esc(text), sort=sort if sort is not None else "", num=True)


def cost_html(
    total: CostTotal, display: DisplayCurrency | None, models: Sequence[str] = ()
) -> str:
    note = unpriced_note(total, models)
    note_html = f' <span class="note">{esc(note)}</span>' if note else ""
    return f"{esc(format_cost(total, display))}{note_html}"


def cost_td(total: CostTotal, display: DisplayCurrency | None) -> str:
    sort = total.cost_usd if total.cost_usd is not None else Decimal(-1)
    return td(cost_html(total, display), sort=sort, num=True)


def timestamp(value: datetime | None) -> str:
    return DASH if value is None else value.astimezone(UTC).strftime("%Y-%m-%d %H:%M UTC")


def table(headers: Sequence[str], rows: Iterable[str], *, table_id: str = "") -> str:
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    ident = f' id="{esc(table_id)}"' if table_id else ""
    return (
        f'<div class="table-wrap"><table class="sortable"{ident}><thead><tr>{head}</tr>'
        f"</thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


def table_view(table_html: str) -> str:
    """The accessible twin of a chart, collapsed under a toggle."""
    return (
        '<details class="table-view"><summary>Table view</summary>'
        f"{table_html}</details>"
    )


def section(section_id: str, title: str, subtitle: str, *parts: str) -> str:
    sub = f'<p class="section-sub">{esc(subtitle)}</p>' if subtitle else ""
    return (
        f'<section id="{esc(section_id)}" class="section">'
        f'<div class="section-head"><h2>{esc(title)}</h2>{sub}</div>{"".join(parts)}</section>'
    )


def h3(title: str) -> str:
    return f"<h3>{esc(title)}</h3>"


def muted(text: str) -> str:
    return f'<p class="muted">{esc(text)}</p>'


def _size(wide: bool) -> str:
    return ' data-size="wide"' if wide else ""


def card(title: str, *parts: str, wide: bool = True, extra_class: str = "") -> str:
    classes = f"card {extra_class}" if extra_class else "card"
    heading = f'<h3 class="card-title">{esc(title)}</h3>' if title else ""
    return f'<div class="{classes}"{_size(wide)}>{heading}{"".join(parts)}</div>'


def chart_card(
    title: str, subtitle: str, chart_html: str, table_html: str, *, wide: bool = False
) -> str:
    """A ``<figure>`` holding one chart (or small multiples) and its table view."""
    sub = f'<span class="card-sub">{esc(subtitle)}</span>' if subtitle else ""
    return (
        f'<figure class="card chart-card"{_size(wide)}><figcaption>'
        f'<span class="card-title">{esc(title)}</span>{sub}</figcaption>'
        f"{chart_html}{table_view(table_html)}</figure>"
    )


def kpi(label: str, value_html: str, sub: str = "", *, hero: bool = False) -> str:
    """A stat tile: label, value (escaped HTML) and an optional plain-text sub line."""
    classes = "kpi kpi-hero" if hero else "kpi"
    sub_html = f'<span class="kpi-sub">{esc(sub)}</span>' if sub else ""
    return (
        f'<div class="{classes}"><span class="kpi-label">{esc(label)}</span>'
        f'<span class="kpi-value">{value_html}</span>{sub_html}</div>'
    )


def callout(kind: str, label: str, text: str) -> str:
    """A calm notice: status icon + label, never colour alone (``warning`` / ``info``)."""
    return (
        f'<div class="callout callout-{esc(kind)}" role="note">{_ICONS[kind]}'
        f'<div class="callout-body"><strong class="callout-label">{esc(label)}</strong>'
        f"<p>{esc(text)}</p></div></div>"
    )
