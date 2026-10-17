-- agent-meter BigQuery views, schema v1 (ADR §3.8/§3.11, contracts §6/§7).
-- Rendered by sinks/bigquery.py with ${project} and ${dataset}; one statement per ';'.
-- View names and columns mirror the DuckDB views (sql/duckdb/views.sql). Dialect
-- differences are limited to DATE(ts, tz), FORMAT_DATE, BIGNUMERIC and window-only
-- PERCENTILE_CONT. Cost is computed here at query time from the uploaded pricing tables.

-- 1. Dedup views: latest ingest_seq per natural key over the append-only raw tables.

CREATE OR REPLACE VIEW `${project}.${dataset}.llm_calls` AS
SELECT * EXCEPT(_uploaded_at) FROM `${project}.${dataset}.raw_llm_calls`
WHERE TRUE
QUALIFY ROW_NUMBER() OVER (PARTITION BY call_id ORDER BY ingest_seq DESC, _uploaded_at DESC) = 1;

CREATE OR REPLACE VIEW `${project}.${dataset}.tasks` AS
SELECT * EXCEPT(_uploaded_at) FROM `${project}.${dataset}.raw_tasks`
WHERE TRUE
QUALIFY ROW_NUMBER() OVER (PARTITION BY task_id ORDER BY ingest_seq DESC, _uploaded_at DESC) = 1;

CREATE OR REPLACE VIEW `${project}.${dataset}.agent_runs` AS
SELECT * EXCEPT(_uploaded_at) FROM `${project}.${dataset}.raw_agent_runs`
WHERE TRUE
QUALIFY ROW_NUMBER() OVER (PARTITION BY agent_run_id ORDER BY ingest_seq DESC, _uploaded_at DESC) = 1;

CREATE OR REPLACE VIEW `${project}.${dataset}.tool_uses` AS
SELECT * EXCEPT(_uploaded_at) FROM `${project}.${dataset}.raw_tool_uses`
WHERE TRUE
QUALIFY ROW_NUMBER() OVER (PARTITION BY agent_run_id, tool_name ORDER BY ingest_seq DESC, _uploaded_at DESC) = 1;

CREATE OR REPLACE VIEW `${project}.${dataset}.sessions` AS
SELECT * EXCEPT(_uploaded_at) FROM `${project}.${dataset}.raw_sessions`
WHERE TRUE
QUALIFY ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY ingest_seq DESC, _uploaded_at DESC) = 1;

-- 2. v_calls: price resolution identical to pricing.resolve_price() / cost_usd() (contracts §3.4).

