"""Logical outbox for the cloud sink (ADR §3.11, contracts §3.11 and §7).

There is no second copy of the data: the rows of a fact table whose ``ingest_seq`` is past
``meta['bq_watermark:<table>']`` *are* the outbox. At sync time they are serialized to
``<outbox_dir>/<table>/<batch_id>.ndjson`` with an explicit column projection (the cloud
column set equals the local columns minus ``row_hash`` and ``owner_rank``, plus
``_uploaded_at``). Reference tables are small and always serialized in full.

This module performs no network access and imports no cloud SDK (invariant I-2).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from types import MappingProxyType
from typing import Final, Literal, Protocol

__all__ = [
    "ANONYMIZED_COLUMNS",
    "FACT_TABLES",
    "REFERENCE_TABLES",
    "TABLE_SCHEMAS",
    "UPLOADED_AT",
    "WATERMARK_PREFIX",
    "Anonymizer",
    "Column",
    "Disposition",
    "OutboxFile",
    "OutboxStore",
    "discard_stale",
    "encode_row",
    "load_salt",
    "materialize",
    "new_batch_id",
    "pending_counts",
    "watermark",
]

FACT_TABLES: Final = ("llm_calls", "tasks", "agent_runs", "tool_uses", "sessions")
REFERENCE_TABLES: Final = (
    "projects", "pricing", "pricing_aliases", "host_defaults", "dev_hours_manual",
    "dev_hours_derived", "task_tags", "tag_history", "settings", "untracked",
)
UPLOADED_AT: Final = "_uploaded_at"
WATERMARK_PREFIX: Final = "bq_watermark:"
ANONYMIZED_COLUMNS: Final = frozenset({"project_id", "display_name", "client", "remote_url", "tag"})
"""Hashed when ``anonymize_projects`` is on. ``tag`` (``task_tags`` / ``tag_history``) is included
because work-item tags often carry client or project names (compliance finding L-3)."""
MIN_SALT_BYTES: Final = 16

Column = tuple[str, str]
"""``(column name, BigQuery type)``; types are STRING, INT64, BOOL, TIMESTAMP, DATE, NUMERIC."""

Disposition = Literal["WRITE_APPEND", "WRITE_TRUNCATE"]

_S, _I, _B, _T, _D, _N = "STRING", "INT64", "BOOL", "TIMESTAMP", "DATE", "NUMERIC"
_BATCH_ID = re.compile(r"^\d{8}T\d{6}Z-[0-9a-f]{8}$")


def _schema(*columns: Column) -> tuple[Column, ...]:
    return (*columns, (UPLOADED_AT, _T))


TABLE_SCHEMAS: Final[Mapping[str, tuple[Column, ...]]] = MappingProxyType({
    "sessions": _schema(
        ("session_id", _S), ("host", _S), ("project_id", _S), ("started_at", _T),
        ("ended_at", _T), ("status", _S), ("host_version", _S), ("ingest_seq", _I),
        ("schema_version", _I),
    ),
    "tasks": _schema(
        ("task_id", _S), ("session_id", _S), ("host", _S), ("project_id", _S),
        ("seq_in_session", _I), ("started_at", _T), ("ended_at", _T), ("wall_clock_ms", _I),
        ("active_ms", _I), ("reported_ms", _I), ("duration_source", _S), ("status", _S),
        ("agent_runs", _I), ("max_spawn_depth", _I), ("critical_path_ms", _I),
        ("critical_path", _S), ("retries", _I), ("retry_summary", _S), ("ingest_seq", _I),
        ("schema_version", _I),
    ),
    "agent_runs": _schema(
        ("agent_run_id", _S), ("task_id", _S), ("session_id", _S), ("host", _S),
        ("project_id", _S), ("parent_agent_run_id", _S), ("agent_type", _S),
        ("description_hash", _S), ("spawn_depth", _I), ("started_at", _T), ("ended_at", _T),
        ("active_ms", _I), ("status", _S), ("errors", _I), ("files_touched", _I),
        ("test_runs", _I), ("test_failures", _I), ("tools_untracked", _B), ("ingest_seq", _I),
        ("schema_version", _I),
    ),
    "llm_calls": _schema(
        ("call_id", _S), ("host", _S), ("project_id", _S), ("session_id", _S), ("task_id", _S),
        ("agent_run_id", _S), ("ts", _T), ("model", _S), ("model_label", _S),
        ("input_tokens", _I), ("output_tokens", _I), ("thinking_tokens", _I),
        ("cache_write_5m_tokens", _I), ("cache_write_1h_tokens", _I), ("cache_read_tokens", _I),
        ("latency_ms", _I), ("speed", _S), ("inference_geo", _S), ("is_error", _B),
        ("source_format", _S), ("ingest_seq", _I), ("schema_version", _I),
    ),
    "tool_uses": _schema(
        ("agent_run_id", _S), ("tool_name", _S), ("calls", _I), ("errors", _I),
        ("project_id", _S), ("host", _S), ("ingest_seq", _I),
    ),
    "untracked": _schema(
        ("conversation_id", _S), ("host", _S), ("reason", _S), ("observed_from", _D),
        ("observed_to", _D), ("ingest_seq", _I),
    ),
    "projects": _schema(
        ("project_id", _S), ("kind", _S), ("display_name", _S), ("remote_url", _S),
        ("client", _S), ("billing_model", _S), ("hourly_rate", _N), ("fixed_price", _N),
        ("rate_currency", _S),
    ),
    "pricing": _schema(
        ("model", _S), ("effective_from", _D), ("min_prompt_tokens", _I),
        ("input_per_mtok", _N), ("output_per_mtok", _N), ("cache_write_5m_per_mtok", _N),
        ("cache_write_1h_per_mtok", _N), ("cache_read_per_mtok", _N), ("source", _S),
        ("source_url", _S), ("fetched_at", _D),
    ),
    "pricing_aliases": _schema(("alias", _S), ("model", _S), ("estimated", _B), ("source", _S)),
    "host_defaults": _schema(("host", _S), ("default_model", _S)),
    "settings": _schema(("key", _S), ("value", _S)),
    "dev_hours_manual": _schema(
        ("project_id", _S), ("period", _S), ("hours", _N), ("set_at", _T),
    ),
    "dev_hours_derived": _schema(("project_id", _S), ("local_date", _D), ("hours", _N)),
    "tag_history": _schema(("project_id", _S), ("tag", _S), ("from_ts", _T), ("to_ts", _T)),
    "task_tags": _schema(("task_id", _S), ("tag", _S), ("set_at", _T)),
})


class OutboxStore(Protocol):
    """The part of ``agent_meter.store.Store`` (contracts §3.7) the outbox reads."""

    def get_meta(self, key: str) -> str | None: ...

    def rows_since(
        self, table: str, after_seq: int, columns: Sequence[str]
    ) -> Iterator[dict[str, object]]: ...

    def query(self, sql: str, params: Sequence[object] = ()) -> list[dict[str, object]]: ...


@dataclass(frozen=True, slots=True)
class OutboxFile:
    table: str
    path: Path
    rows: int
    max_seq: int
    disposition: Disposition


class Anonymizer:
    """Stable, irreversible pseudonyms: ``HMAC-SHA256(salt, value)`` hex, first 16 chars (BR-17)."""

    __slots__ = ("_salt",)

    def __init__(self, salt: bytes) -> None:
        if len(salt) < MIN_SALT_BYTES:
            raise ValueError(f"anonymization salt must be at least {MIN_SALT_BYTES} bytes")
        self._salt = salt

    def __call__(self, value: str | None) -> str | None:
        if value is None:
            return None
        return hmac.new(self._salt, value.encode("utf-8"), hashlib.sha256).hexdigest()[:16]

    def __repr__(self) -> str:
        return "Anonymizer(<salt redacted>)"


def load_salt(path: Path) -> bytes:
    """Read the local anonymization salt; it is never uploaded or logged."""
    try:
        salt = path.read_bytes()
    except FileNotFoundError:
        raise ValueError(
            "anonymization salt file is missing; run 'agent-meter setup' to create it"
        ) from None
    if len(salt) < MIN_SALT_BYTES:
        raise ValueError(f"anonymization salt must be at least {MIN_SALT_BYTES} bytes")
    return salt


def new_batch_id(now: datetime) -> str:
    """``YYYYMMDDTHHMMSSZ-<8 hex>`` in UTC (contracts §7)."""
    return f"{now.astimezone(UTC):%Y%m%dT%H%M%SZ}-{secrets.token_hex(4)}"


def watermark(store: OutboxStore, table: str) -> int:
    """Highest ``ingest_seq`` already loaded into BigQuery for a fact table (0 = none)."""
    if table not in FACT_TABLES:
        raise ValueError(f"watermarks exist only for fact tables, not {table!r}")
    key = WATERMARK_PREFIX + table
    raw = store.get_meta(key)
    if raw is None:
        return 0
    try:
        value = int(raw)
    except ValueError:
        raise ValueError(f"meta value for {key} is not an integer") from None
    if value < 0:
        raise ValueError(f"meta value for {key} is negative")
    return value


def pending_counts(store: OutboxStore) -> dict[str, int]:
    """Rows waiting in the logical outbox: ``ingest_seq > watermark`` per fact table."""
    counts: dict[str, int] = {}
    for table in FACT_TABLES:
        rows = store.query(
            f"SELECT COUNT(*) AS n FROM {table} WHERE ingest_seq > ?", [watermark(store, table)]
        )
        counts[table] = _as_int(rows[0]["n"]) if rows else 0
    return counts


def materialize(
    store: OutboxStore,
    out_dir: Path,
    *,
    batch_id: str,
    full: bool = False,
    anonymizer: Anonymizer | None = None,
    now: datetime | None = None,
) -> list[OutboxFile]:
    """Serialize the outbox to NDJSON files; never advances watermarks.

    Fact tables yield rows past their watermark (``WRITE_APPEND``) and are skipped when
    nothing is pending; ``full=True`` yields every row with ``WRITE_TRUNCATE``. Reference
    tables are always written in full with ``WRITE_TRUNCATE``, even when empty, so local
    removals (e.g. a deleted price) propagate.
    """
    if not _BATCH_ID.fullmatch(batch_id):
        raise ValueError("batch_id must look like YYYYMMDDTHHMMSSZ-<8 hex>")
    writer = _BatchWriter(out_dir, batch_id, (now or datetime.now(UTC)).astimezone(UTC), anonymizer)
    fact_disposition: Disposition = "WRITE_TRUNCATE" if full else "WRITE_APPEND"
    files: list[OutboxFile | None] = []
    for table in FACT_TABLES:
        after = 0 if full else watermark(store, table)
        rows = store.rows_since(table, after, _store_columns(table))
        files.append(writer.write(table, rows, fact_disposition, floor_seq=after, keep_empty=full))
    for table in REFERENCE_TABLES:
        rows_list = store.query(f"SELECT {', '.join(_store_columns(table))} FROM {table}")
        files.append(writer.write(table, rows_list, "WRITE_TRUNCATE", floor_seq=0, keep_empty=True))
    return [f for f in files if f is not None]


def discard_stale(out_dir: Path) -> int:
    """Remove NDJSON files left by an earlier, failed sync (they are regenerated from watermarks)."""
    removed = 0
    for table in TABLE_SCHEMAS:
        table_dir = out_dir / table
        if not table_dir.is_dir():
            continue
        for path in table_dir.glob("*.ndjson"):
            path.unlink()
            removed += 1
    return removed


def encode_row(
    row: Mapping[str, object],
    schema: Sequence[Column],
    *,
    uploaded_at: datetime,
    anonymizer: Anonymizer | None = None,
) -> str:
    """One NDJSON line (``\\n``-terminated) with exactly the schema's keys, in schema order."""
    out: dict[str, object] = {}
    for name, kind in schema:
        if name == UPLOADED_AT:
            out[name] = _encode_timestamp(uploaded_at)
            continue
        if name not in row:
            raise ValueError(f"row is missing column {name!r}")
        value = row[name]
        if anonymizer is not None and name in ANONYMIZED_COLUMNS and isinstance(value, str):
            value = anonymizer(value)
        out[name] = _encode_value(name, kind, value)
    return json.dumps(out, ensure_ascii=False, separators=(",", ":")) + "\n"


