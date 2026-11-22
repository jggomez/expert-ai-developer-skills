"""``agent-meter`` pricing commands, split out of ``cli.py``.

Shared helpers and lock timeouts stay in ``cli`` and are read through ``core`` at call time.
"""

from __future__ import annotations

import argparse
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

from agent_meter import cli as core

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


def _cmd_pricing(ctx: core.Ctx, ns: argparse.Namespace) -> int:
    from agent_meter import pricing

    command = ns.pricing_command
    local = ctx.home.pricing_local
    if command == "list":
        table = pricing.load_pricing(local)
        rows = [_price_dict(r) for r in table.rows]
        if ns.json:
            core._emit_json(rows)
            return core.EXIT_OK
        for r in rows:
            print(f"{r['model']:<34} from {r['effective_from']}  ≥{r['min_prompt_tokens']:>7} tok  "
                  f"in {r['input']}  out {r['output']}  read {r['cache_read']}  ({r['source']})")
        for alias in table.aliases:
            note = " (estimated)" if alias.estimated else ""
            print(f"alias {alias.alias} → {alias.model}{note} ({alias.source})")
        return core.EXIT_OK
    if command == "unpriced":
        with core._reader(ctx) as store:
            rows_u = store.query("SELECT * FROM v_unpriced_models ORDER BY calls DESC, host")
        if ns.json:
            core._emit_json(rows_u)
        elif not rows_u:
            print("Every call is priced")
        else:
            for row in rows_u:
                model = str(row["model_effective"] or "(no model; set hosts.<host>.default_model)")
                print(f"{row['host']:<16} {model:<34} {row['calls']:>6} calls · fix: {_pricing_hint(model)}")
        return core.EXIT_OK
    if command == "validate":
        path = Path(ns.file) if ns.file else local
        if not path.exists():
            if ns.file:
                raise core.UsageError(f"{path} does not exist")
            errors = pricing.validate_file(pricing.SHIPPED_PATH)
        else:
            errors = pricing.validate_file(path)
        for error in errors:
            print(error)
        if errors:
            return core.EXIT_ERROR
        ctx.info(f"{path if path.exists() else pricing.SHIPPED_PATH} is valid")
        return core.EXIT_OK
    _change_pricing(ctx, ns, local)
    if not core._try_refresh(ctx):
        ctx.info("store busy: the new prices apply on the next collect or report")
    return core.EXIT_OK


def _change_pricing(ctx: core.Ctx, ns: argparse.Namespace, local: Path) -> None:
    from agent_meter import pricing

    command = ns.pricing_command
    if command in ("add", "set"):
        effective = core._date(ns.effective_from, "--effective-from") or core.SINCE_FOREVER
        if ns.min_prompt_tokens < 0:
            raise core.UsageError("--min-prompt-tokens must be >= 0")
        row = pricing.PriceRow(
            model=ns.model, effective_from=effective, min_prompt_tokens=ns.min_prompt_tokens,
            input=_req(ns.input, "--input"), output=_req(ns.output, "--output"),
            cache_write_5m=core._decimal(ns.cache_write_5m, "--cache-write-5m"),
            cache_write_1h=core._decimal(ns.cache_write_1h, "--cache-write-1h"),
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
            raise core.UsageError("give --model and/or --alias")
        removed = pricing.remove_local(
            local, model=ns.model, effective_from=core._date(ns.effective_from, "--effective-from"), alias=ns.alias
        )
        if not removed:
            raise core.CommandError("nothing matched in pricing.local.yaml (shipped prices cannot be removed)")
        ctx.info(f"removed {removed} entr{'y' if removed == 1 else 'ies'} from {local}")


def _req(text: str, flag: str) -> Decimal:
    value = core._decimal(text, flag, allow_none=False)
    assert value is not None
    return value
