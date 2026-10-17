"""Session summaries and per-task rollups rendered from the store views (PRD §7, ADR §3.12).

Only ``v_*`` views are read. Task labels are display-only: they are read from the host
transcript at render time and passed to ``render_task_rollup`` ONLY for an interactive
terminal; they never reach ``last-summary.txt``, notifications, the snapshot or the cloud.
"""

from __future__ import annotations

import json
import logging
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final
from zoneinfo import ZoneInfo

from agent_meter.config import Config
from agent_meter.model import Host

if TYPE_CHECKING:
    from agent_meter.store import Store

__all__ = [
    "COLLECTING_NOTE",
    "AgentTypeRow",
    "HostCost",
    "PeriodTotals",
    "SessionSummary",
    "SummaryError",
    "TaskRollup",
    "build_snapshot",
    "fmt_cost",
    "fmt_duration",
    "fmt_tokens",
    "host_label",
    "read_task_label",
    "render_session_summary",
    "render_task_rollup",
    "session_summary",
    "summary_from_snapshot",
    "task_rollups",
]

_LOG = logging.getLogger(__name__)

COLLECTING_NOTE: Final = "(collecting… run 'agent-meter last' in a minute)"
LABEL_MAX: Final = 40
SNAPSHOT_SESSIONS: Final = 20
_HOST_LABELS: Final = {
    Host.CLAUDE_CODE: "Claude Code",
    Host.ANTIGRAVITY_CLI: "Antigravity CLI",
    Host.ANTIGRAVITY_IDE: "Antigravity IDE",
    Host.ANTIGRAVITY_APP: "Antigravity",
}
_ZERO_DECIMAL_CURRENCIES: Final = frozenset({"COP", "CLP", "JPY", "KRW", "VND", "PYG", "ISK", "HUF", "UGX"})
_CENT: Final = Decimal("0.01")
_LABEL_SCAN_BYTES: Final = 64 * 1024 * 1024
_SAFE_ID: Final = re.compile(r"^[A-Za-z0-9_.:@-]{1,200}$")


class SummaryError(LookupError):
    """The requested session or task is not in the store."""


@dataclass(frozen=True, slots=True)
class HostCost:
    host: Host
    cost_usd: Decimal | None


@dataclass(frozen=True, slots=True)
class PeriodTotals:
    cost_usd: Decimal | None
    unpriced_calls: int
    unpriced_models: tuple[str, ...]
    by_host: tuple[HostCost, ...]


@dataclass(frozen=True, slots=True)
class SessionSummary:
    host: Host
    session_id: str
    project_id: str
    project_name: str
    started_at: datetime
    ended_at: datetime
    status: str
    wall_clock_ms: int
    active_ms: int
    tasks: int
    calls: int
    input_tokens: int
    cache_read_tokens: int
    cache_write_tokens: int
    output_tokens: int
    cache_hit_ratio: Decimal | None
    cost_usd: Decimal | None
    unpriced_calls: int
    unpriced_models: tuple[str, ...]
    estimated_calls: int
    inferred_calls: int
    task_p50_ms: int | None
    task_p95_ms: int | None
    today: PeriodTotals
    month: PeriodTotals


@dataclass(frozen=True, slots=True)
class AgentTypeRow:
    agent_type: str
    runs: int
    calls: int
    cost_usd: Decimal | None
    unpriced_calls: int
    tools: tuple[tuple[str, int], ...]  # (tool_name, calls), most used first
    files_touched: int
    test_runs: int
    test_failures: int


@dataclass(frozen=True, slots=True)
class TaskRollup:
    task_id: str
    session_id: str
    host: Host
    project_id: str
    project_name: str
    seq_in_session: int
    started_at: datetime
    ended_at: datetime
    status: str
    wall_clock_ms: int
    active_ms: int
    cost_usd: Decimal | None
    unpriced_calls: int
    unpriced_models: tuple[str, ...]
    estimated_calls: int
    inferred_calls: int
    agent_runs: int
    max_spawn_depth: int
    parallelism: Decimal | None
    retries: int
    retry_summary: str
    calls: int
    tool_calls: int
    files_touched: int
    test_runs: int
    test_failures: int
    work_item_tag: str | None
    agents: tuple[AgentTypeRow, ...]


# ----------------------------------------------------------------------------- formatting


def host_label(host: Host | str) -> str:
    try:
        return _HOST_LABELS[Host(host)]
    except ValueError:
        return str(host)


