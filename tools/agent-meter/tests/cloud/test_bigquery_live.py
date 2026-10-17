"""L4 cloud integration for the BigQuery sink (BQ-02, BQ-03, BQ-08, BQ-09, PV-01).

Runs only with ``AGENT_METER_TEST_GCP_PROJECT`` set (e.g. ``devhack-3f0c2``) and the
``[bigquery]`` extra installed: ``pytest -m bigquery tests/cloud``.
"""

from __future__ import annotations

import dataclasses
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from agent_meter.model import Host
from agent_meter.pricing import load_pricing
from agent_meter.project_resolver import ProjectsConfig
from agent_meter.sinks.bigquery import (
    DEDUP_KEYS,
    VIEW_NAMES,
    BigQueryGateway,
    check_view_costs,
    reconcile,
    sync,
)
from agent_meter.sinks.outbox import (
    FACT_TABLES,
    REFERENCE_TABLES,
    Anonymizer,
    load_salt,
)
from tests.cloud.conftest import PROJECT_ENV, live_project
from tests.cloud.sink_support import FakeBigQueryConfig, FakeConfig
from tests.fixtures.canary import CANARY
from tests.fixtures.records import make_batch, make_call, make_project, ts

pytestmark = [
    pytest.mark.bigquery,
    pytest.mark.skipif(live_project() is None, reason=f"{PROJECT_ENV} is not set"),
]

PROJECT_ID = "git:0123456789abcdef"
SALT_BYTES = 32


def _seed(store: Any, *, display_name: str = "demo-repo", output_tokens: int = 200) -> None:
    store.load_reference_data(
        pricing=load_pricing(None),
        host_defaults={Host.CLAUDE_CODE: None},
        projects=ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={}),
        project_refs=[make_project(display_name=display_name)],
        settings={"timezone": "UTC"},
    )
    calls = tuple(
        make_call(
            call_id=f"claude-code:req-{n:04d}", ts=ts(5 + n),
            output_tokens=output_tokens if n == 1 else 200,
            owner_rank=f"0:2026-10-16T14:00:00.000Z:{CANARY}",
        )
        for n in range(1, 4)
    )
    store.apply_batches([make_batch(calls=calls)])


def _scalar(gateway: BigQueryGateway, sql: str) -> int:
    [row] = gateway.execute(sql)
    value = next(iter(row.values()))
    assert isinstance(value, int)
    return value


def _ensure_salt(home: Any) -> bytes:
    secret: Path = home.secret
    if not secret.exists():
        secret.write_bytes(bytes(range(SALT_BYTES)))
        secret.chmod(0o600)
    return load_salt(secret)


def test_bq02_dedup_views_return_one_row_per_key_after_reuploads(
    dataset: str, gateway: BigQueryGateway, bq_settings: FakeBigQueryConfig,
    local_store: tuple[Any, Any],
) -> None:
    # Arrange: upload, change one call, upload again, then force a full duplicate upload
    home, store = local_store
    cfg = FakeConfig(bigquery=bq_settings)
    factory = lambda _project: gateway  # noqa: E731
    _seed(store)
    assert sync(home, cfg, store, client_factory=factory).status == "ok"
    _seed(store, output_tokens=999)
    assert sync(home, cfg, store, client_factory=factory).status == "ok"
    for table in FACT_TABLES:
        store.set_meta(f"bq_watermark:{table}", "0")

    # Act
    result = sync(home, cfg, store, client_factory=factory)

    # Assert
    assert result.status == "ok"
    assert _scalar(gateway, f"SELECT COUNT(*) AS n FROM `{dataset}.raw_llm_calls`") > 3
    for table, keys in DEDUP_KEYS.items():
        key = ", ".join(keys)
        duplicates = _scalar(
            gateway,
            f"SELECT COUNT(*) AS n FROM (SELECT {key} FROM `{dataset}.{table}` "
            f"GROUP BY {key} HAVING COUNT(*) > 1)",
        )
        assert duplicates == 0, table
    assert _scalar(gateway, f"SELECT COUNT(*) AS n FROM `{dataset}.llm_calls`") == 3
    assert _scalar(
        gateway,
        f"SELECT output_tokens AS n FROM `{dataset}.llm_calls` WHERE call_id = 'claude-code:req-0001'",
    ) == 999


