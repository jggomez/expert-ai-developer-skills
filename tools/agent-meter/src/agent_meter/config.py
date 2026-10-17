"""``~/.agent-meter/config.toml`` (contracts §3.6, §5).

Read with ``tomllib`` and written by a small fixed-schema serializer (no TOML writer
dependency). Sections: ``[general]``, ``[currency]``, ``[hosts.<host>]`` and
``[sinks.bigquery]``. ``get_key``/``set_key`` accept the dotted names shown by
``agent-meter config show`` plus a few short aliases (``timezone``, ``usd_rate``…).
"""

from __future__ import annotations

import json
import os
import re
import tomllib
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, fields, replace
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Final, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agent_meter.model import Host
from agent_meter.paths import AppHome, atomic_write_text

__all__ = [
    "BigQueryConfig",
    "Config",
    "ConfigError",
    "HostConfig",
    "NotifyPolicy",
    "config_items",
    "get_key",
    "host_defaults",
    "load_config",
    "save_config",
    "set_key",
    "settings_for_store",
    "system_timezone",
]

NotifyPolicy = Literal["auto", "session", "long-tasks", "off"]
_NOTIFY_VALUES: Final = ("auto", "session", "long-tasks", "off")
_BQ_MODES: Final = ("billing", "sandbox")
_CURRENCY: Final = re.compile(r"^[A-Z]{3}$")
_TRUE: Final = frozenset({"true", "yes", "on", "1"})
_FALSE: Final = frozenset({"false", "no", "off", "0"})


class ConfigError(ValueError):
    """``config.toml`` or a ``config set`` value is invalid."""


def system_timezone() -> str:
    """The system IANA zone name (``$TZ``, then ``/etc/localtime``), else ``UTC``."""
    candidates: list[str] = []
    env_tz = os.environ.get("TZ", "").lstrip(":")
    if env_tz:
        candidates.append(env_tz)
    try:
        target = os.path.realpath("/etc/localtime")
    except OSError:
        target = ""
    if "zoneinfo/" in target:
        candidates.append(target.split("zoneinfo/", 1)[1])
    for name in candidates:
        if _valid_timezone(name):
            return name
    return "UTC"


def _valid_timezone(name: str) -> bool:
    try:
        ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        return False
    return True


@dataclass(frozen=True, slots=True)
class HostConfig:
    enabled: bool = True
    root: Path | None = None
    default_model: str | None = None


@dataclass(frozen=True, slots=True)
class BigQueryConfig:
    enabled: bool = False
    project: str = ""
    dataset: str = "agent_metrics"
    location: str = "US"
    mode: Literal["billing", "sandbox"] = "billing"
    anonymize_projects: bool = False
    looker_template_id: str = ""


# Antigravity often omits the model id; such calls are priced (flagged inferred) as this.
ANTIGRAVITY_DEFAULT_MODEL: Final = "gemini-3.8-flash"
_ANTIGRAVITY_HOSTS: Final = frozenset(
    {Host.ANTIGRAVITY_CLI, Host.ANTIGRAVITY_IDE, Host.ANTIGRAVITY_APP}
)


def _default_host_config(host: Host) -> HostConfig:
    if host in _ANTIGRAVITY_HOSTS:
        return HostConfig(default_model=ANTIGRAVITY_DEFAULT_MODEL)
    return HostConfig()


def _default_hosts() -> dict[Host, HostConfig]:
    return {host: _default_host_config(host) for host in Host}


@dataclass(frozen=True, slots=True)
class Config:
    timezone: str
    idle_threshold_s: int = 120
    stale_after_h: int = 24
    dev_hours_merge_gap_min: int = 30
    show_task_labels: bool = True
    store_agent_descriptions: bool = False  # reserved for v2, currently ignored (always hashed)
    notify: NotifyPolicy = "auto"
    notify_min_task_s: int = 120
    claude_inline_summary: bool = False
    display_currency: str | None = None
    usd_rate: Decimal | None = None  # display units per 1 USD
    hosts: Mapping[Host, HostConfig] = field(default_factory=_default_hosts)
    bigquery: BigQueryConfig = field(default_factory=BigQueryConfig)

    def host(self, host: Host) -> HostConfig:
        return self.hosts.get(host) or _default_host_config(host)


