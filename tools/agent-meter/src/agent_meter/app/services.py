"""What the desktop app can read and do. No GUI imports, so everything here is testable.

``AppApi``'s public methods are exposed to the page through the ``pywebview`` bridge. There is no
local server and no open port, so another website cannot reach them. Every result is JSON-safe.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Final
from zoneinfo import ZoneInfo

from agent_meter import i18n
from agent_meter.app.history import load_history
from agent_meter.budgets import budget_document, budget_status
from agent_meter.collector import collect
from agent_meter.config import (
    Config,
    ConfigError,
    config_items,
    load_config,
    save_config,
    set_key,
)
from agent_meter.insights import Thresholds, build_insights, insights_document
from agent_meter.locking import LockTimeout
from agent_meter.paths import AppHome, atomic_write_text
from agent_meter.store import Store

__all__ = ["ACTIVE_WINDOW", "EDITABLE_KEYS", "AppApi"]

ACTIVE_WINDOW: Final = timedelta(minutes=15)
CACHE_NAME: Final = "app-cache.json"
READ_LOCK_S: Final = 2.0
COLLECT_LOCK_S: Final = 1.0
EDITABLE_KEYS: Final = ("budget.daily_usd", "budget.monthly_usd", "budget.plan_monthly_usd", "notify")
_ACTIVE_SESSIONS_SQL: Final = """
WITH recent AS (
  SELECT host, session_id, display_name, calls, cost_usd, ended_at FROM v_sessions
  WHERE ended_at >= ? ORDER BY ended_at DESC, session_id LIMIT 8
),
latest AS (
  SELECT host, session_id, arg_max(prompt_tokens, ts) AS context_tokens FROM v_calls
  WHERE (host, session_id) IN (SELECT host, session_id FROM recent) GROUP BY host, session_id
)
SELECT r.*, l.context_tokens FROM recent r LEFT JOIN latest l USING (host, session_id)
ORDER BY r.ended_at DESC, r.session_id
"""
_LOG = logging.getLogger(__name__)


class AppApi:
    def __init__(self, home: AppHome, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._home = home
        self._clock = clock
        self._cache_lock = threading.Lock()
        self._cache: dict[str, dict[str, Any]] | None = None

    def _config(self) -> Config:
        return load_config(self._home)

    def _today(self, cfg: Config) -> Any:
        return self._clock().astimezone(ZoneInfo(cfg.timezone)).date()

    @property
    def _cache_path(self) -> Path:
        return self._home.state_dir / CACHE_NAME

    def _load_cache(self) -> dict[str, dict[str, Any]]:
        if self._cache is None:
            try:
                self._cache = json.loads(self._cache_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                self._cache = {}
            except (OSError, ValueError) as exc:
                _LOG.warning("ignoring the saved app data: %s", type(exc).__name__)
                self._cache = {}
        return self._cache

    def _remember(self, key: str, document: dict[str, Any]) -> None:
        with self._cache_lock:
            cache = self._load_cache()
            cache[key] = document
            self._home.state_dir.mkdir(parents=True, exist_ok=True)
            atomic_write_text(self._cache_path, json.dumps(cache))

    def _with_store(self, key: str, read: Callable[[Store, Config], dict[str, Any]]) -> dict[str, Any]:
        """A collect holds the store for up to minutes, so fall back to the last figures read."""
        cfg = self._config()
        try:
            with Store.open(self._home, read_only=True, lock_timeout_s=READ_LOCK_S) as store:
                document = read(store, cfg)
        except LockTimeout:
            with self._cache_lock:
                saved = self._load_cache().get(key)
            return {"busy": True} if saved is None else {**saved, "stale": True}
        self._remember(key, document)
        return document

    def texts(self) -> dict[str, Any]:
        language = self._config().language
        return {"language": language, "text": dict(i18n.UI[language])}

    def set_language(self, language: str) -> dict[str, Any]:
        try:
            save_config(set_key(self._config(), "language", str(language)), self._home)
        except ConfigError as exc:
            return {**self.texts(), "error": str(exc)}
        return self.texts()

    def overview(self) -> dict[str, Any]:
        """Spending, budgets and the sessions active in the last 15 minutes."""
        document = self._with_store("overview", self._read_overview)
        if "budgets" not in document:
            return document
        language = self._config().language
        return {**document, "budgets": [i18n.localize_budget_line(line, language) for line in document["budgets"]]}

    def _read_overview(self, store: Store, cfg: Config) -> dict[str, Any]:
        moment = self._clock()
        document = budget_document(budget_status(store, cfg.budget, self._today(cfg)))
        rows = store.query(_ACTIVE_SESSIONS_SQL, [moment - ACTIVE_WINDOW])
        document["sessions"] = [
            {
                "host": str(row["host"]), "project": str(row["display_name"]), "calls": row["calls"],
                "cost_usd": None if row["cost_usd"] is None else str(Decimal(str(row["cost_usd"])).quantize(Decimal("0.01"))),
                "context_tokens": row["context_tokens"],
                "minutes_ago": int((moment - row["ended_at"]).total_seconds() // 60),  # type: ignore[operator]
            }
            for row in rows
        ]
        document["last_collect_at"] = store.get_meta("last_collect_at")
        return document

    def history(self, days: int = 0, project_id: str | None = None) -> dict[str, Any]:
        """Spending by day, month, project and session. ``days`` of 0 means all history."""
        window = max(int(days), 0)
        project = project_id or None

        def read(store: Store, cfg: Config) -> dict[str, Any]:
            return load_history(store, as_of=self._today(cfg), days=window, project_id=project)

        return self._with_store(f"history:{window}:{project}", read)

    def insights(self, days: int = 30) -> dict[str, Any]:
        def read(store: Store, cfg: Config) -> dict[str, Any]:
            limits = Thresholds(window_days=max(int(days), 1))
            return insights_document(build_insights(store, as_of=self._today(cfg), limits=limits))

        document = self._with_store(f"insights:{days}", read)
        if "insights" not in document:
            return document
        return i18n.localize_insights(document, self._config().language)

    def settings(self) -> dict[str, Any]:
        from agent_meter.cli import Ctx, _doctor_checks

        cfg = self._config()
        values = dict(config_items(cfg))
        try:
            checks = _doctor_checks(Ctx(self._home, quiet=True), cloud=False)
        except LockTimeout:
            return {"values": {key: values.get(key, "") for key in EDITABLE_KEYS}, "checks": [], "busy": True}
        translated = [
            {**check, "check": i18n.translate(check["check"], cfg.language),
             "message": i18n.translate(check["message"], cfg.language)}
            for check in checks
        ]
        return {"values": {key: values.get(key, "") for key in EDITABLE_KEYS}, "checks": translated}

    def save_setting(self, key: str, value: str) -> dict[str, Any]:
        if key not in EDITABLE_KEYS:
            return {"ok": False, "error": f"{key} cannot be changed here"}
        try:
            save_config(set_key(self._config(), key, str(value)), self._home)
        except ConfigError as exc:
            return {"ok": False, "error": i18n.translate(str(exc), self._config().language)}
        return {"ok": True}

    def collect_now(self) -> dict[str, Any]:
        result = collect(self._home, self._config(), lock_timeout_s=COLLECT_LOCK_S)
        return {"status": result.status, "message": result.message, "duration_ms": result.duration_ms}
