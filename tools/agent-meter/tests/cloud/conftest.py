"""L4 cloud fixtures: an ephemeral BigQuery dataset per run (PLAN Test Plan L4).

Tests here are marked ``bigquery`` and skip unless ``AGENT_METER_TEST_GCP_PROJECT`` is set.
Each run creates ``agent_metrics_test_<run_id>`` with a 1-day default table expiration as a
safety net and drops it (``DROP SCHEMA ... CASCADE``) in teardown.
"""

from __future__ import annotations

import os
import secrets
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from agent_meter.sinks.bigquery import BigQueryGateway, ensure_dataset, google_gateway
from tests.cloud.sink_support import FakeBigQueryConfig

PROJECT_ENV = "AGENT_METER_TEST_GCP_PROJECT"
LOCATION_ENV = "AGENT_METER_TEST_GCP_LOCATION"


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", f"bigquery: L4 tests against real BigQuery (set {PROJECT_ENV} to run)"
    )


def live_project() -> str | None:
    return os.environ.get(PROJECT_ENV) or None


@pytest.fixture(scope="module")
def bq_settings() -> FakeBigQueryConfig:
    project = live_project()
    if project is None:
        pytest.skip(f"{PROJECT_ENV} is not set")
    run_id = f"{datetime.now(UTC):%Y%m%d%H%M%S}_{secrets.token_hex(3)}"
    return FakeBigQueryConfig(
        project=project,
        dataset=f"agent_metrics_test_{run_id}",
        location=os.environ.get(LOCATION_ENV, "US"),
    )


@pytest.fixture(scope="module")
def gateway(bq_settings: FakeBigQueryConfig) -> BigQueryGateway:
    pytest.importorskip("google.cloud.bigquery", reason="install the [bigquery] extra")
    return google_gateway(bq_settings.project, bq_settings.location)


@pytest.fixture(scope="module")
def dataset(bq_settings: FakeBigQueryConfig, gateway: BigQueryGateway) -> Iterator[str]:
    ensure_dataset(bq_settings, client=gateway, default_table_expiration_days=1)
    try:
        yield f"{bq_settings.project}.{bq_settings.dataset}"
    finally:
        gateway.execute(
            f"DROP SCHEMA IF EXISTS `{bq_settings.project}.{bq_settings.dataset}` CASCADE"
        )


@pytest.fixture
def local_store(tmp_path: Path) -> Iterator[tuple[Any, Any]]:
    """A real Track 11B store in a temp home: ``(home, store)``."""
    paths = pytest.importorskip("agent_meter.paths", reason="Track 11B paths.py not available")
    store_mod = pytest.importorskip("agent_meter.store", reason="Track 11B store.py not available")
    home = paths.AppHome.resolve(str(tmp_path / "home"))
    with store_mod.Store.open(home, read_only=False, lock_timeout_s=10.0) as store:
        store.migrate()
        yield home, store
