# agent-meter — Interface Contracts v1 (normative for Tracks 11A–11D)

> Companion to `ADR-001-agent-meter.md`. If code and this file disagree, this file wins until it is amended, and an amendment needs the architect's or orchestrator's sign-off.
> All paths are relative to `tools/agent-meter/src/agent_meter/` unless they start with `tools/` or `~`.
> Conventions:
> - Python ≥ 3.11 with `from __future__ import annotations`.
> - Timestamps are **timezone-aware UTC** `datetime`.
> - Money is `decimal.Decimal`, never `float`.
> - Token counts are `int`, with `None` meaning **unknown** (never coerced to 0).
> - Every public function is fully type-annotated.

## 1. Ownership and dependency direction

```
cli ─► collector ─► readers/* ─► model, timeline, _protowire
  │        │──────► project_resolver ─► (PathCache protocol, implemented by store)
  │        └──────► store ─► model, pricing (PricingTable rows only)
  ├─► summary ─► store (views only)      ├─► report ─► store (views only)
  ├─► hook ─► (fast path: stdlib only) ─► spawns `agent-meter hook-worker` ─► collector, summary, notify
  ├─► setup/* , scheduler/*              └─► sinks/outbox ─► store ; sinks/bigquery ─► outbox (lazy google import)
```

| Track | Owns (exclusive write) | May import |
| :--- | :--- | :--- |
| 11A | `model.py`, `timeline.py`, `project_resolver.py`, `pricing.py`, `pricing.yaml`, `readers/**`, `tools/agent-meter/tests/unit/{test_readers*,test_timeline,test_project_resolver,test_pricing}.py`, `tools/agent-meter/tests/contract/**`, `tools/agent-meter/tests/fixtures/**` | stdlib, `yaml` |
| 11B | `paths.py`, `config.py`, `locking.py`, `store.py`, `collector.py`, `summary.py`, `notify.py`, `hook.py`, `cli.py`, `__main__.py`, `__init__.py`, `sql/duckdb/**`, `scheduler/**`, `setup/**`, `tools/agent-meter/pyproject.toml`, `tools/agent-meter/README.md`, `tests/unit/{test_store,test_collector,test_summary,test_cli,test_hook,test_scheduler,test_setup_*,test_locking,test_config}.py`, `tests/integration/**` | everything except `sinks/bigquery.py` at module top level |
| 11C | `report/**`, `tests/unit/test_report.py` | `store`, `model`, `paths`, `config` (read-only use) |
| 11D | `sinks/**`, `sql/bigquery/**`, `docs/agent-metrics/looker-studio.md`, `tests/unit/test_outbox.py`, `tests/unit/test_bigquery_sink.py`, `tests/cloud/**` | `store`, `model`, `config`, `paths`, `google.cloud.bigquery` (lazy, inside functions) |

How the tracks build without blocking each other:
- 11B, 11C and 11D code against the dataclasses in §2. They can build stores from hand-made records, using `tests/fixtures/records.py`, which 11A delivers **first**: it is a trivial module of record factories.
- The `cli.py` subcommands `report`, `sync` and `verify --cloud` call only the entry points in §3.10 and §3.11, imported inside the command handlers.

## 2. `model.py` — records (all `@dataclass(frozen=True, slots=True)`)