def fmt_duration(ms: int | float | None) -> str:
    """``35s``, ``4m 10s``, ``1h 05m`` (PRD §7)."""
    seconds = round((ms or 0) / 1000)
    hours, rest = divmod(seconds, 3600)
    minutes, secs = divmod(rest, 60)
    if hours:
        return f"{hours}h {minutes:02d}m"
    if minutes:
        return f"{minutes}m {secs:02d}s"
    return f"{secs}s"


def fmt_tokens(n: int | None) -> str:
    value = n or 0
    if value >= 1_000_000:
        return f"{value / 1_000_000:.2f}M"
    if value >= 10_000:
        return f"{value / 1_000:.0f}K"
    if value >= 1_000:
        return f"{value / 1_000:.1f}K"
    return str(value)


def _usd(value: Decimal | None) -> str:
    amount = (value or Decimal(0)).quantize(_CENT, rounding=ROUND_HALF_UP)
    return f"${amount:,.2f}"


def _display_amount(value: Decimal | None, cfg: Config) -> str:
    currency = cfg.display_currency
    if not currency or currency == "USD" or cfg.usd_rate is None or value is None:
        return ""
    amount = value * cfg.usd_rate
    if currency in _ZERO_DECIMAL_CURRENCIES:
        return f" ({currency} {amount.quantize(Decimal(1), rounding=ROUND_HALF_UP):,.0f})"
    return f" ({currency} {amount.quantize(_CENT, rounding=ROUND_HALF_UP):,.2f})"


def fmt_cost(
    cost: Decimal | None,
    cfg: Config,
    *,
    unpriced_calls: int = 0,
    unpriced_models: Sequence[str] = (),
    estimated: int = 0,
    inferred: int = 0,
    detail: bool = True,
    currency: bool = False,
) -> str:
    """``≈ $1.37`` or the partial lower bound ``≥ $4.10* (312 calls unpriced: gemini-x)`` (BR-01/02/04)."""
    marks = ("*" if estimated else "") + ("†" if inferred else "")
    prefix = "≥" if unpriced_calls else "≈"
    text = f"{prefix} {_usd(cost)}{marks}" + (_display_amount(cost, cfg) if currency else "")
    if unpriced_calls and detail:
        noun = "call" if unpriced_calls == 1 else "calls"
        models = f": {', '.join(unpriced_models)}" if unpriced_models else ""
        text += f" ({unpriced_calls} {noun} unpriced{models})"
    return text


def _footnote(estimated: int, inferred: int) -> str | None:
    parts = (["* estimated price"] if estimated else []) + (["† model inferred"] if inferred else [])
    return "  " + " · ".join(parts) if parts else None


def _percent(ratio: Decimal | None) -> str:
    if ratio is None:
        return "—"
    return f"{(ratio * 100).quantize(Decimal(1), rounding=ROUND_HALF_UP)}%"


# ----------------------------------------------------------------------------- queries


def _int(value: object) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float, Decimal)):
        return int(value)
    return int(str(value))


def _dec(value: object) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _store_timezone(store: Store) -> ZoneInfo:
    rows = store.query("SELECT value FROM settings WHERE key = 'timezone'")
    name = str(rows[0]["value"]) if rows else "UTC"
    try:
        return ZoneInfo(name)
    except (ValueError, KeyError):
        return ZoneInfo("UTC")


def _period_totals(store: Store, project_id: str, where: str, params: Sequence[object]) -> PeriodTotals:
    rows = store.query(
        f"""
        SELECT host, SUM(cost_usd) AS cost_usd, SUM(unpriced_calls) AS unpriced_calls
        FROM v_daily_project_cost WHERE project_id = ? AND {where}
        GROUP BY host ORDER BY host
        """,
        [project_id, *params],
    )
    unpriced_models = store.query(
        f"""
        SELECT DISTINCT model_effective FROM v_calls
        WHERE project_id = ? AND unpriced AND model_effective IS NOT NULL AND {where}
        ORDER BY model_effective
        """,
        [project_id, *params],
    )
    costs = [_dec(r["cost_usd"]) for r in rows]
    priced = [c for c in costs if c is not None]
    return PeriodTotals(
        cost_usd=sum(priced, Decimal(0)) if priced else None,
        unpriced_calls=sum(_int(r["unpriced_calls"]) for r in rows),
        unpriced_models=tuple(str(r["model_effective"]) for r in unpriced_models),
        by_host=tuple(HostCost(Host(str(r["host"])), _dec(r["cost_usd"])) for r in rows),
    )


