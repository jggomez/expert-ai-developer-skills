"""Small value objects shared by the report loader, formatter and renderer."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

__all__ = ["CostTotal", "DisplayCurrency"]


@dataclass(frozen=True, slots=True)
class CostTotal:
    """An API-equivalent cost aggregate, always paired with its quality counters.

    ``cost_usd`` is the exact ``Decimal`` sum over priced calls (``None`` when nothing
    in the aggregate is priced). It is never rounded here: rounding happens only when
    the value is formatted for display (NFR-04).
    """

    cost_usd: Decimal | None
    unpriced_calls: int = 0
    estimated_calls: int = 0
    inferred_calls: int = 0

    @property
    def partial(self) -> bool:
        """True when unpriced calls make the cost a lower bound (BR-02)."""
        return self.unpriced_calls > 0

    @property
    def flagged(self) -> bool:
        """True when an estimated price or an inferred model contributes (BR-04)."""
        return self.estimated_calls > 0 or self.inferred_calls > 0

    def __add__(self, other: CostTotal) -> CostTotal:
        if self.cost_usd is None:
            cost = other.cost_usd
        elif other.cost_usd is None:
            cost = self.cost_usd
        else:
            cost = self.cost_usd + other.cost_usd
        return CostTotal(
            cost_usd=cost,
            unpriced_calls=self.unpriced_calls + other.unpriced_calls,
            estimated_calls=self.estimated_calls + other.estimated_calls,
            inferred_calls=self.inferred_calls + other.inferred_calls,
        )


@dataclass(frozen=True, slots=True)
class DisplayCurrency:
    """A secondary display currency: ``usd_rate`` display units per 1 USD (BR-10)."""

    code: str
    usd_rate: Decimal

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("display currency code must not be empty")
        if self.usd_rate <= 0:
            raise ValueError(f"usd_rate must be positive, got {self.usd_rate}")

    def convert(self, amount_usd: Decimal) -> Decimal:
        return amount_usd * self.usd_rate
