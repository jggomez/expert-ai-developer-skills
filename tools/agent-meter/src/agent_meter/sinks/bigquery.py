"""BigQuery replica of the local store (Option B; ADR §3.11, contracts §3.11 and §7).

Data moves only through batch **load jobs** (NDJSON files from the logical outbox) and
schema changes only through DDL query jobs, which keeps the sink inside the free tier
(NFR-05, invariant I-7). A fact table's watermark advances only after its load job has
finished without errors; failures, offline periods and expired credentials leave the
watermark and the backlog in place for the next cycle (BQ-05/06/07).

The cloud SDK is imported lazily inside :func:`google_gateway` (invariant I-2): Option A
never needs the ``[bigquery]`` extra. Everything else talks to a :class:`BigQueryGateway`,
which keeps this module testable without the SDK.
"""

from __future__ import annotations

import importlib
import logging
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from string import Template
from types import MappingProxyType
from typing import Any, Final, Literal, Protocol

from agent_meter.sinks.outbox import (
    FACT_TABLES,
    TABLE_SCHEMAS,
    WATERMARK_PREFIX,
    Anonymizer,
    Column,
    Disposition,
    OutboxFile,
    OutboxStore,
    discard_stale,
    load_salt,
    materialize,
    new_batch_id,
    pending_counts,
)

__all__ = [
    "DEDUP_KEYS",
    "DEFAULT_BYTE_CEILING",
    "LAST_SYNC_KEY",
    "RECONCILE_METRICS",
    "VIEW_NAMES",
    "BigQueryGateway",
    "BigQuerySettings",
    "DryRunCheck",
    "LoadResult",
    "LoadSpec",
    "SinkConfig",
    "SinkHome",
    "SyncResult",
    "SyncStore",
    "build_load_spec",
    "check_view_costs",
    "classify_error",
    "ddl_statements",
    "describe_sync",
    "ensure_dataset",
    "google_gateway",
    "reconcile",
    "sync",
]

_log = logging.getLogger(__name__)

SyncStatus = Literal["ok", "offline", "auth", "error", "dry_run"]
ErrorKind = Literal["auth", "offline", "error"]

LAST_SYNC_KEY: Final = "bq_last_sync_at"
DEFAULT_BYTE_CEILING: Final = 1 << 30  # 1 GiB per view at 10x volume (ADR §3.11, BQ-09)
SQL_DIR: Final = Path(__file__).resolve().parent.parent / "sql" / "bigquery"

VIEW_NAMES: Final = (
    "v_calls", "v_daily_project_cost", "v_sessions", "v_tasks", "v_agent_runs",
    "v_agent_type_cost", "v_tool_counts", "v_task_latency", "v_dev_hours", "v_client_month",
    "v_unpriced_models", "v_untracked", "v_health",
)
DEDUP_KEYS: Final[Mapping[str, tuple[str, ...]]] = MappingProxyType({
    "llm_calls": ("call_id",),
    "tasks": ("task_id",),
    "agent_runs": ("agent_run_id",),
    "tool_uses": ("agent_run_id", "tool_name"),
    "sessions": ("session_id",),
})
RECONCILE_METRICS: Final = (
    "calls", "input_tokens", "output_tokens", "cache_write_tokens", "cache_read_tokens",
    "cost_usd", "unpriced_calls",
)

_PARTITION_FIELDS: Final[Mapping[str, str | None]] = MappingProxyType({
    "llm_calls": "ts", "tasks": "started_at", "agent_runs": "started_at",
    "sessions": "started_at", "tool_uses": None,
})
_CLUSTER_FIELDS: Final = ("project_id", "host")
_PROJECT_RE: Final = re.compile(r"^[a-z][a-z0-9-]{4,28}[a-z0-9]$")
_DATASET_RE: Final = re.compile(r"^[A-Za-z0-9_]{1,1024}$")
_LOCATION_RE: Final = re.compile(r"^[A-Za-z0-9-]{2,64}$")
_AUTH_ERRORS: Final = frozenset({
    "RefreshError", "DefaultCredentialsError", "Unauthorized", "Forbidden",
    "ReauthFailError", "UserAccessTokenError",
})
_OFFLINE_ERRORS: Final = frozenset({
    "TransportError", "ServiceUnavailable", "RetryError", "DeadlineExceeded", "GatewayTimeout",
    "ConnectionError", "Timeout", "ConnectTimeout", "ReadTimeout",
})
_SEVERITY: Final[Mapping[str, int]] = MappingProxyType(
    {"ok": 0, "error": 1, "offline": 2, "auth": 3}
)