```python
SCHEMA_VERSION: Final = 1

class Host(StrEnum):
    CLAUDE_CODE = "claude-code"; ANTIGRAVITY_CLI = "antigravity-cli"
    ANTIGRAVITY_IDE = "antigravity-ide"; ANTIGRAVITY_APP = "antigravity-app"
class TaskStatus(StrEnum):   IN_PROGRESS = "in_progress"; DONE = "done"; CLOSED_STALE = "closed_stale"
class RunStatus(StrEnum):    RUNNING = "running"; DONE = "done"; ERROR = "error"; STOPPED = "stopped"
class DurationSource(StrEnum): REPORTED = "reported"; DERIVED = "derived"
class DiagnosticKind(StrEnum):
    CORRUPT = "corrupt"; FORMAT_CHANGED = "format_changed"; UNREADABLE = "unreadable"
    UNKNOWN_USAGE_ITERATION = "unknown_usage_iteration"; OWNER_MISSING = "owner_missing"
class UntrackedReason(StrEnum): LEGACY_PB = "legacy_pb"; NO_USAGE_DATA = "no_usage_data"; FORMAT_CHANGED = "format_changed"

@dataclass(frozen=True, slots=True)
class FileFingerprint:
    relpath: str            # relative to the host root; never persisted
    kind: str               # "cc_main" | "cc_sub" | "cc_meta" | "agy_db" | "agy_wal" | "agy_transcript" | "agy_subagents"
    size: int; mtime_ns: int; inode: int

@dataclass(frozen=True, slots=True)
class SessionUnit:
    host: Host
    unit_id: str            # == root session_id (Claude sessionId / Antigravity root conversation_id)
    root: Path              # host root directory (in memory only)
    files: tuple[FileFingerprint, ...]
    member_ids: tuple[str, ...] = ()   # Antigravity: child conversation ids in this unit
    @property
    def fingerprint(self) -> str: ...  # sha256 hex over sorted (relpath,size,mtime_ns,inode)

@dataclass(frozen=True, slots=True)
class ProjectRef:
    project_id: str         # "git:<16 hex>" | "path:<16 hex>" | "(unassigned)"
    kind: Literal["remote", "path", "unassigned"]
    display_name: str
    remote_url: str | None  # normalized, credential-free, e.g. "github.com/owner/repo"

@dataclass(frozen=True, slots=True)
class SessionRecord:
    session_id: str; host: Host
    workspace_path: str | None      # TRANSIENT: consumed by collector → project_id; never stored
    started_at: datetime; ended_at: datetime
    status: Literal["open", "closed"]
    host_version: str | None        # e.g. Claude "2.1.229"; Antigravity None
    owner_rank: str
    project_id: str | None = None   # filled by collector

@dataclass(frozen=True, slots=True)
class TaskRecord:
    task_id: str; session_id: str; host: Host; seq_in_session: int
    started_at: datetime; ended_at: datetime
    wall_clock_ms: int; active_ms: int; reported_ms: int | None; duration_source: DurationSource
    status: TaskStatus
    agent_runs: int; max_spawn_depth: int
    critical_path_ms: int; critical_path: str        # "main→code-implementer→qa-tester"
    retries: int; retry_summary: str                 # "" | "qa-tester→code-implementer"
    owner_rank: str
    project_id: str | None = None

@dataclass(frozen=True, slots=True)
class AgentRunRecord:
    agent_run_id: str; task_id: str; session_id: str; host: Host
    parent_agent_run_id: str | None
    agent_type: str                  # "main" for depth 0; validated charset (ADR §3.13)
    description_hash: str | None     # sha256(salt+description) hex; None for main
    spawn_depth: int
    started_at: datetime; ended_at: datetime; active_ms: int
    status: RunStatus
    errors: int; files_touched: int; test_runs: int; test_failures: int
    tools_untracked: bool
    owner_rank: str
    project_id: str | None = None

@dataclass(frozen=True, slots=True)
class CallRecord:
    call_id: str; host: Host; session_id: str; task_id: str; agent_run_id: str
    ts: datetime
    model: str | None; model_label: str | None
    input_tokens: int | None; output_tokens: int | None; thinking_tokens: int | None
    cache_write_5m_tokens: int | None; cache_write_1h_tokens: int | None; cache_read_tokens: int | None
    latency_ms: int | None
    speed: str | None; inference_geo: str | None
    is_error: bool
    source_format: str               # e.g. "cc-2.1" | "agy-gen-v1" | "agy-transcript-v1"
    owner_rank: str
    project_id: str | None = None

@dataclass(frozen=True, slots=True)
class ToolUseRecord:
    agent_run_id: str; tool_name: str; calls: int; errors: int

@dataclass(frozen=True, slots=True)
class UntrackedRecord:
    conversation_id: str; host: Host; reason: UntrackedReason
    observed_from: date; observed_to: date

@dataclass(frozen=True, slots=True)
class Diagnostic:
    host: Host; kind: DiagnosticKind
    unit_hash: str                   # sha256(unit_id)[:12] — never the raw id or a path
    file_kind: str; error_class: str | None; count: int = 1

@dataclass(frozen=True, slots=True)
class UnitBatch:
    unit: SessionUnit
    sessions: tuple[SessionRecord, ...]; tasks: tuple[TaskRecord, ...]
    agent_runs: tuple[AgentRunRecord, ...]; calls: tuple[CallRecord, ...]
    tool_uses: tuple[ToolUseRecord, ...]
    diagnostics: tuple[Diagnostic, ...]
    format_fingerprint: str          # sha256 of the observed shape (table/column set, 1.20 keys, line types)

@dataclass(frozen=True, slots=True)
class ReaderOptions:
    now: datetime
    idle_threshold_s: int = 120
    stale_after_s: int = 86_400
    store_agent_descriptions: bool = False
    description_salt: bytes = b""    # from ~/.agent-meter/secret
```

ID formats (I-9):

| Record | Claude Code | Antigravity |
| :--- | :--- | :--- |
| `session_id` | `sessionId` | root `conversation_id` |
| `task_id` | `claude-code:<promptId>`; fallback `claude-code:<sid>:pre` | `<host>:<conversation_id>:<user_input_step_idx>` |
| `agent_run_id` | main `<task_id>:main`; sub `claude-code:agent:<agentId>` | main `<task_id>:main`; sub `<host>:agent:<child_conversation_id>` |
| `call_id` | `claude-code:<requestId>` (fallback `claude-code:msg:<message.id>`) | `<host>:<trajectory_id>:<last_step_index>`; fallback `<host>:conv:<conversation_id>:<step_index>` |
| `owner_rank` | `"<0 main\|1 sub>:<file first ts ISO-8601 Z>:<session_id>"` | `"0"` if owned, else `"1:<holder conversation_id>"`. Sessions, tasks and runs use `"0"` |

## 3. Module signatures

### 3.1 `readers/base.py` (11A)
```python
class HostReader(Protocol):
    host: Host
    root: Path
    def discover(self) -> Iterator[SessionUnit]: ...                 # stat-only, never parses content
    def find_unit(self, session_or_conversation_id: str) -> SessionUnit | None: ...  # child id → root unit
    def read_unit(self, unit: SessionUnit, options: ReaderOptions) -> UnitBatch: ...  # never raises for data errors
    def untracked(self) -> list[UntrackedRecord]: ...
    def earliest_available(self) -> date | None: ...                 # for doctor (BR-15)

def available_readers(roots: Mapping[Host, Path] | None = None) -> list[HostReader]: ...
def host_from_transcript_path(path: str) -> Host | None: ...         # ".../antigravity-cli/..." → ANTIGRAVITY_CLI, etc.
```
Concrete classes: `readers.claude_code.ClaudeCodeReader(root: Path)` and `readers.antigravity.AntigravityReader(host: Host, root: Path)`, one instance per Antigravity root. `KNOWN_FORMATS: frozenset[str]` in each module lists the fingerprints that have contract fixtures.

### 3.2 `readers/_protowire.py` (11A)
```python
class ProtoDecodeError(ValueError): ...
def parse(buf: bytes) -> list[tuple[int, int, int | bytes]]          # (field, wire_type, value)
def get_path(buf: bytes, path: str) -> list[int | bytes]             # "1.4.2" → values at that path (repeated-aware)
def kv_map(buf: bytes, path: str = "1.20") -> dict[str, str]         # repeated {1:key,2:value}; non-UTF8 skipped
def duration_ms(buf: bytes, path: str) -> int | None                 # {1:s,2:ns} → ms
```

