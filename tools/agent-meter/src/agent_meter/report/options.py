"""``ReportOptions`` (contracts.md §3.10): the CLI filters and display settings."""

from __future__ import annotations

import calendar
import re
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Final

from agent_meter.report.values import DisplayCurrency

__all__ = ["ReportOptions"]

_MONTH_RE: Final = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True, slots=True)
class ReportOptions:
    """Filters and presentation settings for one report build.

    ``month`` and ``date_from``/``date_to`` are mutually exclusive. ``show_task_labels``
    is accepted for contract compatibility but the report never renders labels (BR-16).
    """

    date_from: date | None = None
    date_to: date | None = None
    month: str | None = None  # "YYYY-MM"
    project_id: str | None = None
    client: str | None = None
    display_currency: str | None = None
    usd_rate: Decimal | None = None
    generated_at: datetime = field(default_factory=_utc_now)
    show_task_labels: bool = False

    def __post_init__(self) -> None:
        if self.month is not None and _MONTH_RE.fullmatch(self.month) is None:
            raise ValueError(f"month must be YYYY-MM, got {self.month!r}")
        if self.month is not None and (
            self.date_from is not None or self.date_to is not None
        ):
            raise ValueError("month cannot be combined with date_from/date_to")
        if (
            self.date_from is not None
            and self.date_to is not None
            and self.date_from > self.date_to
        ):
            raise ValueError(
                f"date_from {self.date_from} is after date_to {self.date_to}"
            )
        if self.usd_rate is not None and self.usd_rate <= 0:
            raise ValueError(f"usd_rate must be positive, got {self.usd_rate}")
        if self.generated_at.tzinfo is None or self.generated_at.utcoffset() is None:
            raise ValueError("generated_at must be timezone-aware")

    def date_range(self) -> tuple[date | None, date | None]:
        """Inclusive local-date bounds; a month becomes its first and last day."""
        if self.month is None:
            return self.date_from, self.date_to
        year, month = (int(part) for part in self.month.split("-"))
        last_day = calendar.monthrange(year, month)[1]
        return date(year, month, 1), date(year, month, last_day)

    def month_range(self) -> tuple[str | None, str | None]:
        """Inclusive ``YYYY-MM`` bounds of the months the date range touches."""
        start, end = self.date_range()
        return (
            start.strftime("%Y-%m") if start is not None else None,
            end.strftime("%Y-%m") if end is not None else None,
        )

    def display(self) -> DisplayCurrency | None:
        """The secondary currency to show, or ``None`` when USD only."""
        if self.display_currency is None or self.usd_rate is None:
            return None
        if self.display_currency.upper() == "USD":
            return None
        return DisplayCurrency(
            code=self.display_currency.upper(), usd_rate=self.usd_rate
        )

    def filters_payload(self) -> dict[str, str | None]:
        start, end = self.date_range()
        return {
            "client": self.client,
            "date_from": start.isoformat() if start is not None else None,
            "date_to": end.isoformat() if end is not None else None,
            "month": self.month,
            "project_id": self.project_id,
        }

    @property
    def generated_at_utc(self) -> datetime:
        return self.generated_at.astimezone(UTC)
