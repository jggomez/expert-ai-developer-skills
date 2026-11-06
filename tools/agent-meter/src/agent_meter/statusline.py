"""One line for the Claude Code status bar. It runs constantly, so it never opens the store."""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Final
from zoneinfo import ZoneInfo

from agent_meter.config import Config
from agent_meter.i18n import money
from agent_meter.paths import AppHome, atomic_write_text

__all__ = ["TODAY_NAME", "render_statusline", "save_today"]

TODAY_NAME: Final = "today.json"
_WORDS: Final = {
    "en": {"session": "session", "today": "today", "context": "context"},
    "es": {"session": "sesión", "today": "hoy", "context": "contexto"},
}
_LOG = logging.getLogger(__name__)


def save_today(home: AppHome, today: date, usd: object) -> None:
    """A failure here must not fail the collect that called it."""
    try:
        home.state_dir.mkdir(parents=True, exist_ok=True)
        atomic_write_text(home.state_dir / TODAY_NAME, json.dumps({"date": today.isoformat(), "usd": str(usd or 0)}))
    except OSError as exc:
        _LOG.warning("could not save today's figure: %s", type(exc).__name__)


def _saved_today(home: AppHome, today: date) -> Decimal | None:
    try:
        saved = json.loads((home.state_dir / TODAY_NAME).read_text(encoding="utf-8"))
        return Decimal(saved["usd"]) if saved["date"] == today.isoformat() else None
    except (OSError, ValueError, KeyError, TypeError, InvalidOperation):
        return None


def _session_usd(payload: dict[str, Any]) -> Decimal | None:
    cost = payload.get("cost")
    value = cost.get("total_cost_usd") if isinstance(cost, dict) else None
    return None if value is None else Decimal(str(value))


def _context_percent(payload: dict[str, Any]) -> int | None:
    window = payload.get("context_window")
    value = window.get("used_percentage") if isinstance(window, dict) else None
    return None if value is None else round(float(value))


def render_statusline(raw: str, home: AppHome, cfg: Config, *, now: datetime | None = None) -> str:
    """Whatever cannot be read is left out, because a broken status bar helps nobody."""
    try:
        payload = json.loads(raw)
    except ValueError:
        payload = {}
    if not isinstance(payload, dict):
        payload = {}
    words = _WORDS[cfg.language]
    parts: list[str] = []
    try:
        session = _session_usd(payload)
        context = _context_percent(payload)
    except (ValueError, TypeError, InvalidOperation):
        session = context = None
    if session is not None:
        parts.append(f"{money(session, cfg.language)} {words['session']}")
    today = _saved_today(home, (now or datetime.now(UTC)).astimezone(ZoneInfo(cfg.timezone)).date())
    if today is not None:
        parts.append(f"{money(today, cfg.language)} {words['today']}")
    if context is not None:
        parts.append(f"{context}% {words['context']}")
    return " · ".join(parts)
