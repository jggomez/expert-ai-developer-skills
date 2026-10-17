"""Presentation formatting for the HTML report.

Every function returns *plain text*; callers HTML-escape it with :func:`esc` before
embedding. Money is ``Decimal`` end to end and is rounded only here (NFR-04).
"""

from __future__ import annotations

import html
import json
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import Final

from agent_meter.report.values import CostTotal, DisplayCurrency

__all__ = [
    "DASH",
    "currency_decimals",
    "esc",
    "format_amount",
    "format_cost",
    "format_cost_compact",
    "format_currency",
    "format_duration_ms",
    "format_duration_tick",
    "format_int",
    "format_multiplier",
    "format_percent",
    "format_token_average",
    "format_tokens",
    "format_usd",
    "format_usd_compact",
    "host_label",
    "script_json",
    "unpriced_note",
]

DASH: Final = "—"

_ZERO_DECIMAL_CURRENCIES: Final = frozenset(
    {"CLP", "COP", "ISK", "JPY", "KRW", "PYG", "UGX", "VND"}
)

_HOST_LABELS: Final = {
    "claude-code": "Claude Code",
    "antigravity-cli": "Antigravity CLI",
    "antigravity-ide": "Antigravity IDE",
    "antigravity-app": "Antigravity App",
}

_JSON_ESCAPES: Final = {ord("<"): "\\u003c", ord(">"): "\\u003e", ord("&"): "\\u0026"}


def esc(value: object) -> str:
    """HTML-escape any value for element content or a quoted attribute."""
    return html.escape(str(value), quote=True)


def host_label(host: str) -> str:
    return _HOST_LABELS.get(host, host)


def _quantize(value: Decimal, decimals: int) -> Decimal:
    return value.quantize(Decimal(1).scaleb(-decimals), rounding=ROUND_HALF_UP)


def format_amount(amount: Decimal, decimals: int) -> str:
    """Thousands-separated amount rounded half-up to ``decimals`` places."""
    return f"{_quantize(amount, decimals):,.{decimals}f}"


def currency_decimals(code: str) -> int:
    return 0 if code.upper() in _ZERO_DECIMAL_CURRENCIES else 2


def format_usd(amount: Decimal) -> str:
    return f"${format_amount(amount, 2)}"


def format_currency(amount: Decimal, code: str) -> str:
    normalized = code.upper()
    if normalized == "USD":
        return format_usd(amount)
    return f"{normalized} {format_amount(amount, currency_decimals(normalized))}"


def format_usd_compact(amount: Decimal) -> str:
    """Short USD for chart caps: ``$4.10``, ``$123``, ``$1.2K``, ``$13K``, ``$2.5M``."""
    sign = "-" if amount < 0 else ""
    value = abs(amount)
    if value == 0:
        return "$0"
    if value < 100:
        text = format_amount(value, 2)
    elif value < Decimal("999.5"):
        text = format_amount(value, 0)
    elif value < 9_950:
        text = f"{_quantize(value / 1_000, 1)}K"
    elif value < 999_500:
        text = f"{_quantize(value / 1_000, 0)}K"
    else:
        text = f"{_quantize(value / 1_000_000, 1)}M"
    return f"{sign}${text}"


def _cost_marks(total: CostTotal) -> tuple[str, Decimal, str] | None:
    """``(prefix, amount, marker)`` for a cost, or ``None`` when there is nothing to show."""
    if total.cost_usd is None and not total.partial:
        return None
    amount = total.cost_usd if total.cost_usd is not None else Decimal(0)
    prefix = "≥ " if total.partial else "≈ "
    marker = "*" if total.flagged else ""
    return prefix, amount, marker


def format_cost(total: CostTotal, display: DisplayCurrency | None = None) -> str:
    """``≈ $4.10``, ``≥ $4.10`` when partial (BR-02), ``*`` when flagged (BR-04)."""
    marks = _cost_marks(total)
    if marks is None:
        return DASH
    prefix, amount, marker = marks
    text = f"{prefix}{format_usd(amount)}{marker}"
    if display is not None:
        text += f" ({format_currency(display.convert(amount), display.code)})"
    return text


def format_cost_compact(total: CostTotal) -> str:
    """:func:`format_cost` with a compact amount (``≈ $1.2K``), keeping ``≥`` and ``*``."""
    marks = _cost_marks(total)
    if marks is None:
        return DASH
    prefix, amount, marker = marks
    return f"{prefix}{format_usd_compact(amount)}{marker}"


def unpriced_note(total: CostTotal, models: Sequence[str] = ()) -> str:
    """``(312 calls unpriced)`` or ``(312 calls unpriced: gemini-x)``; empty if priced."""
    if not total.partial:
        return ""
    noun = "call" if total.unpriced_calls == 1 else "calls"
    suffix = f": {', '.join(models)}" if models else ""
    return f"({total.unpriced_calls:,} {noun} unpriced{suffix})"


def format_duration_ms(ms: int | Decimal | None) -> str:
    """``4.2s`` under 10 s, ``35s``, ``13m 02s``, ``1h 05m``."""
    if ms is None:
        return DASH
    seconds = Decimal(ms) / 1000
    if seconds < 10:
        rounded = _quantize(seconds, 1)
        if rounded < 10:
            return f"{rounded}s"
    total = int(_quantize(seconds, 0))
    if total < 60:
        return f"{total}s"
    if total < 3600:
        minutes, secs = divmod(total, 60)
        return f"{minutes}m {secs:02d}s"
    hours, rest = divmod(total, 3600)
    return f"{hours}h {rest // 60:02d}m"


def format_duration_tick(ms: Decimal) -> str:
    """Axis tick for a duration in whole units: ``0``, ``15s``, ``2m``, ``1m 30s``, ``1h 30m``."""
    total = int(_quantize(Decimal(ms) / 1000, 0))
    if total == 0:
        return "0"
    if total < 60:
        return f"{total}s"
    if total < 3600:
        minutes, secs = divmod(total, 60)
        return f"{minutes}m" if secs == 0 else f"{minutes}m {secs}s"
    hours, rest = divmod(total, 3600)
    minutes = rest // 60
    return f"{hours}h" if minutes == 0 else f"{hours}h {minutes}m"


def format_tokens(tokens: int | None) -> str:
    """Compact token counts: ``850``, ``9.8K``, ``85K``, ``1.21M``."""
    if tokens is None:
        return DASH
    value = Decimal(tokens)
    if abs(tokens) >= 999_500:
        return f"{_quantize(value / 1_000_000, 2)}M"
    if abs(tokens) >= 9_950:
        return f"{_quantize(value / 1_000, 0)}K"
    if abs(tokens) >= 1_000:
        return f"{_quantize(value / 1_000, 1)}K"
    return str(tokens)


def format_token_average(value: Decimal | None) -> str:
    """A mean token count (e.g. context per call), rounded to whole tokens."""
    if value is None:
        return DASH
    return format_tokens(int(value.to_integral_value(rounding=ROUND_HALF_UP)))


def format_int(value: int | None) -> str:
    return DASH if value is None else f"{value:,}"


def format_percent(ratio: Decimal | None) -> str:
    return DASH if ratio is None else f"{_quantize(ratio * 100, 1)}%"


def format_multiplier(value: Decimal | None) -> str:
    return DASH if value is None else f"{_quantize(value, 1)}x"


def script_json(payload: object) -> str:
    """JSON safe to place inside ``<script type="application/json">`` (ADR §3.12)."""
    text = json.dumps(payload, sort_keys=True, default=str, ensure_ascii=False)
    return text.translate(_JSON_ESCAPES)
