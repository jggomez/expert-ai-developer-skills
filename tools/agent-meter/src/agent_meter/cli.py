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

EXIT_OK: Final = 0
EXIT_ERROR: Final = 1
EXIT_USAGE: Final = 2
EXIT_DOCTOR_FAIL: Final = 3
EXIT_BUSY: Final = 4
EXIT_DIFF: Final = 5

INTERACTIVE_LOCK_S: float = 30.0
SCHEDULED_LOCK_S: float = 60.0
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
    result = collect(ctx.home, ctx.cfg, hosts=hosts, since=since, full=ns.full, lock_timeout_s=timeout)
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
    from agent_meter.report import ReportOptions, build_report, write_report

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
        html = build_report(store, options)
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


# ----------------------------------------------------------------------------- projects / hours / tag


def _cmd_projects_list(ctx: Ctx, ns: argparse.Namespace) -> int:
    with _reader(ctx) as store:
        rows = store.query(
            """
            SELECT p.project_id, p.display_name, p.kind, p.remote_url, p.client, p.billing_model,
                   p.hourly_rate, p.fixed_price, p.rate_currency,
                   (SELECT COUNT(*) FROM v_sessions s WHERE s.project_id = p.project_id) AS sessions,
                   (SELECT SUM(d.cost_usd) FROM v_daily_project_cost d WHERE d.project_id = p.project_id) AS cost_usd,
                   (SELECT COALESCE(SUM(d.unpriced_calls), 0) FROM v_daily_project_cost d
                     WHERE d.project_id = p.project_id) AS unpriced_calls
            FROM projects p
            -- Hide orphan identities (e.g. a pre-move path id after its sessions were relocated).
            WHERE p.project_id = '(unassigned)' OR p.client IS NOT NULL OR p.billing_model IS NOT NULL
               OR EXISTS (SELECT 1 FROM sessions s WHERE s.project_id = p.project_id)
               OR EXISTS (SELECT 1 FROM llm_calls c WHERE c.project_id = p.project_id)
               OR EXISTS (SELECT 1 FROM dev_hours_manual h WHERE h.project_id = p.project_id)
            ORDER BY p.display_name, p.project_id
            """
        )
    if ns.json:
        _emit_json(rows)
        return EXIT_OK
    from agent_meter.summary import fmt_cost

    for row in rows:
        cost = row["cost_usd"]
        money = fmt_cost(
            cost if isinstance(cost, Decimal) else None, ctx.cfg, unpriced_calls=int(str(row["unpriced_calls"])),
            detail=False,
        )
        client = f" · client {row['client']}" if row["client"] else ""
        print(f"{row['project_id']:<22} {row['display_name']:<28} {row['sessions']:>5} sessions  {money}{client}")
    return EXIT_OK


def _cmd_projects_set(ctx: Ctx, ns: argparse.Namespace) -> int:
    from dataclasses import replace

    from agent_meter.project_resolver import (
        ProjectOverride,
        ProjectsConfig,
        load_projects_config,
        save_projects_config,
    )

    rate = _decimal(ns.rate, "--rate")
    price = _decimal(ns.price, "--price")
    currency = ns.currency.upper() if ns.currency else None
    if currency is not None and (len(currency) != 3 or not currency.isalpha()):
        raise UsageError(f"--currency: expected a 3-letter ISO code, got {ns.currency!r}")
    with _writer(ctx) as store:
        pid = _resolve_project(store, ns.project, allow_unknown_id=True)
        cfg = load_projects_config(ctx.home.projects)
        current = cfg.projects.get(pid, ProjectOverride())
        changes: dict[str, Any] = {}
        for attr, value in (("display_name", ns.name), ("client", ns.client), ("billing", ns.billing),
                            ("rate", rate), ("fixed_price", price), ("currency", currency)):
            if value is not None:
                changes[attr] = value or None
        updated = replace(current, **changes)
        projects = {**cfg.projects, pid: updated}
        save_projects_config(
            ProjectsConfig(projects=projects, path_aliases=cfg.path_aliases, ignore=cfg.ignore, merges=cfg.merges),
            ctx.home.projects,
        )
        _refresh_reference(ctx, store)
    ctx.info(f"updated {pid} in {ctx.home.projects}")
    return EXIT_OK