### 3.3 `timeline.py` (11A, pure)
```python
Interval = tuple[datetime, datetime]
@dataclass(frozen=True, slots=True)
class RunSpan: agent_run_id: str; agent_type: str; started_at: datetime; ended_at: datetime; active_ms: int
def active_intervals(events: Sequence[datetime], idle_threshold_s: int, extra: Sequence[Interval] = ()) -> list[Interval]
def union(intervals: Iterable[Interval]) -> list[Interval]
def total_ms(intervals: Iterable[Interval]) -> int
def critical_path(runs: Sequence[RunSpan]) -> tuple[int, list[str]]          # (ms, agent_types in order)
def retries(runs: Sequence[RunSpan]) -> tuple[int, str]                      # (count, "a→b, c→d")
def dev_hours(spans: Sequence[Interval], tz: ZoneInfo, merge_gap_s: int = 1800) -> dict[date, Decimal]  # hours, 2 dp
def parallelism(run_active_ms: Sequence[int], task_active_ms: int) -> Decimal | None   # None if len<2 or task_active_ms==0
```

### 3.4 `pricing.py` (11A)
```python
@dataclass(frozen=True, slots=True)
class PriceRow:
    model: str; effective_from: date; min_prompt_tokens: int
    input: Decimal; output: Decimal
    cache_write_5m: Decimal | None; cache_write_1h: Decimal | None; cache_read: Decimal | None
    source: Literal["shipped", "local"]; source_url: str | None; fetched_at: date | None
@dataclass(frozen=True, slots=True)
class Alias: alias: str; model: str; estimated: bool; source: Literal["shipped", "local"]
@dataclass(frozen=True, slots=True)
class PricingTable: rows: tuple[PriceRow, ...]; aliases: tuple[Alias, ...]
@dataclass(frozen=True, slots=True)
class PriceResolution: priced_model: str | None; row: PriceRow | None; estimated: bool; inferred: bool
class PricingError(ValueError):
    errors: list[str]

SHIPPED_PATH: Final[Path]  # importlib.resources path of pricing.yaml
def load_pricing(local: Path | None, shipped: Path | None = None) -> PricingTable   # local invalid → PricingError
def validate_file(path: Path) -> list[str]                                          # [] == valid
def resolve_price(table: PricingTable, model: str | None, at: date, prompt_tokens: int,
                  *, speed: str | None = None, default_model: str | None = None) -> PriceResolution
def cost_usd(res: PriceResolution, *, input_tokens: int | None, output_tokens: int | None,
             cache_write_5m_tokens: int | None, cache_write_1h_tokens: int | None,
             cache_read_tokens: int | None) -> Decimal | None   # ORACLE; quantize(Decimal("1e-9"), ROUND_HALF_UP)
def add_local_price(local: Path, row: PriceRow, *, replace: bool = False) -> None   # validate-then-atomic-write
def add_local_alias(local: Path, alias: str, model: str, *, estimated: bool) -> None
def remove_local(local: Path, *, model: str | None = None, effective_from: date | None = None,
                 alias: str | None = None) -> int                                    # rows removed
```
Resolution semantics, which the SQL view must equal:
1. **Effective model**: `m = model or default_model`. If it falls back to `default_model`, `inferred = True`. If both are missing, the result is unpriced.
2. **Alias**: `a = aliases.get(m)`, giving `base = a.model if a else m` and `estimated = bool(a and a.estimated)`.
3. **Fast variant**: if `speed == "fast"`, the call uses the `base + ":fast"` rows when any exist. Otherwise it uses the `base` rows and sets `estimated = True`.
4. **Price row**: among rows of that model with `effective_from ≤ at` and `min_prompt_tokens ≤ prompt_tokens`, take the maximum by `(effective_from, min_prompt_tokens)`.
5. **Missing cache-write prices**: if `cache_write_5m` or `cache_write_1h` is `None`, the input price is used for it. A missing `cache_read` is a validation error.
6. **Unknown tokens**: any token field `None` (unknown) gives `cost_usd = None`.

### 3.5 `project_resolver.py` (11A)
```python
class PathCache(Protocol):
    def get(self, path_hash: str) -> str | None: ...
    def put(self, path_hash: str, project_id: str) -> None: ...
@dataclass(frozen=True, slots=True)
class ProjectOverride:
    display_name: str | None = None; client: str | None = None
    billing: Literal["hourly", "fixed"] | None = None
    rate: Decimal | None = None; fixed_price: Decimal | None = None; currency: str | None = None
@dataclass(frozen=True, slots=True)
class ProjectsConfig:
    projects: Mapping[str, ProjectOverride]; path_aliases: Mapping[str, str]; ignore: tuple[str, ...]
    merges: Mapping[str, str]        # old project_id → surviving project_id
def normalize_remote(url: str) -> str | None
def path_hash(path: str) -> str      # sha256(realpath-or-abspath) hex
def load_projects_config(path: Path) -> ProjectsConfig          # missing file → empty config
def save_projects_config(cfg: ProjectsConfig, path: Path) -> None   # atomic
class ProjectResolver:
    def __init__(self, cache: PathCache, config: ProjectsConfig, *, home: Path, git_timeout_s: float = 2.0) -> None
    def resolve(self, path: str | None) -> ProjectRef               # accepts plain paths and file:// URIs
```

