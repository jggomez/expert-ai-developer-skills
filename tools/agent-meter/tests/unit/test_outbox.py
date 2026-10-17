"""Tests for ``agent_meter.sinks.outbox`` (ADR §3.11, contracts §3.11/§7; BQ-01, BQ-03, PV-01/02/04)."""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from agent_meter.sinks import outbox
from agent_meter.sinks.outbox import (
    FACT_TABLES,
    REFERENCE_TABLES,
    TABLE_SCHEMAS,
    Anonymizer,
    OutboxFile,
    discard_stale,
    encode_row,
    load_salt,
    materialize,
    new_batch_id,
    pending_counts,
    watermark,
)
from tests.cloud.sink_support import (
    BASE,
    PROJECT_ID,
    ContractStore,
    block_network,
    call_row,
    seed_calls,
    seed_graph,
    seed_reference,
)
from tests.fixtures.canary import CANARY

BATCH = "20261016T140000Z-0a1b2c3d"
NOW = datetime(2026, 10, 16, 15, 0, 0, tzinfo=UTC)
SALT = bytes(range(32))

DUCKDB_TO_BIGQUERY = {
    "VARCHAR": "STRING",
    "BIGINT": "INT64",
    "INTEGER": "INT64",
    "SMALLINT": "INT64",
    "BOOLEAN": "BOOL",
    "TIMESTAMP WITH TIME ZONE": "TIMESTAMP",
    "DATE": "DATE",
    "DECIMAL(12,6)": "NUMERIC",
    "DECIMAL(18,4)": "NUMERIC",
    "DECIMAL(8,2)": "NUMERIC",
}


@pytest.fixture(autouse=True)
def _offline(monkeypatch: pytest.MonkeyPatch) -> None:
    block_network(monkeypatch)


@pytest.fixture
def store() -> ContractStore:
    return ContractStore()