CREATE OR REPLACE VIEW `${project}.${dataset}.v_calls` AS
WITH cfg AS (
  SELECT COALESCE(MAX(IF(key = 'timezone', value, NULL)), 'UTC') AS tz
  FROM `${project}.${dataset}.settings`
),
priced_models AS (
  SELECT DISTINCT model FROM `${project}.${dataset}.pricing`
),
effective AS (
  SELECT
    c.*,
    DATE(c.ts, cfg.tz) AS local_date,
    COALESCE(NULLIF(c.model, ''), NULLIF(hd.default_model, '')) AS model_effective,
    (NULLIF(c.model, '') IS NULL AND NULLIF(hd.default_model, '') IS NOT NULL) AS model_inferred,
    IFNULL(c.speed, '') = 'fast' AS is_fast
  FROM `${project}.${dataset}.llm_calls` AS c
  CROSS JOIN cfg
  LEFT JOIN `${project}.${dataset}.host_defaults` AS hd ON hd.host = c.host
),
aliased AS (
  SELECT
    e.*,
    COALESCE(a.model, e.model_effective) AS base_model,
    IFNULL(a.estimated, FALSE) AS alias_estimated
  FROM effective AS e
  LEFT JOIN `${project}.${dataset}.pricing_aliases` AS a ON a.alias = e.model_effective
),
variant AS (
  SELECT
    x.*,
    IF(x.is_fast AND f.model IS NOT NULL, f.model, x.base_model) AS lookup_model,
    x.alias_estimated OR (x.is_fast AND x.base_model IS NOT NULL AND f.model IS NULL) AS is_estimated,
    IFNULL(x.input_tokens, 0) + IFNULL(x.cache_read_tokens, 0)
      + IFNULL(x.cache_write_5m_tokens, 0) + IFNULL(x.cache_write_1h_tokens, 0) AS tier_tokens
  FROM aliased AS x
  LEFT JOIN priced_models AS f ON x.is_fast AND f.model = CONCAT(x.base_model, ':fast')
),
priced AS (
  SELECT
    v.*,
    p.model AS price_model,
    p.input_per_mtok AS input_price,
    p.output_per_mtok AS output_price,
    COALESCE(p.cache_write_5m_per_mtok, p.input_per_mtok) AS cache_write_5m_price,
    COALESCE(p.cache_write_1h_per_mtok, p.input_per_mtok) AS cache_write_1h_price,
    p.cache_read_per_mtok AS cache_read_price
  FROM variant AS v
  LEFT JOIN `${project}.${dataset}.pricing` AS p
    ON p.model = v.lookup_model
    AND p.effective_from <= v.local_date
    AND p.min_prompt_tokens <= v.tier_tokens
  WHERE TRUE
  QUALIFY ROW_NUMBER() OVER (
    PARTITION BY v.call_id ORDER BY p.effective_from DESC, p.min_prompt_tokens DESC
  ) = 1
),
flagged AS (
  SELECT
    *,
    (input_tokens IS NULL OR output_tokens IS NULL OR cache_write_5m_tokens IS NULL
      OR cache_write_1h_tokens IS NULL OR cache_read_tokens IS NULL) AS is_tokens_unknown
  FROM priced
),
costed AS (
  SELECT
    *,
    IF(
      price_model IS NULL OR is_tokens_unknown,
      NULL,
      ROUND(
        (CAST(input_tokens AS BIGNUMERIC) * input_price
          + CAST(output_tokens AS BIGNUMERIC) * output_price
          + CAST(cache_write_5m_tokens AS BIGNUMERIC) * cache_write_5m_price
          + CAST(cache_write_1h_tokens AS BIGNUMERIC) * cache_write_1h_price
          + CAST(cache_read_tokens AS BIGNUMERIC) * cache_read_price) / 1000000,
        9)
    ) AS call_cost_usd
  FROM flagged
)
SELECT
  call_id, host, project_id, session_id, task_id, agent_run_id, ts, local_date,
  FORMAT_DATE('%Y-%m', local_date) AS local_month,
  model, model_label, model_effective, model_inferred,
  price_model AS priced_model,
  is_estimated AS estimated,
  call_cost_usd IS NULL AS unpriced,
  is_tokens_unknown AS tokens_unknown,
  input_tokens, output_tokens, thinking_tokens,
  cache_write_5m_tokens, cache_write_1h_tokens, cache_read_tokens,
  tier_tokens AS prompt_tokens,
  latency_ms, is_error,
  call_cost_usd AS cost_usd
FROM costed;

-- 3. v_daily_project_cost (reconciliation grain for BQ-08).

CREATE OR REPLACE VIEW `${project}.${dataset}.v_daily_project_cost` AS
SELECT
  c.local_date,
  c.local_month,
  c.project_id,
  COALESCE(p.display_name, c.project_id) AS display_name,
  p.client,
  c.host,
  c.priced_model,
  COUNT(*) AS calls,
  SUM(c.input_tokens) AS input_tokens,
  SUM(c.output_tokens) AS output_tokens,
  SUM(IFNULL(c.cache_write_5m_tokens, 0) + IFNULL(c.cache_write_1h_tokens, 0)) AS cache_write_tokens,
  SUM(c.cache_read_tokens) AS cache_read_tokens,
  SUM(c.cost_usd) AS cost_usd,
  COUNTIF(c.unpriced) AS unpriced_calls,
  COUNTIF(c.estimated) AS estimated_calls,
  COUNTIF(c.model_inferred) AS inferred_calls,
  COUNTIF(c.is_error) AS error_calls
FROM `${project}.${dataset}.v_calls` AS c
LEFT JOIN `${project}.${dataset}.projects` AS p ON p.project_id = c.project_id
GROUP BY 1, 2, 3, 4, 5, 6, 7;

-- 4. v_sessions

