"""``agent-meter`` setup commands, split out of ``cli.py``.

Shared helpers and lock timeouts stay in ``cli`` and are read through ``core`` at call time.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from agent_meter.config import Config, load_config
from agent_meter.paths import AppHome

if TYPE_CHECKING:
    pass

from agent_meter import cli as core
from agent_meter.cli_commands import doctor

# ----------------------------------------------------------------------------- setup / uninstall


def _executable() -> Path:
    import shutil

    return Path(shutil.which("agent-meter") or sys.argv[0]).absolute()


def _cmd_setup(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.config import save_config
    from agent_meter.setup import wizard
    from agent_meter.setup.hosts import parse_hosts
    from agent_meter.setup.prompter import (
        AutoPrompter,
        ConsolePrompter,
        Prompter,
        WizardAborted,
    )

    if not ns.yes and not core._stdin_is_tty():
        raise core.UsageError("setup is interactive: run it in a terminal or pass --yes")
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
        raise core.UsageError(str(exc)) from exc
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
        doctor=lambda: doctor._render_checks(doctor._doctor_checks(core.Ctx(ctx.home, ctx.quiet), cloud=False)),
    )
    try:
        result = wizard.run_setup(options, deps)
    except wizard.SetupUsageError as exc:
        raise core.UsageError(str(exc)) from exc
    except WizardAborted:
        ctx.err("setup aborted")
        return core.EXIT_ERROR
    return core.EXIT_OK if result.ok else core.EXIT_ERROR


def _backfill(home: AppHome) -> str:
    from agent_meter.collector import collect

    result = collect(home, load_config(home), lock_timeout_s=core.SCHEDULED_LOCK_S)
    if result.status != "ok" or result.stats is None:
        return f"backfill {result.status}: {result.message or 'run agent-meter collect later'}"
    return f"backfilled {result.stats.units} sessions ({result.stats.calls_changed} calls) in {result.duration_ms} ms"


def _provision_cloud(home: AppHome, cfg: Config) -> str:
    from agent_meter.sinks import bigquery
    from agent_meter.store import Store

    bigquery.ensure_dataset(cfg.bigquery)
    with Store.open(home, read_only=False, lock_timeout_s=core.SCHEDULED_LOCK_S) as store:
        store.migrate()
        result = bigquery.sync(home, cfg, store, full_reload=True)
    rows = sum(load.rows for load in result.loads)
    return f"BigQuery {cfg.bigquery.project}.{cfg.bigquery.dataset}: sync {result.status} ({rows} rows)"


def _cmd_uninstall(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    import agent_meter.scheduler as scheduler
    from agent_meter.paths import UnsafePurgeError, plan_purge, purge_home
    from agent_meter.setup import settings_merge
    from agent_meter.setup._files import ManifestError

    if ns.purge:
        # Validate before touching any host settings so a refused purge changes nothing.
        try:
            plan_purge(ctx.home)
        except UnsafePurgeError as exc:
            raise core.UsageError(f"refusing to purge: {exc}") from exc
    try:
        actions = list(settings_merge.uninstall(ctx.home))
        if not ns.keep_scheduler:
            actions.append(scheduler.uninstall(ctx.home))
    except (ManifestError, scheduler.SchedulerError) as exc:
        raise core.CommandError(str(exc)) from exc
    for action in actions:
        ctx.info(action)
    if not actions:
        ctx.info("nothing to uninstall")
    if ns.purge:
        if not ns.yes:
            if not core._stdin_is_tty():
                raise core.UsageError("--purge needs --yes when not run in a terminal")
            answer = input(f"Delete {ctx.home.root} and ALL collected data? type 'purge' to confirm: ")
            if answer.strip() != "purge":
                ctx.info("purge cancelled; data kept")
                return core.EXIT_OK
        try:
            deleted = purge_home(ctx.home)
        except UnsafePurgeError as exc:
            raise core.UsageError(f"refusing to purge: {exc}") from exc
        ctx.info(f"deleted {ctx.home.root} ({len(deleted)} agent-meter entries)")
    else:
        ctx.info(f"collected data kept in {ctx.home.root} (use --purge to delete it)")
    return core.EXIT_OK
