"""Unit tests for the pure presentation helpers of the HTML report (Track 11C).

Covers money formatting (NFR-04, BR-01/02/04), durations, tokens, percentiles (SM-05),
safe JSON embedding and the compact labels used on chart caps and axis ticks.
"""

from __future__ import annotations

import json
import statistics
from decimal import Decimal

import duckdb
import pytest

from agent_meter.report.fmt import (
    currency_decimals,
    esc,
    format_cost,
    format_cost_compact,
    format_currency,
    format_duration_ms,
    format_duration_tick,
    format_int,
    format_multiplier,
    format_percent,
    format_token_average,
    format_tokens,
    format_usd,
    format_usd_compact,
    host_label,
    script_json,
    unpriced_note,
)
from agent_meter.report.stats import latency_stats, percentile_cont
from agent_meter.report.values import CostTotal, DisplayCurrency

# --------------------------------------------------------------------------- money


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("0"), "$0.00"),
        (Decimal("4.1"), "$4.10"),
        (Decimal("0.005"), "$0.01"),
        (Decimal("0.004999"), "$0.00"),
        (Decimal("1234567.891"), "$1,234,567.89"),
    ],
)
def test_format_usd_rounds_half_up_to_cents(amount: Decimal, expected: str) -> None:
    # Arrange / Act
    text = format_usd(amount)

    # Assert
    assert text == expected


def test_format_currency_uses_zero_decimals_for_cop_and_two_otherwise() -> None:
    # Arrange
    cop = Decimal("171380.4")
    eur = Decimal("12.345")

    # Act
    cop_text = format_currency(cop, "COP")
    eur_text = format_currency(eur, "EUR")
    usd_text = format_currency(Decimal("3"), "USD")

    # Assert
    assert cop_text == "COP 171,380"
    assert eur_text == "EUR 12.35"
    assert usd_text == "$3.00"
    assert currency_decimals("cop") == 0
    assert currency_decimals("EUR") == 2


def test_format_cost_priced_total_is_approximate() -> None:
    # Arrange
    total = CostTotal(cost_usd=Decimal("4.1"))

    # Act
    text = format_cost(total)

    # Assert
    assert text == "≈ $4.10"


def test_format_cost_with_unpriced_calls_is_a_lower_bound() -> None:
    # Arrange
    total = CostTotal(cost_usd=Decimal("4.1"), unpriced_calls=312)

    # Act
    text = format_cost(total)
    note = unpriced_note(total)

    # Assert
    assert text == "≥ $4.10"
    assert note == "(312 calls unpriced)"


def test_unpriced_note_lists_models_when_given() -> None:
    # Arrange
    total = CostTotal(cost_usd=Decimal("4.1"), unpriced_calls=312)

    # Act
    note = unpriced_note(total, ("gemini-x", "gemini-y"))

    # Assert
    assert note == "(312 calls unpriced: gemini-x, gemini-y)"


def test_format_cost_with_only_unpriced_calls_never_reads_as_zero_cost() -> None:
    # Arrange
    total = CostTotal(cost_usd=None, unpriced_calls=1)

    # Act
    text = format_cost(total)

    # Assert
    assert text == "≥ $0.00"
    assert unpriced_note(total) == "(1 call unpriced)"


def test_format_cost_without_calls_is_a_dash() -> None:
    # Arrange
    total = CostTotal(cost_usd=None)

    # Act / Assert
    assert format_cost(total) == "—"
    assert unpriced_note(total) == ""


@pytest.mark.parametrize(
    "total",
    [
        CostTotal(cost_usd=Decimal("1.2"), estimated_calls=3),
        CostTotal(cost_usd=Decimal("1.2"), inferred_calls=1),
    ],
)
def test_format_cost_marks_estimated_or_inferred_with_asterisk(
    total: CostTotal,
) -> None:
    # Act
    text = format_cost(total)

    # Assert
    assert text == "≈ $1.20*"


def test_format_cost_appends_display_currency_conversion() -> None:
    # Arrange
    total = CostTotal(cost_usd=Decimal("41.80"))
    display = DisplayCurrency(code="COP", usd_rate=Decimal("4100"))

    # Act
    text = format_cost(total, display)

    # Assert
    assert text == "≈ $41.80 (COP 171,380)"