# ------------------------------------------------------------------------- structural types
class BigQuerySettings(Protocol):
    """Fields of ``config.BigQueryConfig`` (contracts §3.6) that the sink reads."""

    @property
    def enabled(self) -> bool: ...
    @property
    def project(self) -> str: ...
    @property
    def dataset(self) -> str: ...
    @property
    def location(self) -> str: ...
    @property
    def anonymize_projects(self) -> bool: ...


class SinkConfig(Protocol):
    """``config.Config`` as seen by the sink."""

    @property
    def bigquery(self) -> BigQuerySettings: ...


class SinkHome(Protocol):
    """``paths.AppHome`` as seen by the sink."""

    @property
    def outbox_dir(self) -> Path: ...
    @property
    def secret(self) -> Path: ...


class SyncStore(OutboxStore, Protocol):
    """``store.Store`` as seen by :func:`sync` (reads plus watermark writes)."""

    def set_meta(self, key: str, value: str) -> None: ...


@dataclass(frozen=True, slots=True)
class LoadSpec:
    """Everything a load job needs, independent of the SDK."""

    destination: str  # "<project>.<dataset>.<table>"
    schema: tuple[Column, ...]
    write_disposition: Disposition
    partition_field: str | None
    clustering_fields: tuple[str, ...]


class BigQueryGateway(Protocol):
    """The three BigQuery operations the sink uses (no streaming, no DML)."""

    def load_ndjson(self, path: Path, spec: LoadSpec) -> str:
        """Run a load job, wait for it, raise on failure, return the job id."""
        ...

    def execute(self, sql: str) -> list[dict[str, object]]:
        """Run a DDL or SELECT query job and return its rows."""
        ...

    def dry_run_bytes(self, sql: str) -> int:
        """Bytes a query would scan, from a dry run (free, nothing executes)."""
        ...


@dataclass(frozen=True, slots=True)
class LoadResult:
    table: str
    rows: int
    job_id: str
    ok: bool
    error_class: str | None


@dataclass(frozen=True, slots=True)
class SyncResult:
    status: SyncStatus
    loads: tuple[LoadResult, ...]
    backlog: dict[str, int]


@dataclass(frozen=True, slots=True)
class DryRunCheck:
    view: str
    bytes_processed: int
    ok: bool


# ----------------------------------------------------------------------------- public API
def build_load_spec(file: OutboxFile, *, project: str, dataset: str) -> LoadSpec:
    """Fact tables append into partitioned ``raw_<table>``; reference tables replace ``<table>``."""
    if file.table in FACT_TABLES:
        return LoadSpec(
            destination=f"{project}.{dataset}.raw_{file.table}",
            schema=TABLE_SCHEMAS[file.table],
            write_disposition=file.disposition,
            partition_field=_PARTITION_FIELDS[file.table],
            clustering_fields=_CLUSTER_FIELDS,
        )
    return LoadSpec(
        destination=f"{project}.{dataset}.{file.table}",
        schema=TABLE_SCHEMAS[file.table],
        write_disposition=file.disposition,
        partition_field=None,
        clustering_fields=(),
    )


def ddl_statements(
    cfg: BigQuerySettings, *, default_table_expiration_days: int | None = None
) -> list[str]:
    """Dataset, tables and views DDL, rendered for ``cfg`` and in dependency order."""
    _validate_target(cfg)
    options = f"location = '{cfg.location}'"
    if default_table_expiration_days is not None:
        if default_table_expiration_days < 1:
            raise ValueError("default_table_expiration_days must be at least 1")
        options += f", default_table_expiration_days = {default_table_expiration_days}"
    statements = [f"CREATE SCHEMA IF NOT EXISTS `{cfg.project}.{cfg.dataset}` OPTIONS ({options})"]
    for name in ("tables.sql", "views.sql"):
        text = (SQL_DIR / name).read_text(encoding="utf-8")
        statements += _render(text, project=cfg.project, dataset=cfg.dataset)
    return statements


