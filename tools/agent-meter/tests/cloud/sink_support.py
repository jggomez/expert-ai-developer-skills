"""Shared test support for the Track 11D sink tests (unit and cloud).

``ContractStore`` is a small DuckDB-backed stand-in for ``agent_meter.store.Store`` that
implements only the surface the sinks use (contracts §3.7: ``get_meta``, ``set_meta``,
``rows_since``, ``max_seq``, ``query``). Its DDL mirrors contracts §4 so the outbox column
projection is tested against the real column set without depending on Track 11B code.
"""

from __future__ import annotations

import socket
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

import duckdb
import pytest

# contracts.md §4 (tables the sink reads, plus local-only tables that must never be exported).
CONTRACT_DDL = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE sessions (
  session_id TEXT PRIMARY KEY, host TEXT NOT NULL, project_id TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ NOT NULL, status TEXT NOT NULL,
  host_version TEXT, owner_rank TEXT NOT NULL, row_hash TEXT NOT NULL, ingest_seq BIGINT NOT NULL,
  schema_version SMALLINT NOT NULL DEFAULT 1);
CREATE TABLE tasks (
  task_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, host TEXT NOT NULL, project_id TEXT NOT NULL,
  seq_in_session INTEGER NOT NULL, started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ NOT NULL,
  wall_clock_ms BIGINT NOT NULL, active_ms BIGINT NOT NULL, reported_ms BIGINT, duration_source TEXT NOT NULL,
  status TEXT NOT NULL, agent_runs INTEGER NOT NULL, max_spawn_depth INTEGER NOT NULL,
  critical_path_ms BIGINT NOT NULL, critical_path TEXT NOT NULL, retries INTEGER NOT NULL,
  retry_summary TEXT NOT NULL, owner_rank TEXT NOT NULL, row_hash TEXT NOT NULL, ingest_seq BIGINT NOT NULL,
  schema_version SMALLINT NOT NULL DEFAULT 1);
CREATE TABLE agent_runs (
  agent_run_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, session_id TEXT NOT NULL, host TEXT NOT NULL,
  project_id TEXT NOT NULL, parent_agent_run_id TEXT, agent_type TEXT NOT NULL, description_hash TEXT,
  spawn_depth INTEGER NOT NULL, started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ NOT NULL,
  active_ms BIGINT NOT NULL, status TEXT NOT NULL, errors INTEGER NOT NULL, files_touched INTEGER NOT NULL,
  test_runs INTEGER NOT NULL, test_failures INTEGER NOT NULL, tools_untracked BOOLEAN NOT NULL,
  owner_rank TEXT NOT NULL, row_hash TEXT NOT NULL, ingest_seq BIGINT NOT NULL,
  schema_version SMALLINT NOT NULL DEFAULT 1);
CREATE TABLE llm_calls (
  call_id TEXT PRIMARY KEY, host TEXT NOT NULL, project_id TEXT NOT NULL, session_id TEXT NOT NULL,
  task_id TEXT NOT NULL, agent_run_id TEXT NOT NULL, ts TIMESTAMPTZ NOT NULL,
  model TEXT, model_label TEXT,
  input_tokens BIGINT, output_tokens BIGINT, thinking_tokens BIGINT,
  cache_write_5m_tokens BIGINT, cache_write_1h_tokens BIGINT, cache_read_tokens BIGINT,
  latency_ms BIGINT, speed TEXT, inference_geo TEXT, is_error BOOLEAN NOT NULL, source_format TEXT NOT NULL,
  owner_rank TEXT NOT NULL, row_hash TEXT NOT NULL, ingest_seq BIGINT NOT NULL,
  schema_version SMALLINT NOT NULL DEFAULT 1);
CREATE TABLE tool_uses (
  agent_run_id TEXT NOT NULL, tool_name TEXT NOT NULL, calls INTEGER NOT NULL, errors INTEGER NOT NULL,
  project_id TEXT NOT NULL, host TEXT NOT NULL, ingest_seq BIGINT NOT NULL,
  PRIMARY KEY (agent_run_id, tool_name));
CREATE TABLE source_units (host TEXT NOT NULL, unit_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
  format_fingerprint TEXT NOT NULL, last_ingested_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (host, unit_id));