### 3.6 `paths.py`, `config.py`, `locking.py` (11B)
```python
@dataclass(frozen=True, slots=True)
class AppHome:
    root: Path   # --home | $AGENT_METER_HOME | ~/.agent-meter ; created 0700
    @property db/lock/config/projects/pricing_local/secret/install_manifest/snapshot/last_summary/notified -> Path
    @property logs_dir/backups_dir/outbox_dir/state_dir -> Path
    @classmethod
    def resolve(cls, cli_home: str | None = None) -> "AppHome"

@dataclass(frozen=True, slots=True)
class HostConfig: enabled: bool = True; root: Path | None = None; default_model: str | None = None
@dataclass(frozen=True, slots=True)
class BigQueryConfig:
    enabled: bool = False; project: str = ""; dataset: str = "agent_metrics"; location: str = "US"
    mode: Literal["billing", "sandbox"] = "billing"; anonymize_projects: bool = False; looker_template_id: str = ""
@dataclass(frozen=True, slots=True)
class Config:
    timezone: str; idle_threshold_s: int = 120; stale_after_h: int = 24; dev_hours_merge_gap_min: int = 30
    show_task_labels: bool = True; store_agent_descriptions: bool = False
    notify: Literal["auto", "session", "long-tasks", "off"] = "auto"; notify_min_task_s: int = 120
    claude_inline_summary: bool = False
    display_currency: str | None = None; usd_rate: Decimal | None = None   # display units per 1 USD
    hosts: Mapping[Host, HostConfig] = ...; bigquery: BigQueryConfig = BigQueryConfig()
def load_config(home: AppHome) -> Config            # missing file → defaults (timezone = system IANA name)
def save_config(cfg: Config, home: AppHome) -> None # fixed-schema TOML writer, atomic
def get_key(cfg: Config, dotted: str) -> str ; def set_key(cfg: Config, dotted: str, value: str) -> Config

class LockTimeout(TimeoutError): ...
@contextmanager
def store_lock(path: Path, *, exclusive: bool, timeout_s: float) -> Iterator[None]   # fcntl.flock poll every 50 ms
```

### 3.7 `store.py` (11B)
```python
@dataclass(frozen=True, slots=True)
class ApplyStats:
    units: int; calls_changed: int; tasks_changed: int; runs_changed: int; sessions_changed: int
    diagnostics: int

class Store:
    @classmethod
    def open(cls, home: AppHome, *, read_only: bool, lock_timeout_s: float) -> "Store": ...  # takes lock; context manager
    def close(self) -> None
    def migrate(self) -> None                               # creates/upgrades schema; idempotent
    def unit_fingerprint(self, host: Host, unit_id: str) -> str | None
    def apply_batches(self, batches: Sequence[UnitBatch]) -> ApplyStats   # one transaction; rank/row_hash rules (ADR §3.9)
    def record_untracked(self, rows: Sequence[UntrackedRecord]) -> None
    def load_reference_data(self, *, pricing: PricingTable, host_defaults: Mapping[Host, str | None],
                            projects: ProjectsConfig, project_refs: Sequence[ProjectRef],
                            settings: Mapping[str, str]) -> None          # full replace of reference tables
    def path_cache(self) -> PathCache
    def recompute_dev_hours(self, tz: str, merge_gap_s: int) -> None     # rewrites dev_hours_derived
    def set_tag(self, project_id: str, tag: str | None, at: datetime) -> None
    def tag_last(self, project_id: str, tag: str, n: int) -> list[str]   # task_ids tagged
    def set_manual_hours(self, project_id: str, period: str, hours: Decimal) -> None   # "YYYY-MM-DD" | "YYYY-MM"
    def unset_manual_hours(self, project_id: str, period: str) -> bool
    def merge_projects(self, src: str, dst: str) -> int                  # re-keys rows (new ingest_seq)
    def query(self, sql: str, params: Sequence[object] = ()) -> list[dict[str, object]]
    def get_meta(self, key: str) -> str | None ; def set_meta(self, key: str, value: str) -> None
    def rows_since(self, table: str, after_seq: int, columns: Sequence[str]) -> Iterator[dict[str, object]]
    def max_seq(self, table: str) -> int
    def write_snapshot(self, path: Path, *, tz: str, now: datetime) -> None
```

### 3.8 `collector.py`, `summary.py`, `notify.py`, `hook.py` (11B)
```python
@dataclass(frozen=True, slots=True)
class CollectResult:
    status: Literal["ok", "locked", "error"]; stats: ApplyStats | None; duration_ms: int
    diagnostics: tuple[Diagnostic, ...]; units_skipped_unchanged: int
def collect(home: AppHome, cfg: Config, *, hosts: Collection[Host] | None = None, since: date | None = None,
            full: bool = False, only: tuple[Host, str] | None = None, lock_timeout_s: float = 60.0,
            readers: Sequence[HostReader] | None = None, now: datetime | None = None) -> CollectResult

@dataclass(frozen=True, slots=True)
class SessionSummary: ...   # fields = every number in PRD §7 "Session summary" + partial/unpriced/inferred flags
@dataclass(frozen=True, slots=True)
class TaskRollup: ...       # fields = PRD §7 "Per-task rollup" incl. per-agent_type rows (v_agent_type_cost)
def session_summary(store: Store, host: Host, session_id: str, *, now: datetime) -> SessionSummary
def task_rollups(store: Store, *, last: int | None = None, session_id: str | None = None,
                 project_id: str | None = None, tag: str | None = None, since: date | None = None) -> list[TaskRollup]
def render_session_summary(s: SessionSummary, cfg: Config) -> str
def render_task_rollup(r: TaskRollup, cfg: Config, *, label: str | None = None) -> str   # label only when isatty
def summary_from_snapshot(snapshot_path: Path, host: Host, session_id: str, cfg: Config) -> str

def notify(title: str, body: str) -> bool   # macOS osascript / Linux notify-send; False if unavailable; never raises

@dataclass(frozen=True, slots=True)
class HookPayload:
    host: Host | None; event: Literal["session-end", "task-end"]
    session_id: str | None; transcript_path: str | None
    fully_idle: bool | None; termination_reason: str | None; reason: str | None
def parse_payload(raw: bytes, *, host_flag: str, event: str) -> HookPayload   # allowlist keys only
def hook_main(argv: Sequence[str], stdin: BinaryIO, stdout: TextIO) -> int     # ALWAYS returns 0; no duckdb import
def worker_main(argv: Sequence[str]) -> int
```