def ensure_dataset(
    cfg: BigQuerySettings,
    *,
    client: BigQueryGateway | None = None,
    default_table_expiration_days: int | None = None,
) -> None:
    """Create the dataset, tables and views; idempotent (``IF NOT EXISTS`` / ``OR REPLACE``)."""
    statements = ddl_statements(cfg, default_table_expiration_days=default_table_expiration_days)
    gateway = client or google_gateway(cfg.project, cfg.location)
    for statement in statements:
        gateway.execute(statement)


def sync(
    home: SinkHome,
    cfg: SinkConfig,
    store: SyncStore,
    *,
    full_reload: bool = False,
    dry_run: bool = False,
    client_factory: Callable[[str], BigQueryGateway] | None = None,
    now: datetime | None = None,
) -> SyncResult:
    """Upload the outbox. Call with the store's exclusive lock held.

    Never raises for cloud-side failures: they map to ``auth``/``offline``/``error`` and leave
    the backlog for the next cycle. Raises ``ValueError`` only for local misconfiguration
    (sink disabled, invalid identifiers, missing anonymization salt).
    """
    bq = cfg.bigquery
    if not bq.enabled:
        raise ValueError("the BigQuery sink is not enabled; run 'agent-meter setup --cloud'")
    _validate_target(bq)
    anonymizer = Anonymizer(load_salt(home.secret)) if bq.anonymize_projects else None
    if dry_run:
        backlog = _total_counts(store) if full_reload else pending_counts(store)
        return SyncResult(status="dry_run", loads=(), backlog=backlog)

    moment = (now or datetime.now(UTC)).astimezone(UTC)
    discard_stale(home.outbox_dir)
    files = materialize(
        store, home.outbox_dir, batch_id=new_batch_id(moment), full=full_reload,
        anonymizer=anonymizer, now=moment,
    )
    gateway = _connect(client_factory or _default_factory(bq.location), bq.project)
    if isinstance(gateway, str):
        return SyncResult(status=gateway, loads=(), backlog=pending_counts(store))
    status, loads = _upload(gateway, store, files, bq)
    if status == "ok":
        store.set_meta(LAST_SYNC_KEY, moment.isoformat())
    return SyncResult(status=status, loads=tuple(loads), backlog=pending_counts(store))


def classify_error(exc: BaseException) -> ErrorKind:
    """Map an SDK/network exception (by class name, SDK-free) to a sync status."""
    seen: set[int] = set()
    current: BaseException | None = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        names = {cls.__name__ for cls in type(current).__mro__}
        if names & _AUTH_ERRORS:
            return "auth"
        if isinstance(current, OSError) or names & _OFFLINE_ERRORS:
            return "offline"
        current = current.__cause__ or current.__context__
    return "error"


def describe_sync(result: SyncResult, cfg: BigQuerySettings) -> str:
    """One user-facing sentence per outcome; never includes exception text or tokens."""
    target = f"{cfg.project}.{cfg.dataset}"
    pending = sum(result.backlog.values())
    if result.status == "ok":
        rows = sum(load.rows for load in result.loads if load.ok)
        return f"Synced {rows} rows to {target} ({len(result.loads)} load jobs)."
    if result.status == "dry_run":
        detail = ", ".join(f"{table} {count}" for table, count in result.backlog.items())
        return (
            f"Dry run: would upload {pending} rows to {target} ({detail}); "
            "reference tables are re-uploaded in full."
        )
    if result.status == "auth":
        return (
            f"BigQuery rejected the credentials for project {cfg.project} (expired, missing or "
            "without permission). Fix: run 'gcloud auth application-default login' and make sure "
            f"your account has roles/bigquery.dataEditor and roles/bigquery.jobUser on "
            f"{cfg.project}. Local collection is unaffected; {pending} rows wait in the outbox "
            "for the next sync."
        )
    if result.status == "offline":
        return (
            "BigQuery is unreachable (offline or network error). Local collection is unaffected; "
            f"{pending} rows wait in the outbox and upload on the next sync."
        )
    failed = ", ".join(
        f"{load.table} ({load.error_class})" for load in result.loads if not load.ok
    )
    return (
        f"BigQuery load failed for {failed}. {pending} rows stay in the outbox and are retried "
        "on the next sync; run 'agent-meter doctor --cloud' for details."
    )