# ----------------------------------------------------------------------------- coercion

Coercer = Callable[[object, str], Any]


def _as_text(raw: object) -> str:
    return raw.strip() if isinstance(raw, str) else str(raw)


def _bool(raw: object, key: str) -> bool:
    if isinstance(raw, bool):
        return raw
    text = _as_text(raw).lower()
    if text in _TRUE:
        return True
    if text in _FALSE:
        return False
    raise ConfigError(f"{key}: expected true or false, got {raw!r}")


def _int(minimum: int) -> Coercer:
    def coerce(raw: object, key: str) -> int:
        if isinstance(raw, bool):
            raise ConfigError(f"{key}: expected an integer, got {raw!r}")
        try:
            value = raw if isinstance(raw, int) else int(_as_text(raw))
        except ValueError as exc:
            raise ConfigError(f"{key}: expected an integer, got {raw!r}") from exc
        if value < minimum:
            raise ConfigError(f"{key}: must be >= {minimum}, got {value}")
        return value

    return coerce


def _timezone(raw: object, key: str) -> str:
    text = _as_text(raw)
    if not text or not _valid_timezone(text):
        raise ConfigError(f"{key}: unknown timezone {raw!r} (use an IANA name like America/Bogota)")
    return text


def _choice(options: tuple[str, ...]) -> Coercer:
    def coerce(raw: object, key: str) -> str:
        text = _as_text(raw)
        if text not in options:
            raise ConfigError(f"{key}: must be one of {', '.join(options)}, got {raw!r}")
        return text

    return coerce


def _currency(raw: object, key: str) -> str | None:
    text = _as_text(raw).upper()
    if not text:
        return None
    if not _CURRENCY.match(text):
        raise ConfigError(f"{key}: expected a 3-letter ISO currency code, got {raw!r}")
    return text


def _rate(raw: object, key: str) -> Decimal | None:
    if isinstance(raw, float):
        raise ConfigError(f"{key}: write the rate as a quoted string, e.g. \"4100.50\"")
    text = _as_text(raw)
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ConfigError(f"{key}: {raw!r} is not a decimal number") from exc
    if not value.is_finite() or value <= 0:
        raise ConfigError(f"{key}: must be a positive decimal, got {raw!r}")
    return value


def _str(raw: object, key: str) -> str:
    if not isinstance(raw, (str, int)) or isinstance(raw, bool):
        raise ConfigError(f"{key}: expected a string, got {raw!r}")
    return _as_text(raw)


def _opt_str(raw: object, key: str) -> str | None:
    return _str(raw, key) or None


def _path(raw: object, key: str) -> Path | None:
    text = _str(raw, key)
    return Path(text).expanduser() if text else None


_GENERAL: Final[dict[str, Coercer]] = {
    "timezone": _timezone,
    "idle_threshold_s": _int(1),
    "stale_after_h": _int(1),
    "dev_hours_merge_gap_min": _int(0),
    "show_task_labels": _bool,
    "store_agent_descriptions": _bool,
    "notify": _choice(_NOTIFY_VALUES),
    "notify_min_task_s": _int(0),
    "claude_inline_summary": _bool,
}
_CURRENCY_KEYS: Final[dict[str, tuple[str, Coercer]]] = {
    "display": ("display_currency", _currency),
    "usd_rate": ("usd_rate", _rate),
}
_HOST_KEYS: Final[dict[str, Coercer]] = {
    "enabled": _bool,
    "root": _path,
    "default_model": _opt_str,
}
_BQ_KEYS: Final[dict[str, Coercer]] = {
    "enabled": _bool,
    "project": _str,
    "dataset": _str,
    "location": _str,
    "mode": _choice(_BQ_MODES),
    "anonymize_projects": _bool,
    "looker_template_id": _str,
}


# ----------------------------------------------------------------------------- key addressing