CREATE OR REPLACE VIEW `${project}.${dataset}.v_sessions` AS
WITH cfg AS (
  SELECT COALESCE(MAX(IF(key = 'timezone', value, NULL)), 'UTC') AS tz
  FROM `${project}.${dataset}.settings`
),
task_stats AS (
  SELECT session_id, COUNT(*) AS tasks, SUM(active_ms) AS active_ms
  FROM `${project}.${dataset}.tasks`
  GROUP BY session_id
),
task_pct AS (
  SELECT DISTINCT
    session_id,
    PERCENTILE_CONT(COALESCE(reported_ms, wall_clock_ms), 0.5) OVER (PARTITION BY session_id) AS task_p50_ms,
    PERCENTILE_CONT(COALESCE(reported_ms, wall_clock_ms), 0.95) OVER (PARTITION BY session_id) AS task_p95_ms
  FROM `${project}.${dataset}.tasks`
),
call_stats AS (
  SELECT
    session_id,
    COUNT(*) AS calls,
    SUM(cost_usd) AS cost_usd,
    COUNTIF(unpriced) AS unpriced_calls,
    ROUND(SAFE_DIVIDE(CAST(SUM(IFNULL(cache_read_tokens, 0)) AS NUMERIC),
                      SUM(IFNULL(input_tokens, 0) + IFNULL(cache_read_tokens, 0)
                          + IFNULL(cache_write_5m_tokens, 0) + IFNULL(cache_write_1h_tokens, 0))),
          4) AS cache_hit_ratio
  FROM `${project}.${dataset}.v_calls`
  GROUP BY session_id
)
SELECT
  s.session_id,
  s.host,
  s.project_id,
  COALESCE(p.display_name, s.project_id) AS display_name,
  s.started_at,
  s.ended_at,
  DATE(s.started_at, cfg.tz) AS local_date,
  TIMESTAMP_DIFF(s.ended_at, s.started_at, MILLISECOND) AS wall_clock_ms,
  IFNULL(t.active_ms, 0) AS active_ms,
  IFNULL(t.tasks, 0) AS tasks,
  IFNULL(c.calls, 0) AS calls,
  c.cost_usd,
  IFNULL(c.unpriced_calls, 0) AS unpriced_calls,
  c.cache_hit_ratio,
  q.task_p50_ms,
  q.task_p95_ms,
  s.status
FROM `${project}.${dataset}.sessions` AS s
CROSS JOIN cfg
LEFT JOIN `${project}.${dataset}.projects` AS p ON p.project_id = s.project_id
LEFT JOIN task_stats AS t ON t.session_id = s.session_id
LEFT JOIN task_pct AS q ON q.session_id = s.session_id
LEFT JOIN call_stats AS c ON c.session_id = s.session_id;

-- 5. v_tasks

CREATE OR REPLACE VIEW `${project}.${dataset}.v_tasks` AS
WITH cfg AS (
  SELECT COALESCE(MAX(IF(key = 'timezone', value, NULL)), 'UTC') AS tz
  FROM `${project}.${dataset}.settings`
),
run_stats AS (
  SELECT
    task_id,
    SUM(active_ms) AS run_active_ms,
    SUM(files_touched) AS files_touched,
    SUM(test_runs) AS test_runs,
    SUM(test_failures) AS test_failures
  FROM `${project}.${dataset}.agent_runs`
  GROUP BY task_id
),
tool_stats AS (
  SELECT r.task_id, SUM(u.calls) AS tool_calls
  FROM `${project}.${dataset}.tool_uses` AS u
  JOIN `${project}.${dataset}.agent_runs` AS r ON r.agent_run_id = u.agent_run_id
  GROUP BY r.task_id
),
call_stats AS (
  SELECT
    task_id,
    COUNT(*) AS calls,
    SUM(input_tokens) AS input_tokens,
    SUM(output_tokens) AS output_tokens,
    SUM(cache_read_tokens) AS cache_read_tokens,
    SUM(IFNULL(cache_write_5m_tokens, 0) + IFNULL(cache_write_1h_tokens, 0)) AS cache_write_tokens,
    SUM(cost_usd) AS cost_usd,
    COUNTIF(unpriced) AS unpriced_calls,
    COUNTIF(estimated) AS estimated_calls,
    COUNTIF(model_inferred) AS inferred_calls
  FROM `${project}.${dataset}.v_calls`
  GROUP BY task_id
),
tagged AS (
  -- An explicit task tag wins; otherwise the project tag active when the task started.
  SELECT t.task_id, COALESCE(tt.tag, th.tag) AS work_item_tag
  FROM `${project}.${dataset}.tasks` AS t
  LEFT JOIN `${project}.${dataset}.task_tags` AS tt ON tt.task_id = t.task_id
  LEFT JOIN `${project}.${dataset}.tag_history` AS th
    ON th.project_id = t.project_id
    AND t.started_at >= th.from_ts
    AND (th.to_ts IS NULL OR t.started_at < th.to_ts)
  WHERE TRUE
  QUALIFY ROW_NUMBER() OVER (PARTITION BY t.task_id ORDER BY th.from_ts DESC NULLS LAST) = 1
)
SELECT
  t.task_id,
  t.session_id,
  t.host,
  t.project_id,
  COALESCE(p.display_name, t.project_id) AS display_name,
  p.client,
  t.seq_in_session,
  t.started_at,
  t.ended_at,
  DATE(t.started_at, cfg.tz) AS local_date,
  t.wall_clock_ms,
  t.active_ms,
  COALESCE(t.reported_ms, t.wall_clock_ms) AS latency_ms,
  t.duration_source,
  t.status,
  t.agent_runs,
  t.max_spawn_depth,
  IF(t.agent_runs > 1 AND t.active_ms > 0,
     ROUND(CAST(r.run_active_ms AS NUMERIC) / t.active_ms, 2), NULL) AS parallelism,
  t.critical_path_ms,
  t.critical_path,
  t.retries,
  t.retry_summary,
  IFNULL(c.calls, 0) AS calls,
  c.input_tokens,
  c.output_tokens,
  c.cache_read_tokens,
  c.cache_write_tokens,
  c.cost_usd,
  IFNULL(c.unpriced_calls, 0) AS unpriced_calls,
  IFNULL(c.estimated_calls, 0) AS estimated_calls,
  IFNULL(c.inferred_calls, 0) AS inferred_calls,
  g.work_item_tag,
  IFNULL(u.tool_calls, 0) AS tool_calls,
  IFNULL(r.files_touched, 0) AS files_touched,
  IFNULL(r.test_runs, 0) AS test_runs,
  IFNULL(r.test_failures, 0) AS test_failures
