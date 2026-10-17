"""Unit tests for the HTML report (Track 11C, PRD US-05/06/08, PLAN SM-03..05, PV-01).

The report reads only the contracts.md §6 views. These tests build a throw-away DuckDB
whose objects carry exactly those view names and columns, populated from hand-made rows,
so the report is exercised independently of the production ``store.py`` / ``views.sql``.
"""

from __future__ import annotations

import json
import os
import re
import stat
import statistics
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import duckdb
import pytest

from agent_meter.model import AgentRunRecord, CallRecord, TaskRecord
from agent_meter.readers.claude_code import ClaudeCodeReader
from agent_meter.report import ReportOptions, build_report, write_report
from agent_meter.report.data import load_report_data
from tests.fixtures.canary import CANARY
from tests.fixtures.claude import ClaudeHome
from tests.fixtures.records import make_options
from tests.fixtures.scenarios import claude_standard_session

GENERATED_AT = datetime(2026, 10, 16, 18, 0, tzinfo=UTC)
BASE_TS = datetime(2026, 10, 14, 15, 0, tzinfo=UTC)
PROJECT_X = "git:aaaaaaaaaaaaaaaa"
PROJECT_Y = "git:bbbbbbbbbbbbbbbb"

SECTION6_VIEWS = frozenset(
    {
        "v_calls",
        "v_daily_project_cost",
        "v_sessions",
        "v_tasks",
        "v_agent_runs",
        "v_agent_type_cost",
        "v_tool_counts",
        "v_task_latency",
        "v_dev_hours",
        "v_client_month",
        "v_unpriced_models",
        "v_untracked",
        "v_health",
    }
)

# Test-local DDL mirroring contracts.md §6 column lists. ``t_projects`` is a test-only
# helper feeding the derived ``v_daily_project_cost`` view; the report never reads it.
VIEW_DDL = """
CREATE TABLE t_projects (project_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, client TEXT);
CREATE TABLE v_calls (
  call_id TEXT, host TEXT, project_id TEXT, session_id TEXT, task_id TEXT, agent_run_id TEXT,
  ts TIMESTAMPTZ, local_date DATE, local_month TEXT, model TEXT, model_label TEXT,
  model_effective TEXT, model_inferred BOOLEAN, priced_model TEXT, estimated BOOLEAN,
  unpriced BOOLEAN, tokens_unknown BOOLEAN, input_tokens BIGINT, output_tokens BIGINT,
  thinking_tokens BIGINT, cache_write_5m_tokens BIGINT, cache_write_1h_tokens BIGINT,
  cache_read_tokens BIGINT, prompt_tokens BIGINT, latency_ms BIGINT, is_error BOOLEAN,
  cost_usd DECIMAL(38,9));
CREATE VIEW v_daily_project_cost AS
  SELECT c.local_date, c.local_month, c.project_id, p.display_name, p.client, c.host,
         c.priced_model, COUNT(*) AS calls, SUM(c.input_tokens) AS input_tokens,
         SUM(c.output_tokens) AS output_tokens,
         SUM(COALESCE(c.cache_write_5m_tokens, 0) + COALESCE(c.cache_write_1h_tokens, 0))
           AS cache_write_tokens,
         SUM(c.cache_read_tokens) AS cache_read_tokens, SUM(c.cost_usd) AS cost_usd,
         COUNT(*) FILTER (WHERE c.unpriced) AS unpriced_calls,
         COUNT(*) FILTER (WHERE c.estimated) AS estimated_calls,
         COUNT(*) FILTER (WHERE c.model_inferred) AS inferred_calls,
         COUNT(*) FILTER (WHERE c.is_error) AS error_calls
  FROM v_calls c LEFT JOIN t_projects p USING (project_id)
  GROUP BY ALL;
CREATE TABLE v_sessions (
  session_id TEXT, host TEXT, project_id TEXT, display_name TEXT, started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ, local_date DATE, wall_clock_ms BIGINT, active_ms BIGINT, tasks BIGINT,
  calls BIGINT, cost_usd DECIMAL(38,9), unpriced_calls BIGINT, cache_hit_ratio DOUBLE,
  task_p50_ms DOUBLE, task_p95_ms DOUBLE, status TEXT);
CREATE TABLE v_tasks (
  task_id TEXT, session_id TEXT, host TEXT, project_id TEXT, display_name TEXT, client TEXT,
  seq_in_session INTEGER, started_at TIMESTAMPTZ, ended_at TIMESTAMPTZ, local_date DATE,
  wall_clock_ms BIGINT, active_ms BIGINT, latency_ms BIGINT, duration_source TEXT,
  status TEXT, agent_runs INTEGER, max_spawn_depth INTEGER, parallelism DOUBLE,
  critical_path_ms BIGINT, critical_path TEXT, retries INTEGER, retry_summary TEXT,
  calls BIGINT, input_tokens BIGINT, output_tokens BIGINT, cache_read_tokens BIGINT,
  cache_write_tokens BIGINT, cost_usd DECIMAL(38,9), unpriced_calls BIGINT,
  estimated_calls BIGINT, inferred_calls BIGINT, work_item_tag TEXT, tool_calls BIGINT,
  files_touched BIGINT, test_runs BIGINT, test_failures BIGINT);
CREATE TABLE v_agent_runs (
  agent_run_id TEXT, task_id TEXT, session_id TEXT, host TEXT, project_id TEXT,
  parent_agent_run_id TEXT, agent_type TEXT, spawn_depth INTEGER, started_at TIMESTAMPTZ,
  ended_at TIMESTAMPTZ, active_ms BIGINT, status TEXT, errors INTEGER, files_touched INTEGER,
  test_runs INTEGER, test_failures INTEGER, tools_untracked BOOLEAN, calls BIGINT,
  cost_usd DECIMAL(38,9), unpriced_calls BIGINT, tool_calls BIGINT);
CREATE TABLE v_agent_type_cost (
  task_id TEXT, agent_type TEXT, runs BIGINT, calls BIGINT, cost_usd DECIMAL(38,9),
  unpriced_calls BIGINT, active_ms BIGINT, tool_calls BIGINT, files_touched BIGINT,
  test_runs BIGINT, test_failures BIGINT, cost_share DOUBLE);
CREATE TABLE v_task_latency (
  local_month TEXT, project_id TEXT, host TEXT, tasks BIGINT, p50_ms DOUBLE, p95_ms DOUBLE,
  p99_ms DOUBLE);
CREATE TABLE v_client_month (
  local_month TEXT, client TEXT, project_id TEXT, display_name TEXT, billing_model TEXT,
  rate_currency TEXT, cost_usd DECIMAL(38,9), unpriced_calls BIGINT, dev_hours DECIMAL(10,2),
  billable_value DECIMAL(38,4), billable_usd DECIMAL(38,9), ai_cost_ratio DECIMAL(38,9));
CREATE TABLE v_unpriced_models (
  host TEXT, model_effective TEXT, calls BIGINT, first_ts TIMESTAMPTZ, last_ts TIMESTAMPTZ);
CREATE TABLE v_untracked (
  host TEXT, reason TEXT, conversations BIGINT, observed_from DATE, observed_to DATE);
CREATE TABLE v_health (
  host TEXT, last_ingested_at TIMESTAMPTZ, units BIGINT, unknown_formats BIGINT,
  diagnostics_7d BIGINT, earliest_call_ts TIMESTAMPTZ);
"""