# --------------------------------------------------------------------------------- helpers
def _store_columns(table: str) -> list[str]:
    return [name for name, _ in TABLE_SCHEMAS[table] if name != UPLOADED_AT]


@dataclass(frozen=True, slots=True)
class _BatchWriter:
    """Writes one NDJSON file per table for a batch (temp file, fsync, atomic rename, 0600)."""

    out_dir: Path
    batch_id: str
    uploaded_at: datetime
    anonymizer: Anonymizer | None

    def write(
        self,
        table: str,
        rows: Iterable[Mapping[str, object]],
        disposition: Disposition,
        *,
        floor_seq: int,
        keep_empty: bool,
    ) -> OutboxFile | None:
        table_dir = self.out_dir / table
        table_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        partial = table_dir / f".{self.batch_id}.ndjson.partial"
        try:
            count, max_seq = self._spool(partial, table, rows, floor_seq)
        except BaseException:
            partial.unlink(missing_ok=True)
            raise
        if count == 0 and not keep_empty:
            partial.unlink()
            _remove_if_empty(table_dir)
            return None
        final = table_dir / f"{self.batch_id}.ndjson"
        os.replace(partial, final)
        return OutboxFile(table=table, path=final, rows=count, max_seq=max_seq, disposition=disposition)

    def _spool(
        self, path: Path, table: str, rows: Iterable[Mapping[str, object]], floor_seq: int
    ) -> tuple[int, int]:
        schema = TABLE_SCHEMAS[table]
        has_seq = any(name == "ingest_seq" for name, _ in schema)
        count, max_seq = 0, floor_seq
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
            for row in rows:
                fh.write(encode_row(row, schema, uploaded_at=self.uploaded_at, anonymizer=self.anonymizer))
                count += 1
                if has_seq:
                    max_seq = max(max_seq, _as_int(row["ingest_seq"]))
            fh.flush()
            os.fsync(fh.fileno())
        return count, max_seq


