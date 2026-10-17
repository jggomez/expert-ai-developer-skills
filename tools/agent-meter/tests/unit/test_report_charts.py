"""Unit tests for the report's HTML chart components and scales (Track 11C redesign).

Charts are plain HTML marks styled by the inline stylesheet (no chart library, no
external assets). These tests pin the geometry (Decimal percentages), the tooltip
contract (``data-tip`` / ``data-val`` read with ``textContent`` by the inline script),
escaping, legends and the categorical tone assignment.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from decimal import Decimal
from html.parser import HTMLParser

import pytest

from agent_meter.report.charts import (
    BarGroup,
    BarPoint,
    Segment,
    Series,
    ShareItem,
    StackColumn,
    TimelineLane,
    bar_list,
    column_chart,
    duration_scale,
    grouped_bars,
    money_scale,
    share_bar,
    stacked_columns,
    timeline,
)
from agent_meter.report.series import OTHER_TONE, assign_tones

Attrs = dict[str, str]


class _MarkCollector(HTMLParser):
    """Collects the attributes of every element that carries a tooltip."""

    def __init__(self) -> None:
        super().__init__()
        self.marks: list[Attrs] = []
        self.titles = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {k: v or "" for k, v in attrs}
        if "title" in values:
            self.titles += 1
        if "data-tip" in values:
            self.marks.append({"tag": tag, **values})


def marks(html: str) -> list[Attrs]:
    collector = _MarkCollector()
    collector.feed(html)
    assert collector.titles == 0, "native title tooltips would double the JS tooltip"
    return collector.marks


def var(mark: Attrs, name: str) -> Decimal:
    match = re.search(rf"--{name}:\s*([0-9.]+)%", mark.get("style", ""))
    assert match is not None, f"--{name} missing on {mark}"
    return Decimal(match.group(1))


def _points() -> list[BarPoint]:
    return [
        BarPoint(label="2026-10-01", value=Decimal("1.5"), caption="≈ $1.50"),
        BarPoint(label="2026-10-02", value=Decimal("3"), caption="≈ $3.00"),
    ]


# -------------------------------------------------------------------- scales


def test_money_scale_rounds_to_clean_ticks() -> None:
    # Act
    scale = money_scale(Decimal(7))

    # Assert
    assert scale.top == Decimal(8)
    assert [value for value, _ in scale.ticks] == [0, 2, 4, 6, 8]
    assert [label for _, label in scale.ticks] == ["$0", "$2", "$4", "$6", "$8"]


def test_money_scale_labels_sub_cent_steps_without_duplicates() -> None:
    # Act
    scale = money_scale(Decimal("0.015"))

    # Assert
    labels = [label for _, label in scale.ticks]
    assert labels == ["$0", "$0.005", "$0.010", "$0.015"]
    assert len(set(labels)) == len(labels)


def test_money_scale_compacts_thousands_and_survives_zero() -> None:
    # Act
    large = money_scale(Decimal(3_400))
    empty = money_scale(Decimal(0))

    # Assert
    assert [label for _, label in large.ticks] == ["$0", "$1K", "$2K", "$3K", "$4K"]
    assert empty.top > 0
    assert empty.ticks[0] == (Decimal(0), "$0")


def test_duration_scale_uses_whole_time_units() -> None:
    # Act
    scale = duration_scale(Decimal(250_000))

    # Assert
    assert [label for _, label in scale.ticks] == ["0", "2m", "4m", "6m"]
    assert scale.top == Decimal(360_000)


# --------------------------------------------------------------------- marks


def test_column_chart_marks_are_proportional_and_carry_tooltips() -> None:
    # Act
    html = column_chart(_points(), title="Cost per day", scale=money_scale(Decimal(3)))

    # Assert
    found = marks(html)
    assert len(found) == 2
    assert [var(m, "h") for m in found] == [Decimal("50.00"), Decimal("100.00")]
    assert found[1]["data-tip"] == "2026-10-02"
    assert found[1]["data-val"] == "≈ $3.00"
    assert 'aria-label="Cost per day"' in html
    assert "http" not in html
    assert "<svg" not in html


def test_column_chart_labels_axis_ticks_and_first_and_last_category() -> None:
    # Act
    html = column_chart(_points(), title="Cost per day", scale=money_scale(Decimal(3)))

    # Assert
    assert re.findall(r'<span class="tick"[^>]*>([^<]*)</span>', html) == [
        "$0",
        "$1",
        "$2",
        "$3",
    ]
    assert "2026-10-01" in html
    assert "2026-10-02" in html


def test_bar_list_scales_to_largest_value_and_escapes_labels() -> None:
    # Arrange
    points = [
        BarPoint(label="<b>evil</b>", value=Decimal("2"), caption="≈ $2.00"),
        BarPoint(label="Claude Code", value=Decimal("4"), caption="≈ $4.00"),
    ]

    # Act
    html = bar_list(points, title="Cost by host")

    # Assert
    assert "<b>" not in html
    assert "&lt;b&gt;evil&lt;/b&gt;" in html
    widths = [var(m, "w") for m in marks(html)]
    assert widths == [Decimal("50.00"), Decimal("100.00")]
    assert '<span class="bar-value">≈ $4.00</span>' in html


def test_bar_list_honours_a_fixed_top_for_ratios() -> None:
    # Arrange
    points = [BarPoint(label="Claude Code", value=Decimal("0.85"), caption="85.0%")]

    # Act
    html = bar_list(points, title="Cache hit", top=Decimal(1))

    # Assert
    assert [var(m, "w") for m in marks(html)] == [Decimal("85.00")]


def test_charts_are_empty_without_points_and_survive_all_zero_values() -> None:
    # Arrange
    zeros = [BarPoint(label="d", value=Decimal("0"), caption="≈ $0.00")]
    scale = money_scale(Decimal(0))

    # Act / Assert
    assert column_chart([], title="x", scale=scale) == ""
    assert bar_list([], title="x") == ""
    assert [var(m, "h") for m in marks(column_chart(zeros, title="x", scale=scale))] == [
        Decimal("0.00")
    ]
    assert [var(m, "w") for m in marks(bar_list(zeros, title="x"))] == [Decimal("0.00")]


def _two_series() -> list[Series]:
    return [
        Series(key="p1", label="project-x", tone="s1"),
        Series(key="p2", label="project-y", tone="s2"),
    ]


def test_stacked_columns_stack_segments_with_a_legend_and_cap_totals() -> None:
    # Arrange
    columns = [
        StackColumn(
            label="2026-09",
            caption="≈ $4.00",
            segments=(Segment("p2", Decimal(4), "≈ $4.00"),),
        ),
        StackColumn(
            label="2026-10",
            caption="≈ $8.00",
            segments=(
                Segment("p1", Decimal(6), "≈ $6.00"),
                Segment("p2", Decimal(2), "≈ $2.00"),
            ),
        ),
    ]

    # Act
    html = stacked_columns(
        columns, _two_series(), title="Cost by project", scale=money_scale(Decimal(8))
    )

    # Assert
    found = marks(html)
    assert [m["data-tip"] for m in found] == [
        "2026-09 · project-y",
        "2026-10 · project-x",
        "2026-10 · project-y",
    ]
    assert [m["data-tone"] for m in found] == ["s2", "s1", "s2"]
    assert [var(m, "h") for m in found[1:]] == [Decimal("75.00"), Decimal("25.00")]
    assert re.search(r'class="col-slot" style="--h:\s*50.00%"><div class="col-stack">', html)
    assert html.count('class="legend-item"') == 2
    assert '<span class="cap">≈ $8.00</span>' in html


def test_single_series_charts_have_no_legend_box() -> None:
    # Arrange
    columns = [
        StackColumn(
            label="2026-10",
            caption="≈ $1.00",
            segments=(Segment("p1", Decimal(1), "≈ $1.00"),),
        )
    ]

    # Act
    html = stacked_columns(
        columns, _two_series()[:1], title="x", scale=money_scale(Decimal(1))
    )

    # Assert
    assert 'class="legend"' not in html


def test_grouped_bars_draw_one_mark_per_series_on_one_axis() -> None:
    # Arrange
    series = [
        Series(key="p50", label="P50", tone="o1"),
        Series(key="p95", label="P95", tone="o2"),
        Series(key="p99", label="P99", tone="o3"),
    ]
    groups = [
        BarGroup(
            label="Claude Code",
            note="P95 4m 00s",
            values=(
                Segment("p50", Decimal(60_000), "1m 00s"),
                Segment("p95", Decimal(240_000), "4m 00s"),
                Segment("p99", Decimal(300_000), "5m 00s"),
            ),
        )
    ]

    # Act
    html = grouped_bars(
        groups, series, title="Task latency", scale=duration_scale(Decimal(300_000))
    )

    # Assert
    found = marks(html)
    assert [m["data-tone"] for m in found] == ["o1", "o2", "o3"]
    assert [m["data-val"] for m in found] == ["1m 00s", "4m 00s", "5m 00s"]
    assert html.count('class="legend-item"') == 3
    assert html.count('class="ticks"') == 1  # a single shared value axis


def test_share_bar_sizes_priced_segments_and_lists_every_item() -> None:
    # Arrange
    items = [
        ShareItem(label="code-implementer", tone="s1", value=Decimal(3), caption="75.0% · ≈ $3.00"),
        ShareItem(label="main", tone="s2", value=Decimal(1), caption="25.0% · ≈ $1.00"),
        ShareItem(label="qa-tester", tone="s3", value=None, caption="≥ $0.00 (22 calls unpriced)"),
    ]

    # Act
    html = share_bar(items, title="Cost share by agent type")

    # Assert
    found = marks(html)
    assert [var(m, "w") for m in found] == [Decimal("75.00"), Decimal("25.00")]
    assert html.count('class="legend-item"') == 3
    assert "22 calls unpriced" in html


def test_timeline_positions_runs_relative_to_the_task_window() -> None:
    # Arrange
    lanes = [
        TimelineLane(
            label="main",
            depth=0,
            start_ms=Decimal(0),
            end_ms=Decimal(600_000),
            tone="s1",
            caption="10m 00s",
        ),
        TimelineLane(
            label="code-implementer",
            depth=1,
            start_ms=Decimal(60_000),
            end_ms=Decimal(360_000),
            tone="s2",
            caption="5m 00s",
        ),
    ]

    # Act
    html = timeline(lanes, title="task #1", scale=duration_scale(Decimal(600_000)))

    # Assert
    found = marks(html)
    assert [var(m, "x") for m in found] == [Decimal("0.00"), Decimal("10.00")]
    assert [var(m, "w") for m in found] == [Decimal("100.00"), Decimal("50.00")]
    assert 'style="--depth:1"' in html


ChartBuilder = Callable[[], str]


@pytest.mark.parametrize(
    "build",
    [
        lambda: column_chart(_points(), title="t", scale=money_scale(Decimal(3))),
        lambda: bar_list(_points(), title="t"),
        lambda: share_bar(
            [ShareItem(label="a", tone="s1", value=Decimal(1), caption="100%")],
            title="t",
        ),
    ],
)
def test_every_mark_is_keyboard_focusable_and_labelled(build: ChartBuilder) -> None:
    # Act
    found = marks(build())

    # Assert
    assert found
    for mark in found:
        assert mark["tabindex"] == "0"
        assert mark["role"] == "img"
        assert mark["aria-label"] == f"{mark['data-tip']}: {mark['data-val']}"


# ---------------------------------------------------------------- tones


def test_assign_tones_uses_seven_slots_in_order_then_folds_to_other() -> None:
    # Arrange
    keys = [f"k{i}" for i in range(9)]

    # Act
    tones = assign_tones(keys)

    # Assert
    assert [tones[k] for k in keys[:7]] == [f"s{i}" for i in range(1, 8)]
    assert tones["k7"] == OTHER_TONE
    assert tones["k8"] == OTHER_TONE
