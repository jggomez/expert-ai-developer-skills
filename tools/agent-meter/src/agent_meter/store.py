"""DuckDB store: the local source of truth (ADR §3.9, contracts §3.7, §4, §6).

* Every store user holds the advisory lock first (``LOCK_EX`` writers, ``LOCK_SH`` readers).
* Facts are upserted by natural key from temporary staging tables in one transaction:
  a staged row wins when the key is new, its ``owner_rank`` is lower, or the owner is the
  same and its ``row_hash`` changed. Only changed rows receive a new ``ingest_seq``.
* Nothing is deleted when a unit yields an empty batch (BR-15).
* Cost is never stored; it is computed in ``v_calls`` from the pricing reference tables.
* The connection runs with ``TimeZone = 'UTC'``; TIMESTAMPTZ values are fetched as
  UTC-aware ``datetime`` objects (DuckDB needs ``pytz`` for that, a runtime dependency).
"""

from __future__ import annotations

import os
import re
from collections.abc import Iterator, Mapping, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from importlib.resources import files
from pathlib import Path
from types import TracebackType
from typing import Any, Final
from zoneinfo import ZoneInfo

import duckdb

from agent_meter.locking import store_lock
from agent_meter.model import (
    SCHEMA_VERSION,
    DiagnosticKind,
    Host,
    ProjectRef,
    UnitBatch,
    UntrackedRecord,
)
from agent_meter.paths import AppHome, atomic_write_text
from agent_meter.pricing import PricingTable
from agent_meter.project_resolver import PathCache, ProjectsConfig
from agent_meter.timeline import dev_hours

__all__ = [
    "MIGRATIONS",
    "TARGET_SCHEMA_VERSION",
    "UNASSIGNED_ID",
    "ApplyStats",
    "Store",
    "StoreError",
]

UNASSIGNED_ID: Final = "(unassigned)"
TARGET_SCHEMA_VERSION: int = SCHEMA_VERSION
# Forward-only migrations: target version -> statements (v1 is ``schema_v1.sql``).
MIGRATIONS: dict[int, tuple[str, ...]] = {}

_CHUNK_ROWS: Final = 500
_DIAGNOSTICS_RETENTION: Final = timedelta(days=30)
_PERIOD_DAY: Final = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PERIOD_MONTH: Final = re.compile(r"^\d{4}-\d{2}$")
_IDENTIFIER: Final = re.compile(r"^[a-z_][a-z0-9_]*$")
_SEQ_TABLES: Final = frozenset({"sessions", "tasks", "agent_runs", "llm_calls", "tool_uses", "untracked"})
_HASH_NULL: Final = "\\N"


class StoreError(RuntimeError):
    """The store cannot perform the requested operation (bad input or incompatible schema)."""


@dataclass(frozen=True, slots=True)
class ApplyStats:
    units: int
    calls_changed: int
    tasks_changed: int
    runs_changed: int
    sessions_changed: int
    diagnostics: int


@dataclass(frozen=True, slots=True)
class _FactSpec:
    table: str
    key: str
    columns: tuple[str, ...]  # business columns (row_hash covers exactly these)
    batch_attr: str


