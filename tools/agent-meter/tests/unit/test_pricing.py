"""Tests for ``agent_meter.pricing`` (ADR §3.8, contracts §3.4/§5; PC-01..05, PC-07, PC-09)."""

from __future__ import annotations

import textwrap
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from agent_meter.pricing import (
    SHIPPED_PATH,
    Alias,
    PriceResolution,
    PriceRow,
    PricingError,
    PricingTable,
    add_local_alias,
    add_local_price,
    cost_usd,
    load_pricing,
    remove_local,
    resolve_price,
    validate_file,
)

SHIPPED_DOC = """\
version: 1
models:
  claude-opus-5-5:
    source_url: https://platform.claude.com/docs/en/about-claude/pricing
    fetched_at: 2026-10-16
    windows:
      - effective_from: 2000-01-01
        tiers:
          - {min_prompt_tokens: 0, input: "4.00", cache_write_5m: "5.00", cache_write_1h: "8.00", cache_read: "0.20", output: "20.00"}
  claude-haiku-5-5:
    windows:
      - effective_from: 2000-01-01
        tiers:
          - {min_prompt_tokens: 0, input: "0.10", cache_write_5m: "0.125", cache_write_1h: "0.20", cache_read: "0.01", output: "0.50"}
          - {min_prompt_tokens: 100001, input: "0.50", cache_write_5m: "0.625", cache_write_1h: "1.00", cache_read: "0.05", output: "2.50"}
  claude-haiku-4-5:
    windows:
      - {effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "1.00", cache_write_5m: "1.25", cache_write_1h: "2.00", cache_read: "0.10", output: "5.00"}]}
  gemini-4-argon:
    source_url: https://ai.google.dev/gemini-api/docs/pricing
    fetched_at: 2026-10-16
    windows:
      - {effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "2.00", cache_read: "0.10", output: "10.00"}]}
      - {effective_from: 2026-12-01, tiers: [{min_prompt_tokens: 0, input: "4.00", cache_read: "0.20", output: "20.00"}]}
  gemini-3.8-flash:
    windows:
      - {effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "0.75", cache_read: "0.075", output: "3.75"}]}
aliases:
  claude-haiku-4-5-20251001: {model: claude-haiku-4-5}
  gemini-3.8-flash-n: {model: gemini-3.8-flash, estimated: true}
"""


@pytest.fixture()
def shipped(tmp_path: Path) -> Path:
    path = tmp_path / "pricing.yaml"
    path.write_text(SHIPPED_DOC, encoding="utf-8")
    return path


@pytest.fixture()
def table(shipped: Path) -> PricingTable:
    return load_pricing(None, shipped)


def write(path: Path, text: str) -> Path:
    path.write_text(textwrap.dedent(text), encoding="utf-8")
    return path


def resolve(
    table: PricingTable, model: str | None, at: date, prompt: int = 0, **kw: object
) -> PriceResolution:
    return resolve_price(table, model, at, prompt, **kw)  # type: ignore[arg-type]


def cost(
    res: PriceResolution,
    i: int | None = 0,
    o: int | None = 0,
    w5: int | None = 0,
    w1: int | None = 0,
    r: int | None = 0,
) -> Decimal | None:
    return cost_usd(
        res,
        input_tokens=i,
        output_tokens=o,
        cache_write_5m_tokens=w5,
        cache_write_1h_tokens=w1,
        cache_read_tokens=r,
    )


# --- shipped table --------------------------------------------------------------------


def test_real_shipped_pricing_yaml_is_valid_and_matches_sources() -> None:
    assert validate_file(SHIPPED_PATH) == []
    real = load_pricing(None)

    opus = resolve(real, "claude-opus-5-5", date(2026, 10, 16))
    haiku_big = resolve(real, "claude-haiku-5-5", date(2026, 10, 16), 100_001)
    argon_late = resolve(real, "gemini-4-argon", date(2026, 12, 1))
    flash_2027 = resolve(real, "gemini-3.8-flash", date(2027, 1, 1))

    assert opus.row is not None and (opus.row.input, opus.row.output) == (
        Decimal("4.00"),
        Decimal("20.00"),
    )
    assert opus.row.source == "shipped" and opus.row.source_url is not None
    assert haiku_big.row is not None and haiku_big.row.input == Decimal("0.50")
    assert argon_late.row is not None and argon_late.row.input == Decimal("4.00")
    assert flash_2027.row is not None and flash_2027.row.cache_read == Decimal("0.15")
    alias = resolve(real, "claude-haiku-4-5-20251001", date(2026, 10, 16))
    assert alias.priced_model == "claude-haiku-4-5" and alias.estimated is False