def session_summary(store: Store, host: Host, session_id: str, *, now: datetime) -> SessionSummary:
    """Totals for one session plus today / month-to-date for its project across all hosts."""
    rows = store.query("SELECT * FROM v_sessions WHERE session_id = ? AND host = ?", [session_id, host.value])
    if not rows:
        raise SummaryError(f"session {session_id!r} ({host.value}) is not in the store yet")
    s = rows[0]
    tokens = store.query(
        """
        SELECT SUM(input_tokens) AS input_tokens, SUM(cache_read_tokens) AS cache_read_tokens,
               SUM(COALESCE(cache_write_5m_tokens, 0) + COALESCE(cache_write_1h_tokens, 0)) AS cache_write_tokens,
               SUM(output_tokens) AS output_tokens,
               COUNT(*) FILTER (WHERE estimated) AS estimated_calls,
               COUNT(*) FILTER (WHERE model_inferred) AS inferred_calls
        FROM v_calls WHERE session_id = ?
        """,
        [session_id],
    )[0]
    unpriced = store.query(
        "SELECT DISTINCT model_effective FROM v_calls WHERE session_id = ? AND unpriced AND model_effective IS NOT NULL "
        "ORDER BY 1",
        [session_id],
    )
    project_id = str(s["project_id"])
    today = now.astimezone(_store_timezone(store)).date()
    month = today.strftime("%Y-%m")
    p50, p95 = s["task_p50_ms"], s["task_p95_ms"]
    started, ended = s["started_at"], s["ended_at"]
    assert isinstance(started, datetime) and isinstance(ended, datetime)
    return SessionSummary(
        host=host,
        session_id=session_id,
        project_id=project_id,
        project_name=str(s["display_name"]),
        started_at=started,
        ended_at=ended,
        status=str(s["status"]),
        wall_clock_ms=_int(s["wall_clock_ms"]),
        active_ms=_int(s["active_ms"]),
        tasks=_int(s["tasks"]),
        calls=_int(s["calls"]),
        input_tokens=_int(tokens["input_tokens"]),
        cache_read_tokens=_int(tokens["cache_read_tokens"]),
        cache_write_tokens=_int(tokens["cache_write_tokens"]),
        output_tokens=_int(tokens["output_tokens"]),
        cache_hit_ratio=_dec(s["cache_hit_ratio"]),
        cost_usd=_dec(s["cost_usd"]),
        unpriced_calls=_int(s["unpriced_calls"]),
        unpriced_models=tuple(str(r["model_effective"]) for r in unpriced),
        estimated_calls=_int(tokens["estimated_calls"]),
        inferred_calls=_int(tokens["inferred_calls"]),
        task_p50_ms=None if p50 is None else _int(p50),
        task_p95_ms=None if p95 is None else _int(p95),
        today=_period_totals(store, project_id, "local_date = ?", [today]),
        month=_period_totals(store, project_id, "local_month = ? AND local_date <= ?", [month, today]),
    )


def _agent_rows(store: Store, task_id: str) -> tuple[AgentTypeRow, ...]:
    types = store.query("SELECT * FROM v_agent_type_cost WHERE task_id = ?", [task_id])
    tools = store.query(
        """
        SELECT r.agent_type, t.tool_name, SUM(t.calls) AS calls
        FROM v_tool_counts t JOIN v_agent_runs r ON r.agent_run_id = t.agent_run_id
        WHERE t.task_id = ? GROUP BY r.agent_type, t.tool_name
        ORDER BY calls DESC, t.tool_name
        """,
        [task_id],
    )
    by_type: dict[str, list[tuple[str, int]]] = {}
    for row in tools:
        by_type.setdefault(str(row["agent_type"]), []).append((str(row["tool_name"]), _int(row["calls"])))
    agents = [
        AgentTypeRow(
            agent_type=str(row["agent_type"]),
            runs=_int(row["runs"]),
            calls=_int(row["calls"]),
            cost_usd=_dec(row["cost_usd"]),
            unpriced_calls=_int(row["unpriced_calls"]),
            tools=tuple(by_type.get(str(row["agent_type"]), ())),
            files_touched=_int(row["files_touched"]),
            test_runs=_int(row["test_runs"]),
            test_failures=_int(row["test_failures"]),
        )
        for row in types
    ]
    agents.sort(key=lambda a: (a.agent_type != "main", -(a.cost_usd or Decimal(0)), -a.calls, a.agent_type))
    return tuple(agents)