def read_ndjson(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def by_table(files: list[OutboxFile]) -> dict[str, OutboxFile]:
    return {f.table: f for f in files}


# ---------------------------------------------------------------------------------- schema
def test_table_lists_match_contract() -> None:
    assert FACT_TABLES == ("llm_calls", "tasks", "agent_runs", "tool_uses", "sessions")
    assert REFERENCE_TABLES == (
        "projects", "pricing", "pricing_aliases", "host_defaults", "dev_hours_manual",
        "dev_hours_derived", "task_tags", "tag_history", "settings", "untracked",
    )
    assert set(TABLE_SCHEMAS) == set(FACT_TABLES) | set(REFERENCE_TABLES)


@pytest.mark.parametrize("table", FACT_TABLES + REFERENCE_TABLES)
def test_schema_mirrors_duckdb_columns_minus_hash_and_rank(store: ContractStore, table: str) -> None:
    # Arrange
    expected = [
        (name, DUCKDB_TO_BIGQUERY[kind])
        for name, kind in store.columns(table)
        if name not in {"row_hash", "owner_rank"}
    ] + [("_uploaded_at", "TIMESTAMP")]

    # Act
    actual = list(TABLE_SCHEMAS[table])

    # Assert
    assert actual == expected


# ------------------------------------------------------------------------------ anonymizer
def test_anonymizer_is_a_stable_salted_hmac_prefix() -> None:
    # Arrange
    anon = Anonymizer(SALT)
    expected = hmac.new(SALT, b"Client Z", hashlib.sha256).hexdigest()[:16]

    # Act
    first, second = anon("Client Z"), anon("Client Z")

    # Assert
    assert first == second == expected
    assert len(first or "") == 16
    assert anon(None) is None
    assert Anonymizer(b"x" * 32)("Client Z") != first  # salt changes the hash (PV-02)
    assert first != hashlib.sha256(b"Client Z").hexdigest()[:16]  # not an unsalted hash


def test_anonymizer_rejects_short_salt() -> None:
    with pytest.raises(ValueError, match="salt"):
        Anonymizer(b"short")


def test_load_salt_reads_bytes_and_rejects_missing_or_short(tmp_path: Path) -> None:
    # Arrange
    good, short = tmp_path / "secret", tmp_path / "short"
    good.write_bytes(SALT)
    short.write_bytes(b"abc")

    # Act / Assert
    assert load_salt(good) == SALT
    with pytest.raises(ValueError, match="salt"):
        load_salt(short)
    with pytest.raises(ValueError, match="salt"):
        load_salt(tmp_path / "missing")


# -------------------------------------------------------------------------------- encoding
def test_encode_row_uses_contract_value_encodings() -> None:
    # Arrange
    schema = (
        ("s", "STRING"), ("i", "INT64"), ("b", "BOOL"), ("t", "TIMESTAMP"), ("d", "DATE"),
        ("n", "NUMERIC"), ("z", "STRING"), ("_uploaded_at", "TIMESTAMP"),
    )
    bogota = timezone(timedelta(hours=-5))
    row = {
        "s": "ñandú", "i": 7, "b": True, "t": datetime(2026, 10, 16, 13, 42, 7, 123456, tzinfo=bogota),
        "d": date(2026, 10, 16), "n": Decimal("0.200000"), "z": None, "ignored": "x",
    }

    # Act
    line = encode_row(row, schema, uploaded_at=NOW)

    # Assert
    assert line.endswith("\n") and line.count("\n") == 1
    assert json.loads(line) == {
        "s": "ñandú", "i": 7, "b": True, "t": "2026-10-16T18:42:07.123456Z", "d": "2026-10-16",
        "n": "0.200000", "z": None, "_uploaded_at": "2026-10-16T15:00:00.000000Z",
    }
    assert list(json.loads(line)) == [name for name, _ in schema]  # explicit projection, in order


def test_encode_row_writes_plain_decimal_notation() -> None:
    line = encode_row({"n": Decimal("1E+3")}, (("n", "NUMERIC"),), uploaded_at=NOW)
    assert json.loads(line) == {"n": "1000"}


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("TIMESTAMP", datetime(2026, 10, 16, 14, 0)),  # naive
        ("NUMERIC", 0.2),  # float money (NFR-04)
        ("NUMERIC", Decimal("NaN")),
        ("INT64", True),
        ("INT64", "7"),
        ("BOOL", 1),
        ("DATE", datetime(2026, 10, 16, tzinfo=UTC)),
        ("STRING", 5),
    ],
)
def test_encode_row_rejects_values_that_do_not_match_the_column_type(kind: str, value: object) -> None:
    with pytest.raises((TypeError, ValueError)):
        encode_row({"c": value}, (("c", kind),), uploaded_at=NOW)


def test_encode_row_rejects_a_missing_column() -> None:
    with pytest.raises(ValueError, match="missing"):
        encode_row({}, (("c", "STRING"),), uploaded_at=NOW)


# ----------------------------------------------------------------------------- materialize
def test_materialize_writes_fact_rows_past_the_watermark_as_append(
    store: ContractStore, tmp_path: Path
) -> None:
    # Arrange
    ids = seed_calls(store, 3)
    store.set_meta("bq_watermark:llm_calls", "1")

    # Act
    files = by_table(materialize(store, tmp_path, batch_id=BATCH, now=NOW))

    # Assert
    calls = files["llm_calls"]
    assert calls.path == tmp_path / "llm_calls" / f"{BATCH}.ndjson"
    assert (calls.rows, calls.max_seq, calls.disposition) == (2, 3, "WRITE_APPEND")
    assert [r["call_id"] for r in read_ndjson(calls.path)] == ids[1:]
    assert store.get_meta("bq_watermark:llm_calls") == "1"  # materialize never advances it


def test_materialize_skips_fact_tables_without_new_rows(store: ContractStore, tmp_path: Path) -> None:
    # Arrange
    seed_calls(store, 2)
    store.set_meta("bq_watermark:llm_calls", "2")

    # Act
    files = by_table(materialize(store, tmp_path, batch_id=BATCH, now=NOW))

    # Assert
    assert not set(files) & set(FACT_TABLES)
    assert not (tmp_path / "llm_calls").exists()