### 3.9 `cli.py` (11B)
`main(argv: Sequence[str] | None = None) -> int`, built with argparse. Commands and flags follow PRD §7 plus:
- `pricing list|unpriced|add|set|alias|remove|validate`
- `hook-worker` (hidden)
- `collect --scheduled`
- `config show|get|set|edit`

Exit codes:

| Code | Meaning |
| :--- | :--- |
| 0 | ok |
| 1 | error |
| 2 | usage |
| 3 | `doctor` has a FAIL |
| 4 | store busy (lock timeout) |
| 5 | `verify --reconcile` found a difference |

`hook` always exits 0. `--json` output is `json.dumps(obj, default=str, sort_keys=True)`.

### 3.10 `report/` (11C)
```python
@dataclass(frozen=True, slots=True)
class ReportOptions:
    date_from: date | None = None; date_to: date | None = None; month: str | None = None   # "YYYY-MM"
    project_id: str | None = None; client: str | None = None
    display_currency: str | None = None; usd_rate: Decimal | None = None
    generated_at: datetime = ...; show_task_labels: bool = False   # report never shows labels (BR-16)
def build_report(store: Store, options: ReportOptions) -> str      # reads ONLY §6 views; returns full HTML
def write_report(html: str, out: Path) -> Path                     # atomic write; default ~/.agent-meter/report.html
```

### 3.11 `sinks/` (11D)
```python
# sinks/outbox.py — no google imports
FACT_TABLES: Final = ("llm_calls", "tasks", "agent_runs", "tool_uses", "sessions")
REFERENCE_TABLES: Final = ("projects", "pricing", "pricing_aliases", "host_defaults", "dev_hours_manual",
                           "dev_hours_derived", "task_tags", "tag_history", "settings", "untracked")
@dataclass(frozen=True, slots=True)
class OutboxFile: table: str; path: Path; rows: int; max_seq: int; disposition: Literal["WRITE_APPEND", "WRITE_TRUNCATE"]
class Anonymizer:
    def __init__(self, salt: bytes) -> None
    def __call__(self, value: str | None) -> str | None              # hmac-sha256 hex[:16]
def materialize(store: Store, out_dir: Path, *, batch_id: str, full: bool = False,
                anonymizer: Anonymizer | None = None) -> list[OutboxFile]
def pending_counts(store: Store) -> dict[str, int]                   # rows with ingest_seq > watermark

# sinks/bigquery.py — `from google.cloud import bigquery` ONLY inside functions
@dataclass(frozen=True, slots=True)
class LoadResult: table: str; rows: int; job_id: str; ok: bool; error_class: str | None
@dataclass(frozen=True, slots=True)
class SyncResult: status: Literal["ok", "offline", "auth", "error", "dry_run"]; loads: tuple[LoadResult, ...]; backlog: dict[str, int]
def ensure_dataset(cfg: BigQueryConfig, *, client: object | None = None) -> None    # DDL from sql/bigquery/*.sql
def sync(home: AppHome, cfg: Config, store: Store, *, full_reload: bool = False, dry_run: bool = False,
         client_factory: Callable[[str], object] | None = None) -> SyncResult      # watermark advanced only on ok
def reconcile(cfg: Config, store: Store, date_from: date, date_to: date, *, client: object | None = None) -> list[dict[str, object]]
```

### 3.12 `setup/` and `scheduler/` (11B)
```python
# setup/settings_merge.py
@dataclass(frozen=True, slots=True)
class MergePlan: file: Path; existed: bool; before_sha256: str | None; after_text: str; added: tuple[dict, ...]; changed: bool
class SettingsRefused(Exception): reason: Literal["invalid_json", "not_object", "managed", "not_owner"]
def plan_claude(settings_path: Path, command_prefix: str) -> MergePlan
def plan_antigravity(hooks_path: Path, command_prefix: str) -> MergePlan     # ~/.gemini/config/hooks.json
def apply(plan: MergePlan, home: AppHome) -> None                          # backup + atomic write + install.json
def uninstall(home: AppHome) -> list[str]                                  # BR-19 actions taken
# setup/gcp_checks.py
@dataclass(frozen=True, slots=True)
class Check: id: str; status: Literal["OK", "WARN", "FAIL"]; message: str; fix_command: str | None; autofix_safe: bool
def run_checks(project: str, *, runner: Callable[[list[str]], subprocess.CompletedProcess[str]] = ...) -> list[Check]
# scheduler/__init__.py
def install(home: AppHome, executable: Path) -> str ; def uninstall(home: AppHome) -> str ; def status() -> Literal["loaded", "not_loaded", "unsupported"]
```

## 4. DuckDB schema v1 (`sql/duckdb/schema_v1.sql`)

