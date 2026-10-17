"""Load the report's data model from the contracts.md §6 views, and nothing else.

All SQL here is static text built from fixed fragments; user-supplied filter values are
only ever bound as parameters. Money columns must arrive as ``Decimal`` (I-5): a
``float`` cost is rejected with ``TypeError`` rather than silently converted.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Final, Protocol

from agent_meter.report.options import ReportOptions
from agent_meter.report.stats import LatencyStats, latency_stats
from agent_meter.report.values import CostTotal

__all__ = [
    "TASK_LIMIT",
    "TIMELINE_LIMIT",
    "AgentRunRow",
    "AgentTypeRow",
    "BillableRow",
    "EfficiencyRow",
    "HealthRow",
    "LatencyRow",
    "MonthlyLatencyRow",
    "ProjectMonthRow",
    "ReportData",
    "SessionRow",
    "TagRow",
    "TaskRow",
    "TaskTimeline",
    "UnpricedModelRow",
    "UntrackedRow",
    "UsageRow",
    "ViewSource",
    "load_report_data",
]

TASK_LIMIT: Final = 200
TIMELINE_LIMIT: Final = 6  # most recent multi-agent tasks drawn as agent-run timelines
SESSION_LIMIT: Final = 100
NO_CLIENT: Final = "(no client)"
UNPRICED_MODEL: Final = "(unpriced)"
UNKNOWN_MODEL: Final = "(unknown model)"

Row = Mapping[str, object]


class ViewSource(Protocol):
    """The slice of ``store.Store`` (contracts.md §3.7) the report depends on."""

    def query(
        self, sql: str, params: Sequence[object] = ()
    ) -> list[dict[str, object]]: ...


# ----------------------------------------------------------------- data model


@dataclass(frozen=True, slots=True)
class UsageRow:
    """One aggregate over ``v_daily_project_cost`` (by project, host, day, ...)."""

    key: str
    label: str
    calls: int
    input_tokens: int | None
    output_tokens: int | None
    cache_write_tokens: int | None
    cache_read_tokens: int | None
    cost: CostTotal
    error_calls: int
    client: str | None = None

    @property
    def prompt_tokens(self) -> int:
        return sum(
            v or 0
            for v in (
                self.input_tokens,
                self.cache_write_tokens,
                self.cache_read_tokens,
            )
        )

    @property
    def cache_hit_ratio(self) -> Decimal | None:
        prompt = self.prompt_tokens
        if prompt == 0 or self.cache_read_tokens is None:
            return None
        return Decimal(self.cache_read_tokens) / Decimal(prompt)

    @property
    def error_rate(self) -> Decimal | None:
        return (
            None if self.calls == 0 else Decimal(self.error_calls) / Decimal(self.calls)
        )


EMPTY_TOTAL: Final = UsageRow(
    key="total",
    label="Total",
    calls=0,
    input_tokens=None,
    output_tokens=None,
    cache_write_tokens=None,
    cache_read_tokens=None,
    cost=CostTotal(None),
    error_calls=0,
)


@dataclass(frozen=True, slots=True)
class AgentTypeRow:
    agent_type: str
    runs: int
    calls: int
    cost: CostTotal
    active_ms: int
    tool_calls: int
    files_touched: int
    test_runs: int
    test_failures: int
    cost_share: Decimal | None


@dataclass(frozen=True, slots=True)
class TaskRow:
    task_id: str
    session_id: str
    host: str
    project_label: str
    seq_in_session: int
    started_at: datetime
    local_date: date
    wall_clock_ms: int
    active_ms: int
    latency_ms: int | None
    status: str
    agent_runs: int
    max_spawn_depth: int
    parallelism: Decimal | None
    retries: int
    retry_summary: str
    calls: int
    output_tokens: int | None
    cost: CostTotal
    work_item_tag: str | None
    tool_calls: int
    files_touched: int
    test_runs: int
    test_failures: int
    agents: tuple[AgentTypeRow, ...]


@dataclass(frozen=True, slots=True)
class AgentRunRow:
    """One agent run of a task (``v_agent_runs``), for the task timeline."""

    agent_run_id: str
    agent_type: str
    spawn_depth: int
    started_at: datetime
    ended_at: datetime
    active_ms: int
    status: str
    calls: int
    cost: CostTotal


@dataclass(frozen=True, slots=True)
class TaskTimeline:
    task: TaskRow
    runs: tuple[AgentRunRow, ...]  # ordered by start time


@dataclass(frozen=True, slots=True)
class ProjectMonthRow:
    local_month: str
    key: str  # project_id
    label: str
    cost: CostTotal


@dataclass(frozen=True, slots=True)
class SessionRow:
    session_id: str
    host: str
    project_label: str
    started_at: datetime
    local_date: date
    wall_clock_ms: int
    active_ms: int
    tasks: int
    calls: int
    cost: CostTotal
    cache_hit_ratio: Decimal | None
    task_p50_ms: Decimal | None
    task_p95_ms: Decimal | None
    status: str


@dataclass(frozen=True, slots=True)
class TagRow:
    tag: str
    tasks: int
    wall_clock_ms: int
    active_ms: int
    cost: CostTotal


@dataclass(frozen=True, slots=True)
class LatencyRow:
    key: str
    label: str
    stats: LatencyStats


@dataclass(frozen=True, slots=True)
class MonthlyLatencyRow:
    local_month: str
    project_label: str
    host: str
    tasks: int
    p50_ms: Decimal | None
    p95_ms: Decimal | None
    p99_ms: Decimal | None


@dataclass(frozen=True, slots=True)
class EfficiencyRow:
    key: str
    label: str
    cache_hit_ratio: Decimal | None
    avg_context_tokens: Decimal | None
    output_per_task: Decimal | None
    error_rate: Decimal | None


@dataclass(frozen=True, slots=True)
class BillableRow:
    local_month: str
    client: str | None
    project_id: str
    project_label: str
    billing_model: str | None
    rate_currency: str | None
    cost: CostTotal
    dev_hours: Decimal | None
    billable_value: Decimal | None
    billable_usd: Decimal | None
    ai_cost_ratio: Decimal | None


@dataclass(frozen=True, slots=True)
class UnpricedModelRow:
    host: str
    model: str
    calls: int
    first_ts: datetime | None
    last_ts: datetime | None


@dataclass(frozen=True, slots=True)
class UntrackedRow:
    host: str
    reason: str
    conversations: int
    observed_from: date | None
    observed_to: date | None


@dataclass(frozen=True, slots=True)
class HealthRow:
    host: str
    last_ingested_at: datetime | None
    units: int
    unknown_formats: int
    diagnostics_7d: int
    earliest_call_ts: datetime | None


@dataclass(frozen=True, slots=True)
class ReportData:
    options: ReportOptions
    store_has_data: bool
    scope_label: str
    totals: UsageRow
    unpriced_models_in_scope: tuple[str, ...]
    task_count: int
    session_count: int
    by_day: tuple[UsageRow, ...]
    by_month: tuple[UsageRow, ...]
    by_project: tuple[UsageRow, ...]
    by_client: tuple[UsageRow, ...]
    by_host: tuple[UsageRow, ...]
    by_model: tuple[UsageRow, ...]
    by_project_month: tuple[ProjectMonthRow, ...]
    tasks: tuple[TaskRow, ...]
    agent_types: tuple[AgentTypeRow, ...]  # scope-wide, by cost
    timelines: tuple[TaskTimeline, ...]
    sessions: tuple[SessionRow, ...]
    tags: tuple[TagRow, ...]
    latency_overall: LatencyStats
    latency_by_host: tuple[LatencyRow, ...]
    latency_by_project: tuple[LatencyRow, ...]
    latency_monthly: tuple[MonthlyLatencyRow, ...]
    efficiency_by_host: tuple[EfficiencyRow, ...]
    efficiency_by_project: tuple[EfficiencyRow, ...]
    billable: tuple[BillableRow, ...]
    unpriced_models: tuple[UnpricedModelRow, ...]
    untracked: tuple[UntrackedRow, ...]
    health: tuple[HealthRow, ...]

    @property
    def scope_empty(self) -> bool:
        return (
            self.totals.calls == 0 and self.task_count == 0 and self.session_count == 0
        )


# ----------------------------------------------------------- value coercion


def _text(row: Row, key: str) -> str:
    value = row[key]
    if value is None:
        raise ValueError(f"view column {key} is unexpectedly NULL")
    return str(value)


def _opt_text(row: Row, key: str) -> str | None:
    value = row[key]
    return None if value is None else str(value)


def _opt_int(row: Row, key: str) -> int | None:
    value = row[key]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | Decimal):
        raise TypeError(
            f"view column {key} must be an integer, got {type(value).__name__}"
        )
    return int(value)


def _count(row: Row, key: str) -> int:
    """Counters and SUMs of counters: NULL (empty aggregate) means 0."""
    value = _opt_int(row, key)
    return 0 if value is None else value


def _money(row: Row, key: str) -> Decimal | None:
    value = row[key]
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, Decimal | int):
        raise TypeError(
            f"money column {key} must be Decimal, got {type(value).__name__} (I-5)"
        )
    return Decimal(value)


def _ratio(row: Row, key: str) -> Decimal | None:
    """Non-money ratios and percentiles; DOUBLE columns are read via their repr."""
    value = row[key]
    if value is None:
        return None
    if isinstance(value, float):
        return Decimal(repr(value))
    if isinstance(value, bool) or not isinstance(value, Decimal | int):
        raise TypeError(
            f"view column {key} must be numeric, got {type(value).__name__}"
        )
    return Decimal(value)


def _opt_datetime(row: Row, key: str) -> datetime | None:
    value = row[key]
    if value is None:
        return None
    if not isinstance(value, datetime):
        raise TypeError(
            f"view column {key} must be a timestamp, got {type(value).__name__}"
        )
    return value


def _datetime(row: Row, key: str) -> datetime:
    value = _opt_datetime(row, key)
    if value is None:
        raise ValueError(f"view column {key} is unexpectedly NULL")
    return value


def _opt_date(row: Row, key: str) -> date | None:
    value = row[key]
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date()
    if not isinstance(value, date):
        raise TypeError(f"view column {key} must be a date, got {type(value).__name__}")
    return value


def _date(row: Row, key: str) -> date:
    value = _opt_date(row, key)
    if value is None:
        raise ValueError(f"view column {key} is unexpectedly NULL")
    return value


def _cost(row: Row, *, flags: bool = True) -> CostTotal:
    return CostTotal(
        cost_usd=_money(row, "cost_usd"),
        unpriced_calls=_count(row, "unpriced_calls"),
        estimated_calls=_count(row, "estimated_calls") if flags else 0,
        inferred_calls=_count(row, "inferred_calls") if flags else 0,
    )


def _divide(numerator: int | None, denominator: int) -> Decimal | None:
    if numerator is None or denominator == 0:
        return None
    return Decimal(numerator) / Decimal(denominator)


# ------------------------------------------------------------------ scoping


_CLIENT_PROJECTS: Final = (
    "project_id IN (SELECT project_id FROM v_daily_project_cost WHERE client = ? "
    "UNION SELECT project_id FROM v_tasks WHERE client = ?)"
)


@dataclass(frozen=True, slots=True)
class _Filter:
    sql: str
    params: tuple[object, ...]

    def where(self, *extra: str) -> str:
        clauses = [c for c in (self.sql, *extra) if c]
        return f" WHERE {' AND '.join(clauses)}" if clauses else ""


@dataclass(frozen=True, slots=True)
class _Scope:
    options: ReportOptions

    def filter(
        self, *, dated: bool, has_client: bool, monthly: bool = False
    ) -> _Filter:
        clauses: list[str] = []
        params: list[object] = []
        if dated:
            start, end = self.options.date_range()
            for bound, op in ((start, ">="), (end, "<=")):
                if bound is not None:
                    clauses.append(f"local_date {op} ?")
                    params.append(bound)
        if monthly:
            first, last = self.options.month_range()
            for month, op in ((first, ">="), (last, "<=")):
                if month is not None:
                    clauses.append(f"local_month {op} ?")
                    params.append(month)
        if self.options.project_id is not None:
            clauses.append("project_id = ?")
            params.append(self.options.project_id)
        if self.options.client is not None:
            if has_client:
                clauses.append("client = ?")
                params.append(self.options.client)
            else:
                clauses.append(_CLIENT_PROJECTS)
                params.extend((self.options.client, self.options.client))
        return _Filter(" AND ".join(clauses), tuple(params))


# ------------------------------------------------------------------ loaders

_USAGE_COLUMNS: Final = (
    "SUM(calls) AS calls, SUM(input_tokens) AS input_tokens, "
    "SUM(output_tokens) AS output_tokens, SUM(cache_write_tokens) AS cache_write_tokens, "
    "SUM(cache_read_tokens) AS cache_read_tokens, SUM(cost_usd) AS cost_usd, "
    "SUM(unpriced_calls) AS unpriced_calls, SUM(estimated_calls) AS estimated_calls, "
    "SUM(inferred_calls) AS inferred_calls, SUM(error_calls) AS error_calls"
)
_BY_COST: Final = "cost_usd DESC NULLS LAST, calls DESC, key"

# (key expression, label expression, ORDER BY) per grouping; fixed text, never user input.
_GROUPINGS: Final = {
    "total": ("'total'", "'Total'", "key"),
    "day": ("CAST(local_date AS VARCHAR)", "CAST(local_date AS VARCHAR)", "key"),
    "month": ("local_month", "local_month", "key"),
    "project": ("project_id", "COALESCE(display_name, project_id)", _BY_COST),
    "client": (
        f"COALESCE(client, '{NO_CLIENT}')",
        f"COALESCE(client, '{NO_CLIENT}')",
        _BY_COST,
    ),
    "host": ("host", "host", _BY_COST),
    "model": (
        f"COALESCE(priced_model, '{UNPRICED_MODEL}')",
        f"COALESCE(priced_model, '{UNPRICED_MODEL}')",
        _BY_COST,
    ),
}


def _usage(store: ViewSource, scope: _Scope, grouping: str) -> tuple[UsageRow, ...]:
    key_sql, label_sql, order_sql = _GROUPINGS[grouping]
    flt = scope.filter(dated=True, has_client=True)
    rows = store.query(
        f"SELECT {key_sql} AS key, MIN({label_sql}) AS label, MIN(client) AS client, "
        f"{_USAGE_COLUMNS} FROM v_daily_project_cost{flt.where()} "
        f"GROUP BY 1 ORDER BY {order_sql}",
        flt.params,
    )
    return tuple(
        UsageRow(
            key=_text(r, "key"),
            label=_text(r, "label"),
            calls=_count(r, "calls"),
            input_tokens=_opt_int(r, "input_tokens"),
            output_tokens=_opt_int(r, "output_tokens"),
            cache_write_tokens=_opt_int(r, "cache_write_tokens"),
            cache_read_tokens=_opt_int(r, "cache_read_tokens"),
            cost=_cost(r),
            error_calls=_count(r, "error_calls"),
            client=_opt_text(r, "client"),
        )
        for r in rows
    )


def _project_months(store: ViewSource, scope: _Scope) -> tuple[ProjectMonthRow, ...]:
    flt = scope.filter(dated=True, has_client=True)
    rows = store.query(
        "SELECT local_month, project_id AS key, "
        "MIN(COALESCE(display_name, project_id)) AS label, SUM(cost_usd) AS cost_usd, "
        "SUM(unpriced_calls) AS unpriced_calls, SUM(estimated_calls) AS estimated_calls, "
        "SUM(inferred_calls) AS inferred_calls "
        f"FROM v_daily_project_cost{flt.where()} GROUP BY 1, 2 ORDER BY 1, 2",
        flt.params,
    )
    return tuple(
        ProjectMonthRow(
            local_month=_text(r, "local_month"),
            key=_text(r, "key"),
            label=_text(r, "label"),
            cost=_cost(r),
        )
        for r in rows
    )


def _unpriced_in_scope(store: ViewSource, scope: _Scope) -> tuple[str, ...]:
    flt = scope.filter(dated=True, has_client=False)
    rows = store.query(
        f"SELECT DISTINCT COALESCE(model_effective, '{UNKNOWN_MODEL}') AS model "
        f"FROM v_calls{flt.where('unpriced')} ORDER BY 1",
        flt.params,
    )
    return tuple(_text(r, "model") for r in rows)


def _scalar_count(store: ViewSource, sql: str, params: Sequence[object] = ()) -> int:
    rows = store.query(sql, params)
    return _count(rows[0], "n") if rows else 0


def _agent_rows(
    store: ViewSource, task_ids: Sequence[str]
) -> dict[str, list[AgentTypeRow]]:
    agents: dict[str, list[AgentTypeRow]] = defaultdict(list)
    if not task_ids:
        return agents
    marks = ", ".join("?" for _ in task_ids)
    rows = store.query(
        "SELECT task_id, agent_type, runs, calls, cost_usd, unpriced_calls, active_ms, "
        "tool_calls, files_touched, test_runs, test_failures, cost_share "
        f"FROM v_agent_type_cost WHERE task_id IN ({marks}) "
        "ORDER BY task_id, cost_usd DESC NULLS LAST, agent_type",
        tuple(task_ids),
    )
    for r in rows:
        agents[_text(r, "task_id")].append(
            AgentTypeRow(
                agent_type=_text(r, "agent_type"),
                runs=_count(r, "runs"),
                calls=_count(r, "calls"),
                cost=_cost(r, flags=False),
                active_ms=_count(r, "active_ms"),
                tool_calls=_count(r, "tool_calls"),
                files_touched=_count(r, "files_touched"),
                test_runs=_count(r, "test_runs"),
                test_failures=_count(r, "test_failures"),
                cost_share=_ratio(r, "cost_share"),
            )
        )
    return agents


def _agent_types(store: ViewSource, scope: _Scope) -> tuple[AgentTypeRow, ...]:
    """Agent-type totals over every task in scope; share = cost ÷ priced cost in scope."""
    flt = scope.filter(dated=True, has_client=True)
    rows = store.query(
        "SELECT agent_type, SUM(runs) AS runs, SUM(calls) AS calls, SUM(cost_usd) AS cost_usd, "
        "SUM(unpriced_calls) AS unpriced_calls, SUM(active_ms) AS active_ms, "
        "SUM(tool_calls) AS tool_calls, SUM(files_touched) AS files_touched, "
        "SUM(test_runs) AS test_runs, SUM(test_failures) AS test_failures "
        "FROM v_agent_type_cost "
        f"WHERE task_id IN (SELECT task_id FROM v_tasks{flt.where()}) "
        "GROUP BY 1 ORDER BY cost_usd DESC NULLS LAST, agent_type",
        flt.params,
    )
    costs = [_cost(r, flags=False) for r in rows]
    priced = sum((c.cost_usd for c in costs if c.cost_usd is not None), Decimal(0))
    return tuple(
        AgentTypeRow(
            agent_type=_text(r, "agent_type"),
            runs=_count(r, "runs"),
            calls=_count(r, "calls"),
            cost=cost,
            active_ms=_count(r, "active_ms"),
            tool_calls=_count(r, "tool_calls"),
            files_touched=_count(r, "files_touched"),
            test_runs=_count(r, "test_runs"),
            test_failures=_count(r, "test_failures"),
            cost_share=cost.cost_usd / priced
            if cost.cost_usd is not None and priced > 0
            else None,
        )
        for r, cost in zip(rows, costs, strict=True)
    )


def _timelines(
    store: ViewSource, tasks: Sequence[TaskRow]
) -> tuple[TaskTimeline, ...]:
    """Agent runs of the most recent tasks that spawned subagents."""
    chosen = [task for task in tasks if task.agent_runs > 1][:TIMELINE_LIMIT]
    if not chosen:
        return ()
    marks = ", ".join("?" for _ in chosen)
    rows = store.query(
        "SELECT agent_run_id, task_id, agent_type, spawn_depth, started_at, ended_at, "
        "active_ms, status, calls, cost_usd, unpriced_calls "
        f"FROM v_agent_runs WHERE task_id IN ({marks}) "
        "ORDER BY task_id, started_at, spawn_depth, agent_run_id",
        tuple(task.task_id for task in chosen),
    )
    runs: dict[str, list[AgentRunRow]] = defaultdict(list)
    for r in rows:
        runs[_text(r, "task_id")].append(
            AgentRunRow(
                agent_run_id=_text(r, "agent_run_id"),
                agent_type=_text(r, "agent_type"),
                spawn_depth=_count(r, "spawn_depth"),
                started_at=_datetime(r, "started_at"),
                ended_at=_datetime(r, "ended_at"),
                active_ms=_count(r, "active_ms"),
                status=_text(r, "status"),
                calls=_count(r, "calls"),
                cost=_cost(r, flags=False),
            )
        )
    return tuple(
        TaskTimeline(task=task, runs=tuple(runs[task.task_id]))
        for task in chosen
        if runs.get(task.task_id)
    )


def _tasks(store: ViewSource, scope: _Scope) -> tuple[int, tuple[TaskRow, ...]]:
    flt = scope.filter(dated=True, has_client=True)
    total = _scalar_count(
        store, f"SELECT COUNT(*) AS n FROM v_tasks{flt.where()}", flt.params
    )
    rows = store.query(
        "SELECT task_id, session_id, host, project_id, display_name, seq_in_session, "
        "started_at, local_date, wall_clock_ms, active_ms, latency_ms, status, agent_runs, "
        "max_spawn_depth, parallelism, retries, retry_summary, calls, output_tokens, "
        "cost_usd, unpriced_calls, estimated_calls, inferred_calls, work_item_tag, "
        "tool_calls, files_touched, test_runs, test_failures "
        f"FROM v_tasks{flt.where()} ORDER BY started_at DESC, task_id LIMIT {TASK_LIMIT}",
        flt.params,
    )
    agents = _agent_rows(store, [_text(r, "task_id") for r in rows])
    tasks = tuple(
        TaskRow(
            task_id=_text(r, "task_id"),
            session_id=_text(r, "session_id"),
            host=_text(r, "host"),
            project_label=_opt_text(r, "display_name") or _text(r, "project_id"),
            seq_in_session=_count(r, "seq_in_session"),
            started_at=_datetime(r, "started_at"),
            local_date=_date(r, "local_date"),
            wall_clock_ms=_count(r, "wall_clock_ms"),
            active_ms=_count(r, "active_ms"),
            latency_ms=_opt_int(r, "latency_ms"),
            status=_text(r, "status"),
            agent_runs=_count(r, "agent_runs"),
            max_spawn_depth=_count(r, "max_spawn_depth"),
            parallelism=_ratio(r, "parallelism"),
            retries=_count(r, "retries"),
            retry_summary=_opt_text(r, "retry_summary") or "",
            calls=_count(r, "calls"),
            output_tokens=_opt_int(r, "output_tokens"),
            cost=_cost(r),
            work_item_tag=_opt_text(r, "work_item_tag"),
            tool_calls=_count(r, "tool_calls"),
            files_touched=_count(r, "files_touched"),
            test_runs=_count(r, "test_runs"),
            test_failures=_count(r, "test_failures"),
            agents=tuple(agents.get(_text(r, "task_id"), ())),
        )
        for r in rows
    )
    return total, tasks


def _tags(store: ViewSource, scope: _Scope) -> tuple[TagRow, ...]:
    flt = scope.filter(dated=True, has_client=True)
    rows = store.query(
        "SELECT work_item_tag AS tag, COUNT(*) AS tasks, SUM(wall_clock_ms) AS wall_clock_ms, "
        "SUM(active_ms) AS active_ms, SUM(cost_usd) AS cost_usd, "
        "SUM(unpriced_calls) AS unpriced_calls, SUM(estimated_calls) AS estimated_calls, "
        "SUM(inferred_calls) AS inferred_calls "
        f"FROM v_tasks{flt.where('work_item_tag IS NOT NULL')} GROUP BY 1 ORDER BY 1",
        flt.params,
    )
    return tuple(
        TagRow(
            tag=_text(r, "tag"),
            tasks=_count(r, "tasks"),
            wall_clock_ms=_count(r, "wall_clock_ms"),
            active_ms=_count(r, "active_ms"),
            cost=_cost(r),
        )
        for r in rows
    )


def _sessions(store: ViewSource, scope: _Scope) -> tuple[int, tuple[SessionRow, ...]]:
    flt = scope.filter(dated=True, has_client=False)
    total = _scalar_count(
        store, f"SELECT COUNT(*) AS n FROM v_sessions{flt.where()}", flt.params
    )
    rows = store.query(
        "SELECT session_id, host, project_id, display_name, started_at, local_date, "
        "wall_clock_ms, active_ms, tasks, calls, cost_usd, unpriced_calls, cache_hit_ratio, "
        "task_p50_ms, task_p95_ms, status "
        f"FROM v_sessions{flt.where()} ORDER BY started_at DESC, session_id "
        f"LIMIT {SESSION_LIMIT}",
        flt.params,
    )
    sessions = tuple(
        SessionRow(
            session_id=_text(r, "session_id"),
            host=_text(r, "host"),
            project_label=_opt_text(r, "display_name") or _text(r, "project_id"),
            started_at=_datetime(r, "started_at"),
            local_date=_date(r, "local_date"),
            wall_clock_ms=_count(r, "wall_clock_ms"),
            active_ms=_count(r, "active_ms"),
            tasks=_count(r, "tasks"),
            calls=_count(r, "calls"),
            cost=_cost(r, flags=False),
            cache_hit_ratio=_ratio(r, "cache_hit_ratio"),
            task_p50_ms=_ratio(r, "task_p50_ms"),
            task_p95_ms=_ratio(r, "task_p95_ms"),
            status=_text(r, "status"),
        )
        for r in rows
    )
    return total, sessions


@dataclass(frozen=True, slots=True)
class _Latencies:
    overall: LatencyStats
    by_host: tuple[LatencyRow, ...]
    by_project: tuple[LatencyRow, ...]
    project_names: dict[str, str]


def _latencies(store: ViewSource, scope: _Scope) -> _Latencies:
    """P50/P95/P99 over finished tasks in scope (same rule as ``v_task_latency``)."""
    flt = scope.filter(dated=True, has_client=True)
    where = flt.where("status <> 'in_progress'", "latency_ms IS NOT NULL")
    rows = store.query(
        f"SELECT host, project_id, display_name, latency_ms FROM v_tasks{where}",
        flt.params,
    )
    by_host: dict[str, list[int]] = defaultdict(list)
    by_project: dict[str, list[int]] = defaultdict(list)
    names: dict[str, str] = {}
    values: list[int] = []
    for r in rows:
        latency = _count(r, "latency_ms")
        project_id = _text(r, "project_id")
        names[project_id] = _opt_text(r, "display_name") or project_id
        by_host[_text(r, "host")].append(latency)
        by_project[project_id].append(latency)
        values.append(latency)

    def ranked(
        groups: dict[str, list[int]], labels: Mapping[str, str]
    ) -> tuple[LatencyRow, ...]:
        ordered = sorted(groups.items(), key=lambda item: (-len(item[1]), item[0]))
        return tuple(
            LatencyRow(key=key, label=labels.get(key, key), stats=latency_stats(group))
            for key, group in ordered
        )

    return _Latencies(
        overall=latency_stats(values),
        by_host=ranked(by_host, {}),
        by_project=ranked(by_project, names),
        project_names=names,
    )


def _monthly_latency(
    store: ViewSource, scope: _Scope, names: Mapping[str, str]
) -> tuple[MonthlyLatencyRow, ...]:
    flt = scope.filter(dated=False, has_client=False, monthly=True)
    rows = store.query(
        "SELECT local_month, project_id, host, tasks, p50_ms, p95_ms, p99_ms "
        f"FROM v_task_latency{flt.where()} ORDER BY local_month DESC, project_id, host",
        flt.params,
    )
    return tuple(
        MonthlyLatencyRow(
            local_month=_text(r, "local_month"),
            project_label=names.get(_text(r, "project_id"), _text(r, "project_id")),
            host=_text(r, "host"),
            tasks=_count(r, "tasks"),
            p50_ms=_ratio(r, "p50_ms"),
            p95_ms=_ratio(r, "p95_ms"),
            p99_ms=_ratio(r, "p99_ms"),
        )
        for r in rows
    )


def _means(
    store: ViewSource, flt: _Filter, view: str, column: str, value: str
) -> dict[str, Decimal | None]:
    """Mean of ``value`` over rows with a known value, per ``column`` key."""
    rows = store.query(
        f"SELECT {column} AS key, SUM({value}) AS total, COUNT({value}) AS n "
        f"FROM {view}{flt.where()} GROUP BY 1",
        flt.params,
    )
    return {
        _text(r, "key"): _divide(_opt_int(r, "total"), _count(r, "n")) for r in rows
    }


def _efficiency(
    store: ViewSource,
    scope: _Scope,
    column: str,
    usage: Sequence[UsageRow],
    labels: Mapping[str, str],
) -> tuple[EfficiencyRow, ...]:
    """Cache %, context per call, output per task and error rate keyed by ``column``."""
    context = _means(
        store,
        scope.filter(dated=True, has_client=False),
        "v_calls",
        column,
        "prompt_tokens",
    )
    output = _means(
        store,
        scope.filter(dated=True, has_client=True),
        "v_tasks",
        column,
        "output_tokens",
    )
    usage_by_key = {row.key: row for row in usage}
    keys = list(usage_by_key) + sorted(set(output) - set(usage_by_key))
    rows = []
    for key in keys:
        row = usage_by_key.get(key)
        rows.append(
            EfficiencyRow(
                key=key,
                label=row.label if row is not None else labels.get(key, key),
                cache_hit_ratio=row.cache_hit_ratio if row is not None else None,
                avg_context_tokens=context.get(key),
                output_per_task=output.get(key),
                error_rate=row.error_rate if row is not None else None,
            )
        )
    return tuple(rows)


def _billable(store: ViewSource, scope: _Scope) -> tuple[BillableRow, ...]:
    flt = scope.filter(dated=False, has_client=True, monthly=True)
    rows = store.query(
        "SELECT local_month, client, project_id, display_name, billing_model, rate_currency, "
        "cost_usd, unpriced_calls, dev_hours, billable_value, billable_usd, ai_cost_ratio "
        f"FROM v_client_month{flt.where()} "
        "ORDER BY local_month DESC, client NULLS LAST, display_name, project_id",
        flt.params,
    )
    return tuple(
        BillableRow(
            local_month=_text(r, "local_month"),
            client=_opt_text(r, "client"),
            project_id=_text(r, "project_id"),
            project_label=_opt_text(r, "display_name") or _text(r, "project_id"),
            billing_model=_opt_text(r, "billing_model"),
            rate_currency=_opt_text(r, "rate_currency"),
            cost=_cost(r, flags=False),
            dev_hours=_ratio(r, "dev_hours"),
            billable_value=_money(r, "billable_value"),
            billable_usd=_money(r, "billable_usd"),
            ai_cost_ratio=_ratio(r, "ai_cost_ratio"),
        )
        for r in rows
    )


def _unpriced_models(store: ViewSource) -> tuple[UnpricedModelRow, ...]:
    rows = store.query(
        "SELECT host, model_effective, calls, first_ts, last_ts FROM v_unpriced_models "
        "ORDER BY calls DESC, host, model_effective"
    )
    return tuple(
        UnpricedModelRow(
            host=_text(r, "host"),
            model=_opt_text(r, "model_effective") or UNKNOWN_MODEL,
            calls=_count(r, "calls"),
            first_ts=_opt_datetime(r, "first_ts"),
            last_ts=_opt_datetime(r, "last_ts"),
        )
        for r in rows
    )


def _untracked(store: ViewSource) -> tuple[UntrackedRow, ...]:
    rows = store.query(
        "SELECT host, reason, conversations, observed_from, observed_to FROM v_untracked "
        "ORDER BY host, reason"
    )
    return tuple(
        UntrackedRow(
            host=_text(r, "host"),
            reason=_text(r, "reason"),
            conversations=_count(r, "conversations"),
            observed_from=_opt_date(r, "observed_from"),
            observed_to=_opt_date(r, "observed_to"),
        )
        for r in rows
    )


def _health(store: ViewSource) -> tuple[HealthRow, ...]:
    rows = store.query(
        "SELECT host, last_ingested_at, units, unknown_formats, diagnostics_7d, "
        "earliest_call_ts FROM v_health ORDER BY host"
    )
    return tuple(
        HealthRow(
            host=_text(r, "host"),
            last_ingested_at=_opt_datetime(r, "last_ingested_at"),
            units=_count(r, "units"),
            unknown_formats=_count(r, "unknown_formats"),
            diagnostics_7d=_count(r, "diagnostics_7d"),
            earliest_call_ts=_opt_datetime(r, "earliest_call_ts"),
        )
        for r in rows
    )


def _period_label(options: ReportOptions) -> str | None:
    if options.month is not None:
        return f"Month: {options.month}"
    start, end = options.date_range()
    if start is not None and end is not None:
        return f"{start.isoformat()} → {end.isoformat()}"
    if start is not None:
        return f"From {start.isoformat()}"
    if end is not None:
        return f"Until {end.isoformat()}"
    return None


def _scope_label(options: ReportOptions, names: Mapping[str, str]) -> str:
    parts: list[str] = []
    if options.project_id is not None:
        parts.append(f"Project: {names.get(options.project_id, options.project_id)}")
    if options.client is not None:
        parts.append(f"Client: {options.client}")
    period = _period_label(options)
    if period is not None:
        parts.append(period)
    return " · ".join(parts) if parts else "All data"


def load_report_data(store: ViewSource, options: ReportOptions) -> ReportData:
    """Run every report query against the §6 views and assemble the data model."""
    scope = _Scope(options)
    totals = _usage(store, scope, "total")
    by_project = _usage(store, scope, "project")
    by_host = _usage(store, scope, "host")
    task_count, tasks = _tasks(store, scope)
    session_count, sessions = _sessions(store, scope)
    latencies = _latencies(store, scope)
    names = {**latencies.project_names, **{row.key: row.label for row in by_project}}
    store_has_data = (
        _scalar_count(
            store,
            "SELECT (SELECT COUNT(*) FROM v_calls) + (SELECT COUNT(*) FROM v_tasks) "
            "+ (SELECT COUNT(*) FROM v_sessions) AS n",
        )
        > 0
    )
    return ReportData(
        options=options,
        store_has_data=store_has_data,
        scope_label=_scope_label(options, names),
        totals=totals[0] if totals else EMPTY_TOTAL,
        unpriced_models_in_scope=_unpriced_in_scope(store, scope),
        task_count=task_count,
        session_count=session_count,
        by_day=_usage(store, scope, "day"),
        by_month=_usage(store, scope, "month"),
        by_project=by_project,
        by_client=_usage(store, scope, "client"),
        by_host=by_host,
        by_model=_usage(store, scope, "model"),
        by_project_month=_project_months(store, scope),
        tasks=tasks,
        agent_types=_agent_types(store, scope),
        timelines=_timelines(store, tasks),
        sessions=sessions,
        tags=_tags(store, scope),
        latency_overall=latencies.overall,
        latency_by_host=latencies.by_host,
        latency_by_project=latencies.by_project,
        latency_monthly=_monthly_latency(store, scope, names),
        efficiency_by_host=_efficiency(store, scope, "host", by_host, {}),
        efficiency_by_project=_efficiency(
            store, scope, "project_id", by_project, names
        ),
        billable=_billable(store, scope),
        unpriced_models=_unpriced_models(store),
        untracked=_untracked(store),
        health=_health(store),
    )