@dataclass(frozen=True, slots=True)
class _Key:
    section: Literal["general", "currency", "host", "bigquery"]
    name: str
    host: Host | None = None

    @property
    def dotted(self) -> str:
        if self.section == "general":
            return self.name
        if self.section == "currency":
            return f"currency.{self.name}"
        if self.section == "host":
            assert self.host is not None
            return f"hosts.{self.host.value}.{self.name}"
        return f"bigquery.{self.name}"


def _parse_key(dotted: str) -> _Key:
    parts = dotted.strip().split(".")
    if parts[0] == "general" and len(parts) == 2:
        parts = parts[1:]
    if parts[0] == "sinks" and len(parts) == 3 and parts[1] == "bigquery":
        parts = parts[1:]
    if len(parts) == 1:
        name = parts[0]
        if name in _GENERAL:
            return _Key("general", name)
        if name == "display_currency":
            return _Key("currency", "display")
        if name == "usd_rate":
            return _Key("currency", "usd_rate")
    if len(parts) == 2 and parts[0] == "currency" and parts[1] in _CURRENCY_KEYS:
        return _Key("currency", parts[1])
    if len(parts) == 2 and parts[0] == "bigquery" and parts[1] in _BQ_KEYS:
        return _Key("bigquery", parts[1])
    if len(parts) == 3 and parts[0] == "hosts" and parts[2] in _HOST_KEYS:
        try:
            host = Host(parts[1])
        except ValueError as exc:
            raise ConfigError(f"unknown host {parts[1]!r} in {dotted!r}") from exc
        return _Key("host", parts[2], host)
    raise ConfigError(f"unknown config key {dotted!r} (see 'agent-meter config show')")


def _assign(cfg: Config, key: _Key, raw: object) -> Config:
    if key.section == "general":
        return replace(cfg, **{key.name: _GENERAL[key.name](raw, key.dotted)})
    if key.section == "currency":
        attr, coerce = _CURRENCY_KEYS[key.name]
        return replace(cfg, **{attr: coerce(raw, key.dotted)})
    if key.section == "host":
        assert key.host is not None
        hosts = dict(cfg.hosts)
        current = hosts.get(key.host) or _default_host_config(key.host)
        hosts[key.host] = replace(current, **{key.name: _HOST_KEYS[key.name](raw, key.dotted)})
        return replace(cfg, hosts=hosts)
    bq = replace(cfg.bigquery, **{key.name: _BQ_KEYS[key.name](raw, key.dotted)})
    return replace(cfg, bigquery=bq)


def _read(cfg: Config, key: _Key) -> object:
    if key.section == "general":
        return getattr(cfg, key.name)
    if key.section == "currency":
        return getattr(cfg, _CURRENCY_KEYS[key.name][0])
    if key.section == "host":
        assert key.host is not None
        return getattr(cfg.host(key.host), key.name)
    return getattr(cfg.bigquery, key.name)