@pytest.mark.parametrize(
    ("model", "priced_as"),
    [
        ("gemini-3.7-flash", "gemini-3.8-flash"),
        ("gemini-default", "gemini-3.8-flash"),
        ("agy-demo-high", "gemini-3.8-flash"),
        ("gemini-pro-default", "gemini-3.1-pro-preview"),
        ("claude-opus-4-6-thinking", "claude-opus-4-6"),
    ],
)
def test_antigravity_internal_ids_are_priced_as_estimated(model: str, priced_as: str) -> None:
    # Arrange
    real = load_pricing(None)

    # Act
    res = resolve(real, model, date(2026, 10, 16))

    # Assert
    assert res.priced_model == priced_as and res.row is not None and res.estimated is True


# --- PC-01 windows ----------------------------------------------------------------------


def test_price_window_boundary_on_exact_change_date(table: PricingTable) -> None:
    before = resolve(table, "gemini-4-argon", date(2026, 11, 30))
    on_change = resolve(table, "gemini-4-argon", date(2026, 12, 1))

    assert before.row is not None and before.row.input == Decimal("2.00")
    assert on_change.row is not None and on_change.row.input == Decimal("4.00")


def test_date_before_first_window_is_unpriced(shipped: Path, tmp_path: Path) -> None:
    local = write(
        tmp_path / "local.yaml",
        """\
        version: 1
        models:
          late-model:
            windows:
              - {effective_from: 2026-06-01, tiers: [{min_prompt_tokens: 0, input: "1", cache_read: "0.1", output: "2"}]}
        """,
    )
    table = load_pricing(local, shipped)

    assert resolve(table, "late-model", date(2026, 5, 31)).row is None
    assert resolve(table, "late-model", date(2026, 6, 1)).row is not None


# --- PC-02 cache writes / PC-05 Decimal --------------------------------------------------------


def test_cache_write_5m_and_1h_priced_separately(table: PricingTable) -> None:
    res = resolve(table, "claude-opus-5-5", date(2026, 10, 16))

    assert cost(res, w5=1_000_000) == Decimal("5.000000000")
    assert cost(res, w1=1_000_000) == Decimal("8.000000000")


def test_cost_formula_is_exact_decimal_quantized_to_nine_places(
    table: PricingTable,
) -> None:
    res = resolve(table, "claude-opus-5-5", date(2026, 10, 16))

    value = cost(res, i=1_234, o=567, w5=89, w1=10, r=98_765)

    expected = (
        Decimal(1_234) * 4
        + Decimal(567) * 20
        + Decimal(89) * 5
        + Decimal(10) * 8
        + Decimal(98_765) * Decimal("0.20")
    ) / Decimal(1_000_000)
    assert value == expected.quantize(Decimal("1e-9"))
    assert isinstance(value, Decimal) and value.as_tuple().exponent == -9


def test_cost_rounds_half_up(shipped: Path, tmp_path: Path) -> None:
    local = write(
        tmp_path / "local.yaml",
        """\
        version: 1
        models:
          tiny:
            windows:
              - {effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "0.0005", cache_read: "0", output: "0"}]}
        """,
    )
    res = resolve(load_pricing(local, shipped), "tiny", date(2026, 1, 1))

    assert cost(res, i=1) == Decimal("0.000000001")  # 0.0000000005 → half-up


def test_missing_cache_write_price_uses_input_price(table: PricingTable) -> None:
    res = resolve(table, "gemini-3.8-flash", date(2026, 10, 16))

    assert cost(res, w5=1_000_000, w1=1_000_000) == Decimal("1.500000000")


# --- tiers (Haiku 5.5 prompt length) ------------------------------------------------------------


