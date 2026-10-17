"""Design-level tests for the redesigned HTML report (light-first dashboard).

Pins the theme tokens (light default, validated dark steps), the KPI stat tiles, the
chart cards with their accessible table views, the tooltip script's ``textContent``-only
DOM writes, the sticky top bar, the notice callouts, and the data behind the new charts
(cost by project and month, agent-type cost share, agent-run timelines).
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from importlib.resources import files

import pytest

from agent_meter.report import build_report
from agent_meter.report.data import load_report_data
from tests.unit.test_report import (
    BASE_TS,
    PROJECT_X,
    PROJECT_Y,
    ViewStore,
    assert_well_formed,
    open_view_store,
    options,
    populate_two_projects,
    section,
)

LIGHT_SERIES = ("#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#008300", "#6250d6")
DARK_SERIES = ("#3987e5", "#d95926", "#199e70", "#c98500", "#d55181", "#008300", "#9085e9")


@pytest.fixture()
def store() -> Iterator[ViewStore]:
    with open_view_store() as view_store:
        yield view_store


def _asset(name: str) -> str:
    return (files("agent_meter.report") / "assets" / name).read_text(encoding="utf-8")


def _block(css: str, selector: str) -> str:
    """The body of the first rule whose selector text is exactly ``selector``."""
    match = re.search(re.escape(selector) + r"\s*\{(.*?)\}", css, re.S)
    assert match is not None, f"{selector} block missing"
    return match.group(1)


def populate_rich(store: ViewStore) -> None:
    """Two projects plus a multi-agent task, agent costs, latency and billable rates."""
    populate_two_projects(store)
    store.add(
        "v_tasks",
        task_id="t-dag",
        seq_in_session=2,
        agent_runs=3,
        max_spawn_depth=1,
        parallelism=1.8,
        started_at=BASE_TS + timedelta(hours=2),
        cost_usd=Decimal("4.000000000"),
    )
    start = BASE_TS + timedelta(hours=2)
    store.add(
        "v_agent_runs",
        agent_run_id="t-dag:main",
        task_id="t-dag",
        started_at=start,
        ended_at=start + timedelta(minutes=10),
        cost_usd=Decimal("1.000000000"),
    )
    store.add(
        "v_agent_runs",
        agent_run_id="t-dag:a1",
        task_id="t-dag",
        agent_type="code-implementer",
        parent_agent_run_id="t-dag:main",
        spawn_depth=1,
        started_at=start + timedelta(minutes=1),
        ended_at=start + timedelta(minutes=6),
        cost_usd=Decimal("3.000000000"),
    )
    store.add(
        "v_agent_runs",
        agent_run_id="t-dag:a2",
        task_id="t-dag",
        agent_type="qa-tester",
        parent_agent_run_id="t-dag:main",
        spawn_depth=1,
        started_at=start + timedelta(minutes=6),
        ended_at=start + timedelta(minutes=9),
        cost_usd=None,
        unpriced_calls=4,
    )
    store.add(
        "v_agent_type_cost",
        task_id="t-dag",
        agent_type="code-implementer",
        cost_usd=Decimal("3.000000000"),
        cost_share=0.75,
    )
    store.add(
        "v_agent_type_cost",
        task_id="t-dag",
        agent_type="main",
        cost_usd=Decimal("1.000000000"),
        cost_share=0.25,
    )
    store.add("v_task_latency")
    store.add("v_client_month", billable_usd=Decimal("253.658536585"))
    store.add("v_unpriced_models")
    store.add("v_untracked")
    store.add("v_health")


# ---------------------------------------------------------------- theme tokens


def test_light_theme_tokens_are_the_default_custom_properties() -> None:
    # Arrange
    css = _asset("report.css")

    # Act
    root = _block(css, ":root")

    # Assert
    assert css.index(":root {") < css.index("@media (prefers-color-scheme: dark)")
    assert "color-scheme: light;" in root
    for token in ("--page:", "--surface: #ffffff", "--text-primary:", "--text-secondary:"):
        assert token in root
    for slot, hex_value in enumerate(LIGHT_SERIES, start=1):
        assert f"--series-{slot}: {hex_value};" in root
    assert "--ordinal-1: #86b6ef;" in root
    assert "--status-warning: #fab219;" in root


def test_dark_mode_is_its_own_validated_block() -> None:
    # Arrange
    css = _asset("report.css")

    # Act
    media = css[css.index("@media (prefers-color-scheme: dark)") :]
    toggled = _block(css, ':root[data-theme="dark"]')

    # Assert
    for block in (media, toggled):
        assert "color-scheme: dark;" in block
        assert "--surface: #1a1a19;" in block
        for slot, hex_value in enumerate(DARK_SERIES, start=1):
            assert f"--series-{slot}: {hex_value};" in block


def test_stylesheet_records_the_validated_palette() -> None:
    # Arrange
    css = _asset("report.css")

    # Act
    header = css[: css.index("*/")]

    # Assert
    assert css.lstrip().startswith("/*")
    assert "validate_palette.js" in header
    assert header.count("ALL CHECKS PASS") >= 3  # light, dark, ordinal ramps
    for hex_value in LIGHT_SERIES + DARK_SERIES:
        assert hex_value in header


def test_stylesheet_uses_system_fonts_and_no_external_resources() -> None:
    # Arrange
    css = _asset("report.css")

    # Assert
    assert "system-ui" in css
    assert "@font-face" not in css
    assert "url(" not in css
    assert "@import" not in css


# ------------------------------------------------------------------ KPI tiles


def _tiles(html: str) -> list[tuple[str, str]]:
    return re.findall(
        r'<span class="kpi-label">(.*?)</span><span class="kpi-value">(.*?)</span>'
        r'(?:<span class="kpi-sub">|</div>)',
        section(html, "overview"),
        re.S,
    )


def test_overview_leads_with_six_kpi_tiles(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    html = build_report(store, options())

    # Assert
    tiles = dict(_tiles(html))
    assert list(tiles) == [
        "Total cost",
        "This month",
        "Tokens",
        "Cache hit",
        "Tasks",
        "P95 task time",
    ]
    assert tiles["Total cost"] == "≈ $7.00"
    assert tiles["This month"] == "≈ $3.00"
    assert tiles["Tokens"] == "20K"
    assert tiles["Tasks"] == "2"
    assert tiles["P95 task time"] == "10m 00s"
    assert '<div class="kpi kpi-hero"><span class="kpi-label">Total cost</span>' in html


def test_month_tile_falls_back_to_the_latest_month_in_scope(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    html = build_report(store, options(month="2026-09"))

    # Assert
    tiles = dict(_tiles(html))
    assert tiles["Latest month"] == "≈ $4.00"
    assert "This month" not in tiles


# --------------------------------------------------------- charts and tables


def test_every_chart_card_has_a_table_view(store: ViewStore) -> None:
    # Arrange
    populate_rich(store)

    # Act
    html = build_report(store, options())

    # Assert
    assert_well_formed(html)
    cards = re.findall(r'<figure class="card chart-card".*?</figure>', html, re.S)
    assert len(cards) >= 10
    for card in cards:
        assert '<details class="table-view">' in card
        assert "<table" in card
        assert "<figcaption" in card


def test_rich_report_has_no_external_references(store: ViewStore) -> None:
    # Arrange
    populate_rich(store)

    # Act
    html = build_report(store, options())

    # Assert
    assert "http://" not in html
    assert "https://" not in html
    assert "url(" not in html
    assert "<link" not in html
    assert "@import" not in html
    assert re.search(r"<(script|img|iframe)[^>]*\bsrc=", html) is None


def test_tooltip_script_writes_text_content_only() -> None:
    # Arrange
    js = _asset("report.js")

    # Assert
    assert "textContent" in js
    assert "createElement" in js
    for banned in (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "document.write",
        "eval(",
        "new Function",
    ):
        assert banned not in js


def test_tooltip_attributes_are_escaped(store: ViewStore) -> None:
    # Arrange
    evil = "<img onerror=x>"
    store.connection.execute(
        "UPDATE t_projects SET display_name = ? WHERE project_id = ?", [evil, PROJECT_X]
    )
    store.add("v_calls")

    # Act
    html = build_report(store, options())

    # Assert
    assert "<img" not in html
    assert re.search(r'data-tip="[^"<>]*&lt;img onerror=x&gt;', html)


def test_overview_charts_cover_time_projects_by_month_and_hosts(
    store: ViewStore,
) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    overview = section(build_report(store, options()), "overview")

    # Assert
    assert "Cost per day" in overview
    assert "Cost by project and month" in overview
    assert "Claude Code vs Antigravity" in overview
    assert 'class="chart chart-stacked"' in overview


def test_cost_over_time_switches_to_weekly_buckets_for_long_ranges(
    store: ViewStore,
) -> None:
    # Arrange
    for offset in range(0, 91, 7):
        day = date(2026, 7, 1) + timedelta(days=offset)
        store.add(
            "v_calls",
            local_date=day,
            ts=datetime(day.year, day.month, day.day, 12, tzinfo=UTC),
        )

    # Act
    overview = section(build_report(store, options()), "overview")

    # Assert
    assert "Cost per week" in overview
    assert "Cost per day" not in overview
    assert "Week of 2026-06-29" in overview


def test_cost_by_project_and_month_folds_the_tail_into_other(store: ViewStore) -> None:
    # Arrange
    for index in range(9):
        store.add(
            "v_calls",
            project_id=f"git:{index:016d}",
            cost_usd=Decimal(10 - index),
        )

    # Act
    data = load_report_data(store, options())
    overview = section(build_report(store, options()), "overview")

    # Assert
    assert len(data.by_project_month) == 9
    stacked = re.search(r'<div class="chart chart-stacked".*?</ul>', overview, re.S)
    assert stacked is not None
    legend = re.findall(r'<span class="legend-label">(.*?)</span>', stacked.group(0))
    assert len(legend) == 8
    assert legend[-1] == "Other"


def test_performance_and_efficiency_render_charts(store: ViewStore) -> None:
    # Arrange
    populate_rich(store)

    # Act
    html = build_report(store, options())

    # Assert
    performance = section(html, "performance")
    assert performance.count('class="card chart-card"') >= 2
    for label in ("P50", "P95", "P99"):
        assert f'<span class="legend-label">{label}</span>' in performance
    efficiency = section(html, "efficiency")
    assert efficiency.count('class="card chart-card"') >= 3
    for title in ("Cache hit rate", "Context per call", "Output per task"):
        assert title in efficiency


def test_billing_chart_compares_cost_with_billable_where_rates_exist(
    store: ViewStore,
) -> None:
    # Arrange
    store.add("v_calls")
    store.add("v_client_month", billable_usd=Decimal("253.658536585"))
    store.add(
        "v_client_month",
        client=None,
        project_id=PROJECT_Y,
        display_name="project-y",
        billing_model=None,
        rate_currency=None,
        billable_value=None,
        billable_usd=None,
        ai_cost_ratio=None,
    )

    # Act
    billing = section(build_report(store, options()), "billing")

    # Assert
    assert billing.count('class="card chart-card"') == 1
    assert '<span class="legend-label">AI cost</span>' in billing
    assert '<span class="legend-label">Billable (USD)</span>' in billing
    assert "4.9%" in billing


def test_billing_without_usd_rates_shows_a_calm_empty_card(store: ViewStore) -> None:
    # Arrange
    store.add("v_calls")
    store.add("v_client_month", billable_usd=None)

    # Act
    billing = section(build_report(store, options()), "billing")

    # Assert
    assert 'class="card chart-card"' not in billing
    assert "No billable rate in USD" in billing


# ------------------------------------------------------- tasks, agents, timeline


def test_agent_types_aggregate_cost_share_over_the_scope(store: ViewStore) -> None:
    # Arrange
    populate_rich(store)
    store.add(
        "v_tasks",
        task_id="t-other",
        project_id=PROJECT_Y,
        display_name="project-y",
        started_at=BASE_TS - timedelta(days=1),
    )
    store.add(
        "v_agent_type_cost",
        task_id="t-other",
        agent_type="main",
        cost_usd=Decimal("6.000000000"),
    )

    # Act
    everything = load_report_data(store, options())
    project_x = load_report_data(store, options(project_id=PROJECT_X))

    # Assert
    assert {a.agent_type: a.cost.cost_usd for a in everything.agent_types} == {
        "main": Decimal("7"),
        "code-implementer": Decimal("3"),
    }
    assert {a.agent_type: a.cost_share for a in project_x.agent_types} == {
        "code-implementer": Decimal("0.75"),
        "main": Decimal("0.25"),
    }


def test_timelines_load_agent_runs_for_recent_multi_agent_tasks(
    store: ViewStore,
) -> None:
    # Arrange
    populate_rich(store)

    # Act
    data = load_report_data(store, options())

    # Assert
    assert [t.task.task_id for t in data.timelines] == ["t-dag"]
    runs = data.timelines[0].runs
    assert [r.agent_type for r in runs] == ["main", "code-implementer", "qa-tester"]
    assert runs[2].cost.partial
    assert runs[1].spawn_depth == 1


def test_tasks_section_shows_agent_timeline_and_cost_share(store: ViewStore) -> None:
    # Arrange
    populate_rich(store)

    # Act
    tasks = section(build_report(store, options()), "tasks")

    # Assert
    assert 'class="chart chart-timeline"' in tasks
    assert "task #2" in tasks
    assert "Cost share by agent type" in tasks
    timeline = re.search(r'<div class="chart chart-timeline".*?</ul>', tasks, re.S)
    assert timeline is not None
    lanes = re.findall(r'<span class="tl-label"[^>]*>(.*?)</span>', timeline.group(0))
    assert lanes == ["main", "code-implementer", "qa-tester"]


# ------------------------------------------------------- top bar and notices


def test_top_bar_is_sticky_and_summarises_period_and_filters(
    store: ViewStore,
) -> None:
    # Arrange
    populate_two_projects(store)
    css = _asset("report.css")

    # Act
    unfiltered = build_report(store, options())
    filtered = build_report(store, options(project_id=PROJECT_X))

    # Assert
    assert "position: sticky" in _block(css, ".topbar")
    topbar = re.search(r'<header class="topbar".*?</header>', unfiltered, re.S)
    assert topbar is not None
    assert "2026-09-30 → 2026-10-14" in topbar.group(0)
    assert "All data" in topbar.group(0)
    assert 'id="theme-toggle"' in topbar.group(0)
    assert "Project: project-x" in filtered


def test_notices_are_calm_callouts_with_icon_and_label(store: ViewStore) -> None:
    # Arrange
    store.add("v_calls", cost_usd=Decimal("1.000000000"))
    store.add(
        "v_calls",
        model_effective="gemini-x",
        priced_model=None,
        unpriced=True,
        cost_usd=None,
    )
    store.add("v_untracked")

    # Act
    notices = section(build_report(store, options()), "notices")

    # Assert
    warning = re.search(r'<div class="callout callout-warning".*?</div></div>', notices, re.S)
    assert warning is not None
    assert '<svg class="callout-icon" aria-hidden="true"' in warning.group(0)
    assert '<strong class="callout-label">Lower-bound totals</strong>' in warning.group(0)
    assert 'class="callout callout-info"' in notices
    assert "100 conversations untracked" in notices


def test_layout_has_a_narrow_screen_breakpoint() -> None:
    # Arrange
    css = _asset("report.css")

    # Assert
    assert re.search(r"@media \(max-width: ?\d+px\)", css)
    assert "overflow-x: auto" in css
