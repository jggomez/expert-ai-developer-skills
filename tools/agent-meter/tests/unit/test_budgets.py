"""Budgets, forecast, plan value and one-time alerts (Phase 3)."""

from __future__ import annotations

from calendar import monthrange
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from agent_meter import notify as notifier
from agent_meter.budgets import (
    budget_document,
    budget_status,
    due_alerts,
    render_budget,
    send_alerts,
)
from agent_meter.config import (
    BudgetConfig,
    Config,
    get_key,
    load_config,
    save_config,
    set_key,
)
from agent_meter.paths import AppHome
from agent_meter.pricing import load_pricing
from agent_meter.project_resolver import ProjectsConfig
from agent_meter.store import Store
from tests.fixtures.records import make_batch, make_call, make_project, ts

DAY = ts(0).date()
PID = "git:0123456789abcdef"


def dollars(amount: int) -> dict[str, object]:
    return {"input_tokens": amount * 500_000, "output_tokens": 0, "cache_read_tokens": 0,
            "cache_write_5m_tokens": 0, "cache_write_1h_tokens": 0, "model": "claude-sonnet-5-5"}


@pytest.fixture()
def home(tmp_path: Path) -> AppHome:
    return AppHome.resolve(str(tmp_path / "h"))


@pytest.fixture()
def store(home: AppHome) -> Iterator[Store]:
    with Store.open(home, read_only=False, lock_timeout_s=1.0) as opened:
        opened.migrate()
        opened.load_reference_data(
            pricing=load_pricing(None), host_defaults={},
            projects=ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={}),
            project_refs=[make_project()], settings={"timezone": "UTC"},
        )
        opened.apply_batches([make_batch(calls=(
            make_call(call_id="today", ts=ts(0), **dollars(90)),
            make_call(call_id="yesterday", ts=ts(0) - timedelta(days=1), **dollars(5)),
        ))])
        yield opened


def test_budget_lines_report_level_and_percent(store: Store) -> None:
    budget = BudgetConfig(daily_usd=Decimal(80), monthly_usd=Decimal(1000), projects={PID: Decimal(100)})

    status = budget_status(store, budget, DAY)

    assert [(line.key, line.level) for line in status.lines] == [
        ("day:all", "over"), ("month:all", "ok"), (f"month:{PID}", "warn"),
    ]
    assert status.lines[2].spent_usd == Decimal(95)


def test_forecast_formula_on_a_fixed_day(store: Store) -> None:
    status = budget_status(store, BudgetConfig(), DAY)
    expected = Decimal(95) + Decimal(95) / 7 * (monthrange(DAY.year, DAY.month)[1] - DAY.day)

    assert status.today_usd == Decimal(90)
    assert status.forecast_usd == expected


def test_plan_value_compares_usage_with_the_declared_price(store: Store) -> None:
    status = budget_status(store, BudgetConfig(plan_monthly_usd=Decimal(19)), DAY)

    assert budget_document(status)["plan_value_ratio"] == "5.0"
    assert "(5.0x)" in render_budget(status)


def test_each_alert_fires_once_per_period(store: Store, monkeypatch: pytest.MonkeyPatch) -> None:
    cfg = Config(timezone="UTC", budget=BudgetConfig(daily_usd=Decimal(50)))
    moment = datetime(DAY.year, DAY.month, DAY.day, 23, 0, tzinfo=UTC)
    sent: list[tuple[str, str]] = []
    monkeypatch.setattr(notifier, "notify", lambda title, body: sent.append((title, body)) or True)

    first = due_alerts(store, cfg, moment)
    second = due_alerts(store, cfg, moment)
    send_alerts(first, cfg)

    assert [line.level for line in first] == ["over"]
    assert second == ()
    assert "over budget" in sent[0][0]


def test_alerts_stay_silent_when_notifications_are_off(monkeypatch: pytest.MonkeyPatch, store: Store) -> None:
    cfg = Config(timezone="UTC", notify="off", budget=BudgetConfig(daily_usd=Decimal(50)))
    sent: list[str] = []
    monkeypatch.setattr(notifier, "notify", lambda title, body: sent.append(title) or True)

    send_alerts(due_alerts(store, cfg, datetime(DAY.year, DAY.month, DAY.day, 23, tzinfo=UTC)), cfg)

    assert sent == []


def test_budget_keys_round_trip_through_config_toml(home: AppHome) -> None:
    cfg = set_key(Config(timezone="UTC"), "budget.monthly_usd", "500")
    cfg = set_key(cfg, f"budget.projects.{PID}", "120.50")
    home.root.mkdir(parents=True, exist_ok=True)

    save_config(cfg, home)
    loaded = load_config(home)

    assert get_key(loaded, "budget.monthly_usd") == "500"
    assert loaded.budget.projects == {PID: Decimal("120.50")}
    assert set_key(loaded, f"budget.projects.{PID}", "").budget.projects == {}