def test_materialize_full_ignores_watermarks_and_truncates(store: ContractStore, tmp_path: Path) -> None:
    # Arrange (BQ-03)
    seed_graph(store)
    seed_calls(store, 3)
    for table in FACT_TABLES:
        store.set_meta(f"bq_watermark:{table}", str(store.max_seq(table)))

    # Act
    files = by_table(materialize(store, tmp_path, batch_id=BATCH, full=True, now=NOW))

    # Assert
    assert set(files) == set(FACT_TABLES) | set(REFERENCE_TABLES)
    assert {f.disposition for f in files.values()} == {"WRITE_TRUNCATE"}
    assert files["llm_calls"].rows == 3
    assert files["llm_calls"].max_seq == store.max_seq("llm_calls")


def test_materialize_writes_every_reference_table_as_truncate(store: ContractStore, tmp_path: Path) -> None:
    # Arrange
    seed_reference(store)

    # Act
    files = by_table(materialize(store, tmp_path, batch_id=BATCH, now=NOW))

    # Assert
    for table in REFERENCE_TABLES:
        assert files[table].disposition == "WRITE_TRUNCATE"
        assert files[table].rows == 1
    pricing = read_ndjson(files["pricing"].path)[0]
    assert pricing["input_per_mtok"] == "4.000000"
    assert pricing["effective_from"] == "2000-01-01"


def test_materialize_writes_empty_reference_files_so_removals_propagate(
    store: ContractStore, tmp_path: Path
) -> None:
    files = by_table(materialize(store, tmp_path, batch_id=BATCH, now=NOW))
    assert files["pricing"].rows == 0
    assert files["pricing"].path.read_bytes() == b""


def test_ndjson_rows_are_utf8_without_bom_and_carry_only_bigquery_columns(
    store: ContractStore, tmp_path: Path
) -> None:
    # Arrange
    seed_graph(store)
    seed_calls(store, 1)

    # Act
    files = materialize(store, tmp_path, batch_id=BATCH, now=NOW)

    # Assert
    for f in files:
        raw = f.path.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert raw == b"" or raw.endswith(b"\n")
        for row in read_ndjson(f.path):
            assert list(row) == [name for name, _ in TABLE_SCHEMAS[f.table]]
            assert "row_hash" not in row and "owner_rank" not in row
            assert row["_uploaded_at"] == "2026-10-16T15:00:00.000000Z"
    call = read_ndjson(by_table(files)["llm_calls"].path)[0]
    assert call["ts"] == "2026-10-16T14:00:00.123456Z"
    assert call["is_error"] is False
    assert call["thinking_tokens"] is None


def test_anonymization_replaces_names_in_every_file(store: ContractStore, tmp_path: Path) -> None:
    # Arrange (PV-02, contracts §7)
    seed_graph(store)
    seed_calls(store, 1)
    anon = Anonymizer(SALT)

    # Act
    files = by_table(materialize(store, tmp_path, batch_id=BATCH, anonymizer=anon, now=NOW))

    # Assert
    hashed = anon(PROJECT_ID)
    project = read_ndjson(files["projects"].path)[0]
    assert project["project_id"] == hashed
    assert project["display_name"] == anon("Project X")
    assert project["client"] == anon("Client Z")
    assert project["remote_url"] == anon("github.com/owner/project-x")
    for table in ("llm_calls", "tasks", "agent_runs", "tool_uses", "sessions",
                  "dev_hours_manual", "dev_hours_derived", "tag_history"):
        assert {r["project_id"] for r in read_ndjson(files[table].path)} == {hashed}
    assert [r["tag"] for r in read_ndjson(files["tag_history"].path)] == [anon("Track 11")]
    assert [r["tag"] for r in read_ndjson(files["task_tags"].path)] == [anon("Track 11")]  # L-3
    everything = b"".join(f.path.read_bytes() for f in files.values())
    assert PROJECT_ID.encode() not in everything
    assert b"Client Z" not in everything
    assert b"Track 11" not in everything