_FACTS: Final = (
    _FactSpec(
        "sessions",
        "session_id",
        ("session_id", "host", "project_id", "started_at", "ended_at", "status", "host_version"),
        "sessions",
    ),
    _FactSpec(
        "tasks",
        "task_id",
        (
            "task_id", "session_id", "host", "project_id", "seq_in_session", "started_at", "ended_at",
            "wall_clock_ms", "active_ms", "reported_ms", "duration_source", "status", "agent_runs",
            "max_spawn_depth", "critical_path_ms", "critical_path", "retries", "retry_summary",
        ),
        "tasks",
    ),
    _FactSpec(
        "agent_runs",
        "agent_run_id",
        (
            "agent_run_id", "task_id", "session_id", "host", "project_id", "parent_agent_run_id",
            "agent_type", "description_hash", "spawn_depth", "started_at", "ended_at", "active_ms",
            "status", "errors", "files_touched", "test_runs", "test_failures", "tools_untracked",
        ),
        "agent_runs",
    ),
    _FactSpec(
        "llm_calls",
        "call_id",
        (
            "call_id", "host", "project_id", "session_id", "task_id", "agent_run_id", "ts", "model",
            "model_label", "input_tokens", "output_tokens", "thinking_tokens", "cache_write_5m_tokens",
            "cache_write_1h_tokens", "cache_read_tokens", "latency_ms", "speed", "inference_geo",
            "is_error", "source_format",
        ),
        "calls",
    ),
)
_FACT_BY_TABLE: Final = {spec.table: spec for spec in _FACTS}


def _sql_resource(name: str) -> str:
    return files("agent_meter").joinpath("sql", "duckdb", name).read_text(encoding="utf-8")


def _hash_expr(columns: Sequence[str], alias: str) -> str:
    parts = ", ".join(f"COALESCE(CAST({alias}.{c} AS VARCHAR), '{_HASH_NULL}')" for c in columns)
    return f"sha256(concat_ws(chr(31), {parts}))"


def _value(record: object, column: str) -> object:
    value = getattr(record, column)
    if column == "project_id" and not value:
        return UNASSIGNED_ID
    if isinstance(value, str):
        return str(value)  # StrEnum -> plain text
    return value


def _project_kind(project_id: str) -> str:
    if project_id.startswith("git:"):
        return "remote"
    if project_id.startswith("path:"):
        return "path"
    return "unassigned"


class _StorePathCache:
    """``PathCache`` backed by ``path_map`` (hashes only, never clear-text paths)."""

    def __init__(self, store: Store) -> None:
        self._store = store

    def get(self, path_hash: str) -> str | None:
        found = self._store.query("SELECT project_id FROM path_map WHERE path_hash = ?", [path_hash])
        return str(found[0]["project_id"]) if found else None

    def put(self, path_hash: str, project_id: str) -> None:
        self._store.execute(
            "INSERT OR REPLACE INTO path_map VALUES (?, ?, ?)", [path_hash, project_id, datetime.now(UTC)]
        )


