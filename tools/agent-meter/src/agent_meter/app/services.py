"""What the desktop app can read and do. No GUI imports, so everything here is testable.

``AppApi``'s public methods are exposed to the page through the ``pywebview`` bridge. There is no
local server and no open port, so another website cannot reach them. Every result is JSON-safe.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Final
from zoneinfo import ZoneInfo

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
from agent_meter.paths import AppHome
from agent_meter.store import Store

__all__ = ["ACTIVE_WINDOW", "EDITABLE_KEYS", "AppApi"]

ACTIVE_WINDOW: Final = timedelta(minutes=15)
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


class AppApi:
    def __init__(self, home: AppHome, *, clock: Callable[[], datetime] = lambda: datetime.now(UTC)) -> None:
        self._home = home
        self._clock = clock

    def _config(self) -> Config:
        return load_config(self._home)

    def _today(self, cfg: Config) -> Any:
        return self._clock().astimezone(ZoneInfo(cfg.timezone)).date()

    def _with_store(self, read: Callable[[Store, Config], dict[str, Any]]) -> dict[str, Any]:
        cfg = self._config()
        try:
            with Store.open(self._home, read_only=True, lock_timeout_s=READ_LOCK_S) as store:
                return read(store, cfg)
        except LockTimeout:
            return {"busy": True}

    def overview(self) -> dict[str, Any]:
        """Spending, budgets and the sessions active in the last 15 minutes."""
        return self._with_store(self._read_overview)

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

    def insights(self, days: int = 30) -> dict[str, Any]:
        def read(store: Store, cfg: Config) -> dict[str, Any]:
            limits = Thresholds(window_days=max(int(days), 1))
            return insights_document(build_insights(store, as_of=self._today(cfg), limits=limits))

        return self._with_store(read)

    def settings(self) -> dict[str, Any]:
        from agent_meter.cli import Ctx, _doctor_checks

        values = dict(config_items(self._config()))
        try:
            checks = _doctor_checks(Ctx(self._home, quiet=True), cloud=False)
        except LockTimeout:
            checks = []
        return {"values": {key: values.get(key, "") for key in EDITABLE_KEYS}, "checks": checks}

    def save_setting(self, key: str, value: str) -> dict[str, Any]:
        if key not in EDITABLE_KEYS:
            return {"ok": False, "error": f"{key} cannot be changed here"}
        try:
            save_config(set_key(self._config(), key, str(value)), self._home)
        except ConfigError as exc:
            return {"ok": False, "error": str(exc)}
        return {"ok": True}

    def collect_now(self) -> dict[str, Any]:
        result = collect(self._home, self._config(), lock_timeout_s=COLLECT_LOCK_S)
        return {"status": result.status, "message": result.message, "duration_ms": result.duration_ms}