def check_view_costs(
    cfg: BigQuerySettings,
    *,
    client: BigQueryGateway | None = None,
    ceiling_bytes: int = DEFAULT_BYTE_CEILING,
    volume_factor: int = 10,
) -> list[DryRunCheck]:
    """BQ-09: dry-run a full-history read of every view; ``ok`` if ``bytes x factor <= ceiling``."""
    _validate_target(cfg)
    if ceiling_bytes <= 0 or volume_factor <= 0:
        raise ValueError("ceiling_bytes and volume_factor must be positive")
    gateway = client or google_gateway(cfg.project, cfg.location)
    checks = []
    for view in VIEW_NAMES:
        scanned = gateway.dry_run_bytes(f"SELECT * FROM `{cfg.project}.{cfg.dataset}.{view}`")
        checks.append(DryRunCheck(view, scanned, scanned * volume_factor <= ceiling_bytes))
    return checks


def reconcile(
    cfg: SinkConfig,
    store: OutboxStore,
    date_from: date,
    date_to: date,
    *,
    client: BigQueryGateway | None = None,
    anonymizer: Anonymizer | None = None,
) -> list[dict[str, object]]:
    """BQ-08: per (local_date, project_id) totals, local vs BigQuery; ``[]`` means identical.

    With ``anonymize_projects`` the cloud holds hashed ids, so local ids are mapped through
    the same ``anonymizer`` before comparing; differences are reported with the local id.
    """
    bq = cfg.bigquery
    _validate_target(bq)
    if date_from > date_to:
        raise ValueError("date_from must not be after date_to")
    if bq.anonymize_projects and anonymizer is None:
        raise ValueError("anonymize_projects is on: pass the local anonymizer to map project ids")
    local_rows = store.query(_reconcile_sql("v_daily_project_cost", "?", "?"), [date_from, date_to])
    gateway = client or google_gateway(bq.project, bq.location)
    cloud_rows = gateway.execute(
        _reconcile_sql(
            f"`{bq.project}.{bq.dataset}.v_daily_project_cost`",
            f"DATE '{date_from.isoformat()}'",
            f"DATE '{date_to.isoformat()}'",
        )
    )
    local, shown = _index_local(local_rows, anonymizer)
    cloud = {(_day(row["local_date"]), str(row["project_id"])): row for row in cloud_rows}
    return _diff_totals(local, cloud, shown)


def google_gateway(project: str, location: str) -> BigQueryGateway:
    """Gateway over ``google.cloud.bigquery`` (ADC; project always explicit)."""
    return _GoogleGateway(project, location)


# --------------------------------------------------------------------------------- helpers
class _GoogleGateway:
    def __init__(self, project: str, location: str) -> None:
        self._bq = importlib.import_module("google.cloud.bigquery")
        self._client: Any = self._bq.Client(project=project, location=location)

    def load_ndjson(self, path: Path, spec: LoadSpec) -> str:
        bq = self._bq
        options: dict[str, object] = {
            "source_format": bq.SourceFormat.NEWLINE_DELIMITED_JSON,
            "write_disposition": spec.write_disposition,
            "schema": [bq.SchemaField(name, kind, mode="NULLABLE") for name, kind in spec.schema],
            "ignore_unknown_values": False,
        }
        if spec.partition_field is not None:
            options["time_partitioning"] = bq.TimePartitioning(
                type_=bq.TimePartitioningType.MONTH, field=spec.partition_field
            )
        if spec.clustering_fields:
            options["clustering_fields"] = list(spec.clustering_fields)
        with path.open("rb") as fh:
            job = self._client.load_table_from_file(
                fh, spec.destination, job_config=bq.LoadJobConfig(**options)
            )
            job.result()
        return str(job.job_id)

    def execute(self, sql: str) -> list[dict[str, object]]:
        job = self._client.query(sql)
        return [dict(row.items()) for row in job.result()]

    def dry_run_bytes(self, sql: str) -> int:
        config = self._bq.QueryJobConfig(dry_run=True, use_query_cache=False)
        job = self._client.query(sql, job_config=config)
        return int(job.total_bytes_processed or 0)


def _default_factory(location: str) -> Callable[[str], BigQueryGateway]:
    def make(project: str) -> BigQueryGateway:
        return google_gateway(project, location)

    return make


