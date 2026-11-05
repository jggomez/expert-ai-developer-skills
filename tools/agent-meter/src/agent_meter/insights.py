"""Deterministic savings insights: fixed rules in SQL and Python over the §6 views, with no AI.

Given the same data, prices, thresholds and ``as_of`` date the result is identical, so nothing
here reads the clock. A fact is measured. A saving is an estimate from the formula published in
``Insight.saving_basis``. Rules can overlap, which is why savings are never added together.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
from statistics import median
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from agent_meter.report.data import ViewSource

__all__ = ["Insight", "InsightsReport", "Thresholds", "build_insights", "insights_document", "render_insights"]

ZERO: Final = Decimal(0)
OVERLAP_NOTE: Final = "Savings are estimates, and rules can overlap, so do not add them together."
_WHAT_IF_MODELS: Final = (("claude-opus-5-5", "claude-sonnet-5-5"),)

_LONG_SESSIONS_SQL: Final = """
WITH numbered AS (
  SELECT host, session_id, cost_usd,
         row_number() OVER (PARTITION BY host, session_id ORDER BY ts, call_id) AS n
  FROM v_calls WHERE {scope} AND NOT unpriced
)
SELECT host, session_id, COUNT(*) AS calls, SUM(cost_usd) AS cost_usd,
       CAST(AVG(cost_usd) FILTER (WHERE n <= ?) AS DECIMAL(38, 9)) AS base_cost,
       SUM(cost_usd) FILTER (WHERE n > ?) AS tail_cost,
       COUNT(*) FILTER (WHERE n > ?) AS tail_calls
FROM numbered GROUP BY host, session_id HAVING COUNT(*) >= ?
ORDER BY cost_usd DESC, session_id
"""

_STALE_CACHE_SQL: Final = """
WITH gaps AS (
  SELECT cost_usd, ts - lag(ts) OVER (PARTITION BY session_id ORDER BY ts, call_id) AS gap
  FROM v_calls WHERE {scope} AND host = 'claude-code' AND NOT unpriced
)
SELECT COUNT(*) FILTER (WHERE gap > to_seconds(?)) AS resumes,
       SUM(cost_usd) FILTER (WHERE gap > to_seconds(?)) AS resume_cost,
       CAST(AVG(cost_usd) FILTER (WHERE gap <= to_seconds(?)) AS DECIMAL(38, 9)) AS normal_cost
FROM gaps
"""

_REPEATED_IMPLEMENTERS_SQL: Final = """
WITH runs AS (
  SELECT r.task_id, r.cost_usd, r.started_at,
         lag(r.ended_at) OVER (PARTITION BY r.task_id ORDER BY r.started_at, r.agent_run_id) AS previous_end
  FROM v_agent_runs r JOIN v_tasks t ON t.task_id = r.task_id
  WHERE {scope} AND r.agent_type ILIKE '%implementer%'
),
repeats AS (SELECT task_id, cost_usd FROM runs WHERE previous_end IS NOT NULL AND started_at >= previous_end),
tasks AS (SELECT task_id FROM repeats GROUP BY task_id HAVING COUNT(*) >= ?)
SELECT COUNT(DISTINCT p.task_id) AS tasks, COUNT(*) AS repeats, SUM(p.cost_usd) AS repeat_cost
FROM repeats p JOIN tasks USING (task_id)
"""

_AGENT_COST_SQL: Final = """
SELECT r.agent_type, COUNT(*) AS runs, CAST(AVG(r.cost_usd) AS DECIMAL(38, 9)) AS avg_cost
FROM v_agent_runs r JOIN v_tasks t ON t.task_id = r.task_id
WHERE {scope} AND r.agent_type <> 'main' AND r.cost_usd IS NOT NULL
GROUP BY r.agent_type HAVING COUNT(*) >= ? ORDER BY r.agent_type
"""

_TASKS_SQL: Final = """
SELECT task_id, cost_usd, calls, agent_runs, retries, test_failures FROM v_tasks
WHERE {scope} AND cost_usd IS NOT NULL ORDER BY cost_usd DESC, task_id
"""

_MODEL_TOKENS_SQL: Final = """
SELECT SUM(cost_usd) AS cost_usd, COUNT(*) AS calls, SUM(input_tokens) AS input_tokens,
       SUM(output_tokens) AS output_tokens, SUM(cache_read_tokens) AS cache_read_tokens,
       SUM(cache_write_5m_tokens) AS cache_write_5m_tokens, SUM(cache_write_1h_tokens) AS cache_write_1h_tokens