def task_rollups(
    store: Store,
    *,
    last: int | None = None,
    session_id: str | None = None,
    project_id: str | None = None,
    tag: str | None = None,
    since: date | None = None,
) -> list[TaskRollup]:
    """Per-task rollups, most recent first, each with one row per agent type (``v_agent_type_cost``)."""
    clauses: list[str] = []
    params: list[object] = []
    for column, value in (("session_id", session_id), ("project_id", project_id), ("work_item_tag", tag)):
        if value is not None:
            clauses.append(f"{column} = ?")
            params.append(value)
    if since is not None:
        clauses.append("local_date >= ?")
        params.append(since)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit = ""
    if last is not None:
        limit = "LIMIT ?"
        params.append(max(last, 0))
    rows = store.query(f"SELECT * FROM v_tasks {where} ORDER BY started_at DESC, task_id DESC {limit}", params)
    result: list[TaskRollup] = []
    for row in rows:
        task_id = str(row["task_id"])
        unpriced = store.query(
            "SELECT DISTINCT model_effective FROM v_calls WHERE task_id = ? AND unpriced AND model_effective IS NOT NULL "
            "ORDER BY 1",
            [task_id],
        )
        started, ended = row["started_at"], row["ended_at"]
        assert isinstance(started, datetime) and isinstance(ended, datetime)
        tag_value = row["work_item_tag"]
        result.append(
            TaskRollup(
                task_id=task_id,
                session_id=str(row["session_id"]),
                host=Host(str(row["host"])),
                project_id=str(row["project_id"]),
                project_name=str(row["display_name"]),
                seq_in_session=_int(row["seq_in_session"]),
                started_at=started,
                ended_at=ended,
                status=str(row["status"]),
                wall_clock_ms=_int(row["wall_clock_ms"]),
                active_ms=_int(row["active_ms"]),
                cost_usd=_dec(row["cost_usd"]),
                unpriced_calls=_int(row["unpriced_calls"]),
                unpriced_models=tuple(str(r["model_effective"]) for r in unpriced),
                estimated_calls=_int(row["estimated_calls"]),
                inferred_calls=_int(row["inferred_calls"]),
                agent_runs=_int(row["agent_runs"]),
                max_spawn_depth=_int(row["max_spawn_depth"]),
                parallelism=_dec(row["parallelism"]),
                retries=_int(row["retries"]),
                retry_summary=str(row["retry_summary"] or ""),
                calls=_int(row["calls"]),
                tool_calls=_int(row["tool_calls"]),
                files_touched=_int(row["files_touched"]),
                test_runs=_int(row["test_runs"]),
                test_failures=_int(row["test_failures"]),
                work_item_tag=None if tag_value is None else str(tag_value),
                agents=_agent_rows(store, task_id),
            )
        )
    return result


# ----------------------------------------------------------------------------- rendering


def render_session_summary(s: SessionSummary, cfg: Config) -> str:
    """The PRD §7 session summary block (never contains a task label)."""
    tokens = [f"{fmt_tokens(s.input_tokens)} in", f"{fmt_tokens(s.cache_read_tokens)} cache read"]
    if s.cache_write_tokens:
        tokens.append(f"{fmt_tokens(s.cache_write_tokens)} cache write")
    tokens += [f"{fmt_tokens(s.output_tokens)} out", f"cache hit {_percent(s.cache_hit_ratio)}"]
    cost_line = [
        "Cost "
        + fmt_cost(
            s.cost_usd, cfg, unpriced_calls=s.unpriced_calls, unpriced_models=s.unpriced_models,
            estimated=s.estimated_calls, inferred=s.inferred_calls,
        ),
        f"{s.tasks} task{'s' if s.tasks != 1 else ''}",
    ]
    if s.task_p50_ms is not None:
        cost_line.append(f"P50 {fmt_duration(s.task_p50_ms)}")
    if s.task_p95_ms is not None:
        cost_line.append(f"P95 {fmt_duration(s.task_p95_ms)}")
    hosts = " · ".join(f"{host_label(h.host)} {_usd(h.cost_usd)}" for h in s.today.by_host)
    today = fmt_cost(s.today.cost_usd, cfg, unpriced_calls=s.today.unpriced_calls, detail=False)
    month = fmt_cost(s.month.cost_usd, cfg, unpriced_calls=s.month.unpriced_calls, detail=False, currency=True)
    lines = [
        f"[agent-meter] {s.project_name} · {host_label(s.host)} · session {fmt_duration(s.wall_clock_ms)} "
        f"(active {fmt_duration(s.active_ms)})",
        "  Tokens " + " · ".join(tokens),
        "  " + " · ".join(cost_line),
        f"  {s.project_name} today {today}" + (f" ({hosts})" if hosts else "") + f" · month {month}",
    ]
    footnote = _footnote(s.estimated_calls, s.inferred_calls)
    if footnote:
        lines.append(footnote)
    return "\n".join(lines)