def _display(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return format(value, "f")
    return str(value)


def get_key(cfg: Config, dotted: str) -> str:
    """The value of one key as text (``""`` for unset optional values)."""
    return _display(_read(cfg, _parse_key(dotted)))


def set_key(cfg: Config, dotted: str, value: str) -> Config:
    """A copy of ``cfg`` with one key changed; an empty value clears optional keys."""
    return _assign(cfg, _parse_key(dotted), value)


def config_items(cfg: Config) -> list[tuple[str, str]]:
    """Every key and its value, in the order ``config show`` prints them."""
    keys = [_Key("general", name) for name in _GENERAL]
    keys += [_Key("currency", name) for name in _CURRENCY_KEYS]
    keys += [_Key("host", name, host) for host in Host for name in _HOST_KEYS]
    keys += [_Key("bigquery", name) for name in _BQ_KEYS]
    return [(k.dotted, _display(_read(cfg, k))) for k in keys]


# ----------------------------------------------------------------------------- file I/O


def _section(doc: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    value = doc.get(name, {})
    if not isinstance(value, Mapping):
        raise ConfigError(f"[{name}] must be a table")
    return value


def _apply_table(
    cfg: Config, table: Mapping[str, Any], allowed: Mapping[str, object], make: Callable[[str], _Key], where: str
) -> Config:
    for name, raw in table.items():
        if name not in allowed:
            raise ConfigError(f"[{where}] unknown key {name!r}")
        cfg = _assign(cfg, make(name), raw)
    return cfg


def _host_key_factory(host: Host) -> Callable[[str], _Key]:
    def make(name: str) -> _Key:
        return _Key("host", name, host)

    return make


def load_config(home: AppHome) -> Config:
    """Parse ``config.toml``; a missing file yields defaults (timezone = system IANA name)."""
    cfg = Config(timezone=system_timezone())
    if not home.config.exists():
        return cfg
    try:
        doc = tomllib.loads(home.config.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"config.toml is not valid TOML: {exc}") from exc
    unknown = set(doc) - {"general", "currency", "hosts", "sinks"}
    if unknown:
        raise ConfigError(f"config.toml: unknown section(s) {sorted(unknown)}")
    cfg = _apply_table(cfg, _section(doc, "general"), _GENERAL, lambda n: _Key("general", n), "general")
    cfg = _apply_table(
        cfg, _section(doc, "currency"), _CURRENCY_KEYS, lambda n: _Key("currency", n), "currency"
    )
    for host_name, table in _section(doc, "hosts").items():
        try:
            host = Host(host_name)
        except ValueError as exc:
            raise ConfigError(f"config.toml: unknown host [hosts.{host_name}]") from exc
        if not isinstance(table, Mapping):
            raise ConfigError(f"[hosts.{host_name}] must be a table")
        cfg = _apply_table(cfg, table, _HOST_KEYS, _host_key_factory(host), f"hosts.{host_name}")
    sinks = _section(doc, "sinks")
    unknown_sinks = set(sinks) - {"bigquery"}
    if unknown_sinks:
        raise ConfigError(f"config.toml: unknown sink(s) {sorted(unknown_sinks)}")
    bq_table = _section(sinks, "bigquery")
    return _apply_table(cfg, bq_table, _BQ_KEYS, lambda n: _Key("bigquery", n), "sinks.bigquery")


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    return json.dumps(_display(value), ensure_ascii=False)


def _lines(header: str, pairs: list[tuple[str, object]]) -> list[str]:
    body = [f"{name} = {_toml_value(value)}" for name, value in pairs if value is not None]
    return [f"[{header}]", *body, ""]


def save_config(cfg: Config, home: AppHome) -> None:
    """Write ``config.toml`` atomically with the fixed section layout."""
    out = ["# agent-meter configuration (edit with 'agent-meter config set <key> <value>')", ""]
    out += _lines("general", [(name, getattr(cfg, name)) for name in _GENERAL])
    out += _lines("currency", [("display", cfg.display_currency), ("usd_rate", cfg.usd_rate)])
    for host in Host:
        host_cfg = cfg.host(host)
        out += _lines(
            f"hosts.{host.value}",
            [(f.name, getattr(host_cfg, f.name)) for f in fields(HostConfig)],
        )
    out += _lines(
        "sinks.bigquery", [(f.name, getattr(cfg.bigquery, f.name)) for f in fields(BigQueryConfig)]
    )
    atomic_write_text(home.config, "\n".join(out))


def settings_for_store(cfg: Config) -> dict[str, str]:
    """The ``settings`` reference rows the store views read (timezone, currency)."""
    settings = {"timezone": cfg.timezone, "idle_threshold_s": str(cfg.idle_threshold_s)}
    if cfg.display_currency:
        settings["display_currency"] = cfg.display_currency
    if cfg.usd_rate is not None:
        settings["usd_rate"] = format(cfg.usd_rate, "f")
    return settings


def host_defaults(cfg: Config) -> dict[Host, str | None]:
    """``default_model`` per host, for ``host_defaults`` (BR-04)."""
    return {host: cfg.host(host).default_model for host in Host}

