-- agent-meter BigQuery tables, schema v1 (ADR §3.11, contracts §7).
-- Rendered by sinks/bigquery.py with ${project} and ${dataset}; one statement per ';'.
-- Columns mirror sinks/outbox.py TABLE_SCHEMAS (a unit test keeps them in lockstep).
-- Every column is NULLABLE: NOT NULL is enforced by the local store (source of truth), and
-- matching modes keep WRITE_APPEND loads from failing on a mode mismatch.
-- Fact tables are append-only (load jobs, WRITE_APPEND) and deduplicated by views.sql.
-- Partitions are monthly and no partition filter is required, so dedup views and
-- Looker Studio work on full history; cost is guarded by dry-run byte checks (BQ-09).

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.raw_llm_calls` (
  call_id STRING,
  host STRING,
  project_id STRING,
  session_id STRING,
  task_id STRING,
  agent_run_id STRING,
  ts TIMESTAMP,
  model STRING,
  model_label STRING,
  input_tokens INT64,
  output_tokens INT64,
  thinking_tokens INT64,
  cache_write_5m_tokens INT64,
  cache_write_1h_tokens INT64,
  cache_read_tokens INT64,
  latency_ms INT64,
  speed STRING,
  inference_geo STRING,
  is_error BOOL,
  source_format STRING,
  ingest_seq INT64,
  schema_version INT64,
  _uploaded_at TIMESTAMP
)
PARTITION BY TIMESTAMP_TRUNC(ts, MONTH)
CLUSTER BY project_id, host;

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.raw_tasks` (
  task_id STRING,
  session_id STRING,
  host STRING,
  project_id STRING,
  seq_in_session INT64,
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  wall_clock_ms INT64,
  active_ms INT64,
  reported_ms INT64,
  duration_source STRING,
  status STRING,
  agent_runs INT64,
  max_spawn_depth INT64,
  critical_path_ms INT64,
  critical_path STRING,
  retries INT64,
  retry_summary STRING,
  ingest_seq INT64,
  schema_version INT64,
  _uploaded_at TIMESTAMP
)
PARTITION BY TIMESTAMP_TRUNC(started_at, MONTH)
CLUSTER BY project_id, host;

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.raw_agent_runs` (
  agent_run_id STRING,
  task_id STRING,
  session_id STRING,
  host STRING,
  project_id STRING,
  parent_agent_run_id STRING,
  agent_type STRING,
  description_hash STRING,
  spawn_depth INT64,
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  active_ms INT64,
  status STRING,
  errors INT64,
  files_touched INT64,
  test_runs INT64,
  test_failures INT64,
  tools_untracked BOOL,
  ingest_seq INT64,
  schema_version INT64,
  _uploaded_at TIMESTAMP
)
PARTITION BY TIMESTAMP_TRUNC(started_at, MONTH)
CLUSTER BY project_id, host;

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.raw_sessions` (
  session_id STRING,
  host STRING,
  project_id STRING,
  started_at TIMESTAMP,
  ended_at TIMESTAMP,
  status STRING,
  host_version STRING,
  ingest_seq INT64,
  schema_version INT64,
  _uploaded_at TIMESTAMP
)
PARTITION BY TIMESTAMP_TRUNC(started_at, MONTH)
CLUSTER BY project_id, host;

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.raw_tool_uses` (
  agent_run_id STRING,
  tool_name STRING,
  calls INT64,
  errors INT64,
  project_id STRING,
  host STRING,
  ingest_seq INT64,
  _uploaded_at TIMESTAMP
)
CLUSTER BY project_id, host;

-- Reference tables: same names as DuckDB, re-loaded with WRITE_TRUNCATE on every sync.

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.projects` (
  project_id STRING,
  kind STRING,
  display_name STRING,
  remote_url STRING,
  client STRING,
  billing_model STRING,
  hourly_rate NUMERIC,
  fixed_price NUMERIC,
  rate_currency STRING,
  _uploaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.pricing` (
  model STRING,
  effective_from DATE,
  min_prompt_tokens INT64,
  input_per_mtok NUMERIC,
  output_per_mtok NUMERIC,
  cache_write_5m_per_mtok NUMERIC,
  cache_write_1h_per_mtok NUMERIC,
  cache_read_per_mtok NUMERIC,
  source STRING,
  source_url STRING,
  fetched_at DATE,
  _uploaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.pricing_aliases` (
  alias STRING,
  model STRING,
  estimated BOOL,
  source STRING,
  _uploaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.host_defaults` (
  host STRING,
  default_model STRING,
  _uploaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.dev_hours_manual` (
  project_id STRING,
  period STRING,
  hours NUMERIC,
  set_at TIMESTAMP,
  _uploaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.dev_hours_derived` (
  project_id STRING,
  local_date DATE,
  hours NUMERIC,
  _uploaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.task_tags` (
  task_id STRING,
  tag STRING,
  set_at TIMESTAMP,
  _uploaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.tag_history` (
  project_id STRING,
  tag STRING,
  from_ts TIMESTAMP,
  to_ts TIMESTAMP,
  _uploaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.settings` (
  key STRING,
  value STRING,
  _uploaded_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `${project}.${dataset}.untracked` (
  conversation_id STRING,
  host STRING,
  reason STRING,
  observed_from DATE,
  observed_to DATE,
  ingest_seq INT64,
  _uploaded_at TIMESTAMP
);