@pytest.mark.parametrize(
    ("prompt", "expected_input"), [(0, "0.10"), (100_000, "0.10"), (100_001, "0.50")]
)
def test_haiku_55_prompt_length_tier(
    table: PricingTable, prompt: int, expected_input: str
) -> None:
    res = resolve(table, "claude-haiku-5-5", date(2026, 10, 16), prompt)

    assert res.row is not None and res.row.input == Decimal(expected_input)


# --- PC-03 unpriced / inferred ------------------------------------------------------------------


def test_unknown_model_is_unpriced_with_null_cost(table: PricingTable) -> None:
    res = resolve(table, "gemini-x-unknown", date(2026, 10, 16))

    assert res == PriceResolution(
        priced_model=None, row=None, estimated=False, inferred=False
    )
    assert cost(res, i=10, o=10) is None


def test_unknown_token_count_gives_null_cost(table: PricingTable) -> None:
    res = resolve(table, "claude-opus-5-5", date(2026, 10, 16))

    assert cost(res, i=None) is None
    assert cost(res, r=None) is None


def test_missing_model_uses_default_model_and_flags_inferred(
    table: PricingTable,
) -> None:
    res = resolve(table, None, date(2026, 10, 16), default_model="gemini-3.8-flash")

    assert res.inferred is True and res.priced_model == "gemini-3.8-flash"
    assert resolve(table, None, date(2026, 10, 16)).row is None


# --- PC-04 Gemini and Claude models priced for Antigravity ----------------------------------------


def test_gemini_and_claude_models_both_priced(table: PricingTable) -> None:
    gemini = resolve(table, "gemini-3.8-flash", date(2026, 10, 16))
    claude = resolve(table, "claude-opus-5-5", date(2026, 10, 16))

    assert cost(gemini, i=1_000_000, o=1_000_000, r=1_000_000) == Decimal("4.575000000")
    assert cost(claude, i=1_000_000) == Decimal("4.000000000")


# --- PC-09 aliases ---------------------------------------------------------------------------------


def test_alias_resolves_to_model_then_window_and_propagates_estimated(
    table: PricingTable,
) -> None:
    exact = resolve(table, "claude-haiku-4-5-20251001", date(2026, 10, 16))
    estimated = resolve(table, "gemini-3.8-flash-n", date(2026, 10, 16))

    assert exact.priced_model == "claude-haiku-4-5" and exact.estimated is False
    assert estimated.priced_model == "gemini-3.8-flash" and estimated.estimated is True


def test_alias_chain_and_cycle_rejected(shipped: Path, tmp_path: Path) -> None:
    chain = write(
        tmp_path / "chain.yaml",
        """\
        version: 1
        aliases:
          my-alias: {model: claude-haiku-4-5-20251001}
        """,
    )
    cycle = write(
        tmp_path / "cycle.yaml",
        """\
        version: 1
        aliases:
          a-1: {model: b-1}
          b-1: {model: a-1}
        """,
    )

    chain_errors = validate_file_against(chain, shipped)
    cycle_errors = validate_file_against(cycle, shipped)

    assert any("alias" in e and "claude-haiku-4-5-20251001" in e for e in chain_errors)
    assert len(cycle_errors) >= 2
    with pytest.raises(PricingError):
        load_pricing(cycle, shipped)


def validate_file_against(path: Path, shipped: Path) -> list[str]:
    try:
        load_pricing(path, shipped)
    except PricingError as exc:
        return exc.errors
    return []


def test_alias_to_undefined_model_rejected(shipped: Path, tmp_path: Path) -> None:
    local = write(
        tmp_path / "local.yaml",
        """\
        version: 1
        aliases:
          foo: {model: does-not-exist}
        """,
    )

    with pytest.raises(PricingError) as excinfo:
        load_pricing(local, shipped)
    assert any("does-not-exist" in e for e in excinfo.value.errors)


# --- fast variant -----------------------------------------------------------------------------------


def test_fast_speed_uses_fast_row_when_present(shipped: Path, tmp_path: Path) -> None:
    local = write(
        tmp_path / "local.yaml",
        """\
        version: 1
        models:
          "claude-opus-5-5:fast":
            windows:
              - {effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "8.00", cache_read: "0.40", output: "40.00"}]}
        """,
    )
    table = load_pricing(local, shipped)

    res = resolve(table, "claude-opus-5-5", date(2026, 10, 16), speed="fast")

    assert res.priced_model == "claude-opus-5-5:fast" and res.estimated is False
    assert res.row is not None and res.row.output == Decimal("40.00")


