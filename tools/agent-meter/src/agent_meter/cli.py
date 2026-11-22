"""``agent-meter`` command line (PRD §7, contracts §3.9).

Exit codes: 0 ok · 1 error · 2 usage · 3 ``doctor`` FAIL · 4 store busy · 5 reconcile diff.
``hook`` always exits 0 and is dispatched BEFORE any heavy import (no ``duckdb``, I-4).
Cross-track modules (``report``, ``sinks``, ``setup``, ``scheduler``) are imported lazily
inside their handlers and called only through their contract signatures.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from agent_meter.config import Config, load_config
from agent_meter.paths import HOME_ENV, AppHome

if TYPE_CHECKING:
    from agent_meter.store import Store

__all__ = [
    "EXIT_BUSY",
    "EXIT_DIFF",
    "EXIT_DOCTOR_FAIL",
    "EXIT_ERROR",
    "EXIT_OK",
    "EXIT_USAGE",
    "main",
]

# Command groups live in agent_meter/cli_commands/; they read shared helpers from this module.
from agent_meter.cli_commands.doctor import _cmd_doctor, _cmd_verify
from agent_meter.cli_commands.pricing_cmd import _cmd_pricing
from agent_meter.cli_commands.projects import (
    _cmd_config,
    _cmd_hours,
    _cmd_projects_list,
    _cmd_projects_merge,
    _cmd_projects_set,
    _cmd_tag,
)
from agent_meter.cli_commands.setup_cmd import _cmd_setup, _cmd_uninstall

EXIT_OK: Final = 0
EXIT_ERROR: Final = 1
EXIT_USAGE: Final = 2
EXIT_DOCTOR_FAIL: Final = 3
EXIT_BUSY: Final = 4
EXIT_DIFF: Final = 5

INTERACTIVE_LOCK_S: float = 30.0
SCHEDULED_LOCK_S: float = 60.0
SCHEDULER_STALE_AFTER: Final = timedelta(hours=2)
REFRESH_LOCK_S: float = 2.0
SANDBOX_RELOAD_EVERY: Final = timedelta(days=7)
SINCE_FOREVER: Final = date(2000, 1, 1)
DEFAULT_TASKS: Final = 5


class UsageError(Exception):
    """Bad command-line input (exit code 2)."""


class CommandError(Exception):
    """The command could not complete (exit code 1)."""


def _is_tty() -> bool:
    try:
        return sys.stdout.isatty()
    except (AttributeError, ValueError):
        return False


def _stdin_is_tty() -> bool:
    try:
        return sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


def _plain(obj: object) -> object:
    if is_dataclass(obj) and not isinstance(obj, type):
        return {f.name: _plain(getattr(obj, f.name)) for f in fields(obj)}
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {str(_plain(k)): _plain(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_plain(v) for v in obj]
    return obj


def _emit_json(obj: object) -> None:
    print(json.dumps(_plain(obj), default=str, sort_keys=True))


def _date(text: str | None, flag: str) -> date | None:
    if text is None:
        return None
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise UsageError(f"{flag}: expected YYYY-MM-DD, got {text!r}") from exc


def _decimal(text: str | None, flag: str, *, allow_none: bool = True) -> Decimal | None:
    if text is None:
        if allow_none:
            return None
        raise UsageError(f"{flag} is required")
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise UsageError(f"{flag}: {text!r} is not a decimal number") from exc
    if not value.is_finite() or value < 0:
        raise UsageError(f"{flag}: must be a non-negative decimal, got {text!r}")
    return value


@dataclass
class Ctx:
    home: AppHome
    quiet: bool
    _cfg: Config | None = field(default=None, repr=False)

    @property
    def cfg(self) -> Config:
        if self._cfg is None:
            self._cfg = load_config(self.home)
        return self._cfg

    def info(self, text: str) -> None:
        if not self.quiet:
            print(text)

    @staticmethod
    def err(text: str) -> None:
        print(f"agent-meter: {text}", file=sys.stderr)


# ----------------------------------------------------------------------------- store helpers


def _refresh_reference(ctx: Ctx, store: Store) -> None:
    """Reload pricing / projects / settings into the store (an invalid local price file keeps the old table)."""
    from agent_meter.config import host_defaults, settings_for_store
    from agent_meter.pricing import PricingError, load_pricing
    from agent_meter.project_resolver import load_projects_config

    try:
        pricing = load_pricing(ctx.home.pricing_local)
    except PricingError:
        pricing = None
    store.load_reference_data(
        pricing=pricing,
        host_defaults=host_defaults(ctx.cfg),
        projects=load_projects_config(ctx.home.projects),
        project_refs=[],
        settings=settings_for_store(ctx.cfg),
    )


@contextmanager
def _writer(ctx: Ctx) -> Iterator[Store]:
    from agent_meter.store import Store

    with Store.open(ctx.home, read_only=False, lock_timeout_s=INTERACTIVE_LOCK_S) as store:
        store.migrate()
        yield store


def _try_refresh(ctx: Ctx) -> bool:
    """Best-effort reference refresh; ``False`` when the store is busy (next open applies it)."""
    from agent_meter.locking import LockTimeout
    from agent_meter.store import Store

    try:
        with Store.open(ctx.home, read_only=False, lock_timeout_s=REFRESH_LOCK_S) as store:
            store.migrate()
            _refresh_reference(ctx, store)
    except LockTimeout:
        return False
    return True


@contextmanager
def _reader(ctx: Ctx) -> Iterator[Store]:
    from agent_meter.store import Store

    _try_refresh(ctx)
    with Store.open(ctx.home, read_only=True, lock_timeout_s=INTERACTIVE_LOCK_S) as store:
        yield store


def _looks_like_id(text: str) -> bool:
    return text.startswith(("git:", "path:")) or text == "(unassigned)"


def _resolve_project(store: Store, text: str, *, allow_unknown_id: bool = False) -> str:
    rows = store.query(
        "SELECT project_id, display_name FROM projects WHERE project_id = ? OR display_name = ? ORDER BY 1",
        [text, text],
    )
    exact = [str(r["project_id"]) for r in rows if r["project_id"] == text]
    if exact:
        return exact[0]
    if len(rows) == 1:
        return str(rows[0]["project_id"])
    if len(rows) > 1:
        ids = ", ".join(str(r["project_id"]) for r in rows)
        raise UsageError(f"project name {text!r} is ambiguous ({ids}); use the project id")
    if allow_unknown_id and _looks_like_id(text):
        return text
    raise UsageError(f"unknown project {text!r} (see 'agent-meter projects list')")


def _current_project(ctx: Ctx, store: Store) -> str:
    from agent_meter.project_resolver import ProjectResolver, load_projects_config

    user_home = Path(os.environ.get("HOME") or os.environ.get("USERPROFILE") or Path.home())
    resolver = ProjectResolver(store.path_cache(), load_projects_config(ctx.home.projects), home=user_home)
    return resolver.resolve(os.getcwd()).project_id


def _host_list(values: Sequence[str] | None) -> list[Any] | None:
    from agent_meter.model import Host

    if not values:
        return None
    hosts = []
    for value in values:
        for name in value.split(","):
            if not name.strip():
                continue
            try:
                hosts.append(Host(name.strip()))
            except ValueError as exc:
                valid = ", ".join(h.value for h in Host)
                raise UsageError(f"unknown host {name.strip()!r}; expected one of: {valid}") from exc
    return hosts


# ----------------------------------------------------------------------------- collect / last / tasks


def _cmd_collect(ctx: Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.collector import collect

    hosts = _host_list(ns.host)
    since = _date(ns.since, "--since")
    timeout = SCHEDULED_LOCK_S if ns.scheduled else INTERACTIVE_LOCK_S
    result = collect(ctx.home, ctx.cfg, hosts=hosts, since=since, full=ns.full, lock_timeout_s=timeout,
                     scheduled=ns.scheduled)
    if result.status == "locked":
        if ns.scheduled:
            ctx.info("store busy; skipping this cycle")
            return EXIT_OK
        ctx.err("store busy (another collect or hook is running); try again in a minute")
        return EXIT_BUSY
    if result.status == "error" or result.stats is None:
        ctx.err(result.message or "collect failed")
        return EXIT_ERROR
    stats = result.stats
    ctx.info(
        f"Collected {stats.units} units ({stats.calls_changed} calls, {stats.tasks_changed} tasks, "
        f"{stats.runs_changed} agent runs changed); skipped {result.units_skipped_unchanged} unchanged "
        f"in {result.duration_ms} ms"
    )
    if result.diagnostics:
        ctx.info(f"{len(result.diagnostics)} unit(s) had problems: run 'agent-meter doctor'")
    if ns.scheduled and ctx.cfg.bigquery.enabled:
        _scheduled_sync(ctx)
    return EXIT_OK


def _cmd_insights(ctx: Ctx, ns: argparse.Namespace) -> int:
    from zoneinfo import ZoneInfo

    from agent_meter.insights import (
        Thresholds,
        build_insights,
        insights_document,
        render_insights,
    )

    as_of = _date(ns.as_of, "--as-of") or datetime.now(ZoneInfo(ctx.cfg.timezone)).date()
    with _reader(ctx) as store:
        project = _resolve_project(store, ns.project) if ns.project else None
        report = build_insights(store, as_of=as_of, project_id=project, limits=Thresholds(window_days=ns.days))
    print(json.dumps(insights_document(report), indent=2, sort_keys=True) if ns.json else render_insights(report))
    return EXIT_OK


def _cmd_statusline(ctx: Ctx, _ns: argparse.Namespace) -> int:
    from agent_meter.statusline import render_statusline

    print(render_statusline(sys.stdin.read(), ctx.home, ctx.cfg))
    return EXIT_OK


def _cmd_budget(ctx: Ctx, ns: argparse.Namespace) -> int:
    from zoneinfo import ZoneInfo

    from agent_meter.budgets import budget_document, budget_status, render_budget

    as_of = _date(ns.as_of, "--as-of") or datetime.now(ZoneInfo(ctx.cfg.timezone)).date()
    with _reader(ctx) as store:
        status = budget_status(store, ctx.cfg.budget, as_of)
    print(json.dumps(budget_document(status), indent=2, sort_keys=True) if ns.json else render_budget(status))
    return EXIT_OK


def _cmd_app(ctx: Ctx, _ns: argparse.Namespace) -> int:
    try:
        from agent_meter.app.window import run_app

        run_app(ctx.home)
    except ModuleNotFoundError as exc:
        if exc.name != "webview":
            raise
        ctx.err("the desktop app needs an extra package: uv tool install --python 3.12 'agent-meter[app] @ git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter'")
        return EXIT_ERROR
    return EXIT_OK


def _scheduled_sync(ctx: Ctx) -> None:
    """``collect --scheduled`` also syncs the cloud sink; failures never fail the local collect."""
    try:
        from agent_meter.sinks import bigquery
    except ImportError as exc:
        ctx.err(f"cloud sync skipped: {type(exc).__name__} (install agent-meter[bigquery])")
        return
    with _writer(ctx) as store:
        last_full = store.get_meta("bq_last_full_reload")
        now = datetime.now(UTC)
        full = ctx.cfg.bigquery.mode == "sandbox" and (
            last_full is None or now - datetime.fromisoformat(last_full) >= SANDBOX_RELOAD_EVERY
        )
        result = bigquery.sync(ctx.home, ctx.cfg, store, full_reload=full)
        if full and result.status == "ok":
            store.set_meta("bq_last_full_reload", now.isoformat())
    if result.status != "ok":
        ctx.err(f"cloud sync {result.status}; the backlog is kept and retried next cycle")


def _cmd_last(ctx: Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.model import Host
    from agent_meter.summary import render_session_summary, session_summary

    with _reader(ctx) as store:
        where, params = "", []
        if ns.project:
            where, params = "WHERE project_id = ?", [_resolve_project(store, ns.project)]
        rows = store.query(f"SELECT host, session_id FROM v_sessions {where} ORDER BY ended_at DESC LIMIT 1", params)
        summary = (
            session_summary(store, Host(str(rows[0]["host"])), str(rows[0]["session_id"]), now=datetime.now(UTC))
            if rows
            else None
        )
    if ns.json:
        _emit_json(summary)
    elif summary is None:
        print("No sessions yet — run `agent-meter collect`")
    else:
        print(render_session_summary(summary, ctx.cfg))
    return EXIT_OK


def _cmd_tasks(ctx: Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.collector import reader_roots
    from agent_meter.summary import read_task_label, render_task_rollup, task_rollups

    last = ns.last
    if last is None and not (ns.session or ns.project or ns.tag or ns.since):
        last = DEFAULT_TASKS
    if last is not None and last < 1:
        raise UsageError("--last must be at least 1")
    since = _date(ns.since, "--since")
    with _reader(ctx) as store:
        project_id = _resolve_project(store, ns.project) if ns.project else None
        rollups = task_rollups(store, last=last, session_id=ns.session, project_id=project_id, tag=ns.tag, since=since)
    if ns.json:
        _emit_json(rollups)
        return EXIT_OK
    if not rollups:
        print("No tasks found — run `agent-meter collect`")
        return EXIT_OK
    labels = _is_tty() and ctx.cfg.show_task_labels  # labels are display-only, never persisted (BR-16)
    roots = reader_roots(ctx.cfg) if labels else {}
    blocks = []
    for rollup in rollups:
        label = read_task_label(roots, rollup.host, rollup.session_id, rollup.task_id) if labels else None
        blocks.append(render_task_rollup(rollup, ctx.cfg, label=label))
    print("\n\n".join(blocks))
    return EXIT_OK


# ----------------------------------------------------------------------------- report / sync


def _cmd_report(ctx: Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.report import (
        ReportOptions,
        build_report,
        report_insights,
        write_report,
    )

    date_from, date_to = _date(ns.date_from, "--from"), _date(ns.date_to, "--to")
    with _reader(ctx) as store:
        project_id = _resolve_project(store, ns.project) if ns.project else None
        try:
            options = ReportOptions(
                date_from=date_from, date_to=date_to, month=ns.month, project_id=project_id, client=ns.client,
                display_currency=ctx.cfg.display_currency, usd_rate=ctx.cfg.usd_rate,
            )
        except ValueError as exc:
            raise UsageError(str(exc)) from exc
        html = build_report(store, options, insights=report_insights(store, options))
    path = write_report(html, Path(ns.out) if ns.out else ctx.home.report)
    print(path)
    if ns.open:
        import webbrowser

        webbrowser.open(path.resolve().as_uri())
    return EXIT_OK


def _cmd_sync(ctx: Ctx, ns: argparse.Namespace) -> int:
    bq = ctx.cfg.bigquery
    if not bq.enabled or not bq.project:
        ctx.err("cloud sink not configured: run 'agent-meter setup --cloud'")
        return EXIT_ERROR
    from agent_meter.sinks import bigquery

    with _writer(ctx) as store:
        _refresh_reference(ctx, store)
        result = bigquery.sync(ctx.home, ctx.cfg, store, full_reload=ns.full_reload, dry_run=ns.dry_run)
    for load in result.loads:
        state = "ok" if load.ok else f"failed ({load.error_class})"
        ctx.info(f"  {load.table:<20} {load.rows:>7} rows  {state}")
    backlog = sum(result.backlog.values())
    ctx.info(f"sync {result.status}" + (f" · backlog {backlog} rows" if backlog else ""))
    if result.status in ("ok", "dry_run"):
        return EXIT_OK
    ctx.err(f"sync {result.status}: the outbox is kept and retried next run (see 'agent-meter doctor')")
    return EXIT_ERROR


# ----------------------------------------------------------------------------- parser


def _json_flag(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", action="store_true", help="machine-readable output")


def _build_parser() -> argparse.ArgumentParser:
    from agent_meter import __version__

    parser = argparse.ArgumentParser(
        prog="agent-meter",
        description="Token, API-equivalent cost and latency metrics for Claude Code and Antigravity.",
    )
    parser.add_argument("--version", action="version", version=f"agent-meter {__version__}")
    parser.add_argument("--home", help=f"data directory (default ${HOME_ENV} or ~/.agent-meter)")
    parser.add_argument("--quiet", action="store_true", help="only print errors")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    _add_ingest_commands(sub)
    _add_data_commands(sub)
    _add_admin_commands(sub)
    _add_pricing_commands(sub)
    return parser


def _add_ingest_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """setup, collect, last, tasks, report, sync."""
    p = sub.add_parser("setup", help="interactive setup wizard (hooks, scheduler, cloud)")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--local", action="store_true")
    mode.add_argument("--cloud", action="store_true")
    p.add_argument("--yes", action="store_true", help="accept defaults without prompting")
    p.add_argument("--hosts", help="claude-code,antigravity-cli,antigravity-ide,antigravity-app")
    p.add_argument("--triggers", help="hooks,scheduler | hooks | scheduler | none")
    p.add_argument("--gcp-project")
    p.add_argument("--mode", choices=("billing", "sandbox"))
    p.add_argument("--no-backfill", action="store_true")
    p.set_defaults(handler=_cmd_setup)

    p = sub.add_parser("collect", help="incremental ingest of all hosts")
    p.add_argument("--host", action="append", help="limit to host(s); repeatable or comma-separated")
    p.add_argument("--since", help="only units modified on/after YYYY-MM-DD")
    p.add_argument("--full", action="store_true", help="re-read every unit (still idempotent)")
    p.add_argument("--scheduled", action="store_true", help=argparse.SUPPRESS)
    p.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    p.set_defaults(handler=_cmd_collect)

    p = sub.add_parser("last", help="print the last session summary")
    p.add_argument("--project")
    _json_flag(p)
    p.set_defaults(handler=_cmd_last)

    p = sub.add_parser("insights", help="where to cut spending, from fixed rules over your data")
    p.add_argument("--project")
    p.add_argument("--days", type=int, default=30, help="period length (default 30)")
    p.add_argument("--as-of", help="last day of the period, YYYY-MM-DD; repeats a past result exactly")
    _json_flag(p)
    p.set_defaults(handler=_cmd_insights)

    p = sub.add_parser("app", help="open the desktop app")
    p.set_defaults(handler=_cmd_app)

    p = sub.add_parser("statusline", help="one line for the Claude Code status bar; reads its JSON from stdin")
    p.set_defaults(handler=_cmd_statusline)

    p = sub.add_parser("budget", help="spending against your limits, month-end forecast and plan value")
    p.add_argument("--as-of", help="day to report on, YYYY-MM-DD")
    _json_flag(p)
    p.set_defaults(handler=_cmd_budget)

    p = sub.add_parser("tasks", help="per-task rollups with every subagent")
    p.add_argument("--last", nargs="?", type=int, const=1, help="the N most recent tasks (default 1)")
    p.add_argument("--session")
    p.add_argument("--project")
    p.add_argument("--tag")
    p.add_argument("--since", help="tasks started on/after YYYY-MM-DD")
    _json_flag(p)
    p.set_defaults(handler=_cmd_tasks)

    p = sub.add_parser("report", help="build the static HTML report")
    p.add_argument("--open", action="store_true")
    p.add_argument("--out")
    p.add_argument("--month", help="YYYY-MM")
    p.add_argument("--from", dest="date_from")
    p.add_argument("--to", dest="date_to")
    p.add_argument("--project")
    p.add_argument("--client")
    p.set_defaults(handler=_cmd_report)

    p = sub.add_parser("sync", help="upload the outbox to BigQuery")
    p.add_argument("--full-reload", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(handler=_cmd_sync)


def _add_data_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """projects, hours, tag."""
    p = sub.add_parser("projects", help="list and edit projects and clients (projects.yaml)")
    psub = p.add_subparsers(dest="projects_command", metavar="<list|set|merge>", required=True)
    q = psub.add_parser("list")
    _json_flag(q)
    q.set_defaults(handler=_cmd_projects_list)
    q = psub.add_parser("set")
    q.add_argument("project", help="project id or display name")
    q.add_argument("--name")
    q.add_argument("--client")
    q.add_argument("--billing", choices=("hourly", "fixed"))
    q.add_argument("--rate")
    q.add_argument("--price")
    q.add_argument("--currency")
    q.set_defaults(handler=_cmd_projects_set)
    q = psub.add_parser("merge")
    q.add_argument("src")
    q.add_argument("dst")
    q.set_defaults(handler=_cmd_projects_merge)

    p = sub.add_parser("hours", help="manual developer-hours overrides")
    hsub = p.add_subparsers(dest="hours_command", metavar="<set|list|unset>", required=True)
    q = hsub.add_parser("set")
    q.add_argument("project")
    q.add_argument("period", help="YYYY-MM-DD or YYYY-MM")
    q.add_argument("hours")
    q.set_defaults(handler=_cmd_hours)
    q = hsub.add_parser("unset")
    q.add_argument("project")
    q.add_argument("period")
    q.set_defaults(handler=_cmd_hours)
    q = hsub.add_parser("list")
    _json_flag(q)
    q.set_defaults(handler=_cmd_hours)

    p = sub.add_parser("tag", help="group tasks into a work item")
    p.add_argument("name", nargs="?")
    p.add_argument("--last", type=int, help="tag the N most recent tasks after the fact")
    p.add_argument("--clear", action="store_true")
    p.add_argument("--project")
    p.set_defaults(handler=_cmd_tag)


def _add_admin_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """doctor, config, uninstall, verify."""
    p = sub.add_parser("doctor", help="health check (exit 3 on FAIL)")
    p.add_argument("--cloud", action="store_true", help="also run the GCP prerequisite checks")
    _json_flag(p)
    p.set_defaults(handler=_cmd_doctor)

    p = sub.add_parser("config", help="show and edit config.toml")
    csub = p.add_subparsers(dest="config_command", metavar="<show|get|set|edit>")
    p.set_defaults(handler=_cmd_config, json=False)
    q = csub.add_parser("show")
    _json_flag(q)
    q = csub.add_parser("get")
    q.add_argument("key")
    _json_flag(q)
    q = csub.add_parser("set")
    q.add_argument("key")
    q.add_argument("value")
    csub.add_parser("edit")

    p = sub.add_parser("uninstall", help="remove hooks and scheduler, restore settings")
    p.add_argument("--purge", action="store_true", help="also delete the data directory (only agent-meter files; refuses $HOME, / and foreign dirs)")
    p.add_argument("--yes", action="store_true")
    p.add_argument("--keep-scheduler", action="store_true")
    p.set_defaults(handler=_cmd_uninstall)

    p = sub.add_parser("verify", help="reconcile local totals against independent sources")
    p.add_argument("--reconcile", action="store_true")
    p.add_argument("--from", dest="date_from")
    p.add_argument("--to", dest="date_to")
    p.add_argument("--host", action="append")
    p.add_argument("--cloud", action="store_true", help="local store vs BigQuery")
    _json_flag(p)
    p.set_defaults(handler=_cmd_verify)


def _add_pricing_commands(sub: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """pricing list|unpriced|add|set|alias|remove|validate."""
    p = sub.add_parser("pricing", help="price table: list, unpriced, add, set, alias, remove, validate")
    rsub = p.add_subparsers(dest="pricing_command", metavar="<command>", required=True)
    for name in ("list", "unpriced"):
        _json_flag(rsub.add_parser(name))
    for name in ("add", "set"):
        q = rsub.add_parser(name)
        q.add_argument("model")
        q.add_argument("--input", required=True, help="USD per million tokens")
        q.add_argument("--output", required=True)
        q.add_argument("--cache-read", required=True)
        q.add_argument("--cache-write-5m")
        q.add_argument("--cache-write-1h")
        q.add_argument("--effective-from", help="YYYY-MM-DD (default: since forever)")
        q.add_argument("--min-prompt-tokens", type=int, default=0)
        q.add_argument("--source-url")
    q = rsub.add_parser("alias")
    q.add_argument("alias")
    q.add_argument("model")
    q.add_argument("--estimated", action="store_true")
    q = rsub.add_parser("remove")
    q.add_argument("--model")
    q.add_argument("--effective-from")
    q.add_argument("--alias")
    q = rsub.add_parser("validate")
    q.add_argument("file", nargs="?")
    p.set_defaults(handler=_cmd_pricing)


# ----------------------------------------------------------------------------- entry point


def _hook_fast_path(args: Sequence[str]) -> int | None:
    """Dispatch ``[--home X] [--quiet] hook …`` before argparse or any heavy import (I-4)."""
    home: str | None = None
    index = 0
    while index < len(args):
        item = args[index]
        if item == "--home" and index + 1 < len(args):
            home, index = args[index + 1], index + 2
        elif item.startswith("--home="):
            home, index = item.split("=", 1)[1], index + 1
        elif item == "--quiet":
            index += 1
        else:
            break
    if index >= len(args) or args[index] not in ("hook", "hook-worker"):
        return None
    if home:
        os.environ[HOME_ENV] = home  # inherited by the detached worker
    if args[index] == "hook-worker":
        from agent_meter.hook import worker_main

        return worker_main(args[index + 1 :])
    from agent_meter.hook import hook_main

    stdin = getattr(sys.stdin, "buffer", None) or io.BytesIO()
    return hook_main(args[index + 1 :], stdin, sys.stdout)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    fast = _hook_fast_path(args)
    if fast is not None:
        return fast
    parser = _build_parser()
    try:
        ns = parser.parse_args(args)
    except SystemExit as exc:
        return exc.code if isinstance(exc.code, int) else EXIT_USAGE
    if ns.command is None:
        parser.print_usage(sys.stderr)
        return EXIT_USAGE
    return _run(ns)


def _run(ns: argparse.Namespace) -> int:
    from agent_meter.config import ConfigError
    from agent_meter.locking import LockTimeout
    from agent_meter.paths import SecretCorruptError
    from agent_meter.pricing import PricingError
    from agent_meter.project_resolver import ProjectsConfigError
    from agent_meter.store import StoreError
    from agent_meter.summary import SummaryError

    ctx = Ctx(home=AppHome.resolve(ns.home), quiet=ns.quiet)
    try:
        code: int = ns.handler(ctx, ns)
    except UsageError as exc:
        ctx.err(str(exc))
        return EXIT_USAGE
    except LockTimeout:
        ctx.err("store busy (a collect or hook is running); try again in a minute")
        return EXIT_BUSY
    except PricingError as exc:
        for error in exc.errors:
            ctx.err(error)
        return EXIT_ERROR
    except (CommandError, ConfigError, ProjectsConfigError, SecretCorruptError, StoreError, SummaryError) as exc:
        ctx.err(str(exc))
        return EXIT_ERROR
    return code