def test_canary_salt_and_local_only_data_never_reach_the_outbox(
    store: ContractStore, tmp_path: Path
) -> None:
    # Arrange (PV-01, PV-04): canary in every local-only or anonymized slot
    seed_graph(store)
    store.insert("llm_calls", call_row(store, 9, owner_rank=f"0:{CANARY}", row_hash=CANARY))
    seed_reference(store, display_name=CANARY, client=CANARY, remote_url=f"github.com/{CANARY}/x")
    store.set_meta("adc_token_probe", CANARY)
    store.insert("path_map", {"path_hash": CANARY, "project_id": PROJECT_ID, "resolved_at": BASE})
    store.insert(
        "source_units",
        {"host": "claude-code", "unit_id": CANARY, "fingerprint": CANARY,
         "format_fingerprint": CANARY, "last_ingested_at": BASE},
    )
    store.insert(
        "diagnostics",
        {"run_at": BASE, "host": "claude-code", "kind": "corrupt", "unit_hash": CANARY,
         "file_kind": "cc_main", "error_class": CANARY, "count": 1},
    )

    # Act
    files = materialize(store, tmp_path, batch_id=BATCH, anonymizer=Anonymizer(SALT), now=NOW)

    # Assert
    everything = b"".join(p.read_bytes() for p in tmp_path.rglob("*") if p.is_file())
    assert files
    assert CANARY.encode() not in everything
    assert SALT not in everything
    assert SALT.hex().encode() not in everything
    assert {p.parent.name for p in tmp_path.rglob("*.ndjson")} <= set(TABLE_SCHEMAS)


def test_materialize_rejects_a_batch_id_that_is_not_the_contract_format(
    store: ContractStore, tmp_path: Path
) -> None:
    with pytest.raises(ValueError, match="batch_id"):
        materialize(store, tmp_path, batch_id="../../etc/passwd", now=NOW)


def test_new_batch_id_has_the_contract_format() -> None:
    batch = new_batch_id(NOW)
    assert re.fullmatch(r"20261016T150000Z-[0-9a-f]{8}", batch)
    assert new_batch_id(NOW) != batch


# --------------------------------------------------------------------- watermark & backlog
def test_watermark_defaults_to_zero_and_rejects_corrupt_values(store: ContractStore) -> None:
    assert watermark(store, "llm_calls") == 0
    store.set_meta("bq_watermark:llm_calls", "not-a-number")
    with pytest.raises(ValueError, match="bq_watermark:llm_calls"):
        watermark(store, "llm_calls")


def test_watermark_is_only_defined_for_fact_tables(store: ContractStore) -> None:
    with pytest.raises(ValueError, match="fact table"):
        watermark(store, "projects")


def test_pending_counts_reports_rows_past_each_watermark(store: ContractStore) -> None:
    # Arrange
    seed_graph(store)
    seed_calls(store, 4)
    store.set_meta("bq_watermark:llm_calls", str(store.max_seq("llm_calls") - 1))

    # Act
    counts = pending_counts(store)

    # Assert
    assert counts == {"llm_calls": 1, "tasks": 1, "agent_runs": 1, "tool_uses": 1, "sessions": 1}


def test_discard_stale_removes_only_outbox_ndjson_files(tmp_path: Path) -> None:
    # Arrange
    stale = tmp_path / "llm_calls" / f"{BATCH}.ndjson"
    stale.parent.mkdir(parents=True)
    stale.write_text("{}\n", encoding="utf-8")
    foreign = tmp_path / "notes.txt"
    foreign.write_text("keep", encoding="utf-8")

    # Act
    removed = discard_stale(tmp_path)

    # Assert
    assert removed == 1
    assert not stale.exists() and foreign.exists()
    assert discard_stale(tmp_path / "missing") == 0


def test_outbox_module_has_no_google_imports() -> None:
    source = Path(outbox.__file__).read_text(encoding="utf-8")
    assert "google" not in source