class Store:
    """A locked DuckDB connection to ``~/.agent-meter/meter.duckdb``; use as a context manager."""

    def __init__(self, con: duckdb.DuckDBPyConnection, home: AppHome, *, read_only: bool, stack: ExitStack) -> None:
        self._con = con
        self._home = home
        self.read_only = read_only
        self._stack = stack
        self._closed = False

    # ------------------------------------------------------------------ lifecycle

    @classmethod
    def open(cls, home: AppHome, *, read_only: bool, lock_timeout_s: float) -> Store:
        """Take the lock (shared for readers) and connect; a missing store is created first."""
        if read_only and not home.db.exists():
            with cls.open(home, read_only=False, lock_timeout_s=lock_timeout_s) as creator:
                creator.migrate()
        stack = ExitStack()
        stack.enter_context(store_lock(home.lock, exclusive=not read_only, timeout_s=lock_timeout_s))
        try:
            existed = home.db.exists()
            con = duckdb.connect(str(home.db), read_only=read_only)
            con.execute("SET TimeZone = 'UTC'")
            if not existed:
                os.chmod(home.db, 0o600)
        except BaseException:
            stack.close()
            raise
        return cls(con, home, read_only=read_only, stack=stack)

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            self._con.close()
        finally:
            self._stack.close()

    def __enter__(self) -> Store:
        return self

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        self.close()

    # ------------------------------------------------------------------ low-level helpers

    def execute(self, sql: str, params: Sequence[object] = ()) -> None:
        self._con.execute(sql, list(params))

    def query(self, sql: str, params: Sequence[object] = ()) -> list[dict[str, object]]:
        cursor = self._con.execute(sql, list(params))
        names = [d[0] for d in cursor.description or ()]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]

    def _scalar(self, sql: str, params: Sequence[object] = ()) -> Any:
        row = self._con.execute(sql, list(params)).fetchone()
        return row[0] if row else None

    def _transaction(self) -> _Transaction:
        return _Transaction(self._con)

    def _insert_rows(self, table: str, columns: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
        if not rows:
            return
        placeholders = "(" + ", ".join("?" for _ in columns) + ")"
        names = ", ".join(columns)
        for start in range(0, len(rows), _CHUNK_ROWS):
            chunk = rows[start : start + _CHUNK_ROWS]
            values = ", ".join(placeholders for _ in chunk)
            params = [v for row in chunk for v in row]
            self._con.execute(f"INSERT INTO {table} ({names}) VALUES {values}", params)

    def _table_exists(self, name: str) -> bool:
        count = self._scalar(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'main' AND table_name = ?", [name]
        )
        return bool(count)

    # ------------------------------------------------------------------ schema

    def migrate(self) -> None:
        """Create or upgrade the schema (forward-only) and (re)create every view; idempotent."""
        with self._transaction():
            current = int(self.get_meta("schema_version") or 0) if self._table_exists("meta") else 0
            if current > TARGET_SCHEMA_VERSION:
                raise StoreError(
                    f"this store uses schema v{current}, written by a newer agent-meter; please upgrade agent-meter"
                )
            if current == 0:
                self._con.execute(_sql_resource("schema_v1.sql"))
                current = 1
                self.set_meta("schema_version", "1")
            for version in range(current + 1, TARGET_SCHEMA_VERSION + 1):
                for statement in MIGRATIONS.get(version, ()):
                    self._con.execute(statement)
                self.set_meta("schema_version", str(version))
            self._con.execute(_sql_resource("views.sql"))

    # ------------------------------------------------------------------ meta

    def get_meta(self, key: str) -> str | None:
        value = self._scalar("SELECT value FROM meta WHERE key = ?", [key])
        return None if value is None else str(value)

    def set_meta(self, key: str, value: str) -> None:
        self._con.execute("INSERT OR REPLACE INTO meta VALUES (?, ?)", [key, value])

    def delete_meta(self, key: str) -> None:
        self._con.execute("DELETE FROM meta WHERE key = ?", [key])

    # ------------------------------------------------------------------ ingest

    def unit_fingerprint(self, host: Host, unit_id: str) -> str | None:
        value = self._scalar(
            "SELECT fingerprint FROM source_units WHERE host = ? AND unit_id = ?", [host.value, unit_id]
        )
        return None if value is None else str(value)

    def apply_batches(
        self,
        batches: Sequence[UnitBatch],
        *,
        known_formats: Mapping[Host, frozenset[str]] | None = None,
        now: datetime | None = None,
    ) -> ApplyStats:
        """Upsert every batch in ONE transaction (ADR §3.9); empty batches never delete rows."""
        moment = now or datetime.now(UTC)
        changed: dict[str, int] = {}
        with self._transaction():
            for spec in _FACTS:
                changed[spec.table] = self._merge_fact(spec, batches)
            self._merge_tool_uses(batches)
            self._record_units(batches, known_formats or {}, moment)
            diagnostics = self._record_diagnostics(batches, moment)
        return ApplyStats(
            units=len(batches),
            calls_changed=changed["llm_calls"],
            tasks_changed=changed["tasks"],
            runs_changed=changed["agent_runs"],
            sessions_changed=changed["sessions"],
            diagnostics=diagnostics,
        )

    def _stage(self, name: str, ddl_columns: str, columns: Sequence[str], rows: Sequence[Sequence[object]]) -> None:
        self._con.execute(f"CREATE OR REPLACE TEMP TABLE {name} ({ddl_columns})")
        self._insert_rows(name, columns, rows)

    def _merge_fact(self, spec: _FactSpec, batches: Sequence[UnitBatch]) -> int:
        records = [r for b in batches for r in getattr(b, spec.batch_attr)]
        if not records:
            return 0
        stage = f"stage_{spec.table}"
        all_columns = (*spec.columns, "owner_rank")
        self._con.execute(
            f"CREATE OR REPLACE TEMP TABLE {stage} AS "
            f"SELECT {', '.join(all_columns)} FROM {spec.table} LIMIT 0"
        )
        self._insert_rows(stage, all_columns, [[_value(r, c) for c in all_columns] for r in records])
        cols = ", ".join(spec.columns)
        s_cols = ", ".join(f"s.{c}" for c in spec.columns)
        key = spec.key
        sql = f"""
            INSERT OR REPLACE INTO {spec.table} ({cols}, owner_rank, row_hash, ingest_seq)
            SELECT {s_cols}, s.owner_rank, s.row_hash, nextval('ingest_seq')
            FROM (
                SELECT st.*, {_hash_expr(spec.columns, "st")} AS row_hash FROM {stage} st
                QUALIFY row_number() OVER (PARTITION BY st.{key} ORDER BY st.owner_rank, row_hash) = 1
            ) s
            LEFT JOIN {spec.table} t ON t.{key} = s.{key}
            WHERE t.{key} IS NULL OR s.owner_rank < t.owner_rank
               OR (s.owner_rank = t.owner_rank AND s.row_hash <> t.row_hash)
        """
        count = int(self._scalar(sql) or 0)
        return count

    def _merge_tool_uses(self, batches: Sequence[UnitBatch]) -> int:
        """Replace tool counts wholesale for the agent runs this batch owns."""
        runs = [(r.agent_run_id, r.owner_rank) for b in batches for r in b.agent_runs]
        if not runs:
            return 0
        self._stage("stage_owned_runs", "agent_run_id TEXT, owner_rank TEXT", ("agent_run_id", "owner_rank"), runs)
        tools = [(t.agent_run_id, t.tool_name, t.calls, t.errors) for b in batches for t in b.tool_uses]
        self._stage(
            "stage_tool_uses",
            "agent_run_id TEXT, tool_name TEXT, calls INTEGER, errors INTEGER",
            ("agent_run_id", "tool_name", "calls", "errors"),
            tools,
        )
        self._con.execute(
            """
            CREATE OR REPLACE TEMP TABLE stage_affected AS
            SELECT DISTINCT o.agent_run_id FROM stage_owned_runs o
            JOIN agent_runs r ON r.agent_run_id = o.agent_run_id AND r.owner_rank = o.owner_rank
            """
        )
        self._con.execute(
            """
            DELETE FROM tool_uses
            WHERE agent_run_id IN (SELECT agent_run_id FROM stage_affected)
              AND NOT EXISTS (
                SELECT 1 FROM stage_tool_uses st
                WHERE st.agent_run_id = tool_uses.agent_run_id AND st.tool_name = tool_uses.tool_name)
            """
        )
        return int(
            self._scalar(
                """
                INSERT OR REPLACE INTO tool_uses (agent_run_id, tool_name, calls, errors, project_id, host, ingest_seq)
                SELECT st.agent_run_id, st.tool_name, st.calls, st.errors, r.project_id, r.host, nextval('ingest_seq')
                FROM (
                    SELECT * FROM stage_tool_uses
                    QUALIFY row_number() OVER (PARTITION BY agent_run_id, tool_name ORDER BY calls DESC, errors DESC) = 1
                ) st
                JOIN stage_affected a ON a.agent_run_id = st.agent_run_id
                JOIN agent_runs r ON r.agent_run_id = st.agent_run_id
                LEFT JOIN tool_uses tu ON tu.agent_run_id = st.agent_run_id AND tu.tool_name = st.tool_name
                WHERE tu.agent_run_id IS NULL OR tu.calls <> st.calls OR tu.errors <> st.errors
                   OR tu.project_id <> r.project_id OR tu.host <> r.host
                """
            )
            or 0
        )

    def _record_units(
        self, batches: Sequence[UnitBatch], known_formats: Mapping[Host, frozenset[str]], moment: datetime
    ) -> None:
        for batch in batches:
            if any(d.kind == DiagnosticKind.UNREADABLE for d in batch.diagnostics):
                continue  # retry next run: the unit could not be read at all
            host = batch.unit.host
            self._con.execute(
                "INSERT OR REPLACE INTO source_units VALUES (?, ?, ?, ?, ?)",
                [host.value, batch.unit.unit_id, batch.unit.fingerprint, batch.format_fingerprint, moment],
            )
            if not (batch.calls or batch.sessions or batch.tasks):
                continue
            known = batch.format_fingerprint in known_formats.get(host, frozenset())
            self._con.execute(
                """
                INSERT INTO format_versions VALUES (?, ?, ?, ?, ?)
                ON CONFLICT (host, fingerprint) DO UPDATE SET known = excluded.known, last_seen = excluded.last_seen
                """,
                [host.value, batch.format_fingerprint, known, moment, moment],
            )

    def _record_diagnostics(self, batches: Sequence[UnitBatch], moment: datetime) -> int:
        rows = [
            (moment, d.host.value, d.kind.value, d.unit_hash, d.file_kind, d.error_class, d.count)
            for b in batches
            for d in b.diagnostics
        ]
        self._insert_rows(
            "diagnostics", ("run_at", "host", "kind", "unit_hash", "file_kind", "error_class", "count"), rows
        )
        self._con.execute("DELETE FROM diagnostics WHERE run_at < ?", [moment - _DIAGNOSTICS_RETENTION])
        return sum(r[6] for r in rows)

    def record_untracked(self, rows: Sequence[UntrackedRecord]) -> None:
        """Upsert untracked conversations by id (BR-22); changed rows get a new ``ingest_seq``."""
        if not rows:
            return
        with self._transaction():
            self._stage(
                "stage_untracked",
                "conversation_id TEXT, host TEXT, reason TEXT, observed_from DATE, observed_to DATE",
                ("conversation_id", "host", "reason", "observed_from", "observed_to"),
                [(r.conversation_id, r.host.value, r.reason.value, r.observed_from, r.observed_to) for r in rows],
            )
            self._con.execute(
                """
                INSERT OR REPLACE INTO untracked
                SELECT s.conversation_id, s.host, s.reason, s.observed_from, s.observed_to, nextval('ingest_seq')
                FROM (SELECT * FROM stage_untracked QUALIFY row_number() OVER (PARTITION BY conversation_id) = 1) s
                LEFT JOIN untracked u ON u.conversation_id = s.conversation_id
                WHERE u.conversation_id IS NULL OR u.host <> s.host OR u.reason <> s.reason
                   OR u.observed_from <> s.observed_from OR u.observed_to <> s.observed_to
                """
            )

    # ------------------------------------------------------------------ reference data

    def load_reference_data(
        self,
        *,
        pricing: PricingTable | None,
        host_defaults: Mapping[Host, str | None],
        projects: ProjectsConfig,
        project_refs: Sequence[ProjectRef],
        settings: Mapping[str, str],
    ) -> None:
        """Replace the reference tables from files/config.

        ``pricing=None`` keeps the current price tables (an invalid ``pricing.local.yaml``
        never replaces the last valid table, PC-07). Project identities seen at ingest are
        kept across runs (a known remote is never overwritten with ``None``); overrides
        from ``projects.yaml`` are overlaid on every run, and its ``merges`` are applied.
        """
        with self._transaction():
            if pricing is not None:
                self._replace_pricing(pricing)
            self._con.execute("DELETE FROM host_defaults")
            self._insert_rows(
                "host_defaults",
                ("host", "default_model"),
                [(h.value, m) for h, m in sorted(host_defaults.items(), key=lambda kv: kv[0].value)],
            )
            self._con.execute("DELETE FROM settings")
            self._insert_rows("settings", ("key", "value"), sorted(settings.items()))
            for src, dst in sorted(projects.merges.items()):
                if src != dst:
                    self._rekey_project(src, dst)
            self._replace_projects(projects, project_refs)

    def _replace_pricing(self, pricing: PricingTable) -> None:
        self._con.execute("DELETE FROM pricing")
        self._insert_rows(
            "pricing",
            (
                "model", "effective_from", "min_prompt_tokens", "input_per_mtok", "output_per_mtok",
                "cache_write_5m_per_mtok", "cache_write_1h_per_mtok", "cache_read_per_mtok", "source",
                "source_url", "fetched_at",
            ),
            [
                (
                    r.model, r.effective_from, r.min_prompt_tokens, r.input, r.output, r.cache_write_5m,
                    r.cache_write_1h, r.cache_read, r.source, r.source_url, r.fetched_at,
                )
                for r in pricing.rows
            ],
        )
        self._con.execute("DELETE FROM pricing_aliases")
        self._insert_rows(
            "pricing_aliases",
            ("alias", "model", "estimated", "source"),
            [(a.alias, a.model, a.estimated, a.source) for a in pricing.aliases],
        )

    def _replace_projects(self, projects: ProjectsConfig, refs: Sequence[ProjectRef]) -> None:
        existing = {
            str(r["project_id"]): r
            for r in self.query("SELECT project_id, kind, display_name, remote_url FROM projects")
        }
        base: dict[str, tuple[str, str, str | None]] = {}
        for pid, row in existing.items():
            remote = row["remote_url"] if isinstance(row["remote_url"], str) else None
            # A remote-backed name is re-derived so a removed projects.yaml override reverts.
            name = remote.rsplit("/", 1)[-1] if remote else str(row["display_name"])
            base[pid] = (str(row["kind"]), name, remote)
        for ref in refs:
            known_remote = base[ref.project_id][2] if ref.project_id in base else None
            remote = ref.remote_url or known_remote
            # A known remote names the project canonically (path-cache hits carry a directory name).
            base[ref.project_id] = (ref.kind, remote.rsplit("/", 1)[-1] if remote else ref.display_name, remote)
        used = self.query(
            "SELECT DISTINCT project_id FROM sessions UNION SELECT DISTINCT project_id FROM llm_calls "
            "UNION SELECT DISTINCT project_id FROM dev_hours_manual"
        )
        for row in used:
            pid = str(row["project_id"])
            base.setdefault(pid, (_project_kind(pid), pid, None))
        for pid in projects.projects:
            base.setdefault(pid, (_project_kind(pid), pid, None))
        for merged in projects.merges:
            base.pop(merged, None)
        base[UNASSIGNED_ID] = ("unassigned", UNASSIGNED_ID, None)
        rows = []
        for pid, (kind, name, remote) in sorted(base.items()):
            override = projects.projects.get(pid)
            display = override.display_name if override is not None and override.display_name else name
            rows.append(
                (
                    pid, kind, display, remote,
                    override.client if override else None,
                    override.billing if override else None,
                    override.rate if override else None,
                    override.fixed_price if override else None,
                    override.currency.upper() if override and override.currency else None,
                )
            )
        self._con.execute("DELETE FROM projects")
        self._insert_rows(
            "projects",
            (
                "project_id", "kind", "display_name", "remote_url", "client", "billing_model",
                "hourly_rate", "fixed_price", "rate_currency",
            ),
            rows,
        )

    def path_cache(self) -> PathCache:
        return _StorePathCache(self)

    # ------------------------------------------------------------------ derived & user-owned facts

    def recompute_dev_hours(self, tz: str, merge_gap_s: int) -> None:
        """Rewrite ``dev_hours_derived`` from task intervals (merged across hosts, OQ-1)."""
        zone = ZoneInfo(tz)
        spans: dict[str, list[tuple[datetime, datetime]]] = {}
        for row in self.query("SELECT project_id, started_at, ended_at FROM tasks"):
            start, end = row["started_at"], row["ended_at"]
            if isinstance(start, datetime) and isinstance(end, datetime):
                spans.setdefault(str(row["project_id"]), []).append((start, end))
        rows = [
            (pid, day, hours)
            for pid, intervals in sorted(spans.items())
            for day, hours in sorted(dev_hours(intervals, zone, merge_gap_s).items())
            if hours > 0
        ]
        with self._transaction():
            self._con.execute("DELETE FROM dev_hours_derived")
            self._insert_rows("dev_hours_derived", ("project_id", "local_date", "hours"), rows)

    def set_tag(self, project_id: str, tag: str | None, at: datetime) -> None:
        """Start tagging new tasks of ``project_id`` with ``tag`` (``None`` clears), BR-21."""
        with self._transaction():
            self._con.execute(
                "UPDATE tag_history SET to_ts = ? WHERE project_id = ? AND to_ts IS NULL", [at, project_id]
            )
            self._con.execute("INSERT OR REPLACE INTO tag_history VALUES (?, ?, ?, NULL)", [project_id, tag, at])

    def tag_last(self, project_id: str, tag: str, n: int) -> list[str]:
        """Tag the ``n`` most recent tasks of a project after the fact; returns their ids."""
        if n < 1:
            raise StoreError("--last must be at least 1")
        task_ids = [
            str(r["task_id"])
            for r in self.query(
                "SELECT task_id FROM tasks WHERE project_id = ? ORDER BY started_at DESC, task_id DESC LIMIT ?",
                [project_id, n],
            )
        ]
        moment = datetime.now(UTC)
        with self._transaction():
            for task_id in task_ids:
                self._con.execute("INSERT OR REPLACE INTO task_tags VALUES (?, ?, ?)", [task_id, tag, moment])
        return task_ids

    @staticmethod
    def _check_period(period: str) -> None:
        try:
            if _PERIOD_DAY.match(period):
                date.fromisoformat(period)
                return
            if _PERIOD_MONTH.match(period):
                date.fromisoformat(period + "-01")
                return
        except ValueError as exc:
            raise StoreError(f"invalid period {period!r}: use YYYY-MM-DD or YYYY-MM") from exc
        raise StoreError(f"invalid period {period!r}: use YYYY-MM-DD or YYYY-MM")

    def set_manual_hours(self, project_id: str, period: str, hours: Decimal) -> None:
        self._check_period(period)
        if not hours.is_finite() or hours < 0 or hours >= Decimal(1_000_000):
            raise StoreError(f"invalid hours {hours}: must be between 0 and 999999.99")
        self._con.execute(
            "INSERT OR REPLACE INTO dev_hours_manual VALUES (?, ?, ?, ?)",
            [project_id, period, hours, datetime.now(UTC)],
        )

    def unset_manual_hours(self, project_id: str, period: str) -> bool:
        self._check_period(period)
        found = self._scalar(
            "SELECT COUNT(*) FROM dev_hours_manual WHERE project_id = ? AND period = ?", [project_id, period]
        )
        self._con.execute("DELETE FROM dev_hours_manual WHERE project_id = ? AND period = ?", [project_id, period])
        return bool(found)

    def merge_projects(self, src: str, dst: str) -> int:
        """Re-key every row of ``src`` to ``dst`` (new ``ingest_seq``); returns fact rows moved."""
        if src == dst:
            return 0
        with self._transaction():
            moved = self._rekey_project(src, dst)
            self._con.execute("DELETE FROM projects WHERE project_id = ?", [src])
        return moved

    def _rekey_project(self, src: str, dst: str) -> int:
        moved = 0
        for spec in _FACTS:
            moved += int(
                self._scalar(
                    f"UPDATE {spec.table} SET project_id = ?, ingest_seq = nextval('ingest_seq') WHERE project_id = ?",
                    [dst, src],
                )
                or 0
            )
            self._con.execute(
                f"UPDATE {spec.table} SET row_hash = {_hash_expr(spec.columns, spec.table)} WHERE project_id = ?",
                [dst],
            )
        self._con.execute(
            "UPDATE tool_uses SET project_id = ?, ingest_seq = nextval('ingest_seq') WHERE project_id = ?", [dst, src]
        )
        self._con.execute("UPDATE path_map SET project_id = ? WHERE project_id = ?", [dst, src])
        for table, key in (("dev_hours_manual", "period"), ("tag_history", "from_ts")):
            other = "hours, set_at" if table == "dev_hours_manual" else "tag, to_ts"
            self._con.execute(
                f"INSERT OR IGNORE INTO {table} SELECT ?, {key}, {other} FROM {table} WHERE project_id = ?", [dst, src]
            )
            self._con.execute(f"DELETE FROM {table} WHERE project_id = ?", [src])
        self._con.execute("DELETE FROM dev_hours_derived WHERE project_id = ?", [src])
        return moved

    # ------------------------------------------------------------------ outbox support

    def _columns_of(self, table: str) -> set[str]:
        return {
            str(r["column_name"])
            for r in self.query(
                "SELECT column_name FROM information_schema.columns WHERE table_schema = 'main' AND table_name = ?",
                [table],
            )
        }

    def _check_seq_table(self, table: str) -> None:
        if table not in _SEQ_TABLES:
            raise StoreError(f"table {table!r} has no ingest_seq")

    def rows_since(self, table: str, after_seq: int, columns: Sequence[str]) -> Iterator[dict[str, object]]:
        """Rows with ``ingest_seq > after_seq`` in sequence order (the logical outbox)."""
        self._check_seq_table(table)
        available = self._columns_of(table)
        bad = [c for c in columns if not _IDENTIFIER.match(c) or c not in available]
        if bad or not columns:
            raise StoreError(f"unknown column(s) for {table}: {bad or 'none requested'}")
        cursor = self._con.execute(
            f"SELECT {', '.join(columns)} FROM {table} WHERE ingest_seq > ? ORDER BY ingest_seq", [after_seq]
        )
        while True:
            chunk = cursor.fetchmany(1000)
            if not chunk:
                return
            for row in chunk:
                yield dict(zip(columns, row, strict=True))

    def max_seq(self, table: str) -> int:
        self._check_seq_table(table)
        return int(self._scalar(f"SELECT COALESCE(MAX(ingest_seq), 0) FROM {table}") or 0)

    # ------------------------------------------------------------------ snapshot

    def write_snapshot(self, path: Path, *, tz: str, now: datetime) -> None:
        """Atomically write ``state/snapshot.json`` (today/MTD per project and host + last sessions)."""
        import json

        from agent_meter.summary import build_snapshot

        document = build_snapshot(self, tz=tz, now=now)
        atomic_write_text(path, json.dumps(document, sort_keys=True, indent=1))


class _Transaction:
    """``BEGIN``/``COMMIT`` with rollback on error; nested use joins the outer transaction."""

    def __init__(self, con: duckdb.DuckDBPyConnection) -> None:
        self._con = con
        self._owner = False

    def __enter__(self) -> None:
        try:
            self._con.execute("BEGIN TRANSACTION")
            self._owner = True
        except duckdb.TransactionException:
            self._owner = False  # already inside a transaction: the outer block commits

    def __exit__(
        self, exc_type: type[BaseException] | None, exc: BaseException | None, tb: TracebackType | None
    ) -> None:
        if not self._owner:
            return
        if exc_type is None:
            self._con.execute("COMMIT")
        else:
            self._con.execute("ROLLBACK")
