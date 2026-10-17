"""Server-rendered HTML charts (ADR §3.12: no chart library, no external assets).

Marks are plain HTML elements sized with CSS custom properties (``--h``, ``--w``,
``--x``) holding ``Decimal`` percentages, so no binary floating point touches cost
values and the text stays crisp at any width (an SVG ``viewBox`` would shrink labels
on narrow screens). The inline stylesheet draws them with the theme tokens.

Every mark is a tooltip target: ``data-tip`` (what) and ``data-val`` (how much) are
read by the inline script with ``textContent`` only, the mark is keyboard focusable
and carries the same text as its ``aria-label``. Each chart is paired with a table
view by the caller, so no value is reachable only by hovering.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal
from typing import Final

from agent_meter.report.fmt import esc, format_amount, format_duration_tick

__all__ = [
    "BarGroup",
    "BarPoint",
    "Scale",
    "Segment",
    "Series",
    "ShareItem",
    "StackColumn",
    "TimelineLane",
    "bar_list",
    "column_chart",
    "duration_scale",
    "grouped_bars",
    "legend",
    "money_scale",
    "share_bar",
    "stacked_columns",
    "timeline",
]

_HUNDRED: Final = Decimal(100)
_CENT: Final = Decimal("0.01")
_TARGET_TICKS: Final = 4
_NICE_MULTIPLIERS: Final = (Decimal(1), Decimal(2), Decimal("2.5"), Decimal(5), Decimal(10))
_DURATION_STEPS_S: Final = (
    1, 2, 5, 10, 15, 30, 60, 120, 300, 600, 900, 1_800, 3_600, 7_200, 10_800, 21_600,
    43_200, 86_400,
)  # fmt: skip
_MAX_CAPPED_COLUMNS: Final = 12
_MAX_DEPTH_INDENT: Final = 4


# ------------------------------------------------------------------ data types


@dataclass(frozen=True, slots=True)
class BarPoint:
    label: str
    value: Decimal
    caption: str  # formatted value shown in the tooltip / value label


@dataclass(frozen=True, slots=True)
class Series:
    """One legend entry; ``tone`` is a stylesheet class (``s1``..``s7``, ``s-other``, ``o1``..)."""

    key: str
    label: str
    tone: str


@dataclass(frozen=True, slots=True)
class Segment:
    series: str  # Series.key
    value: Decimal
    caption: str


@dataclass(frozen=True, slots=True)
class StackColumn:
    label: str
    caption: str  # the column total, shown on the cap
    segments: tuple[Segment, ...]  # bottom first


@dataclass(frozen=True, slots=True)
class BarGroup:
    label: str
    note: str  # the one value labelled directly on the group's head line
    values: tuple[Segment, ...]  # one per series, in legend order


@dataclass(frozen=True, slots=True)
class ShareItem:
    label: str
    tone: str
    value: Decimal | None  # None when the share is unknown (e.g. fully unpriced)
    caption: str


@dataclass(frozen=True, slots=True)
class TimelineLane:
    label: str
    depth: int
    start_ms: Decimal  # offset from the timeline origin
    end_ms: Decimal
    tone: str
    caption: str


@dataclass(frozen=True, slots=True)
class Scale:
    """A value axis from 0 to ``top`` with clean, pre-labelled ticks."""

    top: Decimal
    ticks: tuple[tuple[Decimal, str], ...]


# ---------------------------------------------------------------------- scales


def _nice_step(raw: Decimal) -> Decimal:
    base = Decimal(1).scaleb(raw.adjusted())
    for multiplier in _NICE_MULTIPLIERS:
        step = base * multiplier
        if step >= raw:
            return step
    return base * _NICE_MULTIPLIERS[-1]


def _decimals(step: Decimal) -> int:
    exponent = step.normalize().as_tuple().exponent
    return max(0, -exponent) if isinstance(exponent, int) else 0


def _build_scale(
    maximum: Decimal, step: Decimal, label: Callable[[Decimal], str]
) -> Scale:
    count = max(1, int((maximum / step).to_integral_value(rounding=ROUND_CEILING)))
    values = [step * index for index in range(count + 1)]
    return Scale(top=values[-1], ticks=tuple((v, label(v)) for v in values))


def money_scale(maximum: Decimal) -> Scale:
    """USD axis: ``$0 $2 $4``, sub-cent steps keep their precision, ``$1K`` from 1,000."""
    step = _nice_step(maximum / _TARGET_TICKS) if maximum > 0 else Decimal(1)

    def label(value: Decimal) -> str:
        if value == 0:
            return "$0"
        for divisor, suffix in ((Decimal(1_000_000), "M"), (Decimal(1_000), "K")):
            if step >= divisor:
                return f"${format_amount(value / divisor, _decimals(step / divisor))}{suffix}"
        return f"${format_amount(value, _decimals(step))}"

    return _build_scale(max(maximum, Decimal(0)), step, label)


def duration_scale(maximum_ms: Decimal) -> Scale:
    """Duration axis in whole time units (``0 2m 4m 6m``)."""
    raw = maximum_ms / _TARGET_TICKS
    step = next(
        (Decimal(s * 1_000) for s in _DURATION_STEPS_S if s * 1_000 >= raw),
        Decimal(_DURATION_STEPS_S[-1] * 1_000),
    )
    return _build_scale(max(maximum_ms, Decimal(0)), step, format_duration_tick)


# -------------------------------------------------------------------- helpers


def _pct(value: Decimal, top: Decimal) -> str:
    """``value`` as a percentage of ``top``, clamped to 0..100, two decimals."""
    if top <= 0 or value <= 0:
        ratio = Decimal(0)
    else:
        ratio = min(value * _HUNDRED / top, _HUNDRED)
    return f"{ratio.quantize(_CENT, rounding=ROUND_HALF_UP)}%"


def _mark(label: str, caption: str, tone: str) -> str:
    """Attributes that make an element a focusable, labelled tooltip target."""
    return (
        f' tabindex="0" role="img" aria-label="{esc(label)}: {esc(caption)}"'
        f' data-tip="{esc(label)}" data-val="{esc(caption)}" data-tone="{esc(tone)}"'
    )


def _group(kind: str, title: str, body: str, style: str = "") -> str:
    style_attr = f' style="{style}"' if style else ""
    return (
        f'<div class="chart {kind}" role="group" aria-label="{esc(title)}"{style_attr}>'
        f"{body}</div>"
    )


def _y_axis(scale: Scale) -> str:
    ticks = "".join(
        f'<span class="tick" style="--y:{_pct(v, scale.top)}">{esc(label)}</span>'
        for v, label in scale.ticks
    )
    lines = "".join(f'<i style="--y:{_pct(v, scale.top)}"></i>' for v, _ in scale.ticks)
    return (
        f'<div class="y-axis" aria-hidden="true">{ticks}</div>'
        f'<div class="gridlines" aria-hidden="true">{lines}</div>'
    )


def _x_ticks(scale: Scale) -> str:
    ticks = "".join(
        f'<span class="tick" style="--x:{_pct(v, scale.top)}">{esc(label)}</span>'
        for v, label in scale.ticks
    )
    return f'<div class="ticks" aria-hidden="true">{ticks}</div>'


def _x_labels(labels: Sequence[str]) -> str:
    """First and last category under a column chart (the middle when there are 3+)."""
    picked = [labels[0]]
    if len(labels) > 2:
        picked.append(labels[len(labels) // 2])
    if len(labels) > 1:
        picked.append(labels[-1])
    spans = "".join(f'<span class="x-label">{esc(label)}</span>' for label in picked)
    return f'<div class="x-axis" aria-hidden="true">{spans}</div>'


def _grid_steps(scale: Scale) -> str:
    return f"--n:{max(len(scale.ticks) - 1, 1)}"


def legend(series: Sequence[Series]) -> str:
    """A legend box for two or more series; a single series is named by the title."""
    if len(series) < 2:
        return ""
    items = "".join(
        f'<li class="legend-item"><i class="key {esc(s.tone)}"></i>'
        f'<span class="legend-label">{esc(s.label)}</span></li>'
        for s in series
    )
    return f'<ul class="legend">{items}</ul>'


# --------------------------------------------------------------------- charts


def column_chart(points: Sequence[BarPoint], *, title: str, scale: Scale) -> str:
    """Vertical columns over time (one series); the peak column carries its value."""
    if not points:
        return ""
    peak = max(range(len(points)), key=lambda i: points[i].value)
    slots = []
    for index, point in enumerate(points):
        cap = (
            f'<span class="cap">{esc(point.caption)}</span>'
            if index == peak and point.value > 0
            else ""
        )
        slots.append(
            f'<div class="col-slot" style="--h:{_pct(point.value, scale.top)}"'
            f'{_mark(point.label, point.caption, "s1")}><div class="col s1"></div>{cap}</div>'
        )
    body = (
        f'<div class="plot">{_y_axis(scale)}<div class="cols">{"".join(slots)}</div></div>'
        f"{_x_labels([p.label for p in points])}"
    )
    return _group("chart-columns", title, body)


def stacked_columns(
    columns: Sequence[StackColumn],
    series: Sequence[Series],
    *,
    title: str,
    scale: Scale,
) -> str:
    """Stacked columns (e.g. cost per month by project) with a legend and cap totals."""
    if not columns:
        return ""
    by_key = {s.key: s for s in series}
    totals = [
        sum((seg.value for seg in column.segments if seg.value > 0), Decimal(0))
        for column in columns
    ]
    peak = max(range(len(columns)), key=lambda i: totals[i])
    slots = []
    for index, column in enumerate(columns):
        segments = "".join(
            f'<div class="seg {esc(by_key[seg.series].tone)}" '
            f'style="--h:{_pct(seg.value, totals[index])}"'
            f"{_mark(f'{column.label} · {by_key[seg.series].label}', seg.caption, by_key[seg.series].tone)}>"
            "</div>"
            for seg in column.segments
            if seg.value > 0
        )
        show_cap = len(columns) <= _MAX_CAPPED_COLUMNS or index == peak
        cap = f'<span class="cap">{esc(column.caption)}</span>' if show_cap else ""
        slots.append(
            f'<div class="col-slot" style="--h:{_pct(totals[index], scale.top)}">'
            f'<div class="col-stack">{segments}</div>{cap}</div>'
        )
    body = (
        f"{legend(series)}"
        f'<div class="plot">{_y_axis(scale)}<div class="cols">{"".join(slots)}</div></div>'
        f'<div class="x-axis x-axis-all" aria-hidden="true">'
        + "".join(f'<span class="x-label">{esc(c.label)}</span>' for c in columns)
        + "</div>"
    )
    return _group("chart-stacked", title, body)


def bar_list(
    points: Sequence[BarPoint],
    *,
    title: str,
    top: Decimal | None = None,
    tone: str = "s1",
) -> str:
    """Horizontal bars, label and value on a head line above each bar (one series)."""
    if not points:
        return ""
    maximum = top if top is not None else max(p.value for p in points)
    rows = "".join(
        f'<li class="bar-row"><div class="bar-hit" style="--w:{_pct(p.value, maximum)}"'
        f"{_mark(p.label, p.caption, tone)}>"
        f'<div class="bar-head"><span class="bar-label">{esc(p.label)}</span>'
        f'<span class="bar-value">{esc(p.caption)}</span></div>'
        f'<div class="bar-track"><div class="bar {esc(tone)}"></div></div></div></li>'
        for p in points
    )
    return f'<ul class="chart bar-list" aria-label="{esc(title)}">{rows}</ul>'


def grouped_bars(
    groups: Sequence[BarGroup],
    series: Sequence[Series],
    *,
    title: str,
    scale: Scale,
) -> str:
    """Grouped horizontal bars on one shared value axis (e.g. P50/P95/P99 per host)."""
    if not groups:
        return ""
    by_key = {s.key: s for s in series}
    rows = []
    for group in groups:
        bars = "".join(
            f'<div class="bar-track" style="--w:{_pct(v.value, scale.top)}"'
            f"{_mark(f'{group.label} · {by_key[v.series].label}', v.caption, by_key[v.series].tone)}>"
            f'<div class="bar {esc(by_key[v.series].tone)}"></div></div>'
            for v in group.values
        )
        rows.append(
            f'<li class="bar-group"><div class="bar-head">'
            f'<span class="bar-label">{esc(group.label)}</span>'
            f'<span class="bar-value">{esc(group.note)}</span></div>{bars}</li>'
        )
    body = f'{legend(series)}<ul class="bar-list grouped">{"".join(rows)}</ul>{_x_ticks(scale)}'
    return _group("chart-grouped", title, body, _grid_steps(scale))


def share_bar(items: Sequence[ShareItem], *, title: str) -> str:
    """A single 100% bar for part-to-whole, with a value-carrying legend."""
    if not items:
        return ""
    priced = [i for i in items if i.value is not None and i.value > 0]
    total = sum((i.value for i in priced if i.value is not None), Decimal(0))
    segments = "".join(
        f'<div class="share-seg {esc(i.tone)}" style="--w:{_pct(i.value, total)}"'
        f"{_mark(i.label, i.caption, i.tone)}></div>"
        for i in priced
        if i.value is not None
    )
    bar = f'<div class="share-bar">{segments}</div>' if segments else ""
    entries = "".join(
        f'<li class="legend-item"><i class="key {esc(i.tone)}"></i>'
        f'<span class="legend-label">{esc(i.label)}</span>'
        f'<span class="legend-value">{esc(i.caption)}</span></li>'
        for i in items
    )
    return _group(
        "chart-share", title, f'{bar}<ul class="legend legend-values">{entries}</ul>'
    )


def timeline(lanes: Sequence[TimelineLane], *, title: str, scale: Scale) -> str:
    """Gantt-like lanes: one bar per agent run, positioned within the task window."""
    if not lanes:
        return ""
    rows = "".join(
        f'<li class="tl-lane"><span class="tl-label" '
        f'style="--depth:{min(max(lane.depth, 0), _MAX_DEPTH_INDENT)}">{esc(lane.label)}</span>'
        f'<div class="tl-track" style="--x:{_pct(lane.start_ms, scale.top)};'
        f'--w:{_pct(lane.end_ms - lane.start_ms, scale.top)}"'
        f"{_mark(lane.label, lane.caption, lane.tone)}>"
        f'<div class="tl-bar {esc(lane.tone)}"></div></div></li>'
        for lane in lanes
    )
    body = (
        f'<ul class="tl-lanes">{rows}</ul>'
        f'<div class="tl-axis"><span></span>{_x_ticks(scale)}</div>'
    )
    return _group("chart-timeline", title, body, _grid_steps(scale))