def _connect(
    factory: Callable[[str], BigQueryGateway], project: str
) -> BigQueryGateway | ErrorKind:
    """Build the gateway, or map the failure (no ADC, expired token, offline) to a status."""
    try:
        return factory(project)
    except Exception as exc:  # mapped to a status; the backlog stays for the next cycle
        kind = classify_error(exc)
        _log.warning("bigquery client unavailable (%s): %s", kind, type(exc).__name__)
        return kind


def _index_local(
    rows: list[dict[str, object]], anonymizer: Anonymizer | None
) -> tuple[dict[tuple[str, str], Mapping[str, object]], dict[tuple[str, str], str]]:
    """Key local totals by (day, cloud-side project id); remember the clear id for display."""
    local: dict[tuple[str, str], Mapping[str, object]] = {}
    shown: dict[tuple[str, str], str] = {}
    for row in rows:
        clear_id = str(row["project_id"])
        cloud_id = anonymizer(clear_id) if anonymizer is not None else clear_id
        key = (_day(row["local_date"]), str(cloud_id))
        local[key], shown[key] = row, clear_id
    return local, shown


def _diff_totals(
    local: Mapping[tuple[str, str], Mapping[str, object]],
    cloud: Mapping[tuple[str, str], Mapping[str, object]],
    shown: Mapping[tuple[str, str], str],
) -> list[dict[str, object]]:
    diffs: list[dict[str, object]] = []
    for key in sorted(local.keys() | cloud.keys()):
        mine, theirs = local.get(key, {}), cloud.get(key, {})
        for metric in RECONCILE_METRICS:
            left, right = mine.get(metric), theirs.get(metric)
            if left != right:
                diffs.append({
                    "local_date": key[0], "project_id": shown.get(key, key[1]),
                    "metric": metric, "local": left, "cloud": right,
                })
    return diffs


def _upload(
    gateway: BigQueryGateway, store: SyncStore, files: list[OutboxFile], bq: BigQuerySettings
) -> tuple[SyncStatus, list[LoadResult]]:
    status: Literal["ok", "auth", "offline", "error"] = "ok"
    loads: list[LoadResult] = []
    for file in files:
        spec = build_load_spec(file, project=bq.project, dataset=bq.dataset)
        try:
            job_id = gateway.load_ndjson(file.path, spec)
        except Exception as exc:  # recorded per table; watermark and file stay in place
            kind = classify_error(exc)
            _log.warning("bigquery load of %s failed (%s): %s", file.table, kind, type(exc).__name__)
            loads.append(LoadResult(file.table, file.rows, "", False, type(exc).__name__))
            if _SEVERITY[kind] > _SEVERITY[status]:
                status = kind
            if kind in ("auth", "offline"):
                break
            continue
        loads.append(LoadResult(file.table, file.rows, job_id, True, None))
        if file.table in FACT_TABLES:
            store.set_meta(WATERMARK_PREFIX + file.table, str(file.max_seq))
        file.path.unlink(missing_ok=True)
    return status, loads


def _total_counts(store: OutboxStore) -> dict[str, int]:
    counts: dict[str, int] = {}
    for table in FACT_TABLES:
        rows = store.query(f"SELECT COUNT(*) AS n FROM {table}")
        value = rows[0]["n"] if rows else 0
        counts[table] = value if isinstance(value, int) else 0
    return counts


def _validate_target(cfg: BigQuerySettings) -> None:
    if not _PROJECT_RE.fullmatch(cfg.project):
        raise ValueError(f"invalid GCP project id {cfg.project!r}")
    if not _DATASET_RE.fullmatch(cfg.dataset):
        raise ValueError("invalid BigQuery dataset name (letters, digits and _ only)")
    if not _LOCATION_RE.fullmatch(cfg.location):
        raise ValueError("invalid BigQuery location")


def _render(text: str, *, project: str, dataset: str) -> list[str]:
    body = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith("--"))
    rendered = Template(body).substitute(project=project, dataset=dataset)
    return [part.strip() for part in re.split(r";[ \t]*(?:\n|$)", rendered) if part.strip()]


def _reconcile_sql(source: str, low: str, high: str) -> str:
    sums = ", ".join(f"SUM({metric}) AS {metric}" for metric in RECONCILE_METRICS)
    return (
        f"SELECT local_date, project_id, {sums} FROM {source} "
        f"WHERE local_date BETWEEN {low} AND {high} GROUP BY local_date, project_id"
    )


def _day(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    return str(value)