CREATE TABLE diagnostics (run_at TIMESTAMPTZ NOT NULL, host TEXT NOT NULL, kind TEXT NOT NULL,
  unit_hash TEXT NOT NULL, file_kind TEXT NOT NULL, error_class TEXT, count INTEGER NOT NULL);
CREATE TABLE untracked (conversation_id TEXT PRIMARY KEY, host TEXT NOT NULL, reason TEXT NOT NULL,
  observed_from DATE NOT NULL, observed_to DATE NOT NULL, ingest_seq BIGINT NOT NULL);
CREATE TABLE path_map (path_hash TEXT PRIMARY KEY, project_id TEXT NOT NULL, resolved_at TIMESTAMPTZ NOT NULL);
CREATE TABLE projects (project_id TEXT PRIMARY KEY, kind TEXT NOT NULL, display_name TEXT NOT NULL,
  remote_url TEXT, client TEXT, billing_model TEXT, hourly_rate DECIMAL(18,4), fixed_price DECIMAL(18,4),
  rate_currency TEXT);
CREATE TABLE pricing (model TEXT NOT NULL, effective_from DATE NOT NULL, min_prompt_tokens BIGINT NOT NULL,
  input_per_mtok DECIMAL(12,6) NOT NULL, output_per_mtok DECIMAL(12,6) NOT NULL,
  cache_write_5m_per_mtok DECIMAL(12,6), cache_write_1h_per_mtok DECIMAL(12,6),
  cache_read_per_mtok DECIMAL(12,6) NOT NULL, source TEXT NOT NULL, source_url TEXT, fetched_at DATE,
  PRIMARY KEY (model, effective_from, min_prompt_tokens));
CREATE TABLE pricing_aliases (alias TEXT PRIMARY KEY, model TEXT NOT NULL, estimated BOOLEAN NOT NULL,
  source TEXT NOT NULL);
CREATE TABLE host_defaults (host TEXT PRIMARY KEY, default_model TEXT);
CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE dev_hours_manual (project_id TEXT NOT NULL, period TEXT NOT NULL, hours DECIMAL(8,2) NOT NULL,
  set_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (project_id, period));
CREATE TABLE dev_hours_derived (project_id TEXT NOT NULL, local_date DATE NOT NULL, hours DECIMAL(8,2) NOT NULL,
  PRIMARY KEY (project_id, local_date));
CREATE TABLE tag_history (project_id TEXT NOT NULL, tag TEXT, from_ts TIMESTAMPTZ NOT NULL, to_ts TIMESTAMPTZ,
  PRIMARY KEY (project_id, from_ts));