```sql
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);   -- schema_version, bq_watermark:<t>, …
CREATE SEQUENCE IF NOT EXISTS ingest_seq START 1;

CREATE TABLE IF NOT EXISTS sessions (
  session_id TEXT PRIMARY KEY, host TEXT NOT NULL, project_id TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ NOT NULL, status TEXT NOT NULL,
  host_version TEXT, owner_rank TEXT NOT NULL, row_hash TEXT NOT NULL, ingest_seq BIGINT NOT NULL,
  schema_version SMALLINT NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS tasks (
  task_id TEXT PRIMARY KEY, session_id TEXT NOT NULL, host TEXT NOT NULL, project_id TEXT NOT NULL,
  seq_in_session INTEGER NOT NULL, started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ NOT NULL,
  wall_clock_ms BIGINT NOT NULL, active_ms BIGINT NOT NULL, reported_ms BIGINT, duration_source TEXT NOT NULL,
  status TEXT NOT NULL, agent_runs INTEGER NOT NULL, max_spawn_depth INTEGER NOT NULL,
  critical_path_ms BIGINT NOT NULL, critical_path TEXT NOT NULL, retries INTEGER NOT NULL, retry_summary TEXT NOT NULL,
  owner_rank TEXT NOT NULL, row_hash TEXT NOT NULL, ingest_seq BIGINT NOT NULL, schema_version SMALLINT NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS agent_runs (
  agent_run_id TEXT PRIMARY KEY, task_id TEXT NOT NULL, session_id TEXT NOT NULL, host TEXT NOT NULL,
  project_id TEXT NOT NULL, parent_agent_run_id TEXT, agent_type TEXT NOT NULL, description_hash TEXT,
  spawn_depth INTEGER NOT NULL, started_at TIMESTAMPTZ NOT NULL, ended_at TIMESTAMPTZ NOT NULL, active_ms BIGINT NOT NULL,
  status TEXT NOT NULL, errors INTEGER NOT NULL, files_touched INTEGER NOT NULL, test_runs INTEGER NOT NULL,
  test_failures INTEGER NOT NULL, tools_untracked BOOLEAN NOT NULL,
  owner_rank TEXT NOT NULL, row_hash TEXT NOT NULL, ingest_seq BIGINT NOT NULL, schema_version SMALLINT NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS llm_calls (
  call_id TEXT PRIMARY KEY, host TEXT NOT NULL, project_id TEXT NOT NULL, session_id TEXT NOT NULL,
  task_id TEXT NOT NULL, agent_run_id TEXT NOT NULL, ts TIMESTAMPTZ NOT NULL,
  model TEXT, model_label TEXT,
  input_tokens BIGINT, output_tokens BIGINT, thinking_tokens BIGINT,
  cache_write_5m_tokens BIGINT, cache_write_1h_tokens BIGINT, cache_read_tokens BIGINT,
  latency_ms BIGINT, speed TEXT, inference_geo TEXT, is_error BOOLEAN NOT NULL, source_format TEXT NOT NULL,
  owner_rank TEXT NOT NULL, row_hash TEXT NOT NULL, ingest_seq BIGINT NOT NULL, schema_version SMALLINT NOT NULL DEFAULT 1);
CREATE TABLE IF NOT EXISTS tool_uses (
  agent_run_id TEXT NOT NULL, tool_name TEXT NOT NULL, calls INTEGER NOT NULL, errors INTEGER NOT NULL,
  project_id TEXT NOT NULL, host TEXT NOT NULL, ingest_seq BIGINT NOT NULL, PRIMARY KEY (agent_run_id, tool_name));
-- unit change detection (no paths)
CREATE TABLE IF NOT EXISTS source_units (host TEXT NOT NULL, unit_id TEXT NOT NULL, fingerprint TEXT NOT NULL,
  format_fingerprint TEXT NOT NULL, last_ingested_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (host, unit_id));
CREATE TABLE IF NOT EXISTS format_versions (host TEXT NOT NULL, fingerprint TEXT NOT NULL, known BOOLEAN NOT NULL,
  first_seen TIMESTAMPTZ NOT NULL, last_seen TIMESTAMPTZ NOT NULL, PRIMARY KEY (host, fingerprint));
CREATE TABLE IF NOT EXISTS diagnostics (run_at TIMESTAMPTZ NOT NULL, host TEXT NOT NULL, kind TEXT NOT NULL,
  unit_hash TEXT NOT NULL, file_kind TEXT NOT NULL, error_class TEXT, count INTEGER NOT NULL);   -- pruned > 30 days
CREATE TABLE IF NOT EXISTS untracked (conversation_id TEXT PRIMARY KEY, host TEXT NOT NULL, reason TEXT NOT NULL,
  observed_from DATE NOT NULL, observed_to DATE NOT NULL, ingest_seq BIGINT NOT NULL);
CREATE TABLE IF NOT EXISTS path_map (path_hash TEXT PRIMARY KEY, project_id TEXT NOT NULL, resolved_at TIMESTAMPTZ NOT NULL);
-- reference data (full replace from files/config by load_reference_data; never hand-edited)
CREATE TABLE IF NOT EXISTS projects (project_id TEXT PRIMARY KEY, kind TEXT NOT NULL, display_name TEXT NOT NULL,
  remote_url TEXT, client TEXT, billing_model TEXT, hourly_rate DECIMAL(18,4), fixed_price DECIMAL(18,4), rate_currency TEXT);
CREATE TABLE IF NOT EXISTS pricing (model TEXT NOT NULL, effective_from DATE NOT NULL, min_prompt_tokens BIGINT NOT NULL,
  input_per_mtok DECIMAL(12,6) NOT NULL, output_per_mtok DECIMAL(12,6) NOT NULL, cache_write_5m_per_mtok DECIMAL(12,6),
  cache_write_1h_per_mtok DECIMAL(12,6), cache_read_per_mtok DECIMAL(12,6) NOT NULL, source TEXT NOT NULL,
  source_url TEXT, fetched_at DATE, PRIMARY KEY (model, effective_from, min_prompt_tokens));
CREATE TABLE IF NOT EXISTS pricing_aliases (alias TEXT PRIMARY KEY, model TEXT NOT NULL, estimated BOOLEAN NOT NULL, source TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS host_defaults (host TEXT PRIMARY KEY, default_model TEXT);
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);   -- timezone, idle_threshold_s, usd_rate, display_currency
-- user-owned facts
CREATE TABLE IF NOT EXISTS dev_hours_manual (project_id TEXT NOT NULL, period TEXT NOT NULL, hours DECIMAL(8,2) NOT NULL,
  set_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (project_id, period));
CREATE TABLE IF NOT EXISTS dev_hours_derived (project_id TEXT NOT NULL, local_date DATE NOT NULL, hours DECIMAL(8,2) NOT NULL,
  PRIMARY KEY (project_id, local_date));
CREATE TABLE IF NOT EXISTS tag_history (project_id TEXT NOT NULL, tag TEXT, from_ts TIMESTAMPTZ NOT NULL, to_ts TIMESTAMPTZ,
  PRIMARY KEY (project_id, from_ts));                       -- tag NULL = cleared
CREATE TABLE IF NOT EXISTS task_tags (task_id TEXT PRIMARY KEY, tag TEXT NOT NULL, set_at TIMESTAMPTZ NOT NULL);
```
Upsert rule (ADR §3.9) applies to `sessions`, `tasks`, `agent_runs` and `llm_calls`. `row_hash` covers every column except `row_hash`, `ingest_seq` and `owner_rank`. When `projects merge` or a `merges:` entry re-keys `project_id`, each re-keyed row gets a new `ingest_seq`.