FROM `${project}.${dataset}.tasks` AS t
CROSS JOIN cfg
LEFT JOIN `${project}.${dataset}.projects` AS p ON p.project_id = t.project_id
LEFT JOIN run_stats AS r ON r.task_id = t.task_id
LEFT JOIN tool_stats AS u ON u.task_id = t.task_id
LEFT JOIN call_stats AS c ON c.task_id = t.task_id
LEFT JOIN tagged AS g ON g.task_id = t.task_id;

-- 6. v_agent_runs

CREATE OR REPLACE VIEW `${project}.${dataset}.v_agent_runs` AS
WITH call_stats AS (
  SELECT agent_run_id, COUNT(*) AS calls, SUM(cost_usd) AS cost_usd,
         COUNTIF(unpriced) AS unpriced_calls
  FROM `${project}.${dataset}.v_calls`
  GROUP BY agent_run_id
),
tool_stats AS (
  SELECT agent_run_id, SUM(calls) AS tool_calls
  FROM `${project}.${dataset}.tool_uses`
  GROUP BY agent_run_id
)
SELECT
  r.agent_run_id,
  r.task_id,
  r.session_id,
  r.host,
  r.project_id,
  r.parent_agent_run_id,
  r.agent_type,
  r.spawn_depth,
  r.started_at,
  r.ended_at,
  r.active_ms,
  r.status,
  r.errors,
  r.files_touched,
  r.test_runs,
  r.test_failures,
  r.tools_untracked,
  IFNULL(c.calls, 0) AS calls,
  c.cost_usd,
  IFNULL(c.unpriced_calls, 0) AS unpriced_calls,
  IFNULL(u.tool_calls, 0) AS tool_calls
FROM `${project}.${dataset}.agent_runs` AS r
LEFT JOIN call_stats AS c ON c.agent_run_id = r.agent_run_id
LEFT JOIN tool_stats AS u ON u.agent_run_id = r.agent_run_id;

-- 7. v_agent_type_cost

CREATE OR REPLACE VIEW `${project}.${dataset}.v_agent_type_cost` AS
WITH by_type AS (
  SELECT
    task_id,
    agent_type,
    COUNT(*) AS runs,
    SUM(calls) AS calls,
    SUM(cost_usd) AS cost_usd,
    SUM(unpriced_calls) AS unpriced_calls,
    SUM(active_ms) AS active_ms,
    SUM(tool_calls) AS tool_calls,
    SUM(files_touched) AS files_touched,
    SUM(test_runs) AS test_runs,
    SUM(test_failures) AS test_failures
  FROM `${project}.${dataset}.v_agent_runs`
  GROUP BY task_id, agent_type
)
SELECT
  task_id, agent_type, runs, calls, cost_usd, unpriced_calls, active_ms, tool_calls,
  files_touched, test_runs, test_failures,
  IF(cost_usd IS NOT NULL AND SUM(cost_usd) OVER (PARTITION BY task_id) > 0,
     ROUND(cost_usd / SUM(cost_usd) OVER (PARTITION BY task_id), 4), NULL) AS cost_share
