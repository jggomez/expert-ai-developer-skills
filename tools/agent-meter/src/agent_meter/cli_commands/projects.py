"""``agent-meter`` projects commands, split out of ``cli.py``.

Shared helpers and lock timeouts stay in ``cli`` and are read through ``core`` at call time.
"""

from __future__ import annotations

import argparse
import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from agent_meter.config import load_config

if TYPE_CHECKING:
    pass

from agent_meter import cli as core

# ----------------------------------------------------------------------------- projects / hours / tag


def _cmd_projects_list(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.project_admin import PROJECT_LIST_SQL

    with core._reader(ctx) as store:
        rows = store.query(PROJECT_LIST_SQL)
    if ns.json:
        core._emit_json(rows)
        return core.EXIT_OK
    from agent_meter.summary import fmt_cost

    for row in rows:
        cost = row["cost_usd"]
        money = fmt_cost(
            cost if isinstance(cost, Decimal) else None, ctx.cfg, unpriced_calls=int(str(row["unpriced_calls"])),
            detail=False,
        )
        client = f" · client {row['client']}" if row["client"] else ""
        print(f"{row['project_id']:<22} {row['display_name']:<28} {row['sessions']:>5} sessions  {money}{client}")
    return core.EXIT_OK


def _cmd_projects_set(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.project_admin import save_project_override

    rate = core._decimal(ns.rate, "--rate")
    price = core._decimal(ns.price, "--price")
    currency = ns.currency.upper() if ns.currency else None
    if currency is not None and (len(currency) != 3 or not currency.isalpha()):
        raise core.UsageError(f"--currency: expected a 3-letter ISO code, got {ns.currency!r}")
    with core._writer(ctx) as store:
        pid = core._resolve_project(store, ns.project, allow_unknown_id=True)
        changes: dict[str, Any] = {}
        for attr, value in (("display_name", ns.name), ("client", ns.client), ("billing", ns.billing),
                            ("rate", rate), ("fixed_price", price), ("currency", currency)):
            if value is not None:
                changes[attr] = value or None
        save_project_override(ctx.home.projects, pid, changes)
        core._refresh_reference(ctx, store)
    ctx.info(f"updated {pid} in {ctx.home.projects}")
    return core.EXIT_OK


def _cmd_projects_merge(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.project_resolver import (
        ProjectsConfig,
        load_projects_config,
        save_projects_config,
    )

    with core._writer(ctx) as store:
        src = core._resolve_project(store, ns.src)
        dst = core._resolve_project(store, ns.dst, allow_unknown_id=True)
        if src == dst:
            raise core.UsageError("cannot merge a project into itself")
        cfg = load_projects_config(ctx.home.projects)
        merges = {**cfg.merges, src: dst}
        save_projects_config(
            ProjectsConfig(projects=cfg.projects, path_aliases=cfg.path_aliases, ignore=cfg.ignore, merges=merges),
            ctx.home.projects,
        )
        moved = store.merge_projects(src, dst)
        core._refresh_reference(ctx, store)
    ctx.info(f"merged {src} into {dst}: {moved} rows re-keyed (recorded in {ctx.home.projects})")
    return core.EXIT_OK


def _cmd_hours(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    from agent_meter.store import StoreError

    if ns.hours_command == "list":
        with core._reader(ctx) as store:
            rows = store.query(
                """
                SELECT m.project_id, COALESCE(p.display_name, m.project_id) AS display_name, m.period, m.hours,
                       'manual' AS source, m.set_at
                FROM dev_hours_manual m LEFT JOIN projects p ON p.project_id = m.project_id
                ORDER BY m.project_id, m.period
                """
            )
        if ns.json:
            core._emit_json(rows)
        elif not rows:
            print("No manual hours set (derived hours are used)")
        else:
            for row in rows:
                print(f"{row['display_name']:<28} {row['period']:<10} {row['hours']:>8} h  (manual)")
        return core.EXIT_OK
    with core._writer(ctx) as store:
        pid = core._resolve_project(store, ns.project, allow_unknown_id=True)
        try:
            if ns.hours_command == "set":
                hours = core._decimal(ns.hours, "hours", allow_none=False)
                assert hours is not None
                store.set_manual_hours(pid, ns.period, hours)
                ctx.info(f"{pid} {ns.period}: {hours} h (manual, overrides derived hours)")
            else:
                removed = store.unset_manual_hours(pid, ns.period)
                ctx.info(f"{pid} {ns.period}: " + ("manual hours removed" if removed else "no manual hours were set"))
        except StoreError as exc:
            raise core.UsageError(str(exc)) from exc
    return core.EXIT_OK


def _cmd_tag(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    name = (ns.name or "").strip()
    if ns.clear == bool(name):
        raise core.UsageError("give a tag name, or --clear to stop tagging")
    if len(name) > 80:
        raise core.UsageError("tag names are at most 80 characters")
    if ns.last is not None and (ns.clear or ns.last < 1):
        raise core.UsageError("--last N needs a tag name and N >= 1")
    with core._writer(ctx) as store:
        pid = core._resolve_project(store, ns.project) if ns.project else core._current_project(ctx, store)
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
    return core.EXIT_OK


# ----------------------------------------------------------------------------- config


def _cmd_config(ctx: core.Ctx, ns: argparse.Namespace) -> int:
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
            core._emit_json(dict(items))
        else:
            print("\n".join(f"{key} = {value}" for key, value in items))
        return core.EXIT_OK
    try:
        if command == "get":
            value = get_key(ctx.cfg, ns.key)
            core._emit_json({ns.key: value}) if ns.json else print(value)
            return core.EXIT_OK
        if command == "set":
            save_config(set_key(ctx.cfg, ns.key, ns.value), ctx.home)
            ctx.info(f"{ns.key} = {ns.value}")
            return core.EXIT_OK
    except ConfigError as exc:
        raise core.UsageError(str(exc)) from exc
    return _edit_config(ctx)


def _edit_config(ctx: core.Ctx) -> int:
    import shlex
    import subprocess

    from agent_meter.config import save_config

    if not ctx.home.config.exists():
        save_config(ctx.cfg, ctx.home)
    editor = os.environ.get("VISUAL") or os.environ.get("EDITOR") or "vi"
    completed = subprocess.run([*shlex.split(editor), str(ctx.home.config)], check=False)
    if completed.returncode != 0:
        raise core.CommandError(f"editor exited with code {completed.returncode}")
    load_config(ctx.home)
    ctx.info(f"{ctx.home.config} is valid")
    return core.EXIT_OK