def _call_defaults() -> dict[str, Any]:
    return {
        "call_id": "c-1",
        "host": "claude-code",
        "project_id": PROJECT_X,
        "session_id": "s-1",
        "task_id": "t-1",
        "agent_run_id": "t-1:main",
        "ts": BASE_TS,
        "local_date": BASE_TS.date(),
        "local_month": "2026-10",
        "model": "claude-opus-5-5",
        "model_label": None,
        "model_effective": "claude-opus-5-5",
        "model_inferred": False,
        "priced_model": "claude-opus-5-5",
        "estimated": False,
        "unpriced": False,
        "tokens_unknown": False,
        "input_tokens": 1_000,
        "output_tokens": 200,
        "thinking_tokens": None,
        "cache_write_5m_tokens": 300,
        "cache_write_1h_tokens": 0,
        "cache_read_tokens": 5_000,
        "prompt_tokens": 6_300,
        "latency_ms": 2_000,
        "is_error": False,
        "cost_usd": Decimal("0.010000000"),
    }


def _task_defaults() -> dict[str, Any]:
    return {
        "task_id": "t-1",
        "session_id": "s-1",
        "host": "claude-code",
        "project_id": PROJECT_X,
        "display_name": "project-x",
        "client": None,
        "seq_in_session": 1,
        "started_at": BASE_TS,
        "ended_at": BASE_TS + timedelta(minutes=10),
        "local_date": BASE_TS.date(),
        "wall_clock_ms": 600_000,
        "active_ms": 480_000,
        "latency_ms": 600_000,
        "duration_source": "derived",
        "status": "done",
        "agent_runs": 1,
        "max_spawn_depth": 0,
        "parallelism": None,
        "critical_path_ms": 480_000,
        "critical_path": "main",
        "retries": 0,
        "retry_summary": "",
        "calls": 1,
        "input_tokens": 1_000,
        "output_tokens": 200,
        "cache_read_tokens": 5_000,
        "cache_write_tokens": 300,
        "cost_usd": Decimal("0.010000000"),
        "unpriced_calls": 0,
        "estimated_calls": 0,
        "inferred_calls": 0,
        "work_item_tag": None,
        "tool_calls": 0,
        "files_touched": 0,
        "test_runs": 0,
        "test_failures": 0,
    }


def _session_defaults() -> dict[str, Any]:
    return {
        "session_id": "s-1",
        "host": "claude-code",
        "project_id": PROJECT_X,
        "display_name": "project-x",
        "started_at": BASE_TS,
        "ended_at": BASE_TS + timedelta(minutes=42),
        "local_date": BASE_TS.date(),
        "wall_clock_ms": 2_530_000,
        "active_ms": 1_085_000,
        "tasks": 1,
        "calls": 1,
        "cost_usd": Decimal("0.010000000"),
        "unpriced_calls": 0,
        "cache_hit_ratio": 0.79,
        "task_p50_ms": 35_000.0,
        "task_p95_ms": 250_000.0,
        "status": "closed",
    }


def _agent_type_defaults() -> dict[str, Any]:
    return {
        "task_id": "t-1",
        "agent_type": "main",
        "runs": 1,
        "calls": 1,
        "cost_usd": Decimal("0.010000000"),
        "unpriced_calls": 0,
        "active_ms": 480_000,
        "tool_calls": 0,
        "files_touched": 0,
        "test_runs": 0,
        "test_failures": 0,
        "cost_share": 1.0,
    }