def _agent_line(agent: AgentTypeRow) -> str:
    name = agent.agent_type + (f" ×{agent.runs}" if agent.runs > 1 else "")
    cost = _usd(agent.cost_usd) if agent.cost_usd is not None or not agent.unpriced_calls else "—"
    if agent.unpriced_calls and agent.cost_usd is not None:
        cost = "≥" + cost
    extras = [f"{n} {tool}" for tool, n in agent.tools[:3]]
    if agent.files_touched:
        extras.append(f"{agent.files_touched} file{'s' if agent.files_touched != 1 else ''}")
    if agent.test_runs:
        extras.append(
            "tests ✓" if not agent.test_failures else f"tests ✗ {agent.test_failures}/{agent.test_runs}"
        )
    line = f"  {name:<20} {cost:>7} {agent.calls:>4} call{'s' if agent.calls != 1 else ''}"
    return line + ("".join(f" · {e}" for e in extras))


def _sanitize_label(text: str) -> str | None:
    cleaned = "".join(" " if unicodedata.category(ch)[0] in {"C", "Z"} else ch for ch in text)
    cleaned = " ".join(cleaned.replace('"', "'").split())
    if not cleaned:
        return None
    return cleaned if len(cleaned) <= LABEL_MAX else cleaned[: LABEL_MAX - 1].rstrip() + "…"


def render_task_rollup(r: TaskRollup, cfg: Config, *, label: str | None = None) -> str:
    """The PRD §7 per-task rollup; ``label`` is passed ONLY for interactive terminal output."""
    shown = _sanitize_label(label) if label else None
    title = f'task "{shown}"' if shown else f"task #{r.seq_in_session}"
    head = (
        f"[agent-meter] {r.project_name} · {host_label(r.host)} · {title} · {fmt_duration(r.wall_clock_ms)} "
        f"(active {fmt_duration(r.active_ms)})"
    )
    if r.status == "in_progress":
        head += " · in progress"
    summary = [
        "Cost "
        + fmt_cost(
            r.cost_usd, cfg, unpriced_calls=r.unpriced_calls, unpriced_models=r.unpriced_models,
            estimated=r.estimated_calls, inferred=r.inferred_calls,
        ),
        f"{r.agent_runs} agent{'s' if r.agent_runs != 1 else ''} (max depth {r.max_spawn_depth})",
    ]
    if r.parallelism is not None and r.agent_runs > 1:
        summary.append(f"parallelism {r.parallelism.normalize():f}x")
    if r.retries:
        summary.append(f"{r.retries} retr{'y' if r.retries == 1 else 'ies'} {r.retry_summary}".rstrip())
    if r.work_item_tag:
        summary.append(f"tag {r.work_item_tag}")
    lines = [head, "  " + " · ".join(summary), *(_agent_line(a) for a in r.agents)]
    footnote = _footnote(r.estimated_calls, r.inferred_calls)
    if footnote:
        lines.append(footnote)
    return "\n".join(lines)


# ----------------------------------------------------------------------------- task labels (display only)


def _claude_label(root: Path, session_id: str, prompt_id: str) -> str | None:
    projects = root / "projects"
    if not projects.is_dir():
        return None
    for main in sorted(projects.glob(f"*/{session_id}.jsonl")):
        with main.open("rb") as handle:
            scanned = 0
            for raw in handle:
                scanned += len(raw)
                if scanned > _LABEL_SCAN_BYTES:
                    break
                if b'"promptId"' not in raw or prompt_id.encode() not in raw:
                    continue
                try:
                    line = json.loads(raw)
                except ValueError:
                    continue
                if not isinstance(line, dict) or line.get("type") != "user" or line.get("promptId") != prompt_id:
                    continue
                content = (line.get("message") or {}).get("content")
                if isinstance(content, str):
                    return content
                if isinstance(content, list):
                    texts = [b.get("text") for b in content if isinstance(b, dict) and b.get("type") == "text"]
                    joined = " ".join(t for t in texts if isinstance(t, str))
                    if joined:
                        return joined
    return None