def test_cost_total_combines_and_reports_flags() -> None:
    # Arrange
    first = CostTotal(cost_usd=Decimal("1.5"), unpriced_calls=1)
    second = CostTotal(cost_usd=None, estimated_calls=2, inferred_calls=1)

    # Act
    combined = first + second

    # Assert
    assert combined == CostTotal(
        cost_usd=Decimal("1.5"), unpriced_calls=1, estimated_calls=2, inferred_calls=1
    )
    assert combined.partial is True
    assert combined.flagged is True
    assert CostTotal(cost_usd=None) + CostTotal(cost_usd=None) == CostTotal(None)


def test_display_currency_rejects_non_positive_rate() -> None:
    # Act / Assert
    with pytest.raises(ValueError, match="usd_rate"):
        DisplayCurrency(code="COP", usd_rate=Decimal("0"))


# --------------------------------------------------------------------- durations


@pytest.mark.parametrize(
    ("ms", "expected"),
    [
        (None, "—"),
        (0, "0.0s"),
        (4_240, "4.2s"),
        (35_000, "35s"),
        (59_600, "1m 00s"),
        (782_000, "13m 02s"),
        (3_900_000, "1h 05m"),
        (Decimal("12345.6"), "12s"),
    ],
)
def test_format_duration_ms(ms: int | Decimal | None, expected: str) -> None:
    # Act / Assert
    assert format_duration_ms(ms) == expected


@pytest.mark.parametrize(
    ("tokens", "expected"),
    [
        (None, "—"),
        (850, "850"),
        (9_800, "9.8K"),
        (85_000, "85K"),
        (1_210_000, "1.21M"),
        (999_999, "1.00M"),
    ],
)
def test_format_tokens(tokens: int | None, expected: str) -> None:
    # Act / Assert
    assert format_tokens(tokens) == expected


def test_format_token_average_rounds_to_whole_tokens() -> None:
    # Act / Assert
    assert format_token_average(Decimal("849.5")) == "850"
    assert format_token_average(Decimal("10000")) == "10K"
    assert format_token_average(None) == "—"


def test_format_int_percent_and_multiplier() -> None:
    # Act / Assert
    assert format_int(1234567) == "1,234,567"
    assert format_int(None) == "—"
    assert format_percent(Decimal("0.8912")) == "89.1%"
    assert format_percent(None) == "—"
    assert format_multiplier(Decimal("2.6666")) == "2.7x"
    assert format_multiplier(None) == "—"


def test_host_label_maps_known_hosts_and_passes_unknown_through() -> None:
    # Act / Assert
    assert host_label("claude-code") == "Claude Code"
    assert host_label("antigravity-cli") == "Antigravity CLI"
    assert host_label("antigravity-ide") == "Antigravity IDE"
    assert host_label("antigravity-app") == "Antigravity App"
    assert host_label("future-host") == "future-host"


# ---------------------------------------------------------------------- escaping


def test_esc_escapes_markup_and_quotes() -> None:
    # Act
    text = esc('<b>"Tom\'s" & co</b>')

    # Assert
    assert text == "&lt;b&gt;&quot;Tom&#x27;s&quot; &amp; co&lt;/b&gt;"


def test_script_json_escapes_angle_brackets_and_ampersand() -> None:
    # Arrange
    payload = {"name": "</script><script>alert(1)</script>", "amp": "a&b"}

    # Act
    text = script_json(payload)

    # Assert
    assert "<" not in text
    assert ">" not in text
    assert "&" not in text
    assert json.loads(text) == payload


# -------------------------------------------------------------------- percentiles


LATENCIES = [
    1_200,
    95_000,
    3_400,
    18_250,
    7_700,
    61_000,
    2_050,
    44_444,
    12_000,
    9_999,
    30_303,
    5_500,
    150_000,
    8_800,
    21_000,
    4_321,
    77_777,
    16_000,
    2_222,
    39_000,
]


