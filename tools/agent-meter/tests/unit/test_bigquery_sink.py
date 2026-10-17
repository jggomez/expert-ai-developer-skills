"""Tests for ``agent_meter.sinks.bigquery`` with a fake gateway (ADR §3.11; BQ-01, BQ-03..07, BQ-09, PV-04)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
import types
from collections.abc import Callable, Iterator
from dataclasses import replace
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

import pytest

from agent_meter.config import BigQueryConfig, Config
from agent_meter.model import Host
from agent_meter.paths import AppHome
from agent_meter.pricing import load_pricing
from agent_meter.project_resolver import ProjectsConfig
from agent_meter.sinks import bigquery as sink
from agent_meter.sinks.bigquery import (
    DEDUP_KEYS,
    LAST_SYNC_KEY,
    VIEW_NAMES,
    LoadSpec,
    SyncResult,
    build_load_spec,
    check_view_costs,
    classify_error,
    ddl_statements,
    describe_sync,
    ensure_dataset,
    google_gateway,
    reconcile,
    sync,
)
from agent_meter.sinks.outbox import (
    FACT_TABLES,
    REFERENCE_TABLES,
    TABLE_SCHEMAS,
    Anonymizer,
    OutboxFile,
    pending_counts,
)
from agent_meter.store import Store
from tests.cloud.sink_support import (
    PROJECT_ID,
    ContractStore,
    FakeBigQueryConfig,
    FakeConfig,
    FakeHome,
    block_network,
    seed_calls,
    seed_graph,
)
from tests.fixtures.records import CALL_ID, make_batch, make_project

SRC =Path(sink.__file__).resolve().parents[1]
NOW = datetime(2026, 10, 16, 15, 0, 0, tzinfo=UTC)
SALT = bytes(range(32))
CONTRACT_VIEWS = (
    "v_calls", "v_daily_project_cost", "v_sessions", "v_tasks", "v_agent_runs",
    "v_agent_type_cost", "v_tool_counts", "v_task_latency", "v_dev_hours", "v_client_month",
    "v_unpriced_models", "v_untracked", "v_health",
)


# ---------------------------------------------------------------------------- test doubles
class RefreshError(Exception):
    """Same class name as google.auth.exceptions.RefreshError (expired ADC)."""


class Unauthorized(Exception):
    """Same class name as google.api_core.exceptions.Unauthorized (HTTP 401)."""


class TransportError(Exception):
    """Same class name as google.auth.exceptions.TransportError (no network)."""


class BadRequest(Exception):
    """Same class name as google.api_core.exceptions.BadRequest (schema mismatch)."""


class FakeGateway:
    """Records load jobs and queries; optionally fails loads for given destination tables."""

    def __init__(self, *, fail: dict[str, Exception] | None = None) -> None:
        self.fail = fail or {}
        self.loads: list[tuple[LoadSpec, list[dict[str, object]]]] = []
        self.statements: list[str] = []
        self.dry_runs: list[str] = []
        self.query_rows: list[dict[str, object]] = []
        self.bytes_by_view: dict[str, int] = {}

    def load_ndjson(self, path: Path, spec: LoadSpec) -> str:
        table = spec.destination.rsplit(".", 1)[1]
        if table in self.fail:
            raise self.fail[table]
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        self.loads.append((spec, rows))
        return f"job-{len(self.loads)}"

    def execute(self, sql: str) -> list[dict[str, object]]:
        self.statements.append(sql)
        return self.query_rows

    def dry_run_bytes(self, sql: str) -> int:
        self.dry_runs.append(sql)
        view = re.search(r"\.(v_\w+)`", sql)
        assert view is not None
        return self.bytes_by_view.get(view.group(1), 0)

    def loaded(self, table: str) -> list[tuple[LoadSpec, list[dict[str, object]]]]:
        return [(s, r) for s, r in self.loads if s.destination.endswith(f".{table}")]


def factory_for(gateway: FakeGateway, seen: list[str] | None = None) -> Callable[[str], FakeGateway]:
    def make(project: str) -> FakeGateway:
        if seen is not None:
            seen.append(project)
        return gateway

    return make


def failing_factory(exc: Exception) -> Callable[[str], FakeGateway]:
    def make(project: str) -> FakeGateway:
        raise exc

    return make


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    block_network(monkeypatch)


@pytest.fixture
def store() -> ContractStore:
    s = ContractStore()
    seed_graph(s)
    return s


@pytest.fixture
def home(tmp_path: Path) -> FakeHome:
    return FakeHome(tmp_path / "home")


@pytest.fixture
def cfg() -> FakeConfig:
    return FakeConfig()


def ndjson_files(home: FakeHome) -> list[Path]:
    return sorted(home.outbox_dir.rglob("*.ndjson")) if home.outbox_dir.exists() else []


# ------------------------------------------------------------------------- BQ-01 load spec
def test_build_load_spec_for_fact_table_appends_into_partitioned_raw_table(tmp_path: Path) -> None:
    # Arrange
    file = OutboxFile("llm_calls", tmp_path / "x.ndjson", 3, 9, "WRITE_APPEND")

    # Act
    spec = build_load_spec(file, project="devhack-3f0c2", dataset="agent_metrics")

    # Assert
    assert spec == LoadSpec(
        destination="devhack-3f0c2.agent_metrics.raw_llm_calls",
        schema=TABLE_SCHEMAS["llm_calls"],
        write_disposition="WRITE_APPEND",
        partition_field="ts",
        clustering_fields=("project_id", "host"),
    )


@pytest.mark.parametrize(
    ("table", "partition"),
    [("tasks", "started_at"), ("agent_runs", "started_at"), ("sessions", "started_at"),
     ("tool_uses", None)],
)
def test_build_load_spec_partitions_fact_tables_per_contract(
    tmp_path: Path, table: str, partition: str | None
) -> None:
    spec = build_load_spec(
        OutboxFile(table, tmp_path / "x", 1, 1, "WRITE_TRUNCATE"), project="p-123456", dataset="d"
    )
    assert spec.destination == f"p-123456.d.raw_{table}"
    assert spec.partition_field == partition
    assert spec.clustering_fields == ("project_id", "host")
    assert spec.write_disposition == "WRITE_TRUNCATE"


def test_build_load_spec_for_reference_table_truncates_same_named_table(tmp_path: Path) -> None:
    spec = build_load_spec(
        OutboxFile("pricing", tmp_path / "x", 1, 0, "WRITE_TRUNCATE"), project="p-123456", dataset="d"
    )
    assert spec.destination == "p-123456.d.pricing"
    assert (spec.partition_field, spec.clustering_fields) == (None, ())


# ------------------------------------------------------------------------------ sync (ok)
def test_sync_loads_outbox_and_advances_watermarks_only_after_success(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    # Arrange
    seed_calls(store, 3)
    gateway, seen = FakeGateway(), list[str]()

    # Act
    result = sync(home, cfg, store, client_factory=factory_for(gateway, seen), now=NOW)

    # Assert
    assert result.status == "ok"
    assert seen == ["devhack-3f0c2"]  # project passed explicitly, never the gcloud default
    assert result.backlog == dict.fromkeys(FACT_TABLES, 0)
    [(spec, rows)] = gateway.loaded("raw_llm_calls")
    assert spec.write_disposition == "WRITE_APPEND"
    assert [r["call_id"] for r in rows] == [f"claude-code:req-{n:04d}" for n in (1, 2, 3)]
    for table in FACT_TABLES:
        assert store.get_meta(f"bq_watermark:{table}") == str(store.max_seq(table))
    for table in REFERENCE_TABLES:
        [(ref_spec, _)] = gateway.loaded(table)
        assert ref_spec.write_disposition == "WRITE_TRUNCATE"
    assert {load.table for load in result.loads} == set(FACT_TABLES) | set(REFERENCE_TABLES)
    assert all(load.ok and load.job_id.startswith("job-") for load in result.loads)
    assert ndjson_files(home) == []  # outbox emptied after success
    assert store.get_meta(LAST_SYNC_KEY) == "2026-10-16T15:00:00+00:00"


def test_second_sync_without_new_rows_uploads_only_reference_tables(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    # Arrange
    seed_calls(store, 2)
    sync(home, cfg, store, client_factory=factory_for(FakeGateway()), now=NOW)
    gateway = FakeGateway()

    # Act
    result = sync(home, cfg, store, client_factory=factory_for(gateway), now=NOW)

    # Assert
    assert result.status == "ok"
    assert {s.destination.rsplit(".", 1)[1] for s, _ in gateway.loads} == set(REFERENCE_TABLES)


def test_full_reload_truncates_every_table_with_all_rows(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    # Arrange (BQ-03)
    seed_calls(store, 3)
    sync(home, cfg, store, client_factory=factory_for(FakeGateway()), now=NOW)
    gateway = FakeGateway()

    # Act
    result = sync(home, cfg, store, full_reload=True, client_factory=factory_for(gateway), now=NOW)

    # Assert
    assert result.status == "ok"
    assert {spec.write_disposition for spec, _ in gateway.loads} == {"WRITE_TRUNCATE"}
    [(_, rows)] = gateway.loaded("raw_llm_calls")
    assert len(rows) == 3
    assert store.get_meta("bq_watermark:llm_calls") == str(store.max_seq("llm_calls"))


def test_dry_run_reports_backlog_without_files_or_network(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    # Arrange
    seed_calls(store, 2)

    # Act
    result = sync(
        home, cfg, store, dry_run=True,
        client_factory=failing_factory(AssertionError("must not connect")), now=NOW,
    )

    # Assert
    assert result == SyncResult(status="dry_run", loads=(), backlog=pending_counts(store))
    assert result.backlog["llm_calls"] == 2
    assert ndjson_files(home) == []
    assert "would upload 6 rows" in describe_sync(result, cfg.bigquery)


def test_sync_refuses_when_cloud_sink_is_disabled(
    store: ContractStore, home: FakeHome
) -> None:
    disabled = FakeConfig(bigquery=FakeBigQueryConfig(enabled=False))
    with pytest.raises(ValueError, match="not enabled"):
        sync(home, disabled, store, client_factory=factory_for(FakeGateway()), now=NOW)


def test_sync_refuses_an_invalid_dataset_identifier(store: ContractStore, home: FakeHome) -> None:
    bad = FakeConfig(bigquery=FakeBigQueryConfig(dataset="x`; DROP SCHEMA y"))
    with pytest.raises(ValueError, match="dataset"):
        sync(home, bad, store, client_factory=factory_for(FakeGateway()), now=NOW)


# ------------------------------------------------------------------- BQ-05 failure keeps backlog
def test_load_failure_keeps_watermark_and_outbox_then_retries_next_cycle(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    # Arrange
    ids = seed_calls(store, 3)
    broken = FakeGateway(fail={"raw_llm_calls": BadRequest("schema mismatch")})

    # Act
    failed = sync(home, cfg, store, client_factory=factory_for(broken), now=NOW)

    # Assert: failure is reported, llm_calls backlog and file kept, other tables advanced
    assert failed.status == "error"
    assert failed.backlog["llm_calls"] == 3
    assert store.get_meta("bq_watermark:llm_calls") is None
    assert store.get_meta("bq_watermark:tasks") == str(store.max_seq("tasks"))
    assert [p.parent.name for p in ndjson_files(home)] == ["llm_calls"]
    [bad] = [load for load in failed.loads if not load.ok]
    assert (bad.table, bad.error_class, bad.job_id) == ("llm_calls", "BadRequest", "")
    assert store.get_meta(LAST_SYNC_KEY) is None

    # Act: next cycle with a healthy gateway
    healthy = FakeGateway()
    retried = sync(home, cfg, store, client_factory=factory_for(healthy), now=NOW)

    # Assert: each pending row uploaded exactly once, backlog drained
    assert retried.status == "ok"
    [(_, rows)] = healthy.loaded("raw_llm_calls")
    assert sorted(str(r["call_id"]) for r in rows) == ids
    assert healthy.loaded("raw_tasks") == []
    assert retried.backlog["llm_calls"] == 0
    assert ndjson_files(home) == []


# ----------------------------------------------------------------- BQ-06 expired credentials
def test_expired_credentials_map_to_auth_with_a_clear_fix_and_leak_nothing(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    # Arrange
    seed_calls(store, 2)
    secret = "ya29.SECRET-ACCESS-TOKEN"

    # Act
    result = sync(
        home, cfg, store, client_factory=failing_factory(RefreshError(f"Reauth needed {secret}")),
        now=NOW,
    )
    message = describe_sync(result, cfg.bigquery)

    # Assert
    assert result.status == "auth"
    assert result.loads == ()
    assert result.backlog["llm_calls"] == 2
    assert "gcloud auth application-default login" in message
    assert "devhack-3f0c2" in message
    assert "local collection is unaffected" in message.lower()
    assert secret not in message
    assert all(secret not in p.read_text(encoding="utf-8") for p in ndjson_files(home))
    assert store.get_meta("bq_watermark:llm_calls") is None


def test_auth_error_during_a_load_stops_the_remaining_loads(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    # Arrange
    seed_calls(store, 1)
    gateway = FakeGateway(fail={"raw_llm_calls": Unauthorized("401")})

    # Act
    result = sync(home, cfg, store, client_factory=factory_for(gateway), now=NOW)

    # Assert
    assert result.status == "auth"
    assert [load.table for load in result.loads] == ["llm_calls"]
    assert gateway.loads == []


def test_local_store_stays_writable_after_an_auth_failure(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    # Arrange
    seed_calls(store, 1)
    sync(home, cfg, store, client_factory=failing_factory(RefreshError("expired")), now=NOW)

    # Act: local collection continues
    seed_calls(store, 2, start=10)

    # Assert
    assert pending_counts(store)["llm_calls"] == 3


# ------------------------------------------------------------- BQ-07 offline N cycles, catch-up
def test_offline_cycles_then_single_catch_up_without_loss_or_duplicates(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    # Arrange: three offline cycles, new rows ingested between them
    expected: list[str] = []
    offline_errors: list[Exception] = [
        ConnectionError("down"), TransportError("dns"), TimeoutError("slow"),
    ]
    for cycle, error in enumerate(offline_errors):
        expected += seed_calls(store, 2, start=1 + cycle * 2)
        result = sync(home, cfg, store, client_factory=failing_factory(error), now=NOW)
        assert result.status == "offline"
        assert result.backlog["llm_calls"] == len(expected)
        assert "unreachable" in describe_sync(result, cfg.bigquery)

    # Act: reconnect
    gateway = FakeGateway()
    result = sync(home, cfg, store, client_factory=factory_for(gateway), now=NOW)

    # Assert
    assert result.status == "ok"
    [(_, rows)] = gateway.loaded("raw_llm_calls")
    uploaded = [str(r["call_id"]) for r in rows]
    assert sorted(uploaded) == sorted(expected) and len(set(uploaded)) == len(uploaded)
    assert store.get_meta("bq_watermark:llm_calls") == str(store.max_seq("llm_calls"))
    assert result.backlog == dict.fromkeys(FACT_TABLES, 0)


def test_offline_error_during_a_load_is_reported_as_offline(
    store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    seed_calls(store, 1)
    gateway = FakeGateway(fail={"raw_llm_calls": OSError("network unreachable")})
    result = sync(home, cfg, store, client_factory=factory_for(gateway), now=NOW)
    assert result.status == "offline"


@pytest.mark.parametrize(
    ("exc", "kind"),
    [
        (RefreshError("x"), "auth"), (Unauthorized("x"), "auth"),
        (type("DefaultCredentialsError", (Exception,), {})("x"), "auth"),
        (type("Forbidden", (Exception,), {})("x"), "auth"),
        (TransportError("x"), "offline"), (ConnectionError("x"), "offline"),
        (TimeoutError("x"), "offline"), (type("ServiceUnavailable", (Exception,), {})("x"), "offline"),
        (BadRequest("x"), "error"), (ValueError("x"), "error"),
    ],
)
def test_classify_error(exc: Exception, kind: str) -> None:
    assert classify_error(exc) == kind


def test_classify_error_follows_the_cause_chain() -> None:
    try:
        try:
            raise TransportError("dns")
        except TransportError as inner:
            raise RuntimeError("retry exhausted") from inner
    except RuntimeError as outer:
        assert classify_error(outer) == "offline"


# --------------------------------------------------------------------- anonymization (PV-02)
def test_sync_anonymizes_with_the_local_salt_and_never_uploads_it(
    store: ContractStore, home: FakeHome
) -> None:
    # Arrange
    home.root.mkdir(parents=True)
    home.secret.write_bytes(SALT)
    cfg = FakeConfig(bigquery=FakeBigQueryConfig(anonymize_projects=True))
    seed_calls(store, 1)
    gateway = FakeGateway()

    # Act
    result = sync(home, cfg, store, client_factory=factory_for(gateway), now=NOW)

    # Assert
    assert result.status == "ok"
    uploaded = json.dumps([rows for _, rows in gateway.loads])
    assert PROJECT_ID not in uploaded and "Client Z" not in uploaded
    assert str(Anonymizer(SALT)(PROJECT_ID)) in uploaded
    assert SALT.hex() not in uploaded


def test_sync_refuses_to_upload_clear_names_when_the_salt_is_missing(
    store: ContractStore, home: FakeHome
) -> None:
    cfg = FakeConfig(bigquery=FakeBigQueryConfig(anonymize_projects=True))
    gateway = FakeGateway()
    with pytest.raises(ValueError, match="salt"):
        sync(home, cfg, store, client_factory=factory_for(gateway), now=NOW)
    assert gateway.loads == []


# --------------------------------------------------------------------------- BQ-04 static
FORBIDDEN = re.compile(
    r"insert_rows|insertAll|insert_rows_json|BigQueryWriteClient|write_api"
    r"|\bINSERT\s+INTO\b|\bMERGE\b|\bUPDATE\b|\bDELETE\b|\bTRUNCATE\s+TABLE\b",
)


def test_sink_sources_contain_no_streaming_or_dml() -> None:
    # Arrange
    sources = [*(SRC / "sinks").glob("*.py"), *(SRC / "sql" / "bigquery").glob("*.sql")]

    # Act
    hits = {p.name: FORBIDDEN.findall(p.read_text(encoding="utf-8")) for p in sources}

    # Assert
    assert len(sources) >= 5
    assert {name: found for name, found in hits.items() if found} == {}
    for sql in (SRC / "sql" / "bigquery").glob("*.sql"):
        text = sql.read_text(encoding="utf-8").lower()
        assert re.search(r"\b(insert|update|delete|merge)\b", text) is None
        assert "partition_filter" not in text


def test_bigquery_module_imports_no_google_package_at_import_time() -> None:
    code = (
        "import sys, agent_meter.sinks.bigquery, agent_meter.sinks.outbox; "
        "print(sorted(m for m in sys.modules if m == 'google' or m.startswith('google.')))"
    )
    out = subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, check=True,
        env={"PYTHONPATH": str(SRC.parent)},
    )
    assert out.stdout.strip() == "[]"


# ----------------------------------------------------------------------------- DDL & views
def test_ddl_statements_create_dataset_tables_then_views_in_order() -> None:
    # Act
    statements = ddl_statements(FakeBigQueryConfig(), default_table_expiration_days=1)

    # Assert
    assert statements[0] == (
        "CREATE SCHEMA IF NOT EXISTS `devhack-3f0c2.agent_metrics` "
        "OPTIONS (location = 'US', default_table_expiration_days = 1)"
    )
    created = [re.search(r"`devhack-3f0c2\.agent_metrics\.(\w+)`", s) for s in statements[1:]]
    names = [m.group(1) for m in created if m is not None]
    assert len(names) == len(statements) - 1
    tables = [f"raw_{t}" for t in ("llm_calls", "tasks", "agent_runs", "sessions", "tool_uses")]
    assert names[:5] == tables
    assert names[5:15] == list(REFERENCE_TABLES)
    assert names[15:20] == list(DEDUP_KEYS)
    assert names[20:] == list(VIEW_NAMES)
    assert all("${" not in s and not s.rstrip().endswith(";") for s in statements)


def test_ddl_statements_without_expiration_and_location_option() -> None:
    first = ddl_statements(FakeBigQueryConfig(location="southamerica-east1"))[0]
    assert first == (
        "CREATE SCHEMA IF NOT EXISTS `devhack-3f0c2.agent_metrics` "
        "OPTIONS (location = 'southamerica-east1')"
    )


def test_view_names_match_contract_section_6() -> None:
    assert VIEW_NAMES == CONTRACT_VIEWS
    assert DEDUP_KEYS == {
        "llm_calls": ("call_id",), "tasks": ("task_id",), "agent_runs": ("agent_run_id",),
        "tool_uses": ("agent_run_id", "tool_name"), "sessions": ("session_id",),
    }


def test_dedup_views_keep_latest_ingest_seq_per_natural_key() -> None:
    text = (SRC / "sql" / "bigquery" / "views.sql").read_text(encoding="utf-8")
    for table, keys in DEDUP_KEYS.items():
        pattern = (
            rf"CREATE OR REPLACE VIEW `\$\{{project\}}\.\$\{{dataset\}}\.{table}` AS\s+"
            rf"SELECT \* EXCEPT\(_uploaded_at\) FROM `\$\{{project\}}\.\$\{{dataset\}}\.raw_{table}`\s+"
            rf"WHERE TRUE\s+QUALIFY ROW_NUMBER\(\) OVER \(PARTITION BY {', '.join(keys)} "
            rf"ORDER BY ingest_seq DESC"
        )
        assert re.search(pattern, text), table


def test_tables_sql_mirrors_outbox_schemas_partitions_and_clusters() -> None:
    # Arrange
    text = (SRC / "sql" / "bigquery" / "tables.sql").read_text(encoding="utf-8")
    pattern = re.compile(
        r"CREATE TABLE IF NOT EXISTS `\$\{project\}\.\$\{dataset\}\.(\w+)` \((.*?)\n\)"
        r"(?:\nPARTITION BY TIMESTAMP_TRUNC\((\w+), MONTH\))?(?:\nCLUSTER BY ([\w, ]+))?;",
        re.DOTALL,
    )

    # Act
    parsed = {
        m.group(1): (
            tuple(tuple(line.strip().rstrip(",").split()) for line in m.group(2).strip().splitlines()),
            m.group(3),
            m.group(4),
        )
        for m in pattern.finditer(text)
    }

    # Assert
    expected_names = {f"raw_{t}" for t in FACT_TABLES} | set(REFERENCE_TABLES)
    assert set(parsed) == expected_names
    for name, (columns, partition, cluster) in parsed.items():
        table = name.removeprefix("raw_") if name.startswith("raw_") else name
        assert columns == TABLE_SCHEMAS[table], name
        spec = build_load_spec(
            OutboxFile(table, Path("x"), 0, 0, "WRITE_APPEND"), project="p-123456", dataset="d"
        )
        assert partition == spec.partition_field, name
        assert (cluster.split(", ") if cluster else []) == list(spec.clustering_fields), name


def test_ensure_dataset_runs_every_ddl_statement_through_the_gateway() -> None:
    # Arrange
    gateway = FakeGateway()

    # Act
    ensure_dataset(FakeBigQueryConfig(), client=gateway)

    # Assert
    assert gateway.statements == ddl_statements(FakeBigQueryConfig())
    assert gateway.loads == []


def test_ensure_dataset_validates_identifiers_before_any_call() -> None:
    gateway = FakeGateway()
    with pytest.raises(ValueError, match="project"):
        ensure_dataset(FakeBigQueryConfig(project="Bad Project"), client=gateway)
    with pytest.raises(ValueError, match="location"):
        ensure_dataset(FakeBigQueryConfig(location="US'); --"), client=gateway)
    assert gateway.statements == []


# ----------------------------------------------------------------------------- BQ-09 cost
def test_check_view_costs_dry_runs_every_view_against_the_byte_ceiling() -> None:
    # Arrange
    gateway = FakeGateway()
    gateway.bytes_by_view = {"v_calls": 200 * 1024 * 1024, "v_sessions": 10 * 1024}

    # Act
    checks = check_view_costs(FakeBigQueryConfig(), client=gateway, ceiling_bytes=1 << 30,
                              volume_factor=10)

    # Assert
    assert [c.view for c in checks] == list(VIEW_NAMES)
    by_view = {c.view: c for c in checks}
    assert by_view["v_calls"].ok is False  # 200 MiB x 10 > 1 GiB
    assert by_view["v_sessions"].ok is True
    assert by_view["v_calls"].bytes_processed == 200 * 1024 * 1024
    assert gateway.statements == []  # dry runs only, nothing executed
    assert gateway.dry_runs[0] == "SELECT * FROM `devhack-3f0c2.agent_metrics.v_calls`"


# ------------------------------------------------------------------------- BQ-08 reconcile
def _local_daily(store: ContractStore) -> None:
    store.query(
        "CREATE TABLE v_daily_project_cost (local_date DATE, project_id TEXT, host TEXT, "
        "calls BIGINT, input_tokens BIGINT, output_tokens BIGINT, cache_write_tokens BIGINT, "
        "cache_read_tokens BIGINT, cost_usd DECIMAL(38,9), unpriced_calls BIGINT)"
    )
    for host, cost in (("claude-code", "0.100000000"), ("antigravity-cli", "0.050000000")):
        store.query(
            "INSERT INTO v_daily_project_cost VALUES (?, ?, ?, 2, 100, 20, 0, 1000, ?, 1)",
            [date(2026, 10, 16), PROJECT_ID, host, Decimal(cost)],
        )


def _cloud_row(project_id: str, cost: str) -> dict[str, object]:
    return {
        "local_date": date(2026, 10, 16), "project_id": project_id, "calls": 4,
        "input_tokens": 200, "output_tokens": 40, "cache_write_tokens": 0,
        "cache_read_tokens": 2000, "cost_usd": Decimal(cost), "unpriced_calls": 2,
    }


def test_reconcile_reports_no_difference_when_totals_match(store: ContractStore, cfg: FakeConfig) -> None:
    # Arrange
    _local_daily(store)
    gateway = FakeGateway()
    gateway.query_rows = [_cloud_row(PROJECT_ID, "0.15")]

    # Act
    diffs = reconcile(cfg, store, date(2026, 10, 1), date(2026, 10, 31), client=gateway)

    # Assert
    assert diffs == []
    [sql] = gateway.statements
    assert "`devhack-3f0c2.agent_metrics.v_daily_project_cost`" in sql
    assert "DATE '2026-10-01' AND DATE '2026-10-31'" in sql


def test_reconcile_lists_each_metric_that_differs(store: ContractStore, cfg: FakeConfig) -> None:
    # Arrange
    _local_daily(store)
    gateway = FakeGateway()
    gateway.query_rows = [_cloud_row(PROJECT_ID, "0.149999999")]

    # Act
    diffs = reconcile(cfg, store, date(2026, 10, 1), date(2026, 10, 31), client=gateway)

    # Assert
    assert diffs == [{
        "local_date": "2026-10-16", "project_id": PROJECT_ID, "metric": "cost_usd",
        "local": Decimal("0.150000000"), "cloud": Decimal("0.149999999"),
    }]


def test_reconcile_reports_rows_missing_on_either_side(store: ContractStore, cfg: FakeConfig) -> None:
    _local_daily(store)
    gateway = FakeGateway()
    gateway.query_rows = [{**_cloud_row("git:other", "1"), "local_date": date(2026, 10, 17)}]
    diffs = reconcile(cfg, store, date(2026, 10, 1), date(2026, 10, 31), client=gateway)
    assert {(d["project_id"], d["metric"]) for d in diffs} >= {(PROJECT_ID, "calls"), ("git:other", "calls")}
    missing_cloud = next(d for d in diffs if d["project_id"] == PROJECT_ID and d["metric"] == "calls")
    assert (missing_cloud["local"], missing_cloud["cloud"]) == (4, None)


def test_reconcile_maps_local_ids_through_the_anonymizer(store: ContractStore) -> None:
    # Arrange
    _local_daily(store)
    anon = Anonymizer(SALT)
    cfg = FakeConfig(bigquery=FakeBigQueryConfig(anonymize_projects=True))
    gateway = FakeGateway()
    gateway.query_rows = [_cloud_row(str(anon(PROJECT_ID)), "0.15")]

    # Act / Assert
    assert reconcile(cfg, store, date(2026, 10, 1), date(2026, 10, 31), client=gateway,
                     anonymizer=anon) == []
    with pytest.raises(ValueError, match="anonymizer"):
        reconcile(cfg, store, date(2026, 10, 1), date(2026, 10, 31), client=gateway)


# ---------------------------------------------------------------------- describe_sync text
def test_describe_sync_ok_and_error_messages() -> None:
    ok = SyncResult(
        status="ok",
        loads=(sink.LoadResult("llm_calls", 3, "job-1", True, None),),
        backlog=dict.fromkeys(FACT_TABLES, 0),
    )
    err = SyncResult(
        status="error",
        loads=(sink.LoadResult("llm_calls", 3, "", False, "BadRequest"),),
        backlog={**dict.fromkeys(FACT_TABLES, 0), "llm_calls": 3},
    )
    assert describe_sync(ok, FakeBigQueryConfig()) == (
        "Synced 3 rows to devhack-3f0c2.agent_metrics (1 load jobs)."
    )
    message = describe_sync(err, FakeBigQueryConfig())
    assert "llm_calls (BadRequest)" in message and "3 rows" in message and "next sync" in message


# ------------------------------------------------------ compatibility with the real 11B store
def test_sync_runs_against_the_real_store_home_and_config(tmp_path: Path) -> None:
    # Arrange
    home = AppHome.resolve(str(tmp_path / "home"))
    cfg = Config(timezone="UTC", bigquery=BigQueryConfig(enabled=True, project="devhack-3f0c2"))
    gateway = FakeGateway()
    with Store.open(home, read_only=False, lock_timeout_s=5.0) as store:
        store.migrate()
        store.load_reference_data(
            pricing=load_pricing(None),
            host_defaults={Host.CLAUDE_CODE: None},
            projects=ProjectsConfig(projects={}, path_aliases={}, ignore=(), merges={}),
            project_refs=[make_project()],
            settings={"timezone": "UTC"},
        )
        store.apply_batches([make_batch()])

        # Act
        result = sync(home, cfg, store, client_factory=factory_for(gateway), now=NOW)

        # Assert
        assert result.status == "ok"
        assert result.backlog == dict.fromkeys(FACT_TABLES, 0)
        for table in FACT_TABLES:
            assert store.get_meta(f"bq_watermark:{table}") == str(store.max_seq(table))
    [(_, calls)] = gateway.loaded("raw_llm_calls")
    assert calls[0]["call_id"] == CALL_ID
    assert calls[0]["ts"] == "2026-10-16T14:00:05.000000Z"
    assert calls[0]["project_id"] == "git:0123456789abcdef"
    [(_, prices)] = gateway.loaded("pricing")
    assert prices and all(isinstance(row["input_per_mtok"], str) for row in prices)
    assert ndjson_files(FakeHome(home.root)) == []


# -------------------------------------------------------- real-SDK adapter (fake google module)
class _Recorder:
    def __init__(self, *args: object, **kwargs: object) -> None:
        self.args, self.kwargs = args, kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)


class _FakeJob:
    def __init__(self, job_id: str, total_bytes: int = 0) -> None:
        self.job_id = job_id
        self.total_bytes_processed = total_bytes
        self.waited = False

    def result(self) -> list[dict[str, object]]:
        self.waited = True
        return [{"n": 1}]


class _FakeClient:
    instances: ClassVar[list[_FakeClient]] = []

    def __init__(self, *, project: str, location: str) -> None:
        self.project, self.location = project, location
        self.loads: list[tuple[bytes, str, _Recorder]] = []
        self.queries: list[tuple[str, object]] = []
        self.jobs: list[_FakeJob] = []
        _FakeClient.instances.append(self)

    def load_table_from_file(self, fh: object, destination: str, *, job_config: _Recorder) -> _FakeJob:
        assert hasattr(fh, "read")
        self.loads.append((fh.read(), destination, job_config))
        self.jobs.append(_FakeJob("load-1"))
        return self.jobs[-1]

    def query(self, sql: str, job_config: object = None) -> _FakeJob:
        self.queries.append((sql, job_config))
        self.jobs.append(_FakeJob("query-1", total_bytes=4096))
        return self.jobs[-1]


@pytest.fixture
def fake_google(monkeypatch: pytest.MonkeyPatch) -> Iterator[types.ModuleType]:
    module = types.ModuleType("google.cloud.bigquery")
    module.Client = _FakeClient  # type: ignore[attr-defined]
    module.LoadJobConfig = _Recorder  # type: ignore[attr-defined]
    module.QueryJobConfig = _Recorder  # type: ignore[attr-defined]
    module.SchemaField = _Recorder  # type: ignore[attr-defined]
    module.TimePartitioning = _Recorder  # type: ignore[attr-defined]
    module.SourceFormat = types.SimpleNamespace(NEWLINE_DELIMITED_JSON="NEWLINE_DELIMITED_JSON")  # type: ignore[attr-defined]
    module.TimePartitioningType = types.SimpleNamespace(MONTH="MONTH")  # type: ignore[attr-defined]
    google = types.ModuleType("google")
    cloud = types.ModuleType("google.cloud")
    google.cloud = cloud  # type: ignore[attr-defined]
    cloud.bigquery = module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "google", google)
    monkeypatch.setitem(sys.modules, "google.cloud", cloud)
    monkeypatch.setitem(sys.modules, "google.cloud.bigquery", module)
    _FakeClient.instances = []
    yield module


def test_google_gateway_builds_an_ndjson_load_job_with_explicit_schema(
    fake_google: types.ModuleType, tmp_path: Path
) -> None:
    # Arrange
    path = tmp_path / "rows.ndjson"
    path.write_text('{"call_id":"a"}\n', encoding="utf-8")
    spec = build_load_spec(
        OutboxFile("llm_calls", path, 1, 1, "WRITE_APPEND"), project="devhack-3f0c2", dataset="d"
    )

    # Act
    gateway = google_gateway("devhack-3f0c2", "US")
    job_id = gateway.load_ndjson(path, spec)

    # Assert
    [client] = _FakeClient.instances
    assert (client.project, client.location) == ("devhack-3f0c2", "US")
    [(payload, destination, config)] = client.loads
    assert payload == b'{"call_id":"a"}\n'
    assert destination == "devhack-3f0c2.d.raw_llm_calls"
    assert config.kwargs["source_format"] == "NEWLINE_DELIMITED_JSON"
    assert config.kwargs["write_disposition"] == "WRITE_APPEND"
    assert config.kwargs["ignore_unknown_values"] is False
    schema = config.kwargs["schema"]
    assert isinstance(schema, list)
    first = schema[0]
    assert isinstance(first, _Recorder)
    assert (first.args, first.kwargs) == (("call_id", "STRING"), {"mode": "NULLABLE"})
    assert len(schema) == len(TABLE_SCHEMAS["llm_calls"])
    partition = config.kwargs["time_partitioning"]
    assert isinstance(partition, _Recorder)
    assert partition.kwargs == {"type_": "MONTH", "field": "ts"}
    assert config.kwargs["clustering_fields"] == ["project_id", "host"]
    assert client.jobs[0].waited and job_id == "load-1"


def test_google_gateway_reference_load_has_no_partitioning(
    fake_google: types.ModuleType, tmp_path: Path
) -> None:
    path = tmp_path / "p.ndjson"
    path.write_bytes(b"")
    spec = build_load_spec(OutboxFile("pricing", path, 0, 0, "WRITE_TRUNCATE"), project="p-123456", dataset="d")
    google_gateway("p-123456", "US").load_ndjson(path, spec)
    [(_, _, config)] = _FakeClient.instances[0].loads
    assert "time_partitioning" not in config.kwargs and "clustering_fields" not in config.kwargs


def test_google_gateway_execute_and_dry_run(fake_google: types.ModuleType) -> None:
    # Act
    gateway = google_gateway("devhack-3f0c2", "US")
    rows = gateway.execute("SELECT 1 AS n")
    scanned = gateway.dry_run_bytes("SELECT * FROM `p.d.v_calls`")

    # Assert
    client = _FakeClient.instances[0]
    assert rows == [{"n": 1}]
    assert scanned == 4096
    (_, plain), (_, dry) = client.queries
    assert plain is None
    assert isinstance(dry, _Recorder)
    assert dry.kwargs == {"dry_run": True, "use_query_cache": False}


def test_default_factory_is_used_when_none_is_given(
    fake_google: types.ModuleType, store: ContractStore, home: FakeHome, cfg: FakeConfig
) -> None:
    result = sync(home, replace(cfg, bigquery=replace(cfg.bigquery, location="EU")), store, now=NOW)
    assert result.status == "ok"
    [client] = _FakeClient.instances
    assert (client.project, client.location) == ("devhack-3f0c2", "EU")