FROM by_type;

-- 8. v_tool_counts

CREATE OR REPLACE VIEW `${project}.${dataset}.v_tool_counts` AS
SELECT u.agent_run_id, r.task_id, u.tool_name, u.calls, u.errors
FROM `${project}.${dataset}.tool_uses` AS u
LEFT JOIN `${project}.${dataset}.agent_runs` AS r ON r.agent_run_id = u.agent_run_id;

-- 9. v_task_latency (exact percentiles over finished tasks)

CREATE OR REPLACE VIEW `${project}.${dataset}.v_task_latency` AS
WITH finished AS (
  SELECT FORMAT_DATE('%Y-%m', local_date) AS local_month, project_id, host, latency_ms
  FROM `${project}.${dataset}.v_tasks`
  WHERE status != 'in_progress'
)
SELECT DISTINCT
  local_month,
  project_id,
  host,
  COUNT(*) OVER (PARTITION BY local_month, project_id, host) AS tasks,
  PERCENTILE_CONT(latency_ms, 0.5) OVER (PARTITION BY local_month, project_id, host) AS p50_ms,
  PERCENTILE_CONT(latency_ms, 0.95) OVER (PARTITION BY local_month, project_id, host) AS p95_ms,
  PERCENTILE_CONT(latency_ms, 0.99) OVER (PARTITION BY local_month, project_id, host) AS p99_ms
FROM finished;

-- 10. v_dev_hours: a manual day replaces that day; a manual month replaces the month total.

CREATE OR REPLACE VIEW `${project}.${dataset}.v_dev_hours` AS
WITH manual_month AS (
  SELECT project_id, period AS local_month, hours
  FROM `${project}.${dataset}.dev_hours_manual`
  WHERE LENGTH(period) = 7
),
manual_day AS (
  SELECT project_id, SAFE.PARSE_DATE('%Y-%m-%d', period) AS local_date, hours
  FROM `${project}.${dataset}.dev_hours_manual`
  WHERE LENGTH(period) = 10
),
daily AS (
  SELECT
    COALESCE(m.project_id, d.project_id) AS project_id,
    COALESCE(m.local_date, d.local_date) AS local_date,
    IF(m.project_id IS NOT NULL, m.hours, d.hours) AS hours,
    IF(m.project_id IS NOT NULL, 'manual', 'derived') AS source
  FROM `${project}.${dataset}.dev_hours_derived` AS d
  FULL OUTER JOIN (SELECT * FROM manual_day WHERE local_date IS NOT NULL) AS m
    ON m.project_id = d.project_id AND m.local_date = d.local_date
)
SELECT
  daily.project_id,
  daily.local_date,
  FORMAT_DATE('%Y-%m', daily.local_date) AS local_month,
  daily.hours,
  daily.source
FROM daily
LEFT JOIN manual_month AS mm
  ON mm.project_id = daily.project_id
  AND mm.local_month = FORMAT_DATE('%Y-%m', daily.local_date)
WHERE mm.project_id IS NULL
UNION ALL
SELECT
  project_id,
  SAFE.PARSE_DATE('%Y-%m-%d', CONCAT(local_month, '-01')) AS local_date,
  local_month,
  hours,
  'manual' AS source
FROM manual_month;

-- 11. v_client_month

