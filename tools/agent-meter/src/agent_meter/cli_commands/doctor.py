"""``agent-meter`` doctor commands, split out of ``cli.py``.

Shared helpers and lock timeouts stay in ``cli`` and are read through ``core`` at call time.
"""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

from agent_meter.paths import AppHome

if TYPE_CHECKING:
    from agent_meter.store import Store

from agent_meter import cli as core
from agent_meter.cli_commands import pricing_cmd

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


def _host_checks(ctx: core.Ctx, store: Store, now: datetime) -> list[dict[str, str]]:
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


def _pricing_checks(ctx: core.Ctx, store: Store) -> list[dict[str, str]]:
    from agent_meter import pricing

    checks = []
    if ctx.home.pricing_local.exists():
        errors = pricing.validate_file(ctx.home.pricing_local)
        if errors:
            checks.append(_check("FAIL", "pricing", f"pricing.local.yaml invalid: {errors[0]} (previous table in use)"))
    unpriced = store.query("SELECT * FROM v_unpriced_models ORDER BY calls DESC")
    for row in unpriced:
        model = str(row["model_effective"] or "(no model)")
        checks.append(_check("WARN", "pricing", f"unpriced model: {model} ({row['calls']} calls) · fix: {pricing_cmd._pricing_hint(model)}"))
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


def _doctor_checks(ctx: core.Ctx, *, cloud: bool) -> list[dict[str, str]]:
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
    with core._reader(ctx) as store:
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
        last_scheduled = store.get_meta("last_scheduled_collect_at")
    checks.append(_scheduler_check(scheduler.status(), last_scheduled, now))
    return checks


def _scheduler_check(state: str, last_scheduled: str | None, now: datetime) -> dict[str, str]:
    """A loaded job proves nothing by itself, so look for the trace left by a successful run."""
    if state == "not_loaded":
        return _check("WARN", "scheduler", "not loaded (hooks/manual collect only)")
    if state == "unsupported":
        return _check("WARN", "scheduler", "no supported scheduler on this platform")
    if last_scheduled is None:
        return _check("WARN", "scheduler", "loaded, but no scheduled collect has succeeded yet")
    moment = datetime.fromisoformat(last_scheduled)
    age = _age(moment, now)
    if now - moment > core.SCHEDULER_STALE_AFTER:
        return _check("WARN", "scheduler", f"loaded, but the last scheduled collect succeeded {age}")
    return _check("OK", "scheduler", f"loaded (every 15 min) · last scheduled collect {age}")


def _cloud_checks(ctx: core.Ctx, store: Store, now: datetime, *, deep: bool) -> list[dict[str, str]]:
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


def _cmd_doctor(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    checks = _doctor_checks(ctx, cloud=ns.cloud)
    if ns.json:
        core._emit_json(checks)
    else:
        print(_render_checks(checks))
    return core.EXIT_DOCTOR_FAIL if any(c["status"] == "FAIL" for c in checks) else core.EXIT_OK


# ----------------------------------------------------------------------------- verify --reconcile


_METRICS: Final = ("calls", "input_tokens", "output_tokens", "cache_read_tokens", "cache_write_tokens")


def _source_totals(ctx: core.Ctx, hosts: list[Any] | None, date_from: date, date_to: date) -> dict[tuple[str, date], list[int]]:
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


def _cmd_verify(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    if not ns.reconcile:
        raise core.UsageError("verify needs --reconcile")
    today = datetime.now(UTC).date()
    date_to = core._date(ns.date_to, "--to") or today
    date_from = core._date(ns.date_from, "--from") or (date_to - timedelta(days=30))
    if date_from > date_to:
        raise core.UsageError("--from must not be after --to")
    hosts = core._host_list(ns.host)
    with core._reader(ctx) as store:
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
        core._emit_json(diffs)
    elif not diffs:
        print(f"No differences {date_from} → {date_to} ({'local vs BigQuery' if ns.cloud else 'store vs transcripts'})")
    else:
        for d in diffs:
            print("  ".join(f"{k}={v}" for k, v in d.items()))
        print("Note: transcripts deleted by the host (BR-15) appear as store-only rows.")
    return core.EXIT_DIFF if diffs else core.EXIT_OK