def test_fast_speed_without_fast_row_falls_back_to_base_estimated(
    table: PricingTable,
) -> None:
    res = resolve(table, "claude-opus-5-5", date(2026, 10, 16), speed="fast")

    assert res.priced_model == "claude-opus-5-5" and res.estimated is True


# --- PC-07 local layer --------------------------------------------------------------------------------


def test_local_overrides_shipped_row_and_adds_model(
    shipped: Path, tmp_path: Path
) -> None:
    local = write(
        tmp_path / "local.yaml",
        """\
        version: 1
        models:
          claude-opus-5-5:
            windows:
              - {effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "3.00", cache_read: "0.30", output: "15.00"}]}
          brand-new:
            windows:
              - {effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "1", cache_read: "0.1", output: "2"}]}
        aliases:
          gemini-3.8-flash-n: {model: brand-new}
        """,
    )

    table = load_pricing(local, shipped)

    opus = resolve(table, "claude-opus-5-5", date(2026, 10, 16))
    assert (
        opus.row is not None
        and opus.row.input == Decimal("3.00")
        and opus.row.source == "local"
    )
    assert opus.row.cache_write_5m is None
    assert resolve(table, "brand-new", date(2026, 10, 16)).row is not None
    aliased = resolve(table, "gemini-3.8-flash-n", date(2026, 10, 16))
    assert aliased.priced_model == "brand-new" and aliased.estimated is False
    assert len([r for r in table.rows if r.model == "claude-opus-5-5"]) == 1


@pytest.mark.parametrize(
    ("body", "fragment"),
    [
        (
            'version: 1\nmodels: {m: {windows: [{effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "-1", cache_read: "0", output: "1"}]}]}}\n',
            "negative",
        ),
        (
            'version: 1\nmodels: {m: {windows: [{effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "1", output: "1"}]}]}}\n',
            "cache_read",
        ),
        (
            'version: 1\nmodels: {m: {windows: [{effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: 1.5, cache_read: "0", output: "1"}]}]}}\n',
            "string",
        ),
        (
            'version: 1\nmodels: {m: {windows: [{effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 10, input: "1", cache_read: "0", output: "1"}]}]}}\n',
            "min_prompt_tokens: 0",
        ),
        (
            'version: 1\nmodels: {m: {windows: [{effective_from: not-a-date, tiers: [{min_prompt_tokens: 0, input: "1", cache_read: "0", output: "1"}]}]}}\n',
            "date",
        ),
        (
            'version: 1\nmodels: {m: {colour: red, windows: [{effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "1", cache_read: "0", output: "1"}]}]}}\n',
            "unknown key",
        ),
        ("version: 2\n", "version"),
        (
            'version: 1\nmodels: {m: {windows: [{effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "1", cache_read: "0", output: "1"}]}, {effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "2", cache_read: "0", output: "1"}]}]}}\n',
            "duplicate",
        ),
        (
            'version: 1\nmodels: {m: {windows: [{effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "abc", cache_read: "0", output: "1"}]}]}}\n',
            "decimal",
        ),
        ("version: 1\nmodels: [unclosed\n", "YAML"),
    ],
)
def test_validate_rejects_invalid_local_files_with_clear_error(
    tmp_path: Path, body: str, fragment: str
) -> None:
    path = tmp_path / "pricing.local.yaml"
    path.write_text(body, encoding="utf-8")

    errors = validate_file(path)

    assert errors, "expected validation errors"
    assert any(fragment in e for e in errors), errors


def test_invalid_local_keeps_previous_valid_table(
    shipped: Path, tmp_path: Path
) -> None:
    local = tmp_path / "local.yaml"
    previous = load_pricing(None, shipped)
    local.write_text("version: 1\nmodels: {m: {windows: []}}\n", encoding="utf-8")

    with pytest.raises(PricingError) as excinfo:
        load_pricing(local, shipped)

    current = previous  # caller keeps the last valid table on PricingError
    assert excinfo.value.errors and str(excinfo.value)
    assert resolve(current, "claude-opus-5-5", date(2026, 10, 16)).row is not None


