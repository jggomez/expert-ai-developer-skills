-- agent-meter DuckDB schema v1 (contracts.md §4). Idempotent: every statement is IF NOT EXISTS.
-- No table holds a cost column (cost exists only in v_calls), clear-text paths, prompts or tool content.

CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
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
  unit_hash TEXT NOT NULL, file_kind TEXT NOT NULL, error_class TEXT, count INTEGER NOT NULL);
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
CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);

-- user-owned facts
CREATE TABLE IF NOT EXISTS dev_hours_manual (project_id TEXT NOT NULL, period TEXT NOT NULL, hours DECIMAL(8,2) NOT NULL,
  set_at TIMESTAMPTZ NOT NULL, PRIMARY KEY (project_id, period));
CREATE TABLE IF NOT EXISTS dev_hours_derived (project_id TEXT NOT NULL, local_date DATE NOT NULL, hours DECIMAL(8,2) NOT NULL,
  PRIMARY KEY (project_id, local_date));
CREATE TABLE IF NOT EXISTS tag_history (project_id TEXT NOT NULL, tag TEXT, from_ts TIMESTAMPTZ NOT NULL, to_ts TIMESTAMPTZ,
  PRIMARY KEY (project_id, from_ts));
CREATE TABLE IF NOT EXISTS task_tags (task_id TEXT PRIMARY KEY, tag TEXT NOT NULL, set_at TIMESTAMPTZ NOT NULL);