def test_bq03_full_reload_replaces_raw_tables(
    dataset: str, gateway: BigQueryGateway, bq_settings: FakeBigQueryConfig,
    local_store: tuple[Any, Any],
) -> None:
    # Arrange
    home, store = local_store
    cfg = FakeConfig(bigquery=bq_settings)
    _seed(store)
    sync(home, cfg, store, client_factory=lambda _p: gateway)

    # Act
    result = sync(home, cfg, store, full_reload=True, client_factory=lambda _p: gateway)

    # Assert
    assert result.status == "ok"
    assert _scalar(gateway, f"SELECT COUNT(*) AS n FROM `{dataset}.raw_llm_calls`") == 3


def test_bq08_daily_totals_match_local_exactly_with_anonymization(
    dataset: str, gateway: BigQueryGateway, bq_settings: FakeBigQueryConfig,
    local_store: tuple[Any, Any],
) -> None:
    # Arrange: canary as the project name, uploaded anonymized
    home, store = local_store
    anon_settings = dataclasses.replace(bq_settings, anonymize_projects=True)
    cfg = FakeConfig(bigquery=anon_settings)
    anonymizer = Anonymizer(_ensure_salt(home))
    _seed(store, display_name=CANARY)

    # Act
    result = sync(home, cfg, store, full_reload=True, client_factory=lambda _p: gateway)
    diffs = reconcile(cfg, store, date(2026, 10, 1), date(2026, 10, 31), client=gateway,
                      anonymizer=anonymizer)

    # Assert
    assert result.status == "ok"
    assert diffs == []
    assert _scalar(
        gateway, f"SELECT COUNT(*) AS n FROM `{dataset}.projects` WHERE project_id = '{PROJECT_ID}'"
    ) == 0


def test_pv01_canary_absent_from_every_uploaded_table(
    dataset: str, gateway: BigQueryGateway, bq_settings: FakeBigQueryConfig,
    local_store: tuple[Any, Any],
) -> None:
    # Arrange
    home, store = local_store
    cfg = FakeConfig(bigquery=dataclasses.replace(bq_settings, anonymize_projects=True))
    _ensure_salt(home)
    _seed(store, display_name=CANARY)
    assert sync(home, cfg, store, full_reload=True, client_factory=lambda _p: gateway).status == "ok"

    # Act / Assert
    for table in [f"raw_{t}" for t in FACT_TABLES] + list(REFERENCE_TABLES):
        hits = _scalar(
            gateway,
            f"SELECT COUNT(*) AS n FROM `{dataset}.{table}` AS t "
            f"WHERE CONTAINS_SUBSTR(TO_JSON_STRING(t), '{CANARY}')",
        )
        assert hits == 0, table


def test_views_have_the_same_columns_as_the_duckdb_views(
    dataset: str, gateway: BigQueryGateway, local_store: tuple[Any, Any],
) -> None:
    # Arrange
    _home, store = local_store

    # Act / Assert (contracts §6: identical names and columns on both engines)
    for view in VIEW_NAMES:
        local = [str(r["column_name"]) for r in store.query(f"DESCRIBE {view}")]
        cloud = [
            str(r["column_name"])
            for r in gateway.execute(
                f"SELECT column_name FROM `{dataset}`.INFORMATION_SCHEMA.COLUMNS "
                f"WHERE table_name = '{view}' ORDER BY ordinal_position"
            )
        ]
        assert cloud == local, view


def test_bq09_every_view_dry_runs_under_the_byte_ceiling(
    dataset: str, gateway: BigQueryGateway, bq_settings: FakeBigQueryConfig,
) -> None:
    checks = check_view_costs(bq_settings, client=gateway)
    assert [c.view for c in checks if not c.ok] == []