CREATE OR REPLACE VIEW `${project}.${dataset}.v_client_month` AS
WITH cfg AS (
  SELECT
    MAX(IF(key = 'display_currency', value, NULL)) AS display_currency,
    SAFE_CAST(MAX(IF(key = 'usd_rate', value, NULL)) AS NUMERIC) AS usd_rate
  FROM `${project}.${dataset}.settings`
),
cost AS (
  SELECT local_month, project_id, SUM(cost_usd) AS cost_usd, SUM(unpriced_calls) AS unpriced_calls
  FROM `${project}.${dataset}.v_daily_project_cost`
  GROUP BY local_month, project_id
),
hours AS (
  SELECT local_month, project_id, SUM(hours) AS dev_hours
  FROM `${project}.${dataset}.v_dev_hours`
  GROUP BY local_month, project_id
),
months AS (
  SELECT local_month, project_id FROM cost
  UNION DISTINCT
  SELECT local_month, project_id FROM hours
),
valued AS (
  SELECT
    m.local_month,
    p.client,
    m.project_id,
    COALESCE(p.display_name, m.project_id) AS display_name,
    p.billing_model,
    p.rate_currency,
    c.cost_usd,
    IFNULL(c.unpriced_calls, 0) AS unpriced_calls,
    IFNULL(h.dev_hours, 0) AS dev_hours,
    CASE
      WHEN p.billing_model = 'hourly' AND p.hourly_rate IS NOT NULL
        THEN p.hourly_rate * IFNULL(h.dev_hours, 0)
      WHEN p.billing_model = 'fixed' THEN p.fixed_price
    END AS billable_value,
    SUM(c.cost_usd) OVER (
      PARTITION BY m.project_id ORDER BY m.local_month
      ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
    ) AS cumulative_cost_usd
  FROM months AS m
  LEFT JOIN cost AS c ON c.local_month = m.local_month AND c.project_id = m.project_id
  LEFT JOIN hours AS h ON h.local_month = m.local_month AND h.project_id = m.project_id
  LEFT JOIN `${project}.${dataset}.projects` AS p ON p.project_id = m.project_id
),
converted AS (
  SELECT
    v.*,
    CASE
      WHEN v.rate_currency = 'USD' THEN v.billable_value
      WHEN v.rate_currency = cfg.display_currency AND cfg.usd_rate IS NOT NULL
        THEN ROUND(SAFE_DIVIDE(v.billable_value, cfg.usd_rate), 4)
    END AS billable_usd
  FROM valued AS v
  CROSS JOIN cfg
)
SELECT
  local_month, client, project_id, display_name, billing_model, rate_currency, cost_usd,
  unpriced_calls, dev_hours, billable_value, billable_usd,
  CASE
    WHEN client IS NULL OR billable_usd IS NULL OR billable_usd = 0 THEN NULL
    WHEN billing_model = 'hourly' THEN ROUND(cost_usd / billable_usd, 4)
    WHEN billing_model = 'fixed' THEN ROUND(cumulative_cost_usd / billable_usd, 4)
  END AS ai_cost_ratio
FROM converted;

-- 12. v_unpriced_models

CREATE OR REPLACE VIEW `${project}.${dataset}.v_unpriced_models` AS
SELECT host, model_effective, COUNT(*) AS calls, MIN(ts) AS first_ts, MAX(ts) AS last_ts
FROM `${project}.${dataset}.v_calls`
WHERE priced_model IS NULL
GROUP BY host, model_effective;

-- 13. v_untracked

CREATE OR REPLACE VIEW `${project}.${dataset}.v_untracked` AS
SELECT host, reason, COUNT(*) AS conversations, MIN(observed_from) AS observed_from,
       MAX(observed_to) AS observed_to
FROM `${project}.${dataset}.untracked`
GROUP BY host, reason;

-- 14. v_health (cloud edition): ingest diagnostics stay local, so unknown_formats and
--     diagnostics_7d are NULL and last_ingested_at is the latest upload time.

CREATE OR REPLACE VIEW `${project}.${dataset}.v_health` AS
WITH hosts AS (
  SELECT host FROM `${project}.${dataset}.sessions`
  UNION DISTINCT
  SELECT host FROM `${project}.${dataset}.llm_calls`
),
uploads AS (
  SELECT host, MAX(_uploaded_at) AS last_ingested_at
  FROM (
    SELECT host, _uploaded_at FROM `${project}.${dataset}.raw_sessions`
    UNION ALL
    SELECT host, _uploaded_at FROM `${project}.${dataset}.raw_llm_calls`
  )
  GROUP BY host
),
units AS (
  SELECT host, COUNT(*) AS units FROM `${project}.${dataset}.sessions` GROUP BY host
),
earliest AS (
  SELECT host, MIN(ts) AS earliest_call_ts FROM `${project}.${dataset}.llm_calls` GROUP BY host
)
SELECT
  h.host,
  u.last_ingested_at,
  IFNULL(n.units, 0) AS units,
  CAST(NULL AS INT64) AS unknown_formats,
  CAST(NULL AS INT64) AS diagnostics_7d,
  e.earliest_call_ts
FROM hosts AS h
LEFT JOIN uploads AS u ON u.host = h.host
LEFT JOIN units AS n ON n.host = h.host
LEFT JOIN earliest AS e ON e.host = h.host;