def _agent_run_defaults() -> dict[str, Any]:
    return {
        "agent_run_id": "t-1:main",
        "task_id": "t-1",
        "session_id": "s-1",
        "host": "claude-code",
        "project_id": PROJECT_X,
        "parent_agent_run_id": None,
        "agent_type": "main",
        "spawn_depth": 0,
        "started_at": BASE_TS,
        "ended_at": BASE_TS + timedelta(minutes=10),
        "active_ms": 480_000,
        "status": "done",
        "errors": 0,
        "files_touched": 0,
        "test_runs": 0,
        "test_failures": 0,
        "tools_untracked": False,
        "calls": 1,
        "cost_usd": Decimal("0.010000000"),
        "unpriced_calls": 0,
        "tool_calls": 0,
    }


def _client_month_defaults() -> dict[str, Any]:
    return {
        "local_month": "2026-10",
        "client": "Client Z",
        "project_id": PROJECT_X,
        "display_name": "project-x",
        "billing_model": "hourly",
        "rate_currency": "COP",
        "cost_usd": Decimal("12.500000000"),
        "unpriced_calls": 0,
        "dev_hours": Decimal("13.00"),
        "billable_value": Decimal("1040000.0000"),
        "billable_usd": Decimal("253.658536585"),
        "ai_cost_ratio": Decimal("0.049278846"),
    }


DEFAULTS: Mapping[str, Callable[[], dict[str, Any]]] = {
    "v_calls": _call_defaults,
    "v_tasks": _task_defaults,
    "v_sessions": _session_defaults,
    "v_agent_type_cost": _agent_type_defaults,
    "v_agent_runs": _agent_run_defaults,
    "v_client_month": _client_month_defaults,
    "v_task_latency": lambda: {
        "local_month": "2026-10",
        "project_id": PROJECT_X,
        "host": "claude-code",
        "tasks": 3,
        "p50_ms": 1_000.0,
        "p95_ms": 2_000.0,
        "p99_ms": 3_000.0,
    },
    "v_unpriced_models": lambda: {
        "host": "antigravity-cli",
        "model_effective": "gemini-x",
        "calls": 312,
        "first_ts": BASE_TS,
        "last_ts": BASE_TS + timedelta(days=1),
    },
    "v_untracked": lambda: {
        "host": "antigravity-app",
        "reason": "legacy_pb",
        "conversations": 100,
        "observed_from": date(2026, 5, 2),
        "observed_to": date(2026, 6, 28),
    },
    "v_health": lambda: {
        "host": "claude-code",
        "last_ingested_at": BASE_TS,
        "units": 12,
        "unknown_formats": 0,
        "diagnostics_7d": 2,
        "earliest_call_ts": BASE_TS - timedelta(days=25),
    },
}


@dataclass
class ViewStore:
    """Minimal stand-in for ``Store``: exposes only ``query`` over the §6 view names."""

    connection: duckdb.DuckDBPyConnection
    executed: list[str] = field(default_factory=list)
    _seq: int = 0

    def query(self, sql: str, params: Sequence[object] = ()) -> list[dict[str, object]]:
        self.executed.append(sql)
        cursor = self.connection.execute(sql, list(params))
        columns = [d[0] for d in cursor.description]
        return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def project(
        self, project_id: str, display_name: str, client: str | None = None
    ) -> None:
        self.connection.execute(
            "INSERT INTO t_projects VALUES (?, ?, ?)",
            [project_id, display_name, client],
        )

    def add(self, view: str, **overrides: Any) -> dict[str, Any]:
        row = DEFAULTS[view]()
        unknown = set(overrides) - set(row)
        if unknown:
            raise KeyError(f"unknown columns for {view}: {sorted(unknown)}")
        self._seq += 1
        if view == "v_calls" and "call_id" not in overrides:
            overrides["call_id"] = f"c-{self._seq}"
        if (
            "local_date" in overrides
            and "local_month" in row
            and "local_month" not in overrides
        ):
            overrides["local_month"] = overrides["local_date"].strftime("%Y-%m")
        row.update(overrides)
        names = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        self.connection.execute(
            f"INSERT INTO {view} ({names}) VALUES ({marks})", list(row.values())
        )
        return row


@contextmanager
def open_view_store() -> Iterator[ViewStore]:
    """An in-memory §6 view store with project-x and project-y (Client Z)."""
    connection = duckdb.connect(":memory:")
    try:
        connection.execute("SET TimeZone = 'UTC'")
        connection.execute(VIEW_DDL)
        view_store = ViewStore(connection)
        view_store.project(PROJECT_X, "project-x")
        view_store.project(PROJECT_Y, "project-y", "Client Z")
        yield view_store
    finally:
        connection.close()


@pytest.fixture()
def store() -> Iterator[ViewStore]:
    with open_view_store() as view_store:
        yield view_store


def options(**overrides: Any) -> ReportOptions:
    return ReportOptions(generated_at=GENERATED_AT, **overrides)


class _BalanceChecker(HTMLParser):
    """Fails on mismatched non-void tags, a cheap well-formedness check."""

    VOID = frozenset(
        {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "source",
            "track",
            "wbr",
            "rect",
            "line",
            "path",
            "circle",
            "polyline",
            "text",
        }
    )

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[str] = []
        self.errors: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in self.VOID:
            self.stack.append(tag)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        return None

    def handle_endtag(self, tag: str) -> None:
        if tag in self.VOID:
            return
        if not self.stack or self.stack[-1] != tag:
            self.errors.append(f"unexpected </{tag}> with stack {self.stack[-3:]}")
            return
        self.stack.pop()


def assert_well_formed(html: str) -> None:
    assert html.startswith("<!DOCTYPE html>")
    checker = _BalanceChecker()
    checker.feed(html)
    checker.close()
    assert checker.errors == []
    assert checker.stack == []