def test_missing_local_file_means_shipped_only(shipped: Path, tmp_path: Path) -> None:
    table = load_pricing(tmp_path / "absent.yaml", shipped)

    assert {r.source for r in table.rows} == {"shipped"}
    assert all(isinstance(a, Alias) for a in table.aliases)


# --- local writers -----------------------------------------------------------------------------------


def make_row(model: str, **kw: object) -> PriceRow:
    values: dict[str, object] = {
        "model": model,
        "effective_from": date(2026, 1, 1),
        "min_prompt_tokens": 0,
        "input": Decimal("1.25"),
        "output": Decimal(5),
        "cache_write_5m": None,
        "cache_write_1h": None,
        "cache_read": Decimal("0.125"),
        "source": "local",
        "source_url": None,
        "fetched_at": None,
    }
    values.update(kw)
    return PriceRow(**values)  # type: ignore[arg-type]


def test_add_local_price_creates_file_and_round_trips(
    shipped: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    local = tmp_path / "home" / "pricing.local.yaml"
    local.parent.mkdir()

    add_local_price(local, make_row("gemini-3.7-flash"))

    raw = yaml.safe_load(local.read_text(encoding="utf-8"))
    tier = raw["models"]["gemini-3.7-flash"]["windows"][0]["tiers"][0]
    assert tier["input"] == "1.25" and isinstance(tier["input"], str)
    res = resolve(load_pricing(local, shipped), "gemini-3.7-flash", date(2026, 2, 1))
    assert (
        res.row is not None
        and res.row.input == Decimal("1.25")
        and res.row.source == "local"
    )


def test_add_local_price_duplicate_requires_replace(tmp_path: Path) -> None:
    local = tmp_path / "pricing.local.yaml"
    add_local_price(local, make_row("m1"))

    with pytest.raises(PricingError):
        add_local_price(local, make_row("m1", input=Decimal(9)))
    add_local_price(local, make_row("m1", input=Decimal(9)), replace=True)

    tier = yaml.safe_load(local.read_text())["models"]["m1"]["windows"][0]["tiers"][0]
    assert tier["input"] == "9"


def test_add_local_price_invalid_row_is_not_written(tmp_path: Path) -> None:
    local = tmp_path / "pricing.local.yaml"

    with pytest.raises(PricingError):
        add_local_price(local, make_row("m1", min_prompt_tokens=5))
    with pytest.raises(PricingError):
        add_local_price(local, make_row("m2", input=Decimal(-1)))

    assert not local.exists()


def test_add_local_alias_and_remove(shipped: Path, tmp_path: Path) -> None:
    local = tmp_path / "pricing.local.yaml"
    add_local_price(local, make_row("m1"))
    add_local_price(local, make_row("m1", effective_from=date(2026, 6, 1)))
    add_local_alias(local, "m1-alias", "m1", estimated=True)

    aliased = resolve(load_pricing(local, shipped), "m1-alias", date(2026, 7, 1))
    assert aliased.priced_model == "m1" and aliased.estimated is True

    assert remove_local(local, alias="m1-alias") == 1
    assert remove_local(local, model="m1", effective_from=date(2026, 6, 1)) == 1
    assert remove_local(local, model="m1") == 1
    assert remove_local(local, model="m1") == 0
    assert validate_file(local) == []


def test_add_local_alias_to_alias_rejected(tmp_path: Path) -> None:
    local = tmp_path / "pricing.local.yaml"

    with pytest.raises(PricingError):
        add_local_alias(local, "x", "claude-haiku-4-5-20251001", estimated=False)


def test_remove_local_refuses_to_leave_dangling_alias(tmp_path: Path) -> None:
    local = tmp_path / "pricing.local.yaml"
    add_local_price(local, make_row("m1"))
    add_local_alias(local, "m1-alias", "m1", estimated=False)

    with pytest.raises(PricingError):
        remove_local(local, model="m1")
    assert "m1" in yaml.safe_load(local.read_text())["models"]


def test_remove_local_on_missing_file_is_zero(tmp_path: Path) -> None:
    assert remove_local(tmp_path / "nope.yaml", model="x") == 0