## 5. File formats

**`pricing.yaml` / `pricing.local.yaml`**. Money values are strings, parsed as `Decimal`; YAML floats are rejected.
```yaml
version: 1
models:
  claude-opus-5-5:
    source_url: https://platform.claude.com/docs/en/about-claude/pricing
    fetched_at: 2026-10-16
    windows:
      - effective_from: 2000-01-01          # "since forever" sentinel for first known price
        tiers:
          - {min_prompt_tokens: 0, input: "4.00", cache_write_5m: "5.00", cache_write_1h: "8.00", cache_read: "0.20", output: "20.00"}
  gemini-4-argon:
    source_url: https://ai.google.dev/gemini-api/docs/pricing
    fetched_at: 2026-10-16
    windows:
      - {effective_from: 2000-01-01, tiers: [{min_prompt_tokens: 0, input: "2.00", cache_read: "0.10", output: "10.00"}]}
      - {effective_from: 2026-12-01, tiers: [{min_prompt_tokens: 0, input: "4.00", cache_read: "0.20", output: "20.00"}]}
aliases:
  claude-haiku-4-5-20251001: {model: claude-haiku-4-5}
  gemini-3.8-flash-n: {model: gemini-3.8-flash, estimated: true}
```
`validate` enforces all of the following:
- `version == 1`
- every window has a tier with `min_prompt_tokens: 0`
- prices are non-negative strings
- `input`, `output` and `cache_read` are required
- dates are ISO
- aliases point at a defined model (shipped or local) and never at another alias
- no duplicate `(model, effective_from, min_prompt_tokens)` within one file
- no unknown keys

On error, the previous valid table stays in use (PC-07).

**`projects.yaml`**
```yaml
version: 1
projects:
  "git:3f2a9c0d1e2b4a56": {display_name: "Project X", client: "Client Z", billing: hourly, rate: "80000", currency: COP}
  "git:9a8b7c6d5e4f3a21": {client: "Client Z", billing: fixed, fixed_price: "2500", currency: USD}
paths:            # optional aliases: absolute path → project_id (user's own file; may contain paths)
  /Users/me/old/location: "git:3f2a9c0d1e2b4a56"
ignore: ["/Users/me/scratch"]
merges: {"path:0011223344556677": "git:3f2a9c0d1e2b4a56"}
```

**`config.toml`**: keys exactly as `Config` (§3.6). Sections are `[general]`, `[currency]` (`display`, and `usd_rate` as a string), `[hosts.<host>]` and `[sinks.bigquery]`.

**`install.json`**: `{"version":1,"files":[{"path":str,"backup":str,"existed":bool,"post_sha256":str,"entries":[obj]}],"scheduler":{"kind":"launchd|systemd|cron","path":str}}`.

**`state/snapshot.json`**: `{"generated_at":iso,"timezone":str,"projects":{pid:{"display_name":str,"today":{"total_usd":str,"unpriced_calls":int,"by_host":{host:str}},"month":{…}}},"sessions":[{"host":str,"session_id":str,"text":str}]}`. `text` is a rendered summary without labels.

## 6. Store views (DuckDB `sql/duckdb/views.sql`; BigQuery `sql/bigquery/views.sql` has identical names and columns)

Report, summary, `doctor` and the sink read **only** these views. The reference tables listed in §3.11 are not considered views. `cost_usd` is `DECIMAL(38,9)`, or `BIGNUMERIC` rounded to 9 places in BigQuery. All `*_cost_usd` aggregates are `SUM` over non-NULL values, always returned together with `unpriced_calls`.

