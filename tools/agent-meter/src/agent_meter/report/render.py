"""Render :class:`ReportData` into one self-contained HTML page (ADR §3.12).

Rules enforced here:
- every text value goes through :func:`esc`; numbers are formatted by :mod:`fmt`;
- CSS and JS are inlined from package files and charts are plain HTML marks, so the
  page has no ``http(s)://`` reference at all (SM-04) and works offline;
- task labels are never rendered (BR-16): tasks are identified as ``task #<seq>``.

The page is a light-first dashboard: a sticky top bar (title, period, filter summary,
theme toggle, section nav), calm notice callouts, then one section per topic.
"""

from __future__ import annotations

from functools import cache
from importlib.resources import files
from typing import Final

from agent_meter.report.data import ReportData
from agent_meter.report.fmt import esc, host_label, script_json
from agent_meter.report.html import callout, timestamp
from agent_meter.report.sections import (
    billing,
    efficiency,
    overview,
    performance,
    records,
    tasks,
)

__all__ = ["FLAG_FOOTNOTE", "render_report"]

REPORT_FORMAT_VERSION: Final = 1
FLAG_FOOTNOTE: Final = overview.FLAG_FOOTNOTE
_NAV: Final = (
    ("overview", "Overview"),
    ("tasks", "Tasks & agents"),
    ("performance", "Performance"),
    ("efficiency", "Efficiency"),
    ("billing", "Billing"),
    ("sessions", "Sessions"),
    ("data-quality", "Data quality"),
)


@cache
def _asset(name: str) -> str:
    return (files("agent_meter.report") / "assets" / name).read_text(encoding="utf-8")


def _chip(key: str, value: str) -> str:
    return f'<span class="chip"><span class="chip-key">{esc(key)}</span>{esc(value)}</span>'


def _period(data: ReportData) -> str:
    if not data.by_day:
        return ""
    first, last = data.by_day[0].key, data.by_day[-1].key
    return first if first == last else f"{first} → {last}"


def _topbar(data: ReportData, *, with_nav: bool) -> str:
    period = _period(data)
    chips = (_chip("Period", period) if period else "") + _chip("Scope", data.scope_label)
    display = data.options.display()
    if display is not None:
        chips += _chip("Currency", f"USD + {display.code}")
    nav = ""
    if with_nav:
        links = "".join(f'<a href="#{key}">{esc(label)}</a>' for key, label in _NAV)
        nav = f'<nav class="tabs" aria-label="Report sections">{links}</nav>'
    generated = timestamp(data.options.generated_at_utc)
    return (
        '<header class="topbar"><div class="topbar-inner">'
        '<div class="brand"><span class="brand-mark" aria-hidden="true"></span>'
        '<div class="brand-text"><h1>agent-meter</h1>'
        '<span class="brand-sub">Usage &amp; cost report</span></div></div>'
        f'<div class="chips">{chips}</div>'
        f'<div class="topbar-actions"><span class="generated">Generated {esc(generated)}</span>'
        '<button type="button" id="theme-toggle" aria-label="Toggle colour theme">'
        "Theme: auto</button></div></div>"
        f"{nav}</header>"
    )


def _notices(data: ReportData) -> str:
    items: list[str] = []
    totals = data.totals.cost
    if totals.partial:
        models = ", ".join(data.unpriced_models_in_scope) or "unknown"
        items.append(
            callout(
                "warning",
                "Lower-bound totals",
                f"Totals are lower bounds (≥): {totals.unpriced_calls:,} calls have no "
                f"price ({models}). Add prices with agent-meter pricing add.",
            )
        )
    if totals.flagged:
        items.append(
            callout(
                "info",
                "Estimated or inferred",
                f"* {totals.inferred_calls:,} calls use an inferred model and "
                f"{totals.estimated_calls:,} calls an estimated price.",
            )
        )
    conversations = sum(row.conversations for row in data.untracked)
    if conversations:
        hosts = ", ".join(sorted({host_label(row.host) for row in data.untracked}))
        items.append(
            callout(
                "info",
                "Untracked history",
                f"{conversations:,} conversations untracked ({hosts}): never estimated "
                "and never counted as zero usage.",
            )
        )
    if not items:
        return ""
    return (
        '<section id="notices" class="section notices" aria-label="Notices">'
        f"{''.join(items)}</section>"
    )


def _empty_state(data: ReportData) -> str:
    message = (
        "No data matches the selected filters."
        if data.store_has_data
        else "No data yet — run <code>agent-meter collect</code>"
    )
    return (
        '<section id="empty" class="section empty"><div class="card empty-card">'
        f"<h2>{message}</h2></div></section>"
    )


def _meta(data: ReportData) -> str:
    totals = data.totals
    payload = {
        "format_version": REPORT_FORMAT_VERSION,
        "generated_at": data.options.generated_at_utc.isoformat(),
        "filters": data.options.filters_payload(),
        "totals": {
            "calls": totals.calls,
            "cost_usd": None if totals.cost.cost_usd is None else str(totals.cost.cost_usd),
            "unpriced_calls": totals.cost.unpriced_calls,
            "tasks": data.task_count,
            "sessions": data.session_count,
        },
    }
    return f'<script type="application/json" id="report-meta">{script_json(payload)}</script>'


def _body(data: ReportData) -> list[str]:
    display = data.options.display()
    if data.scope_empty:
        body = [_empty_state(data)]
        if data.unpriced_models or data.untracked or data.health:
            body.append(records.render_data_quality(data))
        return body
    return [
        _notices(data),
        overview.render(data, display),
        tasks.render(data, display),
        performance.render(data),
        efficiency.render(data),
        billing.render(data, display),
        records.render_sessions(data, display),
        records.render_data_quality(data),
    ]


def render_report(data: ReportData) -> str:
    """The complete HTML document for ``data``."""
    footer = (
        '<footer class="footer">agent-meter · self-contained report, works offline · '
        "costs are API-equivalent</footer>"
    )
    return (
        '<!DOCTYPE html>\n<html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<meta name="color-scheme" content="light dark">'
        "<title>agent-meter report</title>"
        f"<style>{_asset('report.css')}</style></head>"
        f"<body>{_topbar(data, with_nav=not data.scope_empty)}"
        f'<main class="container">{"".join(_body(data))}</main>{footer}{_meta(data)}'
        f"<script>{_asset('report.js')}</script></body></html>\n"
    )