CREATE TABLE task_tags (task_id TEXT PRIMARY KEY, tag TEXT NOT NULL, set_at TIMESTAMPTZ NOT NULL);
"""

BASE = datetime(2026, 10, 16, 14, 0, 0, 123456, tzinfo=UTC)
PROJECT_ID = "git:3f2a9c0d1e2b4a56"


class ContractStore:
    """DuckDB store with the contracts §4 schema and the Store read/meta surface."""

    def __init__(self) -> None:
        self._con = duckdb.connect(":memory:")
        self._con.execute("SET TimeZone = 'UTC'")
        self._con.execute(CONTRACT_DDL)
        self._seq = 0

    # --- Store surface used by the sinks (contracts §3.7) -----------------------------
    def get_meta(self, key: str) -> str | None:
        row = self._con.execute("SELECT value FROM meta WHERE key = ?", [key]).fetchone()
        return None if row is None else str(row[0])

    def set_meta(self, key: str, value: str) -> None:
        self._con.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", [key, value])

    def rows_since(
        self, table: str, after_seq: int, columns: Sequence[str]
    ) -> Iterator[dict[str, object]]:
        cols = ", ".join(columns)
        sql = f"SELECT {cols} FROM {table} WHERE ingest_seq > ? ORDER BY ingest_seq"
        yield from self.query(sql, [after_seq])

    def max_seq(self, table: str) -> int:
        row = self._con.execute(f"SELECT COALESCE(MAX(ingest_seq), 0) FROM {table}").fetchone()
        return 0 if row is None else int(row[0])

    def query(self, sql: str, params: Sequence[object] = ()) -> list[dict[str, object]]:
        cur = self._con.execute(sql, list(params))
        if cur.description is None:
            return []
        names = [d[0] for d in cur.description]
        return [dict(zip(names, row, strict=True)) for row in cur.fetchall()]

    # --- Seeding helpers ----------------------------------------------------------------
    def next_seq(self) -> int:
        self._seq += 1
        return self._seq

    def insert(self, table: str, row: Mapping[str, object]) -> None:
        cols = ", ".join(row)
        marks = ", ".join("?" for _ in row)
        verb = "INSERT" if table == "diagnostics" else "INSERT OR REPLACE"  # diagnostics has no PK
        self._con.execute(f"{verb} INTO {table} ({cols}) VALUES ({marks})", list(row.values()))

    def columns(self, table: str) -> list[tuple[str, str]]:
        rows = self._con.execute(
            "SELECT column_name, data_type FROM information_schema.columns "
            "WHERE table_name = ? ORDER BY ordinal_position",
            [table],
        ).fetchall()
        return [(str(name), str(kind)) for name, kind in rows]


def call_row(store: ContractStore, n: int, **overrides: object) -> dict[str, object]:
    row: dict[str, object] = {
        "call_id": f"claude-code:req-{n:04d}",
        "host": "claude-code",
        "project_id": PROJECT_ID,
        "session_id": "s-0001",
        "task_id": "claude-code:p-0001",
        "agent_run_id": "claude-code:p-0001:main",
        "ts": BASE,
        "model": "claude-opus-5-5",
        "model_label": None,
        "input_tokens": 100 + n,
        "output_tokens": 20,
        "thinking_tokens": None,
        "cache_write_5m_tokens": 0,
        "cache_write_1h_tokens": 0,
        "cache_read_tokens": 1000,
        "latency_ms": 1500,
        "speed": None,
        "inference_geo": None,
        "is_error": False,
        "source_format": "cc-2.1",
        "owner_rank": "0:2026-10-16T14:00:00.000Z:s-0001",
        "row_hash": f"hash-{n}",
        "ingest_seq": store.next_seq(),
        "schema_version": 1,
    }
    row.update(overrides)
    return row


def seed_calls(store: ContractStore, count: int, *, start: int = 1) -> list[str]:
    ids = []
    for n in range(start, start + count):
        row = call_row(store, n)
        store.insert("llm_calls", row)
        ids.append(str(row["call_id"]))
    return ids


def seed_graph(store: ContractStore) -> None:
    """One session → task → main run → tool use, plus every reference table."""
    store.insert(
        "sessions",
        {
            "session_id": "s-0001", "host": "claude-code", "project_id": PROJECT_ID,
            "started_at": BASE, "ended_at": BASE, "status": "closed", "host_version": "2.1.229",
            "owner_rank": "0", "row_hash": "h-s", "ingest_seq": store.next_seq(), "schema_version": 1,
        },
    )
    store.insert(
        "tasks",
        {
            "task_id": "claude-code:p-0001", "session_id": "s-0001", "host": "claude-code",
            "project_id": PROJECT_ID, "seq_in_session": 1, "started_at": BASE, "ended_at": BASE,
            "wall_clock_ms": 60000, "active_ms": 45000, "reported_ms": None,
            "duration_source": "derived", "status": "done", "agent_runs": 1, "max_spawn_depth": 0,
            "critical_path_ms": 45000, "critical_path": "main", "retries": 0, "retry_summary": "",
            "owner_rank": "0", "row_hash": "h-t", "ingest_seq": store.next_seq(), "schema_version": 1,
        },
    )
    store.insert(
        "agent_runs",
        {
            "agent_run_id": "claude-code:p-0001:main", "task_id": "claude-code:p-0001",
            "session_id": "s-0001", "host": "claude-code", "project_id": PROJECT_ID,
            "parent_agent_run_id": None, "agent_type": "main", "description_hash": None,
            "spawn_depth": 0, "started_at": BASE, "ended_at": BASE, "active_ms": 45000,
            "status": "done", "errors": 0, "files_touched": 2, "test_runs": 1, "test_failures": 0,
            "tools_untracked": False, "owner_rank": "0", "row_hash": "h-r",
            "ingest_seq": store.next_seq(), "schema_version": 1,
        },
    )
    store.insert(
        "tool_uses",
        {
            "agent_run_id": "claude-code:p-0001:main", "tool_name": "Bash", "calls": 3,
            "errors": 1, "project_id": PROJECT_ID, "host": "claude-code",
            "ingest_seq": store.next_seq(),
        },
    )
    seed_reference(store)


def seed_reference(store: ContractStore, *, display_name: str = "Project X",
                   client: str = "Client Z",
                   remote_url: str = "github.com/owner/project-x") -> None:
    store.insert(
        "projects",
        {
            "project_id": PROJECT_ID, "kind": "remote", "display_name": display_name,
            "remote_url": remote_url, "client": client, "billing_model": "hourly",
            "hourly_rate": Decimal("80000.0000"), "fixed_price": None, "rate_currency": "COP",
        },
    )
    store.insert(
        "pricing",
        {
            "model": "claude-opus-5-5", "effective_from": date(2000, 1, 1), "min_prompt_tokens": 0,
            "input_per_mtok": Decimal("4.000000"), "output_per_mtok": Decimal("20.000000"),
            "cache_write_5m_per_mtok": Decimal("5.000000"),
            "cache_write_1h_per_mtok": Decimal("8.000000"),
            "cache_read_per_mtok": Decimal("0.200000"), "source": "shipped",
            "source_url": "https://platform.claude.com/docs/en/about-claude/pricing",
            "fetched_at": date(2026, 10, 16),
        },
    )
    store.insert(
        "pricing_aliases",
        {"alias": "claude-haiku-4-5-20251001", "model": "claude-haiku-4-5", "estimated": False,
         "source": "shipped"},
    )
    store.insert("host_defaults", {"host": "antigravity-cli", "default_model": "gemini-4-argon"})
    store.insert("settings", {"key": "timezone", "value": "America/Bogota"})
    store.insert(
        "dev_hours_manual",
        {"project_id": PROJECT_ID, "period": "2026-10", "hours": Decimal("12.50"), "set_at": BASE},
    )
    store.insert(
        "dev_hours_derived",
        {"project_id": PROJECT_ID, "local_date": date(2026, 10, 16), "hours": Decimal("1.25")},
    )
    store.insert(
        "tag_history", {"project_id": PROJECT_ID, "tag": "Track 11", "from_ts": BASE, "to_ts": None}
    )
    store.insert("task_tags", {"task_id": "claude-code:p-0001", "tag": "Track 11", "set_at": BASE})
    store.insert(
        "untracked",
        {"conversation_id": "conv-legacy-1", "host": "antigravity-ide", "reason": "legacy_pb",
         "observed_from": date(2026, 9, 1), "observed_to": date(2026, 9, 30),
         "ingest_seq": store.next_seq()},
    )


# --- Config / home fakes mirroring contracts §3.6 field names ------------------------------
@dataclass(frozen=True, slots=True)
class FakeBigQueryConfig:
    enabled: bool = True
    project: str = "devhack-3f0c2"
    dataset: str = "agent_metrics"
    location: str = "US"
    mode: Literal["billing", "sandbox"] = "billing"
    anonymize_projects: bool = False
    looker_template_id: str = ""


@dataclass(frozen=True, slots=True)
class FakeConfig:
    timezone: str = "UTC"
    bigquery: FakeBigQueryConfig = field(default_factory=FakeBigQueryConfig)


@dataclass(frozen=True, slots=True)
class FakeHome:
    root: Path

    @property
    def outbox_dir(self) -> Path:
        return self.root / "outbox"

    @property
    def secret(self) -> Path:
        return self.root / "secret"


def block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """Fail any socket connection attempt (L1 tests run offline)."""

    def refuse(*_args: object, **_kwargs: object) -> socket.socket:
        raise RuntimeError("network access is not allowed in unit tests")

    monkeypatch.setattr(socket, "create_connection", refuse)
    monkeypatch.setattr(socket.socket, "connect", refuse)
