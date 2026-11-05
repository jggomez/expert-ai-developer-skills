"""Automatic rules: each one is off until the user turns it on, and each fires once per period.

A rule only makes a change the user could make on the Changes screen, through the same checks,
backup and undo. When a change is undone the rule stays quiet until the next period.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any, Final

from agent_meter.paths import AppHome, atomic_write_text
from agent_meter.setup import actuators
from agent_meter.setup.actuators import ActuatorError

__all__ = ["RULES", "Fired", "Rule", "enabled_rules", "evaluate", "set_rule"]

STATE_NAME: Final = "rules.json"
_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Rule:
    id: str
    budget_key: str
    action: str
    value: str
    period_format: str


RULES: Final[Mapping[str, Rule]] = {
    rule.id: rule for rule in (
        Rule("monthly_budget_sonnet", "month:all", "claude.model", "sonnet", "%Y-%m"),
        Rule("daily_budget_sonnet", "day:all", "claude.model", "sonnet", "%Y-%m-%d"),
    )
}


@dataclass(frozen=True, slots=True)
class Fired:
    rule: str
    change_id: str


def _state_path(home: AppHome) -> Path:
    return home.root / STATE_NAME


def _load(home: AppHome) -> dict[str, Any]:
    """A damaged file means no rule runs, which is the safe reading for something that edits settings."""
    try:
        state = json.loads(_state_path(home).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {"enabled": [], "fired": {}}
    except (OSError, ValueError) as exc:
        _LOG.warning("ignoring the rules file: %s", type(exc).__name__)
        return {"enabled": [], "fired": {}}
    if not isinstance(state, dict):
        return {"enabled": [], "fired": {}}
    enabled = state.get("enabled")
    fired = state.get("fired")
    return {"enabled": enabled if isinstance(enabled, list) else [], "fired": fired if isinstance(fired, dict) else {}}


def _save(home: AppHome, state: dict[str, Any]) -> None:
    atomic_write_text(_state_path(home), json.dumps(state, indent=2) + "\n")


def enabled_rules(home: AppHome) -> list[str]:
    return [rule for rule in RULES if rule in _load(home)["enabled"]]


def set_rule(home: AppHome, rule_id: str, enabled: bool) -> None:
    if rule_id not in RULES:
        raise ActuatorError("unknown_action")
    state = _load(home)
    others = [rule for rule in state["enabled"] if rule != rule_id]
    _save(home, {**state, "enabled": [*others, rule_id] if enabled else others})


def evaluate(home: AppHome, budget_lines: Sequence[Mapping[str, Any]], *, today: date, now: datetime) -> list[Fired]:
    """Apply the enabled rules whose budget is over. A rule that cannot apply tries again next time."""
    state = _load(home)
    levels = {str(line["key"]): line["level"] for line in budget_lines}
    fired: list[Fired] = []
    for rule_id in state["enabled"]:
        rule = RULES.get(rule_id)
        if rule is None or levels.get(rule.budget_key) != "over":
            continue
        period = today.strftime(rule.period_format)
        if state["fired"].get(rule_id) == period:
            continue
        try:
            plan = actuators.plan_change(rule.action, rule.value)
            change_id = actuators.apply_change(plan, home, now=now)["id"] if plan.changed else None
        except ActuatorError as exc:
            _LOG.warning("rule %s did not apply: %s", rule_id, exc.code)
            continue
        state["fired"][rule_id] = period
        _save(home, state)
        if change_id is not None:
            fired.append(Fired(rule_id, str(change_id)))
    return fired
