"""What the Projects screen reads, and the checks on what it writes."""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any, Final

from agent_meter.project_admin import PROJECT_LIST_SQL
from agent_meter.store import UNASSIGNED_ID, Store

__all__ = ["ProjectInputError", "load_projects", "project_changes", "valid_hours", "valid_period"]

_TAGS_SQL: Final = "SELECT project_id, tag FROM tag_history WHERE to_ts IS NULL AND tag IS NOT NULL"
_HOURS_SQL: Final = "SELECT project_id, period, hours FROM dev_hours_manual ORDER BY period DESC"
_PERIOD: Final = re.compile(r"\d{4}-(0[1-9]|1[0-2])\Z")
_CURRENCY: Final = re.compile(r"[A-Za-z]{3}\Z")
_MAX_AMOUNT: Final = Decimal("999999.99")


@dataclass(frozen=True, slots=True)
class ProjectInputError(ValueError):
    code: str


def _text(value: object) -> str | None:
    return None if value is None else str(value)


def _plain_number(value: object) -> str | None:
    """Rates are stored with four decimals; ``80.0000`` reads as ``80``."""
    return None if value is None else f"{Decimal(str(value)).normalize():f}"


def load_projects(store: Store) -> dict[str, Any]:
    tags = {str(row["project_id"]): str(row["tag"]) for row in store.query(_TAGS_SQL)}
    hours: dict[str, list[dict[str, str | None]]] = {}
    for row in store.query(_HOURS_SQL):
        hours.setdefault(str(row["project_id"]), []).append({"period": str(row["period"]), "hours": _plain_number(row["hours"])})
    return {"projects": [
        {
            "project_id": str(row["project_id"]), "name": str(row["display_name"]), "client": _text(row["client"]),
            "billing": _text(row["billing_model"]), "rate": _plain_number(row["hourly_rate"]),
            "fixed_price": _plain_number(row["fixed_price"]),
            "currency": _text(row["rate_currency"]), "sessions": row["sessions"], "cost_usd": _text(row["cost_usd"]),
            "tag": tags.get(str(row["project_id"])), "hours": hours.get(str(row["project_id"]), []),
        }
        for row in store.query(PROJECT_LIST_SQL) if row["project_id"] != UNASSIGNED_ID
    ]}


def _amount(raw: object) -> Decimal | None:
    text = str(raw or "").strip()
    if not text:
        return None
    try:
        value = Decimal(text)
    except InvalidOperation:
        raise ProjectInputError("invalid_amount") from None
    if not value.is_finite() or value < 0 or value > _MAX_AMOUNT:
        raise ProjectInputError("invalid_amount")
    return value


def project_changes(fields: dict[str, Any]) -> dict[str, Any]:
    """Empty boxes clear the saved value, so every field is always part of the change."""
    billing = str(fields.get("billing") or "").strip()
    if billing not in ("", "hourly", "fixed"):
        raise ProjectInputError("invalid_billing")
    currency = str(fields.get("currency") or "").strip().upper()
    if currency and not _CURRENCY.match(currency):
        raise ProjectInputError("invalid_currency")
    return {
        "display_name": str(fields.get("name") or "").strip() or None,
        "client": str(fields.get("client") or "").strip() or None,
        "billing": billing or None, "rate": _amount(fields.get("rate")), "fixed_price": _amount(fields.get("fixed_price")),
        "currency": currency or None,
    }


def valid_period(period: str) -> str:
    if not _PERIOD.match(period):
        raise ProjectInputError("invalid_period")
    return period


def valid_hours(raw: object) -> Decimal:
    hours = _amount(raw)
    if hours is None:
        raise ProjectInputError("invalid_amount")
    return hours
