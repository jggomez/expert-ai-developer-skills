"""Host detection and host-file locations for the setup wizard (PLAN step 1, ADR §3.2/§3.10)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from agent_meter.model import Host

__all__ = [
    "ANTIGRAVITY_HOSTS",
    "DetectedHost",
    "antigravity_hooks_path",
    "antigravity_plugin_installed",
    "claude_plugin_installed",
    "claude_settings_path",
    "detect_hosts",
    "host_roots",
    "parse_hosts",
]

ANTIGRAVITY_HOSTS: Final = frozenset(
    {Host.ANTIGRAVITY_CLI, Host.ANTIGRAVITY_IDE, Host.ANTIGRAVITY_APP}
)
_PLUGIN_NAME: Final = "agent-metrics"


@dataclass(frozen=True, slots=True)
class DetectedHost:
    host: Host
    root: Path
    present: bool
    units: int  # Claude sessions or Antigravity conversations still on disk


def _claude_root(user_home: Path, environ: Mapping[str, str]) -> Path:
    custom = environ.get("CLAUDE_CONFIG_DIR")
    return Path(custom) if custom else user_home / ".claude"


def host_roots(user_home: Path, environ: Mapping[str, str]) -> dict[Host, Path]:
    gemini = user_home / ".gemini"
    return {
        Host.CLAUDE_CODE: _claude_root(user_home, environ),
        Host.ANTIGRAVITY_CLI: gemini / "antigravity-cli",
        Host.ANTIGRAVITY_IDE: gemini / "antigravity-ide",
        Host.ANTIGRAVITY_APP: gemini / "antigravity",
    }


def _count_units(host: Host, root: Path) -> int:
    if host is Host.CLAUDE_CODE:
        return sum(1 for _ in (root / "projects").glob("*/*.jsonl"))
    conversations = root / "conversations"
    return len(
        {
            path.stem
            for pattern in ("*.db", "*.pb")
            for path in conversations.glob(pattern)
        }
    )


def detect_hosts(user_home: Path, environ: Mapping[str, str]) -> list[DetectedHost]:
    """Every known host with its root, presence and amount of history (stat-only)."""
    detected: list[DetectedHost] = []
    for host, root in host_roots(user_home, environ).items():
        present = root.is_dir()
        detected.append(
            DetectedHost(
                host, root, present, _count_units(host, root) if present else 0
            )
        )
    return detected


def claude_settings_path(user_home: Path, environ: Mapping[str, str]) -> Path:
    return _claude_root(user_home, environ) / "settings.json"


def antigravity_hooks_path(user_home: Path) -> Path:
    """User-level Antigravity hooks file; ``~/.gemini/settings.json`` is Gemini CLI's and off-limits."""
    return user_home / ".gemini" / "config" / "hooks.json"


def claude_plugin_installed(settings_path: Path) -> bool:
    """True when the optional ``agent-metrics`` plugin is enabled in Claude Code settings."""
    try:
        data = json.loads(settings_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError):
        return (
            False  # absent or unreadable settings: the plugin cannot be enabled there
        )
    plugins = data.get("enabledPlugins") if isinstance(data, dict) else None
    if not isinstance(plugins, dict):
        return False
    return any(
        str(name).split("@", 1)[0] == _PLUGIN_NAME and enabled is True
        for name, enabled in plugins.items()
    )


def antigravity_plugin_installed(user_home: Path) -> bool:
    return (user_home / ".gemini" / "config" / "plugins" / _PLUGIN_NAME).is_dir()


def parse_hosts(text: str) -> tuple[Host, ...]:
    """``--hosts claude-code,antigravity-cli`` → hosts in the given order (no duplicates)."""
    hosts: list[Host] = []
    for raw in text.split(","):
        name = raw.strip()
        if not name:
            continue
        try:
            host = Host(name)
        except ValueError as exc:
            valid = ", ".join(h.value for h in Host)
            raise ValueError(
                f"unknown host {name!r}; expected one of: {valid}"
            ) from exc
        if host not in hosts:
            hosts.append(host)
    if not hosts:
        raise ValueError("--hosts needs at least one host")
    return tuple(hosts)
