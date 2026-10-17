"""Unit tests for ``paths`` (AppHome) and ``config`` (config.toml round-trip, get/set keys)."""

from __future__ import annotations

import os
import stat
from decimal import Decimal
from pathlib import Path

import pytest

from agent_meter.config import (
    BigQueryConfig,
    Config,
    ConfigError,
    HostConfig,
    get_key,
    load_config,
    save_config,
    set_key,
    system_timezone,
)
from agent_meter.model import Host
from agent_meter.paths import AppHome, atomic_write_text, load_secret


def test_app_home_resolution_order(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    env_home = tmp_path / "env-home"
    cli_home = tmp_path / "cli-home"
    monkeypatch.setenv("AGENT_METER_HOME", str(env_home))
    monkeypatch.setenv("HOME", str(tmp_path / "user"))

    # Act
    from_cli = AppHome.resolve(str(cli_home))
    from_env = AppHome.resolve()
    monkeypatch.delenv("AGENT_METER_HOME")
    from_default = AppHome.resolve()

    # Assert
    assert from_cli.root == cli_home
    assert from_env.root == env_home
    assert from_default.root == tmp_path / "user" / ".agent-meter"
    assert stat.S_IMODE(os.stat(cli_home).st_mode) == 0o700


def test_app_home_layout(tmp_path: Path) -> None:
    home = AppHome.resolve(str(tmp_path / "h"))

    assert home.db.name == "meter.duckdb"
    assert home.lock.name == "lock"
    assert home.config.name == "config.toml"
    assert home.projects.name == "projects.yaml"
    assert home.pricing_local.name == "pricing.local.yaml"
    assert home.last_summary.name == "last-summary.txt"
    assert home.snapshot == home.state_dir / "snapshot.json"
    assert home.notified == home.state_dir / "notified.json"
    assert {home.logs_dir.name, home.backups_dir.name, home.outbox_dir.name} == {
        "logs",
        "backups",
        "outbox",
    }


def test_secret_is_created_once_with_0600(tmp_path: Path) -> None:
    home = AppHome.resolve(str(tmp_path / "h"))

    first = load_secret(home)
    second = load_secret(home)

    assert len(first) == 32
    assert first == second
    assert stat.S_IMODE(os.stat(home.secret).st_mode) == 0o600


def test_atomic_write_text_replaces_content(tmp_path: Path) -> None:
    target = tmp_path / "a" / "file.txt"

    atomic_write_text(target, "one")
    atomic_write_text(target, "two")

    assert target.read_text(encoding="utf-8") == "two"
    assert stat.S_IMODE(os.stat(target).st_mode) == 0o600
    assert [p.name for p in target.parent.iterdir()] == ["file.txt"]


def test_missing_config_gives_defaults(tmp_path: Path) -> None:
    home = AppHome.resolve(str(tmp_path / "h"))

    cfg = load_config(home)

    assert cfg.timezone == system_timezone()
    assert cfg.idle_threshold_s == 120
    assert cfg.notify == "auto"
    assert cfg.show_task_labels is True
    assert cfg.usd_rate is None
    assert set(cfg.hosts) == set(Host)
    assert cfg.bigquery == BigQueryConfig()


def test_config_round_trip(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "h"))
    cfg = Config(
        timezone="America/Bogota",
        idle_threshold_s=90,
        notify="long-tasks",
        display_currency="COP",
        usd_rate=Decimal("4100.50"),
        hosts={
            **Config(timezone="UTC").hosts,
            Host.ANTIGRAVITY_CLI: HostConfig(
                enabled=False, root=tmp_path / "agy", default_model="gemini-3.8-flash"
            ),
        },
        bigquery=BigQueryConfig(enabled=True, project="devhack-3f0c2", mode="sandbox"),
    )

    # Act
    save_config(cfg, home)
    loaded = load_config(home)

    # Assert
    assert loaded == cfg
    assert 'usd_rate = "4100.50"' in home.config.read_text(encoding="utf-8")


def test_invalid_toml_raises_config_error(tmp_path: Path) -> None:
    home = AppHome.resolve(str(tmp_path / "h"))
    home.config.write_text("[general\ntimezone = 1", encoding="utf-8")

    with pytest.raises(ConfigError):
        load_config(home)


def test_unknown_timezone_rejected(tmp_path: Path) -> None:
    home = AppHome.resolve(str(tmp_path / "h"))
    home.config.write_text('[general]\ntimezone = "Mars/Olympus"\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="timezone"):
        load_config(home)


@pytest.mark.parametrize(
    ("key", "value", "expected"),
    [
        ("timezone", "America/Bogota", "America/Bogota"),
        ("general.idle_threshold_s", "60", "60"),
        ("usd_rate", "4000", "4000"),
        ("currency.display", "COP", "COP"),
        ("hosts.antigravity-cli.default_model", "gemini-3.8-flash", "gemini-3.8-flash"),
        ("bigquery.project", "devhack-3f0c2", "devhack-3f0c2"),
        ("sinks.bigquery.anonymize_projects", "true", "true"),
        ("show_task_labels", "false", "false"),
    ],
)
def test_set_then_get_key(key: str, value: str, expected: str) -> None:
    cfg = Config(timezone="UTC")

    updated = set_key(cfg, key, value)

    assert get_key(updated, key) == expected


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("nope", "1"),
        ("idle_threshold_s", "-5"),
        ("idle_threshold_s", "abc"),
        ("notify", "loud"),
        ("usd_rate", "0"),
        ("hosts.unknown-host.enabled", "true"),
        ("bigquery.mode", "free"),
        ("show_task_labels", "maybe"),
    ],
)
def test_set_key_rejects_bad_input(key: str, value: str) -> None:
    with pytest.raises(ConfigError):
        set_key(Config(timezone="UTC"), key, value)


def test_unset_optional_key_with_empty_value() -> None:
    cfg = set_key(Config(timezone="UTC"), "usd_rate", "4000")

    cleared = set_key(cfg, "usd_rate", "")

    assert cleared.usd_rate is None
    assert get_key(cleared, "usd_rate") == ""


def test_antigravity_hosts_default_to_gemini_flash_model() -> None:
    # Arrange
    cfg = Config(timezone="UTC")

    # Act
    defaults = {host: cfg.host(host).default_model for host in Host}

    # Assert
    assert defaults == {
        Host.CLAUDE_CODE: None,
        Host.ANTIGRAVITY_CLI: "gemini-3.8-flash",
        Host.ANTIGRAVITY_IDE: "gemini-3.8-flash",
        Host.ANTIGRAVITY_APP: "gemini-3.8-flash",
    }