def section(html: str, section_id: str) -> str:
    match = re.search(rf'<section id="{section_id}".*?</section>', html, re.S)
    assert match is not None, f"section {section_id} missing"
    return match.group(0)


def populate_two_projects(store: ViewStore) -> None:
    """Two projects, two hosts, two months; project-y belongs to Client Z."""
    store.add("v_calls", cost_usd=Decimal("1.000000000"))
    store.add(
        "v_calls",
        host="antigravity-cli",
        cost_usd=Decimal("2.000000000"),
        model="gemini-4-argon",
        model_effective="gemini-4-argon",
        priced_model="gemini-4-argon",
    )
    store.add(
        "v_calls",
        project_id=PROJECT_Y,
        cost_usd=Decimal("4.000000000"),
        local_date=date(2026, 9, 30),
        ts=datetime(2026, 9, 30, 12, tzinfo=UTC),
    )
    store.add("v_tasks", task_id="t-x")
    store.add(
        "v_tasks",
        task_id="t-y",
        project_id=PROJECT_Y,
        display_name="project-y",
        client="Client Z",
        local_date=date(2026, 9, 30),
        started_at=datetime(2026, 9, 30, 12, tzinfo=UTC),
    )
    store.add("v_sessions", session_id="s-x")
    store.add(
        "v_sessions",
        session_id="s-y",
        project_id=PROJECT_Y,
        display_name="project-y",
        local_date=date(2026, 9, 30),
        started_at=datetime(2026, 9, 30, 12, tzinfo=UTC),
    )


# ---------------------------------------------------------------- SM-03 empty store


def test_empty_store_renders_friendly_empty_state(store: ViewStore) -> None:
    # Arrange: no rows at all

    # Act
    html = build_report(store, options())

    # Assert
    assert_well_formed(html)
    assert "No data yet — run <code>agent-meter collect</code>" in html
    assert 'id="overview"' not in html