| View | Grain | Columns |
| :--- | :--- | :--- |
| `v_calls` | call | `call_id, host, project_id, session_id, task_id, agent_run_id, ts, local_date, local_month, model, model_label, model_effective, model_inferred, priced_model, estimated, unpriced, tokens_unknown, input_tokens, output_tokens, thinking_tokens, cache_write_5m_tokens, cache_write_1h_tokens, cache_read_tokens, prompt_tokens, latency_ms, is_error, cost_usd` |
| `v_daily_project_cost` | (local_date, project_id, host, priced_model) | `local_date, local_month, project_id, display_name, client, host, priced_model, calls, input_tokens, output_tokens, cache_write_tokens, cache_read_tokens, cost_usd, unpriced_calls, estimated_calls, inferred_calls, error_calls` |
| `v_sessions` | session | `session_id, host, project_id, display_name, started_at, ended_at, local_date, wall_clock_ms, active_ms, tasks, calls, cost_usd, unpriced_calls, cache_hit_ratio, task_p50_ms, task_p95_ms, status` |
| `v_tasks` | task | `task_id, session_id, host, project_id, display_name, client, seq_in_session, started_at, ended_at, local_date, wall_clock_ms, active_ms, latency_ms, duration_source, status, agent_runs, max_spawn_depth, parallelism, critical_path_ms, critical_path, retries, retry_summary, calls, input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, cost_usd, unpriced_calls, estimated_calls, inferred_calls, work_item_tag, tool_calls, files_touched, test_runs, test_failures` |
| `v_agent_runs` | agent run | `agent_run_id, task_id, session_id, host, project_id, parent_agent_run_id, agent_type, spawn_depth, started_at, ended_at, active_ms, status, errors, files_touched, test_runs, test_failures, tools_untracked, calls, cost_usd, unpriced_calls, tool_calls` |
| `v_agent_type_cost` | (task_id, agent_type) | `task_id, agent_type, runs, calls, cost_usd, unpriced_calls, active_ms, tool_calls, files_touched, test_runs, test_failures, cost_share` |
| `v_tool_counts` | (agent_run_id, tool_name) | `agent_run_id, task_id, tool_name, calls, errors` |
| `v_task_latency` | (local_month, project_id, host) | `local_month, project_id, host, tasks, p50_ms, p95_ms, p99_ms` (`quantile_cont` / `PERCENTILE_CONT` over `v_tasks.latency_ms`, status ≠ in_progress) |
| `v_dev_hours` | (project_id, local_date) | `project_id, local_date, local_month, hours, source` (`manual` day > `manual` month pro-rata is **not** applied: a month override replaces the month total; day override replaces that day) |
| `v_client_month` | (local_month, client, project_id) | `local_month, client, project_id, display_name, billing_model, rate_currency, cost_usd, unpriced_calls, dev_hours, billable_value, billable_usd, ai_cost_ratio` (`ai_cost_ratio` NULL when no client/rate; fixed = cumulative cost ÷ fixed_price) |
| `v_unpriced_models` | (host, model_effective) | `host, model_effective, calls, first_ts, last_ts` |
| `v_untracked` | host | `host, reason, conversations, observed_from, observed_to` |
| `v_health` | host | `host, last_ingested_at, units, unknown_formats, diagnostics_7d, earliest_call_ts` |

Currency: `billable_usd = billable_value / usd_rate` when `rate_currency = settings.display_currency` and `usd_rate` is set. When the rate currency is `USD` it equals `billable_value`, and otherwise it is NULL. This view does no other conversion.

## 7. Outbox NDJSON and BigQuery tables

- **File**: `~/.agent-meter/outbox/<table>/<batch_id>.ndjson`, where `batch_id = YYYYMMDDTHHMMSSZ-<8 hex>`. Encoding is UTF-8 with one JSON object per line, terminated by `\n` and with no BOM.
- **Row**: keys = the BigQuery column names, which equal the DuckDB table columns minus `row_hash` and `owner_rank`, plus `_uploaded_at`.
- **Value encoding**:

| Type | Encoding |
| :--- | :--- |
| `TIMESTAMP` | `"2026-10-16T18:42:07.123456Z"` (UTC, microseconds) |
| `DATE` | `"2026-10-16"` |
| `DECIMAL`/`NUMERIC` | JSON string, e.g. `"0.200000"` |
| `INT64` | JSON number |
| `BOOL` | `true`/`false` |
| `NULL` | `null` |

- **Anonymisation**: when enabled, `project_id`, `display_name`, `client`, `remote_url` and work-item `tag` (`task_tags`, `tag_history`) are replaced by `Anonymizer(value)` in **every** file, including `projects` and `dev_hours_*`.
- **Load and dedup**: fact tables load `WRITE_APPEND` into `raw_<table>`. Reference tables load `WRITE_TRUNCATE` into `<table>` with the same name. Per fact table, a dedup view with the plain name is defined as:
  ```sql
  CREATE OR REPLACE VIEW `<p>.<d>.llm_calls` AS
  SELECT * EXCEPT(_uploaded_at) FROM `<p>.<d>.raw_llm_calls`
  WHERE TRUE QUALIFY ROW_NUMBER() OVER (PARTITION BY call_id ORDER BY ingest_seq DESC) = 1;
  ```
  The `v_*` views (§6) are written against those plain names on both engines. Dialect differences are limited to `DATE(ts, tz)` versus `CAST(timezone(tz, ts) AS DATE)`, `FORMAT_DATE`/`strftime`, and `BIGNUMERIC`/`DECIMAL`.
- **Raw fact DDL** (`sql/bigquery/tables.sql`, `CREATE TABLE IF NOT EXISTS`):

| Table | Partition (`TIMESTAMP_TRUNC(…, MONTH)`) | Cluster |
| :--- | :--- | :--- |
| `raw_llm_calls` | `ts` | `project_id, host` |
| `raw_tasks` | `started_at` | `project_id, host` |
| `raw_agent_runs` | `started_at` | `project_id, host` |
| `raw_sessions` | `started_at` | `project_id, host` |
| `raw_tool_uses` | none | `project_id, host` |

Column types map as follows:

| DuckDB | BigQuery |
| :--- | :--- |
| `TEXT` | `STRING` |
| `BIGINT` / `INTEGER` / `SMALLINT` | `INT64` |
| `BOOLEAN` | `BOOL` |
| `TIMESTAMPTZ` | `TIMESTAMP` |
| `DATE` | `DATE` |
| `DECIMAL(12,6)` / `DECIMAL(18,4)` / `DECIMAL(8,2)` | `NUMERIC` |

There is no `require_partition_filter` (ADR §3.11).