@pytest.mark.parametrize("percent", [50, 95, 99])
def test_percentile_cont_matches_python_reference(percent: int) -> None:
    # Arrange
    reference = statistics.quantiles(LATENCIES, n=100, method="inclusive")[percent - 1]

    # Act
    value = percentile_cont(LATENCIES, Decimal(percent) / 100)

    # Assert
    assert value is not None
    assert float(value) == pytest.approx(reference, abs=1e-9)


@pytest.mark.parametrize("percent", [50, 95, 99])
def test_percentile_cont_matches_duckdb_quantile_cont(percent: int) -> None:
    # Arrange
    connection = duckdb.connect(":memory:")
    connection.execute("CREATE TABLE t (v BIGINT)")
    connection.executemany("INSERT INTO t VALUES (?)", [(v,) for v in LATENCIES])
    row = connection.execute(
        f"SELECT quantile_cont(v, {percent / 100}) FROM t"
    ).fetchone()
    connection.close()
    assert row is not None

    # Act
    value = percentile_cont(LATENCIES, Decimal(percent) / 100)

    # Assert
    assert value is not None
    assert float(value) == pytest.approx(float(row[0]), abs=1e-6)


def test_percentile_cont_edge_cases() -> None:
    # Act / Assert
    assert percentile_cont([], Decimal("0.5")) is None
    assert percentile_cont([42], Decimal("0.99")) == Decimal(42)
    assert percentile_cont([10, 20], Decimal("0.5")) == Decimal(15)
    assert percentile_cont([30, 10, 20], Decimal("0")) == Decimal(10)
    assert percentile_cont([30, 10, 20], Decimal("1")) == Decimal(30)
    with pytest.raises(ValueError, match="fraction"):
        percentile_cont([1, 2], Decimal("1.5"))


def test_latency_stats_counts_tasks_and_computes_three_percentiles() -> None:
    # Act
    stats = latency_stats([100, 200, 300, 400])

    # Assert
    assert stats.tasks == 4
    assert stats.p50 == Decimal("250")
    assert stats.p95 == Decimal("385")
    assert stats.p99 == Decimal("397")
    assert latency_stats([]).p50 is None


# ------------------------------------------------------------- compact chart labels


@pytest.mark.parametrize(
    ("amount", "expected"),
    [
        (Decimal("0"), "$0"),
        (Decimal("0.015"), "$0.02"),
        (Decimal("4.1"), "$4.10"),
        (Decimal("99.994"), "$99.99"),
        (Decimal("123.4"), "$123"),
        (Decimal("1234"), "$1.2K"),
        (Decimal("12500"), "$13K"),
        (Decimal("2500000"), "$2.5M"),
    ],
)
def test_format_usd_compact_shortens_large_amounts(
    amount: Decimal, expected: str
) -> None:
    # Act / Assert
    assert format_usd_compact(amount) == expected


@pytest.mark.parametrize(
    ("total", "expected"),
    [
        (CostTotal(cost_usd=Decimal("1234")), "≈ $1.2K"),
        (CostTotal(cost_usd=Decimal("4.1"), unpriced_calls=3), "≥ $4.10"),
        (CostTotal(cost_usd=None, unpriced_calls=3), "≥ $0"),
        (CostTotal(cost_usd=Decimal("12.5"), estimated_calls=1), "≈ $12.50*"),
        (CostTotal(cost_usd=None), "—"),
    ],
)
def test_format_cost_compact_keeps_lower_bound_and_flag_markers(
    total: CostTotal, expected: str
) -> None:
    # Act / Assert
    assert format_cost_compact(total) == expected


@pytest.mark.parametrize(
    ("ms", "expected"),
    [
        (Decimal(0), "0"),
        (Decimal(15_000), "15s"),
        (Decimal(120_000), "2m"),
        (Decimal(90_000), "1m 30s"),
        (Decimal(3_600_000), "1h"),
        (Decimal(5_400_000), "1h 30m"),
    ],
)
def test_format_duration_tick_uses_whole_units(ms: Decimal, expected: str) -> None:
    # Act / Assert
    assert format_duration_tick(ms) == expected