def test_filters_matching_nothing_render_a_no_match_message(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    html = build_report(store, options(project_id="git:ffffffffffffffff"))

    # Assert
    assert_well_formed(html)
    assert "No data matches the selected filters." in html
    assert "No data yet" not in html


def test_empty_state_still_reports_untracked_history(store: ViewStore) -> None:
    # Arrange
    store.add("v_untracked")

    # Act
    html = build_report(store, options())

    # Assert
    assert "No data yet" in html
    quality = section(html, "data-quality")
    assert "Antigravity App" in quality
    assert "100" in quality
    assert "2026-05-02" in quality


# ------------------------------------------------------- SM-04 self-contained HTML


@pytest.mark.parametrize("populated", [False, True])
def test_report_has_no_external_references(store: ViewStore, populated: bool) -> None:
    # Arrange
    if populated:
        populate_two_projects(store)
        store.add("v_agent_type_cost", task_id="t-x")
        store.add("v_tasks", task_id="t-dag", agent_runs=2, max_spawn_depth=1)
        store.add("v_agent_runs", agent_run_id="t-dag:main", task_id="t-dag")
        store.add(
            "v_agent_runs",
            agent_run_id="t-dag:sub",
            task_id="t-dag",
            agent_type="code-implementer",
            spawn_depth=1,
            parent_agent_run_id="t-dag:main",
        )
        store.add("v_client_month")
        store.add("v_unpriced_models")
        store.add("v_untracked")
        store.add("v_health")

    # Act
    html = build_report(store, options())

    # Assert
    assert re.search(r"""(src|href)=["']https?:""", html) is None
    assert "http://" not in html
    assert "https://" not in html
    assert "<link" not in html
    assert re.search(r"<script[^>]*\bsrc=", html) is None
    assert "@import" not in html
    assert "url(" not in html
    assert "<style>" in html
    assert "<script>" in html


def test_report_is_light_and_dark_aware(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    html = build_report(store, options())

    # Assert
    assert "prefers-color-scheme: dark" in html
    assert 'id="theme-toggle"' in html
    assert '<meta name="color-scheme" content="light dark">' in html


# ----------------------------------------------------------- SM-05 percentiles


def test_latency_percentiles_match_reference_calculation(store: ViewStore) -> None:
    # Arrange
    cc_latencies = [1_200, 95_000, 3_400, 18_250, 7_700, 61_000, 2_050, 44_444, 12_000]
    agy_latencies = [5_000, 6_500, 8_000, 120_000]
    for i, value in enumerate(cc_latencies):
        store.add("v_tasks", task_id=f"cc-{i}", latency_ms=value)
    for i, value in enumerate(agy_latencies):
        store.add(
            "v_tasks",
            task_id=f"agy-{i}",
            host="antigravity-cli",
            latency_ms=value,
            project_id=PROJECT_Y,
            display_name="project-y",
        )
    store.add("v_tasks", task_id="open", latency_ms=9_999_999, status="in_progress")
    store.add("v_tasks", task_id="unknown", latency_ms=None)

    def reference(values: list[int]) -> list[float]:
        cuts = statistics.quantiles(values, n=100, method="inclusive")
        return [cuts[49], cuts[94], cuts[98]]

    # Act
    data = load_report_data(store, options())

    # Assert
    by_host = {row.key: row.stats for row in data.latency_by_host}
    for host, values in (
        ("claude-code", cc_latencies),
        ("antigravity-cli", agy_latencies),
    ):
        stats = by_host[host]
        assert stats.tasks == len(values)
        got = [stats.p50, stats.p95, stats.p99]
        assert all(v is not None for v in got)
        assert [float(v) for v in got if v is not None] == pytest.approx(
            reference(values)
        )
    by_project = {row.key: row.stats for row in data.latency_by_project}
    assert by_project[PROJECT_Y].tasks == len(agy_latencies)
    overall = data.latency_overall
    assert overall.tasks == len(cc_latencies) + len(agy_latencies)
    assert overall.p95 is not None
    assert float(overall.p95) == pytest.approx(
        reference(cc_latencies + agy_latencies)[1]
    )


def test_latency_percentiles_are_rendered_by_host_and_project(store: ViewStore) -> None:
    # Arrange
    for i, value in enumerate([10_000, 20_000, 30_000, 40_000, 50_000]):
        store.add("v_tasks", task_id=f"t-{i}", latency_ms=value)
    store.add("v_task_latency", p50_ms=30_000.0, p95_ms=48_000.0, p99_ms=49_600.0)

    # Act
    html = build_report(store, options())

    # Assert
    performance = section(html, "performance")
    assert "Claude Code" in performance
    assert "project-x" in performance
    assert "30s" in performance  # P50
    assert "48s" in performance  # P95 = 40000 + 0.8 * 10000
    assert "50s" in performance  # P99 = 49600 ms rounds to 50 s
    assert "2026-10" in performance  # monthly v_task_latency row


# ---------------------------------------------------------- overview and money


def test_overview_groups_by_project_client_month_and_host(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    data = load_report_data(store, options())

    # Assert
    assert data.totals.calls == 3
    assert data.totals.cost.cost_usd == Decimal("7")
    assert {r.label: r.cost.cost_usd for r in data.by_project} == {
        "project-x": Decimal("3"),
        "project-y": Decimal("4"),
    }
    assert {r.label: r.cost.cost_usd for r in data.by_client} == {
        "(no client)": Decimal("3"),
        "Client Z": Decimal("4"),
    }
    assert {r.key: r.calls for r in data.by_month} == {"2026-09": 1, "2026-10": 2}
    assert {r.key: r.cost.cost_usd for r in data.by_host} == {
        "claude-code": Decimal("5"),
        "antigravity-cli": Decimal("2"),
    }
    assert {r.key for r in data.by_model} == {"claude-opus-5-5", "gemini-4-argon"}
    assert data.task_count == 2
    assert data.session_count == 2


def test_overview_html_shows_host_comparison_and_chart(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    html = build_report(store, options())

    # Assert
    overview = section(html, "overview")
    assert "Antigravity CLI" in overview
    assert "Claude Code" in overview
    assert "≈ $7.00" in overview
    assert 'class="card chart-card"' in overview
    assert 'class="chart chart-columns"' in overview
    assert "API-equivalent" in html


def test_money_is_rounded_only_at_presentation(store: ViewStore) -> None:
    # Arrange: per-call rounding would give $0.03 (half-up) or $0.00 (half-even)
    for _ in range(3):
        store.add("v_calls", cost_usd=Decimal("0.005000000"))

    # Act
    data = load_report_data(store, options())
    html = build_report(store, options())

    # Assert
    assert data.totals.cost.cost_usd == Decimal("0.015")
    assert "≈ $0.02" in section(html, "overview")


def test_unpriced_calls_render_as_lower_bound_with_models(store: ViewStore) -> None:
    # Arrange
    store.add("v_calls", cost_usd=Decimal("4.100000000"))
    for _ in range(2):
        store.add(
            "v_calls",
            host="antigravity-cli",
            model="gemini-x",
            model_effective="gemini-x",
            priced_model=None,
            unpriced=True,
            cost_usd=None,
        )

    # Act
    data = load_report_data(store, options())
    html = build_report(store, options())

    # Assert
    assert data.totals.cost.unpriced_calls == 2
    assert data.unpriced_models_in_scope == ("gemini-x",)
    cost_kpi = re.search(
        r'<span class="kpi-label">Total cost</span><span class="kpi-value">(.*?)</span>'
        r'(?:<span class="kpi-sub">|</div>)',
        html,
        re.S,
    )
    assert cost_kpi is not None
    assert cost_kpi.group(1).startswith("≥ $4.10")
    assert "(2 calls unpriced: gemini-x)" in cost_kpi.group(1)
    assert "≈" not in cost_kpi.group(1)


def test_only_unpriced_calls_never_render_as_zero_cost(store: ViewStore) -> None:
    # Arrange
    store.add(
        "v_calls",
        model_effective="gemini-x",
        priced_model=None,
        unpriced=True,
        cost_usd=None,
    )

    # Act
    html = build_report(store, options())

    # Assert
    assert "≈ $0.00" not in html
    assert "≥ $0.00" in html


def test_inferred_and_estimated_costs_are_starred_with_footnote(
    store: ViewStore,
) -> None:
    # Arrange
    store.add("v_calls", cost_usd=Decimal("1.200000000"), model_inferred=True)
    store.add("v_calls", cost_usd=Decimal("1.000000000"), estimated=True)

    # Act
    data = load_report_data(store, options())
    html = build_report(store, options())

    # Assert
    assert data.totals.cost.inferred_calls == 1
    assert data.totals.cost.estimated_calls == 1
    assert "≈ $2.20*" in html
    assert "* includes an inferred model or an estimated price" in html


def test_display_currency_is_shown_next_to_usd(store: ViewStore) -> None:
    # Arrange
    store.add("v_calls", cost_usd=Decimal("4.100000000"))

    # Act
    html = build_report(
        store, options(display_currency="COP", usd_rate=Decimal("4100"))
    )

    # Assert
    assert "≈ $4.10 (COP 16,810)" in html


# ---------------------------------------------------------------- filters


def test_project_and_date_range_filters_restrict_every_section(
    store: ViewStore,
) -> None:
    # Arrange
    populate_two_projects(store)
    store.add(
        "v_calls",
        local_date=date(2026, 10, 20),
        ts=BASE_TS + timedelta(days=6),
        cost_usd=Decimal("8.000000000"),
    )

    # Act
    data = load_report_data(
        store,
        options(
            project_id=PROJECT_X,
            date_from=date(2026, 10, 1),
            date_to=date(2026, 10, 15),
        ),
    )

    # Assert
    assert data.totals.calls == 2
    assert data.totals.cost.cost_usd == Decimal("3")
    assert [t.task_id for t in data.tasks] == ["t-x"]
    assert [s.session_id for s in data.sessions] == ["s-x"]
    assert "project-x" in data.scope_label
    assert "2026-10-01 → 2026-10-15" in data.scope_label


def test_month_filter_matches_equivalent_date_range(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    by_month = load_report_data(store, options(month="2026-09"))
    by_range = load_report_data(
        store, options(date_from=date(2026, 9, 1), date_to=date(2026, 9, 30))
    )

    # Assert
    assert by_month.totals == by_range.totals
    assert by_month.totals.cost.cost_usd == Decimal("4")


def test_client_filter_applies_to_views_without_client_column(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    data = load_report_data(store, options(client="Client Z"))

    # Assert
    assert data.totals.cost.cost_usd == Decimal("4")
    assert [s.session_id for s in data.sessions] == ["s-y"]
    assert [t.task_id for t in data.tasks] == ["t-y"]


# --------------------------------------------------------- tasks and agents


def test_tasks_show_agent_breakdown_parallelism_and_retries(store: ViewStore) -> None:
    # Arrange
    store.add("v_calls", task_id="t-dag")
    store.add(
        "v_tasks",
        task_id="t-dag",
        agent_runs=6,
        max_spawn_depth=1,
        parallelism=2.7,
        retries=1,
        retry_summary="qa-tester→code-implementer",
        cost_usd=Decimal("4.100000000"),
        test_runs=2,
        test_failures=1,
        files_touched=7,
        work_item_tag="Track 11",
    )
    store.add(
        "v_tasks",
        task_id="t-solo",
        seq_in_session=2,
        parallelism=1.0,
        started_at=BASE_TS + timedelta(hours=1),
    )
    store.add(
        "v_agent_type_cost",
        task_id="t-dag",
        agent_type="main",
        cost_usd=Decimal("0.400000000"),
        calls=9,
        cost_share=0.1,
    )
    store.add(
        "v_agent_type_cost",
        task_id="t-dag",
        agent_type="code-implementer",
        runs=2,
        cost_usd=Decimal("2.900000000"),
        calls=188,
        tool_calls=53,
        files_touched=7,
        cost_share=0.7,
    )
    store.add(
        "v_agent_type_cost",
        task_id="t-dag",
        agent_type="qa-tester",
        cost_usd=None,
        unpriced_calls=22,
        calls=22,
        test_runs=2,
        test_failures=1,
        cost_share=None,
    )

    # Act
    data = load_report_data(store, options())
    html = build_report(store, options())

    # Assert
    dag = next(t for t in data.tasks if t.task_id == "t-dag")
    assert [a.agent_type for a in dag.agents] == [
        "code-implementer",
        "main",
        "qa-tester",
    ]
    assert dag.parallelism == Decimal("2.7")
    tasks_html = section(html, "tasks")
    assert "code-implementer ×2" in tasks_html
    assert "2.7x" in tasks_html
    assert "1 retry qa-tester→code-implementer" in tasks_html
    assert "6 agents (max depth 1)" in tasks_html
    assert "1 ✓ · 1 ✗" in tasks_html
    assert "Track 11" in tasks_html
    solo_row = re.search(r'<tr data-task="t-solo".*?</tr>', tasks_html, re.S)
    assert solo_row is not None
    assert "1.0x" not in solo_row.group(0)  # BR-12: parallelism only with subagents


def test_work_item_tags_roll_up_tasks(store: ViewStore) -> None:
    # Arrange
    store.add("v_tasks", task_id="a", work_item_tag="Track 11", cost_usd=Decimal("1.5"))
    store.add(
        "v_tasks",
        task_id="b",
        work_item_tag="Track 11",
        host="antigravity-cli",
        cost_usd=Decimal("2.5"),
    )
    store.add("v_tasks", task_id="c", work_item_tag=None)

    # Act
    data = load_report_data(store, options())

    # Assert
    assert len(data.tags) == 1
    assert data.tags[0].tag == "Track 11"
    assert data.tags[0].tasks == 2
    assert data.tags[0].cost.cost_usd == Decimal("4")


def test_task_labels_never_reach_the_report(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    with_labels = build_report(store, options(show_task_labels=True))
    without_labels = build_report(store, options(show_task_labels=False))

    # Assert
    assert with_labels == without_labels
    assert "task #1" in with_labels


def test_sessions_section_lists_sessions(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    html = build_report(store, options())

    # Assert
    sessions = section(html, "sessions")
    assert "project-x" in sessions
    assert "42m 10s" in sessions
    assert "79.0%" in sessions


# --------------------------------------------------------------- efficiency


def test_efficiency_metrics_by_host(store: ViewStore) -> None:
    # Arrange
    store.add(
        "v_calls",
        input_tokens=1_000,
        cache_write_5m_tokens=0,
        cache_write_1h_tokens=0,
        cache_read_tokens=9_000,
        prompt_tokens=10_000,
        is_error=False,
    )
    store.add(
        "v_calls",
        input_tokens=1_000,
        cache_write_5m_tokens=1_000,
        cache_write_1h_tokens=0,
        cache_read_tokens=8_000,
        prompt_tokens=10_000,
        is_error=True,
    )
    store.add(
        "v_calls",
        prompt_tokens=None,
        tokens_unknown=True,
        input_tokens=None,
        cache_write_5m_tokens=None,
        cache_write_1h_tokens=None,
        cache_read_tokens=None,
        cost_usd=None,
        unpriced=True,
        output_tokens=None,
    )
    store.add("v_tasks", task_id="a", output_tokens=300)
    store.add("v_tasks", task_id="b", output_tokens=500)

    # Act
    data = load_report_data(store, options())

    # Assert
    row = next(r for r in data.efficiency_by_host if r.key == "claude-code")
    assert row.cache_hit_ratio == Decimal(17_000) / Decimal(20_000)
    assert row.avg_context_tokens == Decimal(10_000)
    assert row.output_per_task == Decimal(400)
    assert row.error_rate == Decimal(1) / Decimal(3)
    efficiency_html = section(build_report(store, options()), "efficiency")
    assert "85.0%" in efficiency_html
    assert "10K" in efficiency_html


# ---------------------------------------------------------- cost vs billable


def test_cost_vs_billable_shows_ratio_and_dash_without_rate(store: ViewStore) -> None:
    # Arrange
    store.add("v_calls", cost_usd=Decimal("12.5"))
    store.add("v_client_month")
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
        dev_hours=Decimal("4.00"),
    )

    # Act
    html = build_report(
        store, options(display_currency="COP", usd_rate=Decimal("4100"))
    )

    # Assert
    billing = section(html, "billing")
    assert "Client Z" in billing
    assert "COP 1,040,000" in billing
    assert "$253.66" in billing
    assert "4.9%" in billing
    no_rate = re.search(
        r'<tr data-project="git:bbbbbbbbbbbbbbbb".*?</tr>', billing, re.S
    )
    assert no_rate is not None
    assert "—" in no_rate.group(0)
    assert "0.0%" not in no_rate.group(0)


def test_cost_vs_billable_ratio_is_lower_bound_when_cost_partial(
    store: ViewStore,
) -> None:
    # Arrange
    store.add("v_calls")
    store.add("v_client_month", unpriced_calls=3)

    # Act
    html = build_report(store, options())

    # Assert
    assert "≥ 4.9%" in section(html, "billing")


def test_billing_month_filter_uses_months_spanned_by_range(store: ViewStore) -> None:
    # Arrange
    store.add("v_calls")
    store.add("v_client_month", local_month="2026-08")
    store.add("v_client_month", local_month="2026-10")

    # Act
    data = load_report_data(
        store, options(date_from=date(2026, 9, 15), date_to=date(2026, 10, 2))
    )

    # Assert
    assert [r.local_month for r in data.billable] == ["2026-10"]


# ------------------------------------------------------------- data quality


def test_data_quality_lists_unpriced_untracked_and_health(store: ViewStore) -> None:
    # Arrange
    store.add("v_calls")
    store.add("v_unpriced_models")
    store.add("v_untracked")
    store.add("v_health")

    # Act
    html = build_report(store, options())

    # Assert
    quality = section(html, "data-quality")
    assert "gemini-x" in quality
    assert "312" in quality
    assert "legacy_pb" in quality
    assert "never estimated" in quality
    assert "2026-09-19" in quality  # earliest call date in v_health
    notices = section(html, "notices")
    assert "100 conversations untracked" in notices


# ------------------------------------------------------------- safety / privacy


def test_text_values_are_html_escaped(store: ViewStore) -> None:
    # Arrange
    evil = "<script>alert('x')</script>&"
    store.connection.execute(
        "UPDATE t_projects SET display_name = ? WHERE project_id = ?", [evil, PROJECT_X]
    )
    store.add("v_calls")
    store.add(
        "v_tasks",
        display_name=evil,
        critical_path=evil,
        retry_summary=evil,
        retries=1,
        work_item_tag=evil,
    )

    # Act
    html = build_report(store, options())

    # Assert
    assert "<script>alert" not in html
    assert "&lt;script&gt;alert(&#x27;x&#x27;)&lt;/script&gt;&amp;" in html
    assert_well_formed(html)


def test_embedded_report_metadata_is_safe_json(store: ViewStore) -> None:
    # Arrange
    store.add("v_calls")

    # Act
    html = build_report(store, options(client="</script><b>"))

    # Assert
    match = re.search(
        r'<script type="application/json" id="report-meta">(.*?)</script>', html, re.S
    )
    assert match is not None
    payload = match.group(1)
    assert "<" not in payload and ">" not in payload and "&" not in payload
    meta = json.loads(payload)
    assert meta["filters"]["client"] == "</script><b>"
    assert meta["generated_at"] == "2026-10-16T18:00:00+00:00"


def test_report_reads_only_section6_views(store: ViewStore) -> None:
    # Arrange
    populate_two_projects(store)

    # Act
    build_report(store, options(client="Client Z", month="2026-09"))

    # Assert
    referenced = {
        name
        for sql in store.executed
        for name in re.findall(r"\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*)", sql, re.I)
    }
    assert referenced
    assert referenced <= SECTION6_VIEWS


def test_float_money_from_store_is_rejected(store: ViewStore) -> None:
    # Arrange
    class FloatMoneyStore:
        def query(
            self, sql: str, params: Sequence[object] = ()
        ) -> list[dict[str, object]]:
            rows = store.query(sql, params)
            return [
                {
                    k: (float(v) if k == "cost_usd" and isinstance(v, Decimal) else v)
                    for k, v in row.items()
                }
                for row in rows
            ]

    store.add("v_calls")

    # Act / Assert
    with pytest.raises(TypeError, match="cost_usd"):
        build_report(FloatMoneyStore(), options())


def _view_rows_from_batches(store: ViewStore, home: Path) -> None:
    """Project real reader output onto the test-local §6 tables (PV-01 data path)."""
    reader = ClaudeCodeReader(home)
    for unit in reader.discover():
        batch = reader.read_unit(unit, make_options(description_salt=b"salt"))
        calls: tuple[CallRecord, ...] = batch.calls
        tasks: tuple[TaskRecord, ...] = batch.tasks
        runs: tuple[AgentRunRecord, ...] = batch.agent_runs
        for call in calls:
            store.add(
                "v_calls",
                call_id=call.call_id,
                host=str(call.host),
                project_id=PROJECT_X,
                session_id=call.session_id,
                task_id=call.task_id,
                agent_run_id=call.agent_run_id,
                ts=call.ts,
                local_date=call.ts.date(),
                model=call.model,
                model_label=call.model_label,
                model_effective=call.model,
                priced_model=call.model,
                input_tokens=call.input_tokens,
                output_tokens=call.output_tokens,
                cache_read_tokens=call.cache_read_tokens,
                latency_ms=call.latency_ms,
                is_error=call.is_error,
            )
        for task in tasks:
            store.add(
                "v_tasks",
                task_id=task.task_id,
                session_id=task.session_id,
                host=str(task.host),
                seq_in_session=task.seq_in_session,
                started_at=task.started_at,
                ended_at=task.ended_at,
                local_date=task.started_at.date(),
                wall_clock_ms=task.wall_clock_ms,
                active_ms=task.active_ms,
                latency_ms=task.wall_clock_ms,
                status=str(task.status),
                agent_runs=task.agent_runs,
                max_spawn_depth=task.max_spawn_depth,
                critical_path=task.critical_path,
                retries=task.retries,
                retry_summary=task.retry_summary,
            )
        for run in runs:
            store.add(
                "v_agent_runs",
                agent_run_id=run.agent_run_id,
                task_id=run.task_id,
                session_id=run.session_id,
                host=str(run.host),
                parent_agent_run_id=run.parent_agent_run_id,
                agent_type=run.agent_type,
                spawn_depth=run.spawn_depth,
                started_at=run.started_at,
                ended_at=run.ended_at,
                active_ms=run.active_ms,
                status=str(run.status),
            )
            store.add(
                "v_agent_type_cost",
                task_id=run.task_id,
                agent_type=run.agent_type,
                active_ms=run.active_ms,
                files_touched=run.files_touched,
                test_runs=run.test_runs,
                test_failures=run.test_failures,
            )


@pytest.mark.privacy
def test_pv01_canary_absent_from_report_built_from_reader_output(
    store: ViewStore, tmp_path: Path
) -> None:
    # Arrange
    claude = ClaudeHome(tmp_path / ".claude")
    claude.write(claude_standard_session())
    _view_rows_from_batches(store, claude.root)
    assert store.query("SELECT COUNT(*) AS n FROM v_calls")[0]["n"] != 0

    # Act
    html = build_report(store, options(show_task_labels=True))

    # Assert
    assert CANARY not in html
    assert "code-implementer" in html


# --------------------------------------------------------------- options


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"month": "2026-13"}, "month"),
        ({"month": "October"}, "month"),
        ({"month": "2026-10", "date_from": date(2026, 10, 1)}, "month"),
        ({"date_from": date(2026, 10, 2), "date_to": date(2026, 10, 1)}, "date_from"),
        ({"usd_rate": Decimal("0")}, "usd_rate"),
        ({"generated_at": datetime(2026, 10, 16, 18, 0)}, "generated_at"),
    ],
)
def test_report_options_reject_invalid_values(
    kwargs: dict[str, Any], message: str
) -> None:
    # Act / Assert
    with pytest.raises(ValueError, match=message):
        ReportOptions(**{"generated_at": GENERATED_AT, **kwargs})


def test_report_options_default_generated_at_is_aware_utc() -> None:
    # Act
    opts = ReportOptions()

    # Assert
    assert opts.generated_at.tzinfo is not None
    assert opts.generated_at.utcoffset() == timedelta(0)


# ----------------------------------------------------------- write_report


def test_write_report_writes_atomically_with_private_permissions(
    tmp_path: Path,
) -> None:
    # Arrange
    out = tmp_path / "nested" / "report.html"

    # Act
    written = write_report("<!DOCTYPE html><html></html>", out)
    write_report("<!DOCTYPE html><html>v2</html>", out)

    # Assert
    assert written == out
    assert out.read_text(encoding="utf-8") == "<!DOCTYPE html><html>v2</html>"
    assert stat.S_IMODE(out.stat().st_mode) == 0o600
    assert sorted(p.name for p in out.parent.iterdir()) == ["report.html"]


def test_write_report_removes_temp_file_when_replace_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    out = tmp_path / "report.html"
    out.write_text("old", encoding="utf-8")

    def failing_replace(src: object, dst: object) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", failing_replace)

    # Act
    with pytest.raises(OSError, match="disk full"):
        write_report("new", out)

    # Assert
    assert out.read_text(encoding="utf-8") == "old"
    assert sorted(p.name for p in tmp_path.iterdir()) == ["report.html"]
