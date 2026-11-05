"""What the desktop app can read and do. No GUI imports, so everything here is testable.

``AppApi``'s public methods are exposed to the page through the ``pywebview`` bridge. There is no
local server and no open port, so another website cannot reach them. Every result is JSON-safe.
"""

from __future__ import annotations

import json
import logging
import threading
import webbrowser
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Final
from zoneinfo import ZoneInfo

from agent_meter import __version__, i18n
from agent_meter.app.history import load_history
from agent_meter.app.projects import (
    ProjectInputError,
    load_projects,
    project_changes,
    valid_hours,
    valid_period,
)
from agent_meter.app.updates import RELEASES_PAGE, check_for_update
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
from agent_meter.notify import notify
from agent_meter.paths import AppHome, atomic_write_text
from agent_meter.project_admin import save_project_override
from agent_meter.project_resolver import ProjectsConfigError
from agent_meter.setup import actuators, auto_rules
from agent_meter.setup.actuators import ActuatorError
from agent_meter.store import Store

__all__ = ["ACTIVE_WINDOW", "EDITABLE_KEYS", "AppApi"]

ACTIVE_WINDOW: Final = timedelta(minutes=15)
CACHE_NAME: Final = "app-cache.json"
READ_LOCK_S: Final = 2.0
COLLECT_LOCK_S: Final = 1.0
WRITE_LOCK_S: Final = 5.0
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
_OBSERVED_MODELS_SQL: Final = """
SELECT model_label, COUNT(*) AS calls FROM v_calls
WHERE host = 'antigravity-cli' AND model_label IS NOT NULL AND local_date >= ?
GROUP BY model_label ORDER BY calls DESC, model_label
"""
_EFFECT_SQL: Final = """
SELECT COUNT(*) AS tasks, AVG(cost_usd) AS cost_per_task, AVG(retries) AS retries_per_task FROM v_tasks
WHERE host LIKE ? AND local_date BETWEEN ? AND ? AND cost_usd IS NOT NULL
"""
OBSERVED_DAYS: Final = 30
EFFECT_DAYS: Final = 7
MIN_EFFECT_TASKS: Final = 5
_INSIGHT_ACTIONS: Final[dict[str, tuple[str, str]]] = {
    "model_what_if": ("claude.model", "sonnet"),
    "long_session": ("claude.autocompact", "70"),
}
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
        localized = i18n.localize_insights(document, self._config().language)
        for item in localized["insights"]:
            item["suggestion"] = _INSIGHT_ACTIONS.get(item["rule"])
        return localized

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

    def _observed_models(self) -> list[str]:
        def read(store: Store, cfg: Config) -> dict[str, Any]:
            start = self._today(cfg) - timedelta(days=OBSERVED_DAYS)
            return {"models": [str(row["model_label"]) for row in store.query(_OBSERVED_MODELS_SQL, [start])]}

        return list(self._with_store("observed_models", read).get("models", []))

    def actions(self) -> dict[str, Any]:
        """Every setting the app can change, with its value now and the values on offer."""
        observed = self._observed_models()
        return {"actions": [
            {"id": action.id, "target": action.target, "current": actuators.current_value(action),
             "options": list(action.values or observed)}
            for action in actuators.ACTIONS.values()
        ]}

    def preview(self, action_id: str, value: str) -> dict[str, Any]:
        try:
            plan = actuators.plan_change(str(action_id), str(value), observed=self._observed_models())
        except ActuatorError as exc:
            return {"ok": False, "code": exc.code}
        return {"ok": True, "action": plan.action.id, "file": str(plan.file), "old_value": plan.old_value,
                "new_value": plan.new_value, "diff": plan.diff, "changed": plan.changed, "before_sha256": plan.before_sha256}

    def apply_action(self, action_id: str, value: str, before_sha256: str | None) -> dict[str, Any]:
        """``before_sha256`` is what the user saw: a file changed since then is never written."""
        try:
            plan = actuators.plan_change(str(action_id), str(value), observed=self._observed_models())
            if plan.before_sha256 != before_sha256:
                raise ActuatorError("stale")
            change = actuators.apply_change(plan, self._home, now=self._clock())
        except ActuatorError as exc:
            return {"ok": False, "code": exc.code}
        return {"ok": True, "id": change["id"]}

    def undo_action(self, change_id: str) -> dict[str, Any]:
        try:
            actuators.undo_change(str(change_id), self._home, now=self._clock())
        except ActuatorError as exc:
            return {"ok": False, "code": exc.code}
        return {"ok": True}

    def changes(self) -> dict[str, Any]:
        """Past changes with coarse before and after figures, which show correlation and not cause."""
        history = actuators.list_changes(self._home)

        def read(store: Store, cfg: Config) -> dict[str, Any]:
            return {"effects": {c["id"]: self._effect(store, cfg, c) for c in history}}

        effects = self._with_store("change_effects", read).get("effects", {})
        return {"changes": [{**c, "effect": effects.get(c["id"])} for c in history]}

    def _effect(self, store: Store, cfg: Config, change: dict[str, Any]) -> dict[str, Any]:
        applied = datetime.fromisoformat(change["applied_at"]).astimezone(ZoneInfo(cfg.timezone)).date()
        last = min(applied + timedelta(days=EFFECT_DAYS), self._today(cfg))
        host = "claude-code" if actuators.ACTIONS[change["action"]].target == "claude" else "antigravity%"
        before = store.query(_EFFECT_SQL, [host, applied - timedelta(days=EFFECT_DAYS), applied - timedelta(days=1)])[0]
        after = store.query(_EFFECT_SQL, [host, applied + timedelta(days=1), last])[0]
        tasks = int(str(after["tasks"] or 0))
        if tasks < MIN_EFFECT_TASKS or not before["tasks"]:
            return {"enough": False, "tasks_after": tasks}

        def figures(row: dict[str, object]) -> dict[str, str]:
            cost = Decimal(str(row["cost_per_task"])).quantize(Decimal("0.01"))
            return {"cost_per_task": str(cost), "retries_per_task": f"{float(str(row['retries_per_task'])):.2f}"}

        return {"enough": True, "tasks_after": tasks, "before": figures(before), "after": figures(after)}

    def projects(self) -> dict[str, Any]:
        return self._with_store("projects", lambda store, _cfg: load_projects(store))

    def _edit_project(self, project_id: str, edit: Callable[[Store, str], None]) -> dict[str, Any]:
        try:
            with Store.open(self._home, read_only=False, lock_timeout_s=WRITE_LOCK_S) as store:
                if not store.query("SELECT 1 FROM projects WHERE project_id = ?", [str(project_id)]):
                    raise ProjectInputError("unknown_project")
                edit(store, str(project_id))
        except LockTimeout:
            return {"ok": False, "code": "busy"}
        except ProjectInputError as exc:
            return {"ok": False, "code": exc.code}
        except ProjectsConfigError:
            return {"ok": False, "code": "projects_file"}
        return {"ok": True}

    def save_project(self, project_id: str, fields: dict[str, Any]) -> dict[str, Any]:
        from agent_meter.cli import Ctx, _refresh_reference

        def edit(store: Store, project: str) -> None:
            save_project_override(self._home.projects, project, project_changes(fields))
            _refresh_reference(Ctx(self._home, quiet=True), store)

        return self._edit_project(project_id, edit)

    def set_project_tag(self, project_id: str, tag: str) -> dict[str, Any]:
        """The tag marks the project's tasks from now on; earlier tasks keep theirs."""
        return self._edit_project(project_id, lambda store, project: store.set_tag(project, str(tag).strip() or None, self._clock()))

    def set_project_hours(self, project_id: str, period: str, hours: str) -> dict[str, Any]:
        return self._edit_project(project_id, lambda store, project: store.set_manual_hours(project, valid_period(str(period)), valid_hours(hours)))

    def remove_project_hours(self, project_id: str, period: str) -> dict[str, Any]:
        def edit(store: Store, project: str) -> None:
            store.unset_manual_hours(project, valid_period(str(period)))

        return self._edit_project(project_id, edit)

    def rules(self) -> dict[str, Any]:
        enabled = auto_rules.enabled_rules(self._home)
        return {"rules": [{"id": rule, "enabled": rule in enabled} for rule in auto_rules.RULES]}

    def set_rule(self, rule_id: str, enabled: bool) -> dict[str, Any]:
        try:
            auto_rules.set_rule(self._home, str(rule_id), bool(enabled))
        except ActuatorError as exc:
            return {"ok": False, "code": exc.code}
        return {"ok": True}

    def run_rules(self) -> list[str]:
        """Runs after a collect. Saved figures can be old, so a rule only acts on a fresh read."""
        if not auto_rules.enabled_rules(self._home):
            return []
        document = self._with_store("overview", self._read_overview)
        if "budgets" not in document or document.get("stale"):
            return []
        cfg = self._config()
        fired = auto_rules.evaluate(self._home, document["budgets"], today=self._today(cfg), now=self._clock())
        words = i18n.UI[cfg.language]
        for item in fired:
            notify("agent-meter", words[f"rule.{item.rule}.fired"])
        return [item.change_id for item in fired]

    def check_update(self) -> dict[str, Any]:
        return check_for_update(__version__)

    def open_release(self, url: str) -> dict[str, Any]:
        if not str(url).startswith(RELEASES_PAGE):
            return {"ok": False}
        return {"ok": webbrowser.open(str(url))}

    def collect_now(self) -> dict[str, Any]:
        result = collect(self._home, self._config(), lock_timeout_s=COLLECT_LOCK_S)
        return {"status": result.status, "message": result.message, "duration_ms": result.duration_ms}