def _cmd_projects_merge(ctx: Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.project_resolver import (
        ProjectsConfig,
        load_projects_config,
        save_projects_config,
    )

    with _writer(ctx) as store:
        src = _resolve_project(store, ns.src)
        dst = _resolve_project(store, ns.dst, allow_unknown_id=True)
        if src == dst:
            raise UsageError("cannot merge a project into itself")
        cfg = load_projects_config(ctx.home.projects)
        merges = {**cfg.merges, src: dst}
        save_projects_config(
            ProjectsConfig(projects=cfg.projects, path_aliases=cfg.path_aliases, ignore=cfg.ignore, merges=merges),
            ctx.home.projects,
        )
        moved = store.merge_projects(src, dst)
        _refresh_reference(ctx, store)
    ctx.info(f"merged {src} into {dst}: {moved} rows re-keyed (recorded in {ctx.home.projects})")
    return EXIT_OK


def _cmd_hours(ctx: Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.store import StoreError

    if ns.hours_command == "list":
        with _reader(ctx) as store:
            rows = store.query(
                """
                SELECT m.project_id, COALESCE(p.display_name, m.project_id) AS display_name, m.period, m.hours,
                       'manual' AS source, m.set_at
                FROM dev_hours_manual m LEFT JOIN projects p ON p.project_id = m.project_id
                ORDER BY m.project_id, m.period
                """
            )
        if ns.json:
            _emit_json(rows)
        elif not rows:
            print("No manual hours set (derived hours are used)")
        else:
            for row in rows:
                print(f"{row['display_name']:<28} {row['period']:<10} {row['hours']:>8} h  (manual)")
        return EXIT_OK
    with _writer(ctx) as store:
        pid = _resolve_project(store, ns.project, allow_unknown_id=True)
        try:
            if ns.hours_command == "set":
                hours = _decimal(ns.hours, "hours", allow_none=False)
                assert hours is not None
                store.set_manual_hours(pid, ns.period, hours)
                ctx.info(f"{pid} {ns.period}: {hours} h (manual, overrides derived hours)")
            else:
                removed = store.unset_manual_hours(pid, ns.period)
                ctx.info(f"{pid} {ns.period}: " + ("manual hours removed" if removed else "no manual hours were set"))
        except StoreError as exc:
            raise UsageError(str(exc)) from exc
    return EXIT_OK


def _cmd_tag(ctx: Ctx, ns: argparse.Namespace) -> int:
    name = (ns.name or "").strip()
    if ns.clear == bool(name):
        raise UsageError("give a tag name, or --clear to stop tagging")
    if len(name) > 80:
        raise UsageError("tag names are at most 80 characters")
    if ns.last is not None and (ns.clear or ns.last < 1):
        raise UsageError("--last N needs a tag name and N >= 1")
    with _writer(ctx) as store:
        pid = _resolve_project(store, ns.project) if ns.project else _current_project(ctx, store)
        now = datetime.now(UTC)
        if ns.clear:
            store.set_tag(pid, None, now)
            ctx.info(f"{pid}: tagging stopped")
        elif ns.last is not None:
            tagged = store.tag_last(pid, name, ns.last)
            ctx.info(f"{pid}: tagged {len(tagged)} task(s) with {name!r}")
        else:
            store.set_tag(pid, name, now)
            ctx.info(f"{pid}: new tasks are tagged {name!r} until 'agent-meter tag --clear'")
    return EXIT_OK


# ----------------------------------------------------------------------------- config


def _cmd_config(ctx: Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.config import (
        ConfigError,
        config_items,
        get_key,
        save_config,
        set_key,
    )

    command = ns.config_command or "show"
    if command == "show":
        items = config_items(ctx.cfg)
        if ns.json:
            _emit_json(dict(items))
        else:
            print("\n".join(f"{key} = {value}" for key, value in items))
        return EXIT_OK
    try:
        if command == "get":
            value = get_key(ctx.cfg, ns.key)
            _emit_json({ns.key: value}) if ns.json else print(value)
            return EXIT_OK
        if command == "set":
            save_config(set_key(ctx.cfg, ns.key, ns.value), ctx.home)
            ctx.info(f"{ns.key} = {ns.value}")
            return EXIT_OK
    except ConfigError as exc:
        raise UsageError(str(exc)) from exc
    return _edit_config(ctx)


def _edit_config(ctx: Ctx) -> int:
    import shlex
    import subprocess

    from agent_meter.config import save_config

    if not ctx.home.config.exists():
        save_config(ctx.cfg, ctx.home)
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    completed = subprocess.run([*shlex.split(editor), str(ctx.home.config)], check=False)
    if completed.returncode != 0:
        raise CommandError(f"editor exited with code {completed.returncode}")
    load_config(ctx.home)
    ctx.info(f"{ctx.home.config} is valid")
    return EXIT_OK


# ----------------------------------------------------------------------------- pricing


def _price_dict(row: Any) -> dict[str, object]:
    return {
        "model": row.model, "effective_from": row.effective_from.isoformat(),
        "min_prompt_tokens": row.min_prompt_tokens, "input": row.input, "output": row.output,
        "cache_write_5m": row.cache_write_5m, "cache_write_1h": row.cache_write_1h,
        "cache_read": row.cache_read, "source": row.source,
    }


def _pricing_hint(model: str) -> str:
    return f"agent-meter pricing add {model} --input … --output … --cache-read … --effective-from YYYY-MM-DD"


def _cmd_pricing(ctx: Ctx, ns: argparse.Namespace) -> int:
    from agent_meter import pricing

    command = ns.pricing_command
    local = ctx.home.pricing_local
    if command == "list":
        table = pricing.load_pricing(local)
        rows = [_price_dict(r) for r in table.rows]
        if ns.json:
            _emit_json(rows)
            return EXIT_OK
        for r in rows:
            print(f"{r['model']:<34} from {r['effective_from']}  ≥{r['min_prompt_tokens']:>7} tok  "
                  f"in {r['input']}  out {r['output']}  read {r['cache_read']}  ({r['source']})")
        for alias in table.aliases:
            note = " (estimated)" if alias.estimated else ""
            print(f"alias {alias.alias} → {alias.model}{note} ({alias.source})")
        return EXIT_OK
    if command == "unpriced":
        with _reader(ctx) as store:
            rows_u = store.query("SELECT * FROM v_unpriced_models ORDER BY calls DESC, host")
        if ns.json:
            _emit_json(rows_u)
        elif not rows_u:
            print("Every call is priced")
        else:
            for row in rows_u:
                model = str(row["model_effective"] or "(no model; set hosts.<host>.default_model)")
                print(f"{row['host']:<16} {model:<34} {row['calls']:>6} calls · fix: {_pricing_hint(model)}")
        return EXIT_OK
    if command == "validate":
        path = Path(ns.file) if ns.file else local
        if not path.exists():
            if ns.file:
                raise UsageError(f"{path} does not exist")
            errors = pricing.validate_file(pricing.SHIPPED_PATH)
        else:
            errors = pricing.validate_file(path)
        for error in errors:
            print(error)
        if errors:
            return EXIT_ERROR
        ctx.info(f"{path if path.exists() else pricing.SHIPPED_PATH} is valid")
        return EXIT_OK
    _change_pricing(ctx, ns, local)
    if not _try_refresh(ctx):
        ctx.info("store busy: the new prices apply on the next collect or report")
    return EXIT_OK


def _change_pricing(ctx: Ctx, ns: argparse.Namespace, local: Path) -> None:
    from agent_meter import pricing

    command = ns.pricing_command
    if command in ("add", "set"):
        effective = _date(ns.effective_from, "--effective-from") or SINCE_FOREVER
        if ns.min_prompt_tokens < 0:
            raise UsageError("--min-prompt-tokens must be >= 0")
        row = pricing.PriceRow(
            model=ns.model, effective_from=effective, min_prompt_tokens=ns.min_prompt_tokens,
            input=_req(ns.input, "--input"), output=_req(ns.output, "--output"),
            cache_write_5m=_decimal(ns.cache_write_5m, "--cache-write-5m"),
            cache_write_1h=_decimal(ns.cache_write_1h, "--cache-write-1h"),
            cache_read=_req(ns.cache_read, "--cache-read"), source="local", source_url=ns.source_url,
            fetched_at=datetime.now(UTC).date(),
        )
        pricing.add_local_price(local, row, replace=command == "set")
        ctx.info(f"{'set' if command == 'set' else 'added'} {ns.model} from {effective} in {local}")
    elif command == "alias":
        pricing.add_local_alias(local, ns.alias, ns.model, estimated=ns.estimated)
        ctx.info(f"alias {ns.alias} → {ns.model}{' (estimated)' if ns.estimated else ''}")
    elif command == "remove":
        if not ns.model and not ns.alias:
            raise UsageError("give --model and/or --alias")
        removed = pricing.remove_local(
            local, model=ns.model, effective_from=_date(ns.effective_from, "--effective-from"), alias=ns.alias
        )
        if not removed:
            raise CommandError("nothing matched in pricing.local.yaml (shipped prices cannot be removed)")
        ctx.info(f"removed {removed} entr{'y' if removed == 1 else 'ies'} from {local}")


def _req(text: str, flag: str) -> Decimal:
    value = _decimal(text, flag, allow_none=False)
    assert value is not None
    return value


# ----------------------------------------------------------------------------- doctor


def _age(value: object, now: datetime) -> str:
    if not isinstance(value, datetime):
        return "never"
    seconds = int((now - value).total_seconds())
    if seconds < 120:
        return "just now"
    if seconds < 7200:
        return f"{seconds // 60} min ago"
    if seconds < 172_800:
        return f"{seconds // 3600} h ago"
    return f"{seconds // 86_400} days ago"


def _check(status: str, name: str, message: str) -> dict[str, str]:
    return {"status": status, "check": name, "message": message}


def _host_checks(ctx: Ctx, store: Store, now: datetime) -> list[dict[str, str]]:
    from agent_meter.collector import reader_roots
    from agent_meter.model import Host
    from agent_meter.readers.base import available_readers
    from agent_meter.setup import hosts as setup_hosts
    from agent_meter.setup import settings_merge

    user_home = Path(os.environ.get("HOME") or Path.home())
    claude_reg = settings_merge.registration_status(
        setup_hosts.claude_settings_path(user_home, os.environ), "claude-code"
    )
    agy_reg = settings_merge.registration_status(setup_hosts.antigravity_hooks_path(user_home), "antigravity")
    health = {str(r["host"]): r for r in store.query("SELECT * FROM v_health")}
    checks = []
    for reader in available_readers(reader_roots(ctx.cfg)):
        registration = claude_reg if reader.host is Host.CLAUDE_CODE else agy_reg
        row = health.get(reader.host.value, {})
        parts = ["hook registered" if registration == "registered" else f"hooks {registration} (scheduler-only)"]
        parts.append(f"last ingest {_age(row.get('last_ingested_at'), now)}")
        parts.append(f"{int(str(row.get('units') or 0))} units")
        earliest = reader.earliest_available()
        if earliest is not None:
            parts.append(f"earliest transcript {earliest.isoformat()}")
        status = "OK"
        unknown = int(str(row.get("unknown_formats") or 0))
        diagnostics = int(str(row.get("diagnostics_7d") or 0))
        if unknown:
            status = "WARN"
            parts.append(f"format changed: {unknown} unknown host format(s)")
        if diagnostics:
            status = "WARN"
            parts.append(f"{diagnostics} file(s) skipped or corrupt in 7 days")
        if not row or registration in ("partial", "unreadable"):
            status = "WARN"
        checks.append(_check(status, reader.host.value, " · ".join(parts)))
    if not checks:
        checks.append(_check("WARN", "hosts", "no Claude Code or Antigravity data found"))
    return checks


def _pricing_checks(ctx: Ctx, store: Store) -> list[dict[str, str]]:
    from agent_meter import pricing

    checks = []
    if ctx.home.pricing_local.exists():
        errors = pricing.validate_file(ctx.home.pricing_local)
        if errors:
            checks.append(_check("FAIL", "pricing", f"pricing.local.yaml invalid: {errors[0]} (previous table in use)"))
    unpriced = store.query("SELECT * FROM v_unpriced_models ORDER BY calls DESC")
    for row in unpriced:
        model = str(row["model_effective"] or "(no model)")
        checks.append(_check("WARN", "pricing", f"unpriced model: {model} ({row['calls']} calls) · fix: {_pricing_hint(model)}"))
    if not checks:
        count = store.query("SELECT COUNT(DISTINCT model) AS n FROM pricing")[0]["n"]
        checks.append(_check("OK", "pricing", f"{count} models priced · every call priced"))
    return checks


def _secret_check(home: AppHome) -> dict[str, str]:
    from agent_meter.paths import SecretCorruptError, read_secret

    try:
        salt = read_secret(home)
    except SecretCorruptError as exc:
        return _check("FAIL", "secret", str(exc))
    if salt is None:
        return _check("OK", "secret", "not created yet (created on first collect)")
    return _check("OK", "secret", "present · mode 0600")


def _doctor_checks(ctx: Ctx, *, cloud: bool) -> list[dict[str, str]]:
    import agent_meter.scheduler as scheduler
    from agent_meter.config import ConfigError

    now = datetime.now(UTC)
    checks: list[dict[str, str]] = []
    try:
        cfg = ctx.cfg
        checks.append(_check("OK", "config", f"timezone {cfg.timezone} · notify {cfg.notify}"))
    except ConfigError as exc:
        return [_check("FAIL", "config", str(exc))]
    checks.append(_secret_check(ctx.home))
    with _reader(ctx) as store:
        checks += _host_checks(ctx, store, now)
        last = store.get_meta("last_collect_at")
        if last:
            checks.append(_check("OK", "store", f"schema v{store.get_meta('schema_version')} · last collect "
                                                f"{_age(datetime.fromisoformat(last), now)}"))
        else:
            checks.append(_check("WARN", "store", "no data yet — run 'agent-meter collect'"))
        checks += _pricing_checks(ctx, store)
        for row in store.query("SELECT * FROM v_untracked ORDER BY host"):
            checks.append(_check(
                "WARN", str(row["host"]),
                f"{row['conversations']} {row['reason']} conversations untracked "
                f"({row['observed_from']} → {row['observed_to']})",
            ))
        if cfg.bigquery.enabled:
            checks += _cloud_checks(ctx, store, now, deep=cloud)
    state = scheduler.status()
    checks.append(_check("OK" if state == "loaded" else "WARN", "scheduler", {
        "loaded": "loaded (every 15 min)", "not_loaded": "not loaded (hooks/manual collect only)",
        "unsupported": "no supported scheduler on this platform",
    }[state]))
    return checks


def _cloud_checks(ctx: Ctx, store: Store, now: datetime, *, deep: bool) -> list[dict[str, str]]:
    from agent_meter.sinks.outbox import pending_counts

    bq = ctx.cfg.bigquery
    backlog = sum(pending_counts(store).values())
    last = store.get_meta("bq_last_sync_at")
    age = _age(datetime.fromisoformat(last), now) if last else "never"
    status = "OK" if last and backlog == 0 else "WARN"
    checks = [_check(status, "bigquery", f"{bq.project}.{bq.dataset} · last sync {age} · outbox {backlog}")]
    if deep:
        from agent_meter.setup import gcp_checks

        for item in gcp_checks.run_checks(bq.project):
            fix = f" · fix: {item.fix_command}" if item.fix_command else ""
            checks.append(_check(item.status, f"gcp:{item.id}", item.message + fix))
    return checks


def _render_checks(checks: Sequence[dict[str, str]]) -> str:
    return "\n".join(f"{c['status']:<5} {c['check']:<17} {c['message']}" for c in checks)


def _cmd_doctor(ctx: Ctx, ns: argparse.Namespace) -> int:
    checks = _doctor_checks(ctx, cloud=ns.cloud)
    if ns.json:
        _emit_json(checks)
    else:
        print(_render_checks(checks))
    return EXIT_DOCTOR_FAIL if any(c["status"] == "FAIL" for c in checks) else EXIT_OK


# ----------------------------------------------------------------------------- verify --reconcile


_METRICS: Final = ("calls", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")


def _source_totals(ctx: Ctx, hosts: list[Any] | None, date_from: date, date_to: date) -> dict[tuple[str, date], list[int]]:
    """Independent re-read of every unit, deduplicated by call id (lowest owner rank wins)."""
    from zoneinfo import ZoneInfo

    from agent_meter.collector import reader_roots
    from agent_meter.model import ReaderOptions
    from agent_meter.paths import load_secret
    from agent_meter.readers.base import available_readers

    zone = ZoneInfo(ctx.cfg.timezone)
    options = ReaderOptions(now=datetime.now(UTC), idle_threshold_s=ctx.cfg.idle_threshold_s,
                            description_salt=load_secret(ctx.home))
    best: dict[str, Any] = {}
    for reader in available_readers(reader_roots(ctx.cfg)):
        if hosts is not None and reader.host not in hosts:
            continue
        for unit in reader.discover():
            for call in reader.read_unit(unit, options).calls:
                kept = best.get(call.call_id)
                if kept is None or call.owner_rank < kept.owner_rank:
                    best[call.call_id] = call
    totals: dict[tuple[str, date], list[int]] = {}
    for call in best.values():
        day = call.ts.astimezone(zone).date()
        if not date_from <= day <= date_to:
            continue
        row = totals.setdefault((call.host.value, day), [0, 0, 0, 0, 0])
        values = (1, call.input_tokens, call.output_tokens, call.cache_read_tokens,
                  (call.cache_write_5m_tokens or 0) + (call.cache_write_1h_tokens or 0))
        for index, value in enumerate(values):
            row[index] += value or 0
    return totals


def _store_totals(store: Store, hosts: list[Any] | None, date_from: date, date_to: date) -> dict[tuple[str, date], list[int]]:
    rows = store.query(
        """
        SELECT host, local_date, COUNT(*) AS calls, SUM(COALESCE(input_tokens, 0)) AS input_tokens,
               SUM(COALESCE(output_tokens, 0)) AS output_tokens, SUM(COALESCE(cache_read_tokens, 0)) AS cache_read_tokens,
               SUM(COALESCE(cache_write_5m_tokens, 0) + COALESCE(cache_write_1h_tokens, 0)) AS cache_write_tokens
        FROM v_calls WHERE local_date BETWEEN ? AND ? GROUP BY host, local_date
        """,
        [date_from, date_to],
    )
    wanted = None if hosts is None else {h.value for h in hosts}
    result: dict[tuple[str, date], list[int]] = {}
    for row in rows:
        if wanted is not None and row["host"] not in wanted:
            continue
        local_date = row["local_date"]
        assert isinstance(local_date, date)
        result[(str(row["host"]), local_date)] = [int(str(row[m])) for m in _METRICS]
    return result


def _cmd_verify(ctx: Ctx, ns: argparse.Namespace) -> int:
    if not ns.reconcile:
        raise UsageError("verify needs --reconcile")
    today = datetime.now(UTC).date()
    date_to = _date(ns.date_to, "--to") or today
    date_from = _date(ns.date_from, "--from") or (date_to - timedelta(days=30))
    if date_from > date_to:
        raise UsageError("--from must not be after --to")
    hosts = _host_list(ns.host)
    with _reader(ctx) as store:
        if ns.cloud:
            from agent_meter.sinks import bigquery

            diffs: list[dict[str, object]] = bigquery.reconcile(ctx.cfg, store, date_from, date_to)
        else:
            local = _store_totals(store, hosts, date_from, date_to)
            source = _source_totals(ctx, hosts, date_from, date_to)
            diffs = [
                {"host": host, "local_date": day, "metric": metric, "store": s[i], "source": t[i]}
                for host, day in sorted(set(local) | set(source))
                for s, t in [(local.get((host, day), [0] * 5), source.get((host, day), [0] * 5))]
                for i, metric in enumerate(_METRICS)
                if s[i] != t[i]
            ]
    if ns.json:
        _emit_json(diffs)
    elif not diffs:
        print(f"No differences {date_from} → {date_to} ({'local vs BigQuery' if ns.cloud else 'store vs transcripts'})")
    else:
        for d in diffs:
            print("  ".join(f"{k}={v}" for k, v in d.items()))
        print("Note: transcripts deleted by the host (BR-15) appear as store-only rows.")
    return EXIT_DIFF if diffs else EXIT_OK


# ----------------------------------------------------------------------------- setup / uninstall


def _executable() -> Path:
    import shutil

    return Path(shutil.which("agent-meter") or sys.argv[0]).absolute()


def _cmd_setup(ctx: Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.config import save_config
    from agent_meter.setup import wizard
    from agent_meter.setup.hosts import parse_hosts
    from agent_meter.setup.prompter import (
        AutoPrompter,
        ConsolePrompter,
        Prompter,
        WizardAborted,
    )

    if not ns.yes and not _stdin_is_tty():
        raise UsageError("setup is interactive: run it in a terminal or pass --yes")
    try:
        options = wizard.SetupOptions(
            mode="cloud" if ns.cloud else "local" if ns.local else None,
            assume_yes=ns.yes,
            hosts=parse_hosts(ns.hosts) if ns.hosts else None,
            triggers=wizard.parse_triggers(ns.triggers) if ns.triggers else None,
            gcp_project=ns.gcp_project,
            bq_mode=ns.mode,
            backfill=not ns.no_backfill,
        )
    except ValueError as exc:
        raise UsageError(str(exc)) from exc
    prompter: Prompter = AutoPrompter(sys.stdout) if ns.yes else ConsolePrompter(sys.stdin, sys.stdout)
    deps = wizard.SetupDeps(
        home=ctx.home,
        config=ctx.cfg,
        save_config=lambda cfg: save_config(cfg, ctx.home),
        executable=_executable(),
        user_home=Path(os.environ.get("HOME") or Path.home()),
        environ=os.environ,
        prompter=prompter,
        backfill=lambda: _backfill(ctx.home),
        provision_cloud=lambda cfg: _provision_cloud(ctx.home, cfg),
        doctor=lambda: _render_checks(_doctor_checks(Ctx(ctx.home, ctx.quiet), cloud=False)),
    )
    try:
        result = wizard.run_setup(options, deps)
    except wizard.SetupUsageError as exc:
        raise UsageError(str(exc)) from exc
    except WizardAborted:
        ctx.err("setup aborted")
        return EXIT_ERROR
    return EXIT_OK if result.ok else EXIT_ERROR


def _backfill(home: AppHome) -> str:
    from agent_meter.collector import collect

    result = collect(home, load_config(home), lock_timeout_s=SCHEDULED_LOCK_S)
    if result.status != "ok" or result.stats is None:
        return f"backfill {result.status}: {result.message or 'run agent-meter collect later'}"
    return f"backfilled {result.stats.units} sessions ({result.stats.calls_changed} calls) in {result.duration_ms} ms"


def _provision_cloud(home: AppHome, cfg: Config) -> str:
    from agent_meter.sinks import bigquery
    from agent_meter.store import Store

    bigquery.ensure_dataset(cfg.bigquery)
    with Store.open(home, read_only=False, lock_timeout_s=SCHEDULED_LOCK_S) as store:
        store.migrate()
        result = bigquery.sync(home, cfg, store, full_reload=True)
    rows = sum(load.rows for load in result.loads)
    return f"BigQuery {cfg.bigquery.project}.{cfg.bigquery.dataset}: sync {result.status} ({rows} rows)"


def _cmd_uninstall(ctx: Ctx, ns: argparse.Namespace) -> int:
    import agent_meter.scheduler as scheduler
    from agent_meter.paths import UnsafePurgeError, plan_purge, purge_home
    from agent_meter.setup import settings_merge
    from agent_meter.setup._files import ManifestError

    if ns.purge:
        # Validate before touching any host settings so a refused purge changes nothing.
        try:
            plan_purge(ctx.home)
        except UnsafePurgeError as exc:
            raise UsageError(f"refusing to purge: {exc}") from exc
    try:
        actions = list(settings_merge.uninstall(ctx.home))
        if not ns.keep_scheduler:
            actions.append(scheduler.uninstall(ctx.home))
    except (ManifestError, scheduler.SchedulerError) as exc:
        raise CommandError(str(exc)) from exc
    for action in actions:
        ctx.info(action)
    if not actions:
        ctx.info("nothing to uninstall")
    if ns.purge:
        if not ns.yes:
            if not _stdin_is_tty():
                raise UsageError("--purge needs --yes when not run in a terminal")
            answer = input(f"Delete {ctx.home.root} and ALL collected data? type 'purge' to confirm: ")
            if answer.strip() != "purge":
                ctx.info("purge cancelled; data kept")
                return EXIT_OK
        try:
            deleted = purge_home(ctx.home)
        except UnsafePurgeError as exc:
            raise UsageError(f"refusing to purge: {exc}") from exc
        ctx.info(f"deleted {ctx.home.root} ({len(deleted)} agent-meter entries)")
    else:
        ctx.info(f"collected data kept in {ctx.home.root} (use --purge to delete it)")
    return EXIT_OK


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
    p.set_defaults(handler=_cmd_collect)

    p = sub.add_parser("last", help="print the last session summary")
    p.add_argument("--project")
    _json_flag(p)
    p.set_defaults(handler=_cmd_last)

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