def _remove_if_empty(directory: Path) -> None:
    if not any(directory.iterdir()):
        directory.rmdir()


def _as_int(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"expected an integer, got {type(value).__name__}")
    return value


def _encode_timestamp(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timestamps must be timezone-aware")
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _encode_string(value: object) -> object:
    if not isinstance(value, str):
        raise TypeError(type(value).__name__)
    return str(value)


def _encode_int(value: object) -> object:
    return _as_int(value)


def _encode_bool(value: object) -> object:
    if not isinstance(value, bool):
        raise TypeError(type(value).__name__)
    return value


def _encode_ts(value: object) -> object:
    if not isinstance(value, datetime):
        raise TypeError(type(value).__name__)
    return _encode_timestamp(value)


def _encode_date(value: object) -> object:
    if not isinstance(value, date) or isinstance(value, datetime):
        raise TypeError(type(value).__name__)
    return value.isoformat()


def _encode_numeric(value: object) -> object:
    if isinstance(value, bool) or not isinstance(value, Decimal | int):
        raise TypeError(type(value).__name__)  # floats never carry money (NFR-04)
    number = Decimal(value)
    if not number.is_finite():
        raise ValueError("non-finite number")
    return format(number, "f")


_ENCODERS: Final[Mapping[str, Callable[[object], object]]] = MappingProxyType({
    "STRING": _encode_string,
    "INT64": _encode_int,
    "BOOL": _encode_bool,
    "TIMESTAMP": _encode_ts,
    "DATE": _encode_date,
    "NUMERIC": _encode_numeric,
})


def _encode_value(name: str, kind: str, value: object) -> object:
    if value is None:
        return None
    try:
        return _ENCODERS[kind](value)
    except (TypeError, ValueError) as exc:
        raise type(exc)(f"column {name!r} ({kind}) cannot hold this value: {exc}") from exc
