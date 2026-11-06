"""Budgets, month-end forecast and plan value. Budgets warn by default and never block anything."""

from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Final
from zoneinfo import ZoneInfo

from agent_meter import i18n
from agent_meter import notify as notifier
from agent_meter.config import BudgetConfig, Config

if TYPE_CHECKING:
    from agent_meter.store import Store

__all__ = ["BudgetLine", "BudgetStatus", "budget_document", "budget_status", "due_alerts", "render_budget",
           "send_alerts"]

WARN_PCT: Final = Decimal(80)
OVER_PCT: Final = Decimal(100)
FORECAST_DAYS: Final = 7
ZERO: Final = Decimal(0)


@dataclass(frozen=True, slots=True)
class BudgetLine:
    key: str  # stable identity for "already alerted", e.g. "month:all"
    label: str
    period: str
    limit_usd: Decimal
    spent_usd: Decimal

    @property
    def percent(self) -> Decimal:
        return self.spent_usd * 100 / self.limit_usd

    @property
    def level(self) -> str:
        if self.percent >= OVER_PCT:
            return "over"
        return "warn" if self.percent >= WARN_PCT else "ok"


@dataclass(frozen=True, slots=True)
class BudgetStatus:
    as_of: date
    today_usd: Decimal
    month_usd: Decimal
    forecast_usd: Decimal
    lines: tuple[BudgetLine, ...]
    plan_monthly_usd: Decimal | None


def _usd(value: Decimal) -> str:
    return f"${value.quantize(Decimal('0.01')):,}"


def _month_costs(store: Store, as_of: date) -> list[dict[str, object]]:
    start = min(as_of.replace(day=1), as_of - timedelta(days=FORECAST_DAYS - 1))
    return store.query(
        """
        SELECT project_id, display_name, local_date, SUM(cost_usd) AS cost_usd FROM v_daily_project_cost
        WHERE local_date BETWEEN ? AND ? GROUP BY project_id, display_name, local_date
        """,
        [start, as_of],
    )


def _cost(rows: list[dict[str, object]]) -> Decimal:
    return sum((Decimal(str(r["cost_usd"])) for r in rows if r["cost_usd"] is not None), ZERO)


def budget_status(store: Store, budget: BudgetConfig, as_of: date) -> BudgetStatus:
    """Forecast: month to date plus the average of the last 7 days for each day left in the month."""
    rows = _month_costs(store, as_of)
    month_start = as_of.replace(day=1)
    month_rows = [r for r in rows if r["local_date"] >= month_start]  # type: ignore[operator]
    today = _cost([r for r in rows if r["local_date"] == as_of])
    month = _cost(month_rows)
    days_left = calendar.monthrange(as_of.year, as_of.month)[1] - as_of.day
    recent = as_of - timedelta(days=FORECAST_DAYS - 1)
    pace = _cost([r for r in rows if r["local_date"] >= recent]) / FORECAST_DAYS  # type: ignore[operator]
    lines: list[BudgetLine] = []
    if budget.daily_usd is not None:
        lines.append(BudgetLine("day:all", "All projects", "today", budget.daily_usd, today))
    if budget.monthly_usd is not None:
        lines.append(BudgetLine("month:all", "All projects", "this month", budget.monthly_usd, month))
    for project, limit in sorted(budget.projects.items()):
        scoped = [r for r in month_rows if r["project_id"] == project]
        name = str(scoped[0]["display_name"]) if scoped else project
        lines.append(BudgetLine(f"month:{project}", name, "this month", limit, _cost(scoped)))
    return BudgetStatus(as_of, today, month, month + pace * days_left, tuple(lines), budget.plan_monthly_usd)


def due_alerts(store: Store, cfg: Config, moment: datetime) -> tuple[BudgetLine, ...]:
    """Lines that crossed a threshold, each returned once per level and period."""
    as_of = moment.astimezone(ZoneInfo(cfg.timezone)).date()
    status = budget_status(store, cfg.budget, as_of)
    due = []
    for line in status.lines:
        if line.level == "ok":
            continue
        period = as_of.isoformat() if line.key.startswith("day:") else as_of.strftime("%Y-%m")
        marker = f"budget_alert:{line.key}:{period}:{line.level}"
        if store.get_meta(marker) is None:
            store.set_meta(marker, moment.isoformat())
            due.append(line)
    return tuple(due)


def send_alerts(alerts: tuple[BudgetLine, ...], cfg: Config) -> None:
    if cfg.notify == "off":
        return
    for line in alerts:
        notifier.notify(*_alert_text(line, cfg.language))


def _alert_text(line: BudgetLine, language: str) -> tuple[str, str]:
    spent, limit = i18n.money(line.spent_usd, language), i18n.money(line.limit_usd, language)
    label, period = i18n.translate(line.label, language), i18n.translate(line.period, language)
    if language == "es":
        state = "presupuesto superado" if line.level == "over" else "cerca del presupuesto"
        return f"agent-meter: {state}", f"{label}: {spent} de {limit} {period} (costo a precio de lista)"
    state = "over budget" if line.level == "over" else "near budget"
    return f"agent-meter: {state}", f"{label}: {spent} of {limit} {period} (list-price cost)"


def _line_document(line: BudgetLine) -> dict[str, Any]:
    return {"key": line.key, "label": line.label, "period": line.period, "limit_usd": str(line.limit_usd),
            "spent_usd": str(line.spent_usd.quantize(Decimal("0.01"))),
            "percent": str(line.percent.quantize(Decimal("0.1"))), "level": line.level}


def budget_document(status: BudgetStatus) -> dict[str, Any]:
    plan = status.plan_monthly_usd
    return {
        "as_of": status.as_of.isoformat(),
        "today_usd": str(status.today_usd.quantize(Decimal("0.01"))),
        "month_usd": str(status.month_usd.quantize(Decimal("0.01"))),
        "forecast_usd": str(status.forecast_usd.quantize(Decimal("0.01"))),
        "budgets": [_line_document(line) for line in status.lines],
        "plan_monthly_usd": None if plan is None else str(plan),
        "plan_value_ratio": None if plan is None else str((status.month_usd / plan).quantize(Decimal("0.1"))),
    }


def render_budget(status: BudgetStatus) -> str:
    lines = [
        f"Spending · {status.as_of} (list-price cost)",
        f"Today {_usd(status.today_usd)} · month to date {_usd(status.month_usd)} · "
        f"month-end forecast {_usd(status.forecast_usd)} (estimate, last {FORECAST_DAYS} days' pace)",
    ]
    for line in status.lines:
        percent = line.percent.quantize(Decimal("1"))
        lines.append(f"{line.level.upper():5} {line.label} {line.period}: "
                     f"{_usd(line.spent_usd)} of {_usd(line.limit_usd)} ({percent}%)")
    if not status.lines:
        lines.append("No budgets set. Try: agent-meter config set budget.monthly_usd 500")
    if status.plan_monthly_usd is not None:
        ratio = (status.month_usd / status.plan_monthly_usd).quantize(Decimal("0.1"))
        lines.append(f"Plan value: {_usd(status.month_usd)} of list-price usage for "
                     f"{_usd(status.plan_monthly_usd)} a month ({ratio}x)")
    return "\n".join(lines)
