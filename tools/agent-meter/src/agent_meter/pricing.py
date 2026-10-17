"""Two-layer price table: shipped ``pricing.yaml`` + user ``pricing.local.yaml`` (ADR §3.8).

Local rows win per ``(model, effective_from, min_prompt_tokens)`` and local aliases win
per alias name. ``resolve_price`` + ``cost_usd`` are the Python oracle that the store's
``v_calls`` SQL view must equal (contracts §3.4). Money is always ``Decimal``.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any, Final, Literal

import yaml

__all__ = [
    "SHIPPED_PATH",
    "Alias",
    "PriceResolution",
    "PriceRow",
    "PricingError",
    "PricingTable",
    "add_local_alias",
    "add_local_price",
    "cost_usd",
    "load_pricing",
    "remove_local",
    "resolve_price",
    "validate_file",
]

Source = Literal["shipped", "local"]

SHIPPED_PATH: Final[Path] = Path(__file__).resolve().with_name("pricing.yaml")

_FAST_SUFFIX: Final = ":fast"
_PER_TOKENS: Final = Decimal(1_000_000)
_COST_QUANTUM: Final = Decimal("1e-9")
_MAX_PRICE: Final = Decimal(1_000_000)  # DECIMAL(12,6) → < 10^6
_MAX_PRICE_PLACES: Final = 6

_TOP_KEYS: Final = frozenset({"version", "models", "aliases"})
_MODEL_KEYS: Final = frozenset({"source_url", "fetched_at", "windows"})
_WINDOW_KEYS: Final = frozenset({"effective_from", "tiers"})
_REQUIRED_PRICES: Final = ("input", "output", "cache_read")
_OPTIONAL_PRICES: Final = ("cache_write_5m", "cache_write_1h")
_TIER_KEYS: Final = frozenset(
    {"min_prompt_tokens", *_REQUIRED_PRICES, *_OPTIONAL_PRICES}
)
_ALIAS_KEYS: Final = frozenset({"model", "estimated"})


@dataclass(frozen=True, slots=True)
class PriceRow:
    model: str
    effective_from: date
    min_prompt_tokens: int
    input: Decimal
    output: Decimal
    cache_write_5m: Decimal | None
    cache_write_1h: Decimal | None
    cache_read: Decimal | None
    source: Source
    source_url: str | None
    fetched_at: date | None


@dataclass(frozen=True, slots=True)
class Alias:
    alias: str
    model: str
    estimated: bool
    source: Source


@dataclass(frozen=True, slots=True)
class PricingTable:
    rows: tuple[PriceRow, ...]
    aliases: tuple[Alias, ...]


@dataclass(frozen=True, slots=True)
class PriceResolution:
    priced_model: str | None
    row: PriceRow | None
    estimated: bool
    inferred: bool


class PricingError(ValueError):
    """A pricing file is invalid; ``errors`` lists every problem found."""

    errors: list[str]

    def __init__(self, errors: Iterable[str]) -> None:
        self.errors = list(errors)
        super().__init__("; ".join(self.errors) or "invalid pricing data")


# ----------------------------------------------------------------------------- parsing


@dataclass(slots=True)
class _Parsed:
    rows: list[PriceRow] = field(default_factory=list)
    aliases: list[Alias] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _read_document(path: Path) -> tuple[Any, list[str]]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"{path.name}: cannot read file ({type(exc).__name__})"]
    try:
        return yaml.safe_load(text), []
    except yaml.YAMLError as exc:
        problem = getattr(exc, "problem", None) or type(exc).__name__
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}" if mark is not None else ""
        return None, [f"{path.name}: invalid YAML{where}: {problem}"]


def _check_keys(
    value: Mapping[Any, Any], allowed: frozenset[str], where: str, errors: list[str]
) -> None:
    for key in value:
        if key not in allowed:
            errors.append(f"{where}: unknown key {key!r}")


def _parse_date(value: Any, where: str, errors: list[str]) -> date | None:
    if isinstance(value, datetime):
        errors.append(f"{where}: invalid date (expected YYYY-MM-DD, got a timestamp)")
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError:
            pass
    errors.append(f"{where}: invalid date {value!r} (expected ISO YYYY-MM-DD)")
    return None


def _parse_price(value: Any, where: str, errors: list[str]) -> Decimal | None:
    if not isinstance(value, str):
        errors.append(
            f"{where}: price must be a quoted decimal string, got {type(value).__name__}"
        )
        return None
    try:
        price = Decimal(value.strip())
    except InvalidOperation:
        errors.append(f"{where}: {value!r} is not a valid decimal")
        return None
    if not price.is_finite():
        errors.append(f"{where}: {value!r} is not a valid decimal")
        return None
    if price < 0:
        errors.append(f"{where}: negative price {value!r}")
        return None
    exponent = price.normalize().as_tuple().exponent
    if isinstance(exponent, int) and -exponent > _MAX_PRICE_PLACES:
        errors.append(
            f"{where}: more than {_MAX_PRICE_PLACES} decimal places in {value!r}"
        )
        return None
    if price >= _MAX_PRICE:
        errors.append(f"{where}: price {value!r} is too large")
        return None
    return price


def _parse_tier(
    tier: Any,
    model: str,
    effective_from: date | None,
    meta: tuple[str | None, date | None],
    source: Source,
    where: str,
    errors: list[str],
) -> PriceRow | None:
    if not isinstance(tier, Mapping):
        errors.append(f"{where}: tier must be a mapping")
        return None
    _check_keys(tier, _TIER_KEYS, where, errors)
    min_tokens = tier.get("min_prompt_tokens")
    if (
        isinstance(min_tokens, bool)
        or not isinstance(min_tokens, int)
        or min_tokens < 0
    ):
        errors.append(f"{where}: min_prompt_tokens must be a non-negative integer")
        min_tokens = None
    prices: dict[str, Decimal | None] = {}
    for key in _REQUIRED_PRICES:
        if key not in tier:
            errors.append(f"{where}: missing required price {key}")
            prices[key] = None
        else:
            prices[key] = _parse_price(tier[key], f"{where}.{key}", errors)
    for key in _OPTIONAL_PRICES:
        prices[key] = (
            _parse_price(tier[key], f"{where}.{key}", errors) if key in tier else None
        )
    input_price, output_price = prices["input"], prices["output"]
    required_ok = (
        input_price is not None
        and output_price is not None
        and prices["cache_read"] is not None
    )
    optional_ok = all(k not in tier or prices[k] is not None for k in _OPTIONAL_PRICES)
    if (
        effective_from is None
        or min_tokens is None
        or input_price is None
        or output_price is None
    ):
        return None
    if not (required_ok and optional_ok):
        return None
    return PriceRow(
        model=model,
        effective_from=effective_from,
        min_prompt_tokens=min_tokens,
        input=input_price,
        output=output_price,
        cache_write_5m=prices["cache_write_5m"],
        cache_write_1h=prices["cache_write_1h"],
        cache_read=prices["cache_read"],
        source=source,
        source_url=meta[0],
        fetched_at=meta[1],
    )


def _parse_model(name: Any, body: Any, source: Source, parsed: _Parsed) -> None:
    errors = parsed.errors
    where = f"models.{name}"
    if not isinstance(name, str) or not name.strip():
        errors.append(f"{where}: model name must be a non-empty string")
        return
    if not isinstance(body, Mapping):
        errors.append(f"{where}: must be a mapping")
        return
    _check_keys(body, _MODEL_KEYS, where, errors)
    source_url = body.get("source_url")
    if source_url is not None and not isinstance(source_url, str):
        errors.append(f"{where}.source_url: must be a string")
        source_url = None
    fetched_at = (
        _parse_date(body["fetched_at"], f"{where}.fetched_at", errors)
        if body.get("fetched_at") is not None
        else None
    )
    windows = body.get("windows")
    if not isinstance(windows, list) or not windows:
        errors.append(f"{where}.windows: must be a non-empty list")
        return
    seen: set[tuple[date, int]] = set()
    for w_index, window in enumerate(windows):
        w_where = f"{where}.windows[{w_index}]"
        if not isinstance(window, Mapping):
            errors.append(f"{w_where}: must be a mapping")
            continue
        _check_keys(window, _WINDOW_KEYS, w_where, errors)
        effective_from = _parse_date(
            window.get("effective_from"), f"{w_where}.effective_from", errors
        )
        tiers = window.get("tiers")
        if not isinstance(tiers, list) or not tiers:
            errors.append(f"{w_where}.tiers: must be a non-empty list")
            continue
        has_zero_tier = any(
            isinstance(t, Mapping) and t.get("min_prompt_tokens") == 0 for t in tiers
        )
        if not has_zero_tier:
            errors.append(
                f"{w_where}: every window needs a tier with min_prompt_tokens: 0"
            )
        for t_index, tier in enumerate(tiers):
            row = _parse_tier(
                tier,
                name,
                effective_from,
                (source_url, fetched_at),
                source,
                f"{w_where}.tiers[{t_index}]",
                errors,
            )
            if row is None:
                continue
            key = (row.effective_from, row.min_prompt_tokens)
            if key in seen:
                errors.append(
                    f"{where}: duplicate row (effective_from={row.effective_from.isoformat()}, "
                    f"min_prompt_tokens={row.min_prompt_tokens})"
                )
                continue
            seen.add(key)
            parsed.rows.append(row)


def _parse_alias(name: Any, body: Any, source: Source, parsed: _Parsed) -> None:
    where = f"aliases.{name}"
    if not isinstance(name, str) or not name.strip():
        parsed.errors.append(f"{where}: alias name must be a non-empty string")
        return
    if not isinstance(body, Mapping):
        parsed.errors.append(f"{where}: must be a mapping like {{model: <id>}}")
        return
    _check_keys(body, _ALIAS_KEYS, where, parsed.errors)
    target = body.get("model")
    estimated = body.get("estimated", False)
    if not isinstance(target, str) or not target.strip():
        parsed.errors.append(f"{where}.model: must be a non-empty string")
        return
    if not isinstance(estimated, bool):
        parsed.errors.append(f"{where}.estimated: must be true or false")
        return
    parsed.aliases.append(
        Alias(alias=name, model=target, estimated=estimated, source=source)
    )


def _parse_document(doc: Any, source: Source) -> _Parsed:
    parsed = _Parsed()
    if not isinstance(doc, Mapping):
        parsed.errors.append("document must be a mapping with 'version: 1'")
        return parsed
    _check_keys(doc, _TOP_KEYS, "top level", parsed.errors)
    if doc.get("version") != 1 or isinstance(doc.get("version"), bool):
        parsed.errors.append(f"version must be 1, got {doc.get('version')!r}")
    models = doc.get("models") or {}
    aliases = doc.get("aliases") or {}
    if not isinstance(models, Mapping):
        parsed.errors.append("models: must be a mapping")
        models = {}
    if not isinstance(aliases, Mapping):
        parsed.errors.append("aliases: must be a mapping")
        aliases = {}
    for name, body in models.items():
        _parse_model(name, body, source, parsed)
    for name, body in aliases.items():
        _parse_alias(name, body, source, parsed)
    return parsed


def _parse_file(path: Path, source: Source) -> _Parsed:
    doc, errors = _read_document(path)
    if errors:
        return _Parsed(errors=errors)
    parsed = _parse_document(doc, source)
    parsed.errors = [f"{path.name}: {e}" for e in parsed.errors]
    return parsed


def _merge(shipped: _Parsed, local: _Parsed | None) -> tuple[PricingTable, list[str]]:
    rows: dict[tuple[str, date, int], PriceRow] = {
        (r.model, r.effective_from, r.min_prompt_tokens): r for r in shipped.rows
    }
    aliases: dict[str, Alias] = {a.alias: a for a in shipped.aliases}
    if local is not None:
        rows.update(
            {(r.model, r.effective_from, r.min_prompt_tokens): r for r in local.rows}
        )
        local_models = {r.model for r in local.rows}
        for name in [
            n for n, a in aliases.items() if n in local_models and a.source == "shipped"
        ]:
            del aliases[name]  # a local model shadows a shipped alias of the same name
        aliases.update({a.alias: a for a in local.aliases})
    models = {key[0] for key in rows}
    errors: list[str] = []
    for alias in aliases.values():
        if alias.alias in models:
            errors.append(
                f"alias {alias.alias!r} shadows a defined model of the same name"
            )
        elif alias.model in aliases:
            errors.append(
                f"alias {alias.alias!r} points at another alias {alias.model!r}; "
                "aliases must target a priced model directly"
            )
        elif alias.model not in models:
            errors.append(
                f"alias {alias.alias!r} points at undefined model {alias.model!r}"
            )
    table = PricingTable(
        rows=tuple(
            sorted(
                rows.values(),
                key=lambda r: (r.model, r.effective_from, r.min_prompt_tokens),
            )
        ),
        aliases=tuple(sorted(aliases.values(), key=lambda a: a.alias)),
    )
    return table, errors


def load_pricing(local: Path | None, shipped: Path | None = None) -> PricingTable:
    """Load and merge the shipped and local tables; any invalid file raises ``PricingError``."""
    shipped_parsed = _parse_file(shipped or SHIPPED_PATH, "shipped")
    if shipped_parsed.errors:
        raise PricingError(shipped_parsed.errors)
    local_parsed = (
        _parse_file(local, "local") if local is not None and local.exists() else None
    )
    if local_parsed is not None and local_parsed.errors:
        raise PricingError(local_parsed.errors)
    table, errors = _merge(shipped_parsed, local_parsed)
    if errors:
        raise PricingError(errors)
    return table


def validate_file(path: Path) -> list[str]:
    """Validate one pricing file (aliases checked against the shipped table too)."""
    parsed = _parse_file(path, "local")
    if parsed.errors:
        return parsed.errors
    if path.resolve() == SHIPPED_PATH:
        _table, errors = _merge(parsed, None)
        return errors
    shipped = _parse_file(SHIPPED_PATH, "shipped")
    _table, errors = _merge(shipped, parsed)
    return [*shipped.errors, *errors]


# ----------------------------------------------------------------------------- resolution


def _alias_for(table: PricingTable, model: str) -> Alias | None:
    return next((a for a in table.aliases if a.alias == model), None)


def _has_rows(table: PricingTable, model: str) -> bool:
    return any(r.model == model for r in table.rows)


def resolve_price(
    table: PricingTable,
    model: str | None,
    at: date,
    prompt_tokens: int,
    *,
    speed: str | None = None,
    default_model: str | None = None,
) -> PriceResolution:
    """Resolve the price row for one call (contracts §3.4 semantics 1–4)."""
    effective = model or default_model
    inferred = not model and bool(default_model)
    if not effective:
        return PriceResolution(
            priced_model=None, row=None, estimated=False, inferred=False
        )
    alias = _alias_for(table, effective)
    base = alias.model if alias else effective
    estimated = bool(alias and alias.estimated)
    priced_model = base
    if speed == "fast":
        if _has_rows(table, base + _FAST_SUFFIX):
            priced_model = base + _FAST_SUFFIX
        else:
            estimated = True
    candidates = [
        r
        for r in table.rows
        if r.model == priced_model
        and r.effective_from <= at
        and r.min_prompt_tokens <= prompt_tokens
    ]
    if not candidates:
        return PriceResolution(
            priced_model=None, row=None, estimated=estimated, inferred=inferred
        )
    row = max(candidates, key=lambda r: (r.effective_from, r.min_prompt_tokens))
    return PriceResolution(
        priced_model=priced_model, row=row, estimated=estimated, inferred=inferred
    )


def cost_usd(
    res: PriceResolution,
    *,
    input_tokens: int | None,
    output_tokens: int | None,
    cache_write_5m_tokens: int | None,
    cache_write_1h_tokens: int | None,
    cache_read_tokens: int | None,
) -> Decimal | None:
    """API-equivalent cost of one call, or ``None`` when unpriced or any count is unknown."""
    row = res.row
    tokens = (
        input_tokens,
        output_tokens,
        cache_write_5m_tokens,
        cache_write_1h_tokens,
        cache_read_tokens,
    )
    counts = [t for t in tokens if t is not None]
    if row is None or row.cache_read is None or len(counts) != len(tokens):
        return None
    write_5m = row.cache_write_5m if row.cache_write_5m is not None else row.input
    write_1h = row.cache_write_1h if row.cache_write_1h is not None else row.input
    prices = (row.input, row.output, write_5m, write_1h, row.cache_read)
    with localcontext() as ctx:
        ctx.prec = 50
        total = sum(
            (Decimal(t) * p for t, p in zip(counts, prices, strict=True)), Decimal(0)
        )
        return (total / _PER_TOKENS).quantize(_COST_QUANTUM, rounding=ROUND_HALF_UP)


# ----------------------------------------------------------------------------- local writers


def _load_local_document(local: Path) -> dict[str, Any]:
    if not local.exists():
        return {"version": 1, "models": {}, "aliases": {}}
    doc, errors = _read_document(local)
    if errors:
        raise PricingError(errors)
    if doc is None:
        return {"version": 1, "models": {}, "aliases": {}}
    if not isinstance(doc, dict):
        raise PricingError([f"{local.name}: document must be a mapping"])
    doc.setdefault("models", {})
    doc.setdefault("aliases", {})
    if doc["models"] is None:
        doc["models"] = {}
    if doc["aliases"] is None:
        doc["aliases"] = {}
    return doc


def _validate_document(doc: Mapping[str, Any], name: str) -> None:
    parsed = _parse_document(doc, "local")
    if parsed.errors:
        raise PricingError([f"{name}: {e}" for e in parsed.errors])
    shipped = _parse_file(SHIPPED_PATH, "shipped")
    _table, errors = _merge(shipped, parsed)
    if shipped.errors or errors:
        raise PricingError([*shipped.errors, *errors])


def _atomic_write(local: Path, doc: Mapping[str, Any]) -> None:
    _validate_document(doc, local.name)
    local.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    text = yaml.safe_dump(
        dict(doc), sort_keys=False, allow_unicode=True, default_flow_style=False
    )
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{local.name}.", suffix=".tmp", dir=local.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp_name, 0o600)
        os.replace(tmp_name, local)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def _money(value: Decimal) -> str:
    return format(value, "f")


def add_local_price(local: Path, row: PriceRow, *, replace: bool = False) -> None:
    """Add (or with ``replace`` overwrite) one tier in the local file; validate, then write atomically."""
    doc = _load_local_document(local)
    model = doc["models"].setdefault(row.model, {})
    if row.source_url is not None:
        model["source_url"] = row.source_url
    if row.fetched_at is not None:
        model["fetched_at"] = row.fetched_at
    windows: list[dict[str, Any]] = model.setdefault("windows", [])
    window = next(
        (w for w in windows if _same_date(w.get("effective_from"), row.effective_from)),
        None,
    )
    if window is None:
        window = {"effective_from": row.effective_from, "tiers": []}
        windows.append(window)
        windows.sort(key=lambda w: str(w.get("effective_from")))
    tiers: list[dict[str, Any]] = window.setdefault("tiers", [])
    existing = next(
        (t for t in tiers if t.get("min_prompt_tokens") == row.min_prompt_tokens), None
    )
    if existing is not None and not replace:
        key = f"({row.model}, {row.effective_from.isoformat()}, min_prompt_tokens={row.min_prompt_tokens})"
        raise PricingError(
            [f"price row {key} already exists; use replace to overwrite it"]
        )
    tier: dict[str, Any] = {
        "min_prompt_tokens": row.min_prompt_tokens,
        "input": _money(row.input),
    }
    if row.cache_write_5m is not None:
        tier["cache_write_5m"] = _money(row.cache_write_5m)
    if row.cache_write_1h is not None:
        tier["cache_write_1h"] = _money(row.cache_write_1h)
    if row.cache_read is not None:
        tier["cache_read"] = _money(row.cache_read)
    tier["output"] = _money(row.output)
    if existing is not None:
        tiers[tiers.index(existing)] = tier
    else:
        tiers.append(tier)
        tiers.sort(key=_tier_order)
    _atomic_write(local, doc)


def _tier_order(tier: Mapping[str, Any]) -> int:
    value = tier.get("min_prompt_tokens")
    return value if isinstance(value, int) else -1


def _same_date(value: Any, wanted: date) -> bool:
    if isinstance(value, date) and not isinstance(value, datetime):
        return value == wanted
    return isinstance(value, str) and value == wanted.isoformat()


def add_local_alias(local: Path, alias: str, model: str, *, estimated: bool) -> None:
    """Add or replace a local alias; validate, then write atomically."""
    doc = _load_local_document(local)
    entry: dict[str, Any] = {"model": model}
    if estimated:
        entry["estimated"] = True
    doc["aliases"][alias] = entry
    _atomic_write(local, doc)


def remove_local(
    local: Path,
    *,
    model: str | None = None,
    effective_from: date | None = None,
    alias: str | None = None,
) -> int:
    """Remove local price rows (all windows, or one window) and/or an alias; returns rows removed."""
    if not local.exists():
        return 0
    doc = _load_local_document(local)
    removed = 0
    if model is not None and model in doc["models"]:
        body = doc["models"][model]
        windows = (body.get("windows") or []) if isinstance(body, dict) else []
        keep: list[Any] = []
        for window in windows:
            if effective_from is None or _same_date(
                window.get("effective_from"), effective_from
            ):
                removed += len(window.get("tiers") or [])
            else:
                keep.append(window)
        if keep:
            body["windows"] = keep
        else:
            del doc["models"][model]
    if alias is not None and alias in doc["aliases"]:
        del doc["aliases"][alias]
        removed += 1
    if removed:
        _atomic_write(local, doc)
    return removed