def _antigravity_label(root: Path, conversation_id: str, step_index: int) -> str | None:
    transcript = root / "brain" / conversation_id / ".system_generated" / "logs" / "transcript_full.jsonl"
    if not transcript.is_file():
        return None
    with transcript.open("rb") as handle:
        for raw in handle:
            try:
                line = json.loads(raw)
            except ValueError:
                continue
            if isinstance(line, dict) and line.get("step_index") == step_index and line.get("type") == "USER_INPUT":
                content = line.get("content")
                return content if isinstance(content, str) else None
    return None


def read_task_label(roots: Mapping[Host, Path], host: Host, session_id: str, task_id: str) -> str | None:
    """The task's prompt (≤ 40 chars) read from the host transcript, for terminal display only."""
    root = roots.get(host)
    if root is None or not _SAFE_ID.match(session_id):
        return None
    try:
        if host is Host.CLAUDE_CODE:
            prompt_id = task_id.removeprefix(f"{host.value}:")
            if prompt_id.endswith(":pre") or not _SAFE_ID.match(prompt_id):
                return None
            text = _claude_label(root, session_id, prompt_id)
        else:
            parts = task_id.split(":")
            if len(parts) != 3 or not _SAFE_ID.match(parts[1]) or not parts[2].isdigit():
                return None
            text = _antigravity_label(root, parts[1], int(parts[2]))
    except OSError as exc:
        _LOG.debug("task label unavailable: %s", type(exc).__name__)
        return None
    return _sanitize_label(text) if text else None


# ----------------------------------------------------------------------------- snapshot


def _config_from_settings(store: Store, tz: str) -> Config:
    settings = {str(r["key"]): str(r["value"]) for r in store.query("SELECT key, value FROM settings")}
    rate = _dec(settings.get("usd_rate"))
    return Config(timezone=tz, display_currency=settings.get("display_currency") or None, usd_rate=rate)


def _totals_doc(totals: PeriodTotals) -> dict[str, Any]:
    return {
        "total_usd": str(totals.cost_usd if totals.cost_usd is not None else Decimal(0)),
        "unpriced_calls": totals.unpriced_calls,
        "by_host": {h.host.value: str(h.cost_usd if h.cost_usd is not None else Decimal(0)) for h in totals.by_host},
    }


def build_snapshot(store: Store, *, tz: str, now: datetime) -> dict[str, Any]:
    """``state/snapshot.json`` content (contracts §5); session texts never carry labels."""
    zone = ZoneInfo(tz)
    today = now.astimezone(zone).date()
    month = today.strftime("%Y-%m")
    cfg = _config_from_settings(store, tz)
    projects: dict[str, Any] = {}
    active = store.query(
        "SELECT DISTINCT project_id, display_name FROM v_daily_project_cost WHERE local_month = ? ORDER BY 1", [month]
    )
    for row in active:
        pid = str(row["project_id"])
        projects[pid] = {
            "display_name": str(row["display_name"]),
            "today": _totals_doc(_period_totals(store, pid, "local_date = ?", [today])),
            "month": _totals_doc(_period_totals(store, pid, "local_month = ? AND local_date <= ?", [month, today])),
        }
    sessions = []
    for row in store.query(
        "SELECT host, session_id FROM sessions ORDER BY ended_at DESC, session_id LIMIT ?", [SNAPSHOT_SESSIONS]
    ):
        host = Host(str(row["host"]))
        sid = str(row["session_id"])
        text = render_session_summary(session_summary(store, host, sid, now=now), cfg)
        sessions.append({"host": host.value, "session_id": sid, "text": text})
    return {
        "generated_at": now.astimezone(UTC).isoformat(),
        "timezone": tz,
        "projects": projects,
        "sessions": sessions,
    }


def summary_from_snapshot(snapshot_path: Path, host: Host, session_id: str, cfg: Config) -> str:
    """Render from the last snapshot when the store is busy (US-01), with the collecting note."""
    try:
        doc = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        _LOG.debug("snapshot unavailable: %s", type(exc).__name__)
        doc = {}
    sessions = doc.get("sessions") if isinstance(doc, dict) else None
    for entry in sessions if isinstance(sessions, list) else []:
        if (
            isinstance(entry, dict)
            and entry.get("host") == host.value
            and entry.get("session_id") == session_id
            and isinstance(entry.get("text"), str)
        ):
            return f"{entry['text']}\n  {COLLECTING_NOTE}"
    return f"[agent-meter] {host_label(host)} · session {session_id[:8]} {COLLECTING_NOTE}"