FROM v_calls WHERE {scope} AND priced_model = ? AND NOT unpriced
"""

_TARGET_PRICE_SQL: Final = """
SELECT input_per_mtok, output_per_mtok, cache_read_per_mtok, cache_write_5m_per_mtok, cache_write_1h_per_mtok
FROM pricing WHERE model = ? AND effective_from <= ? AND min_prompt_tokens = 0
ORDER BY effective_from DESC LIMIT 1
"""


@dataclass(frozen=True, slots=True)
class Thresholds:
    window_days: int = 30
    long_session_calls: int = 1000
    session_baseline_calls: int = 500
    stale_gap_seconds: int = 3600
    min_stale_resumes: int = 5
    min_repeats_per_task: int = 2
    min_agent_runs: int = 5
    agent_cost_ratio: Decimal = Decimal(2)
    min_tasks_for_outliers: int = 10
    outlier_share_pct: Decimal = Decimal(50)
    outlier_tasks_shown: int = 10
    many_agents: int = 5
    many_calls: int = 200


@dataclass(frozen=True, slots=True)
class Insight:
    rule: str
    title: str
    action: str
    evidence: dict[str, Any]
    saving_usd: Decimal | None
    saving_basis: str
    query: str


@dataclass(frozen=True, slots=True)
class InsightsReport:
    date_from: date
    date_to: date
    insights: tuple[Insight, ...]
    window_cost_usd: Decimal


@dataclass(frozen=True, slots=True)
class _Scope:
    """Date window and optional project of one ``build_insights`` run."""

    date_from: date
    date_to: date
    project_id: str | None

    def where(self, prefix: str = "") -> str:
        project = f" AND {prefix}project_id = ?" if self.project_id else ""
        return f"{prefix}local_date BETWEEN ? AND ?{project}"

    @property
    def params(self) -> list[object]:
        project = [self.project_id] if self.project_id else []
        return [self.date_from, self.date_to, *project]


def _money(value: object) -> Decimal:
    return ZERO if value is None else Decimal(str(value))


def _usd(value: Decimal) -> str:
    return f"${value.quantize(Decimal('0.01')):,}"


def _long_sessions(store: ViewSource, scope: _Scope, limits: Thresholds) -> list[Insight]:
    baseline = limits.session_baseline_calls
    sql = _LONG_SESSIONS_SQL.format(scope=scope.where())
    rows = store.query(sql, [*scope.params, baseline, baseline, baseline, limits.long_session_calls])
    if not rows:
        return []
    total = sum((_money(r["cost_usd"]) for r in rows), ZERO)
    saving = sum(
        (max(ZERO, _money(r["tail_cost"]) - _money(r["base_cost"]) * _money(r["tail_calls"])) for r in rows), ZERO
    )
    top = rows[0]
    return [Insight(
        rule="long_session",
        title=f"{len(rows)} session(s) passed {limits.long_session_calls:,} calls and cost {_usd(total)}",
        action="Start a new session for each task, and keep shared decisions in project notes.",
        evidence={"sessions": len(rows), "cost_usd": str(total), "top_session": str(top["session_id"]),
                  "top_session_calls": int(str(top["calls"])), "top_session_cost_usd": str(_money(top["cost_usd"]))},
        saving_usd=saving,
        saving_basis=f"Each call after the first {baseline:,} priced at the average of those first calls.",
        query=sql,
    )]


def _stale_cache(store: ViewSource, scope: _Scope, limits: Thresholds) -> list[Insight]:
    sql = _STALE_CACHE_SQL.format(scope=scope.where())
    gap = limits.stale_gap_seconds
    row = store.query(sql, [*scope.params, gap, gap, gap])[0]
    resumes = int(str(row["resumes"] or 0))
    if resumes < limits.min_stale_resumes:
        return []
    cost = _money(row["resume_cost"])
    normal = _money(row["normal_cost"])
    hours = gap / 3600
    return [Insight(
        rule="stale_cache",
        title=f"{resumes} resumes after more than {hours:g} h idle cost {_usd(cost)}",
        action="After a long pause, start a new session or run /compact before continuing.",
        evidence={"resumes": resumes, "cost_usd": str(cost), "average_resume_usd": str(cost / resumes),
                  "average_normal_call_usd": str(normal)},
        saving_usd=max(ZERO, cost - normal * resumes),
        saving_basis="Each resume priced at the average cost of a call without that pause.",
        query=sql,
    )]


def _repeated_implementers(store: ViewSource, scope: _Scope, limits: Thresholds) -> list[Insight]:
    sql = _REPEATED_IMPLEMENTERS_SQL.format(scope=scope.where("t."))
    row = store.query(sql, [*scope.params, limits.min_repeats_per_task])[0]
    tasks = int(str(row["tasks"] or 0))
    if not tasks:
        return []
    cost = _money(row["repeat_cost"])
    return [Insight(
        rule="repeated_implementers",
        title=f"{tasks} task(s) ran an implementer again after it finished, costing {_usd(cost)}",
        action="Check those tasks for unclear specs or weak acceptance criteria. Planned phases are not rework.",
        evidence={"tasks": tasks, "repeats": int(str(row["repeats"])), "cost_usd": str(cost)},
        saving_usd=cost,
        saving_basis="The full cost of each sequential repeat, an upper bound because some may be planned phases.",
        query=sql,
    )]


def _expensive_agents(store: ViewSource, scope: _Scope, limits: Thresholds) -> list[Insight]:
    sql = _AGENT_COST_SQL.format(scope=scope.where("t."))
    rows = store.query(sql, [*scope.params, limits.min_agent_runs])
    found: list[Insight] = []
    for row in rows:
        peers = [_money(r["avg_cost"]) for r in rows if r is not row]
        if not peers:
            continue
        peer = Decimal(median(peers))
        average = _money(row["avg_cost"])
        if peer <= ZERO or average < peer * limits.agent_cost_ratio:
            continue
        runs = int(str(row["runs"]))
        ratio = (average / peer).quantize(Decimal("0.1"))
        name = str(row["agent_type"])
        found.append(Insight(
            rule="expensive_agent",
            title=f"{name} costs {_usd(average)} per run, {ratio} times its peers",
            action=f"Review the instructions, model and scope given to {name}.",
            evidence={"agent_type": name, "runs": runs, "average_usd": str(average), "peer_median_usd": str(peer)},
            saving_usd=(average - peer) * runs,
            saving_basis="Each run priced at the median average of the other agent types.",
            query=sql,
        ))
    return found


def _task_reason(row: dict[str, object], limits: Thresholds) -> str:
    reasons = [
        (int(str(row["agent_runs"] or 0)) >= limits.many_agents, "many agents"),
        (int(str(row["calls"] or 0)) >= limits.many_calls, "many calls"),
        (int(str(row["retries"] or 0)) > 0, "retries"),
        (int(str(row["test_failures"] or 0)) > 0, "failed tests"),
    ]
    return ", ".join(label for matched, label in reasons if matched) or "large context"


def _outlier_tasks(store: ViewSource, scope: _Scope, limits: Thresholds) -> list[Insight]:
    sql = _TASKS_SQL.format(scope=scope.where())
    rows = store.query(sql, scope.params)
    if len(rows) < limits.min_tasks_for_outliers:
        return []
    total = sum((_money(r["cost_usd"]) for r in rows), ZERO)
    count = math.ceil(len(rows) / 10)
    top_cost = sum((_money(r["cost_usd"]) for r in rows[:count]), ZERO)
    share = top_cost * 100 / total if total else ZERO
    if share < limits.outlier_share_pct:
        return []
    shown = [
        {"task_id": str(r["task_id"]), "cost_usd": str(_money(r["cost_usd"])), "reason": _task_reason(r, limits)}
        for r in rows[: limits.outlier_tasks_shown]
    ]
    return [Insight(
        rule="outlier_tasks",
        title=f"{count} of {len(rows)} tasks made up {share.quantize(Decimal('1'))}% of the cost",
        action="Open the costliest tasks and split similar work into smaller tasks.",
        evidence={"tasks": len(rows), "top_tasks": count, "top_cost_usd": str(top_cost), "costliest": shown},
        saving_usd=None,
        saving_basis="No estimate: this shows where the cost sits, not how much of it is avoidable.",
        query=sql,
    )]


def _model_what_if(store: ViewSource, scope: _Scope, _limits: Thresholds) -> list[Insight]:
    found: list[Insight] = []
    sql = _MODEL_TOKENS_SQL.format(scope=scope.where())
    for source, target in _WHAT_IF_MODELS:
        usage = store.query(sql, [*scope.params, source])[0]
        price = store.query(_TARGET_PRICE_SQL, [target, scope.date_to])
        if not usage["calls"] or not price:
            continue
        rate = price[0]
        input_rate = _money(rate["input_per_mtok"])
        rates = (
            (usage["input_tokens"], input_rate),
            (usage["output_tokens"], _money(rate["output_per_mtok"])),
            (usage["cache_read_tokens"], _money(rate["cache_read_per_mtok"])),
            (usage["cache_write_5m_tokens"], _money(rate["cache_write_5m_per_mtok"] or input_rate)),
            (usage["cache_write_1h_tokens"], _money(rate["cache_write_1h_per_mtok"] or input_rate)),
        )
        cost = _money(usage["cost_usd"])
        alternative = sum((_money(tokens) * value for tokens, value in rates), ZERO) / 1_000_000
        if alternative >= cost:
            continue
        found.append(Insight(
            rule="model_what_if",
            title=f"{usage['calls']:,} {source} calls cost {_usd(cost)}; {target} would list at {_usd(alternative)}",
            action=f"Try {target} on routine work. This compares price only, not quality.",
            evidence={"source": source, "target": target, "calls": int(str(usage["calls"])),
                      "cost_usd": str(cost), "alternative_usd": str(alternative)},
            saving_usd=cost - alternative,
            saving_basis="The same tokens at the target model's list price. Quality and rework may change.",
            query=sql,
        ))
    return found


_RULES: Final[tuple[Callable[[ViewSource, _Scope, Thresholds], list[Insight]], ...]] = (
    _long_sessions, _stale_cache, _repeated_implementers, _expensive_agents, _outlier_tasks, _model_what_if,
)


def build_insights(
    store: ViewSource, *, as_of: date, project_id: str | None = None, limits: Thresholds | None = None
) -> InsightsReport:
    """Run every rule over the ``limits.window_days`` days ending on ``as_of``."""
    limits = limits or Thresholds()
    start = as_of - timedelta(days=limits.window_days - 1)
    scope = _Scope(start, as_of, project_id)
    found = [insight for rule in _RULES for insight in rule(store, scope, limits)]
    found.sort(key=lambda i: (i.saving_usd is None, -(i.saving_usd or ZERO), i.rule, i.title))
    cost = store.query(f"SELECT SUM(cost_usd) AS cost_usd FROM v_calls WHERE {scope.where()}", scope.params)[0]
    return InsightsReport(start, as_of, tuple(found), _money(cost["cost_usd"]))


def insights_document(report: InsightsReport) -> dict[str, Any]:
    return {
        "from": report.date_from.isoformat(),
        "to": report.date_to.isoformat(),
        "window_cost_usd": str(report.window_cost_usd),
        "note": OVERLAP_NOTE,
        "insights": [
            {
                "rule": i.rule, "title": i.title, "action": i.action, "evidence": i.evidence,
                "saving_usd": None if i.saving_usd is None else str(i.saving_usd.quantize(Decimal("0.01"))),
                "saving_basis": i.saving_basis, "query": i.query.strip(),
            }
            for i in report.insights
        ],
    }


def render_insights(report: InsightsReport) -> str:
    lines = [f"Where to cut · {report.date_from} → {report.date_to} · {_usd(report.window_cost_usd)} list-price cost"]
    if not report.insights:
        lines.append("No rule fired in this period.")
    for insight in report.insights:
        saving = "no estimate" if insight.saving_usd is None else f"about {_usd(insight.saving_usd)} (estimate)"
        lines += ["", f"- {insight.title}", f"  Saving: {saving}. {insight.saving_basis}", f"  Action: {insight.action}"]
    if report.insights:
        lines += ["", OVERLAP_NOTE]
    return "\n".join(lines)
