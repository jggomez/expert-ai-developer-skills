-- agent-meter DuckDB views (contracts.md §6). Report, summary, doctor and the sink read ONLY these.
-- Cost is computed here at query time from the pricing reference tables (ADR §3.8): never persisted.
-- cost_usd IS NULL <=> unpriced (I-6); aggregates SUM non-NULL costs and always return unpriced_calls.

-- Exact money division (I-5, compliance finding L-2). DuckDB evaluates DECIMAL / DECIMAL as DOUBLE,
-- so money ratios divide scaled HUGEINTs instead: both operands become integers at 9 decimal places,
-- the quotient is rounded half away from zero to 9 places (BigQuery NUMERIC division semantics) and
-- returned as DECIMAL(38,9). Callers ROUND(..., 4) on top, exactly like ROUND(SAFE_DIVIDE(..), 4) in
-- BigQuery. Division by zero returns NULL (SAFE_DIVIDE parity).
CREATE OR REPLACE MACRO am_money_div(numerator, denominator) AS (
  CASE WHEN CAST(denominator AS DECIMAL(38, 9)) = 0 THEN NULL ELSE
    CAST(
      sign(CAST(CAST(numerator AS DECIMAL(38, 9)) * 1000000000 AS HUGEINT))
      * sign(CAST(CAST(denominator AS DECIMAL(38, 9)) * 1000000000 AS HUGEINT))
      * ((abs(CAST(CAST(numerator AS DECIMAL(38, 9)) * 1000000000 AS HUGEINT)) * 2000000000
          + abs(CAST(CAST(denominator AS DECIMAL(38, 9)) * 1000000000 AS HUGEINT)))
         // (2 * abs(CAST(CAST(denominator AS DECIMAL(38, 9)) * 1000000000 AS HUGEINT))))
      AS DECIMAL(38, 0)
    ) * CAST(0.000000001 AS DECIMAL(10, 9))
  END
);

CREATE OR REPLACE VIEW v_calls AS
WITH tz AS (
  SELECT COALESCE(MAX(CASE WHEN key = 'timezone' THEN value END), 'UTC') AS name FROM settings
),
base AS (
  SELECT
    c.*,
    CAST(timezone(tz.name, c.ts) AS DATE) AS local_date,
    COALESCE(NULLIF(c.model, ''), NULLIF(hd.default_model, '')) AS model_effective,
    (NULLIF(c.model, '') IS NULL AND NULLIF(hd.default_model, '') IS NOT NULL) AS model_inferred,
    (c.input_tokens IS NULL OR c.output_tokens IS NULL OR c.cache_write_5m_tokens IS NULL
      OR c.cache_write_1h_tokens IS NULL OR c.cache_read_tokens IS NULL) AS tokens_unknown,
    CAST(COALESCE(c.input_tokens, 0) + COALESCE(c.cache_read_tokens, 0)
      + COALESCE(c.cache_write_5m_tokens, 0) + COALESCE(c.cache_write_1h_tokens, 0) AS BIGINT) AS prompt_tokens
  FROM llm_calls c
  CROSS JOIN tz
  LEFT JOIN host_defaults hd ON hd.host = c.host
),
aliased AS (
  SELECT b.*, COALESCE(a.model, b.model_effective) AS base_model, COALESCE(a.estimated, FALSE) AS alias_estimated
  FROM base b
  LEFT JOIN pricing_aliases a ON a.alias = b.model_effective
),
variant AS (
  SELECT
    x.*,
    COALESCE(x.speed = 'fast' AND fm.model IS NOT NULL, FALSE) AS use_fast,
    COALESCE(x.speed = 'fast' AND fm.model IS NULL, FALSE) AS fast_fallback
  FROM aliased x
  LEFT JOIN (SELECT DISTINCT model FROM pricing) fm ON fm.model = x.base_model || ':fast'
),
keyed AS (
  SELECT
    v.*,
    CASE WHEN v.use_fast THEN v.base_model || ':fast' ELSE v.base_model END AS lookup_model,
    (v.model_effective IS NOT NULL AND (v.alias_estimated OR v.fast_fallback)) AS estimated
  FROM variant v
),
priced AS (
  SELECT
    k.*,
    p.model AS price_model,
    p.input_per_mtok, p.output_per_mtok, p.cache_write_5m_per_mtok, p.cache_write_1h_per_mtok, p.cache_read_per_mtok
  FROM keyed k
  LEFT JOIN pricing p
    ON p.model = k.lookup_model AND p.effective_from <= k.local_date AND p.min_prompt_tokens <= k.prompt_tokens
  QUALIFY row_number() OVER (
    PARTITION BY k.call_id ORDER BY p.effective_from DESC NULLS LAST, p.min_prompt_tokens DESC NULLS LAST
  ) = 1
),
costed AS (
  SELECT
    pr.*,
    CASE WHEN pr.price_model IS NULL OR pr.tokens_unknown THEN NULL ELSE CAST(ROUND((
        CAST(pr.input_tokens AS DECIMAL(20, 0)) * pr.input_per_mtok
      + CAST(pr.output_tokens AS DECIMAL(20, 0)) * pr.output_per_mtok
      + CAST(pr.cache_write_5m_tokens AS DECIMAL(20, 0)) * COALESCE(pr.cache_write_5m_per_mtok, pr.input_per_mtok)
      + CAST(pr.cache_write_1h_tokens AS DECIMAL(20, 0)) * COALESCE(pr.cache_write_1h_per_mtok, pr.input_per_mtok)
      + CAST(pr.cache_read_tokens AS DECIMAL(20, 0)) * pr.cache_read_per_mtok
    ) * CAST('0.000001' AS DECIMAL(7, 6)), 9) AS DECIMAL(38, 9)) END AS cost_usd
  FROM priced pr
)
SELECT
  call_id, host, project_id, session_id, task_id, agent_run_id, ts, local_date,
  strftime(local_date, '%Y-%m') AS local_month,
  model, model_label, model_effective, model_inferred,
  price_model AS priced_model, estimated, (cost_usd IS NULL) AS unpriced, tokens_unknown,
  input_tokens, output_tokens, thinking_tokens, cache_write_5m_tokens, cache_write_1h_tokens, cache_read_tokens,
  prompt_tokens, latency_ms, is_error, cost_usd
FROM costed;

CREATE OR REPLACE VIEW v_daily_project_cost AS
SELECT
  c.local_date, c.local_month, c.project_id,
  COALESCE(p.display_name, c.project_id) AS display_name, p.client, c.host, c.priced_model,
  COUNT(*) AS calls,
  SUM(c.input_tokens) AS input_tokens,
  SUM(c.output_tokens) AS output_tokens,
  SUM(COALESCE(c.cache_write_5m_tokens, 0) + COALESCE(c.cache_write_1h_tokens, 0)) AS cache_write_tokens,
  SUM(c.cache_read_tokens) AS cache_read_tokens,
  SUM(c.cost_usd) AS cost_usd,
  COUNT(*) FILTER (WHERE c.unpriced) AS unpriced_calls,
  COUNT(*) FILTER (WHERE c.estimated) AS estimated_calls,
  COUNT(*) FILTER (WHERE c.model_inferred) AS inferred_calls,
  COUNT(*) FILTER (WHERE c.is_error) AS error_calls
FROM v_calls c
LEFT JOIN projects p ON p.project_id = c.project_id
GROUP BY c.local_date, c.local_month, c.project_id, p.display_name, p.client, c.host, c.priced_model;

CREATE OR REPLACE VIEW v_tasks AS
WITH tz AS (
  SELECT COALESCE(MAX(CASE WHEN key = 'timezone' THEN value END), 'UTC') AS name FROM settings
),
call_agg AS (
  SELECT
    task_id, COUNT(*) AS calls, SUM(input_tokens) AS input_tokens, SUM(output_tokens) AS output_tokens,
    SUM(cache_read_tokens) AS cache_read_tokens,
    SUM(COALESCE(cache_write_5m_tokens, 0) + COALESCE(cache_write_1h_tokens, 0)) AS cache_write_tokens,
    SUM(cost_usd) AS cost_usd,
    COUNT(*) FILTER (WHERE unpriced) AS unpriced_calls,
    COUNT(*) FILTER (WHERE estimated) AS estimated_calls,
    COUNT(*) FILTER (WHERE model_inferred) AS inferred_calls
  FROM v_calls GROUP BY task_id
),
run_agg AS (
  SELECT task_id, SUM(active_ms) AS run_active_ms, SUM(files_touched) AS files_touched,
    SUM(test_runs) AS test_runs, SUM(test_failures) AS test_failures
  FROM agent_runs GROUP BY task_id
),
tool_agg AS (
  SELECT r.task_id, SUM(u.calls) AS tool_calls
  FROM tool_uses u JOIN agent_runs r ON r.agent_run_id = u.agent_run_id
  GROUP BY r.task_id
),
tagged AS (
  SELECT t.task_id, COALESCE(tt.tag, th.tag) AS work_item_tag
  FROM tasks t
  LEFT JOIN task_tags tt ON tt.task_id = t.task_id
  LEFT JOIN tag_history th
    ON th.project_id = t.project_id AND t.started_at >= th.from_ts AND (th.to_ts IS NULL OR t.started_at < th.to_ts)
  QUALIFY row_number() OVER (PARTITION BY t.task_id ORDER BY th.from_ts DESC NULLS LAST) = 1
)
SELECT
  t.task_id, t.session_id, t.host, t.project_id,
  COALESCE(p.display_name, t.project_id) AS display_name, p.client,
  t.seq_in_session, t.started_at, t.ended_at,
  CAST(timezone(tz.name, t.started_at) AS DATE) AS local_date,
  t.wall_clock_ms, t.active_ms,
  COALESCE(t.reported_ms, t.wall_clock_ms) AS latency_ms,
  t.duration_source, t.status, t.agent_runs, t.max_spawn_depth,
  CASE WHEN t.agent_runs > 1 AND t.active_ms > 0
    THEN CAST(ROUND(CAST(r.run_active_ms AS DOUBLE) / t.active_ms, 2) AS DECIMAL(10, 2)) END AS parallelism,
  t.critical_path_ms, t.critical_path, t.retries, t.retry_summary,
  COALESCE(c.calls, 0) AS calls,
  c.input_tokens, c.output_tokens, c.cache_read_tokens, c.cache_write_tokens,
  c.cost_usd, COALESCE(c.unpriced_calls, 0) AS unpriced_calls,
  COALESCE(c.estimated_calls, 0) AS estimated_calls, COALESCE(c.inferred_calls, 0) AS inferred_calls,
  g.work_item_tag,
  COALESCE(ta.tool_calls, 0) AS tool_calls,
  COALESCE(r.files_touched, 0) AS files_touched,
  COALESCE(r.test_runs, 0) AS test_runs,
  COALESCE(r.test_failures, 0) AS test_failures
FROM tasks t
CROSS JOIN tz
LEFT JOIN projects p ON p.project_id = t.project_id
LEFT JOIN call_agg c ON c.task_id = t.task_id
LEFT JOIN run_agg r ON r.task_id = t.task_id
LEFT JOIN tool_agg ta ON ta.task_id = t.task_id
LEFT JOIN tagged g ON g.task_id = t.task_id;

CREATE OR REPLACE VIEW v_sessions AS
WITH tz AS (
  SELECT COALESCE(MAX(CASE WHEN key = 'timezone' THEN value END), 'UTC') AS name FROM settings
),
task_agg AS (
  SELECT session_id, COUNT(*) AS tasks, SUM(active_ms) AS active_ms,
    quantile_cont(COALESCE(reported_ms, wall_clock_ms), 0.5) AS task_p50_ms,
    quantile_cont(COALESCE(reported_ms, wall_clock_ms), 0.95) AS task_p95_ms
  FROM tasks GROUP BY session_id
),
call_agg AS (
  SELECT session_id, COUNT(*) AS calls, SUM(cost_usd) AS cost_usd,
    COUNT(*) FILTER (WHERE unpriced) AS unpriced_calls,
    SUM(COALESCE(input_tokens, 0)) AS input_tokens, SUM(COALESCE(cache_read_tokens, 0)) AS cache_read_tokens,
    SUM(COALESCE(cache_write_5m_tokens, 0) + COALESCE(cache_write_1h_tokens, 0)) AS cache_write_tokens
  FROM v_calls GROUP BY session_id
)
SELECT
  s.session_id, s.host, s.project_id, COALESCE(p.display_name, s.project_id) AS display_name,
  s.started_at, s.ended_at,
  CAST(timezone(tz.name, s.started_at) AS DATE) AS local_date,
  date_diff('millisecond', s.started_at, s.ended_at) AS wall_clock_ms,
  COALESCE(ta.active_ms, 0) AS active_ms,
  COALESCE(ta.tasks, 0) AS tasks,
  COALESCE(c.calls, 0) AS calls,
  c.cost_usd, COALESCE(c.unpriced_calls, 0) AS unpriced_calls,
  CASE WHEN c.input_tokens + c.cache_read_tokens + c.cache_write_tokens > 0
    THEN CAST(ROUND(CAST(c.cache_read_tokens AS DOUBLE)
      / (c.input_tokens + c.cache_read_tokens + c.cache_write_tokens), 4) AS DECIMAL(6, 4)) END AS cache_hit_ratio,
  ta.task_p50_ms, ta.task_p95_ms, s.status
FROM sessions s
CROSS JOIN tz
LEFT JOIN projects p ON p.project_id = s.project_id
LEFT JOIN task_agg ta ON ta.session_id = s.session_id
LEFT JOIN call_agg c ON c.session_id = s.session_id;

CREATE OR REPLACE VIEW v_agent_runs AS
WITH call_agg AS (
  SELECT agent_run_id, COUNT(*) AS calls, SUM(cost_usd) AS cost_usd, COUNT(*) FILTER (WHERE unpriced) AS unpriced_calls
  FROM v_calls GROUP BY agent_run_id
),
tool_agg AS (
  SELECT agent_run_id, SUM(calls) AS tool_calls FROM tool_uses GROUP BY agent_run_id
)
SELECT
  r.agent_run_id, r.task_id, r.session_id, r.host, r.project_id, r.parent_agent_run_id, r.agent_type,
  r.spawn_depth, r.started_at, r.ended_at, r.active_ms, r.status, r.errors, r.files_touched,
  r.test_runs, r.test_failures, r.tools_untracked,
  COALESCE(c.calls, 0) AS calls, c.cost_usd, COALESCE(c.unpriced_calls, 0) AS unpriced_calls,
  COALESCE(tl.tool_calls, 0) AS tool_calls
FROM agent_runs r
LEFT JOIN call_agg c ON c.agent_run_id = r.agent_run_id
LEFT JOIN tool_agg tl ON tl.agent_run_id = r.agent_run_id;

CREATE OR REPLACE VIEW v_agent_type_cost AS
WITH per_type AS (
  SELECT task_id, agent_type, COUNT(*) AS runs, SUM(calls) AS calls, SUM(cost_usd) AS cost_usd,
    SUM(unpriced_calls) AS unpriced_calls, SUM(active_ms) AS active_ms, SUM(tool_calls) AS tool_calls,
    SUM(files_touched) AS files_touched, SUM(test_runs) AS test_runs, SUM(test_failures) AS test_failures
  FROM v_agent_runs GROUP BY task_id, agent_type
),
task_cost AS (
  SELECT task_id, SUM(cost_usd) AS task_cost FROM per_type GROUP BY task_id
)
SELECT
  pt.task_id, pt.agent_type, pt.runs, pt.calls, pt.cost_usd, pt.unpriced_calls, pt.active_ms, pt.tool_calls,
  pt.files_touched, pt.test_runs, pt.test_failures,
  CASE WHEN tc.task_cost > 0 AND pt.cost_usd IS NOT NULL
    THEN CAST(ROUND(am_money_div(pt.cost_usd, tc.task_cost), 4) AS DECIMAL(6, 4)) END AS cost_share
FROM per_type pt
JOIN task_cost tc ON tc.task_id = pt.task_id;

CREATE OR REPLACE VIEW v_tool_counts AS
SELECT u.agent_run_id, r.task_id, u.tool_name, u.calls, u.errors
FROM tool_uses u
LEFT JOIN agent_runs r ON r.agent_run_id = u.agent_run_id;

CREATE OR REPLACE VIEW v_task_latency AS
SELECT
  strftime(local_date, '%Y-%m') AS local_month, project_id, host,
  COUNT(*) AS tasks,
  quantile_cont(latency_ms, 0.5) AS p50_ms,
  quantile_cont(latency_ms, 0.95) AS p95_ms,
  quantile_cont(latency_ms, 0.99) AS p99_ms
FROM v_tasks
WHERE status <> 'in_progress'
GROUP BY strftime(local_date, '%Y-%m'), project_id, host;

CREATE OR REPLACE VIEW v_dev_hours AS
WITH manual_day AS (
  SELECT project_id, CAST(period AS DATE) AS local_date, hours FROM dev_hours_manual WHERE length(period) = 10
),
manual_month AS (
  SELECT project_id, period AS local_month, hours FROM dev_hours_manual WHERE length(period) = 7
),
days AS (
  SELECT d.project_id, d.local_date, strftime(d.local_date, '%Y-%m') AS local_month,
    COALESCE(md.hours, d.hours) AS hours,
    CASE WHEN md.hours IS NOT NULL THEN 'manual' ELSE 'derived' END AS source
  FROM dev_hours_derived d
  LEFT JOIN manual_day md ON md.project_id = d.project_id AND md.local_date = d.local_date
  UNION ALL
  SELECT md.project_id, md.local_date, strftime(md.local_date, '%Y-%m'), md.hours, 'manual'
  FROM manual_day md
  WHERE NOT EXISTS (
    SELECT 1 FROM dev_hours_derived d WHERE d.project_id = md.project_id AND d.local_date = md.local_date
  )
)
SELECT project_id, local_date, local_month, hours, source
FROM days
WHERE NOT EXISTS (
  SELECT 1 FROM manual_month mm WHERE mm.project_id = days.project_id AND mm.local_month = days.local_month
)
UNION ALL
SELECT project_id, CAST(local_month || '-01' AS DATE), local_month, hours, 'manual' FROM manual_month;

CREATE OR REPLACE VIEW v_client_month AS
WITH kv AS (
  SELECT
    MAX(CASE WHEN key = 'display_currency' THEN value END) AS display_currency,
    TRY_CAST(MAX(CASE WHEN key = 'usd_rate' THEN value END) AS DECIMAL(18, 6)) AS usd_rate
  FROM settings
),
cost AS (
  SELECT local_month, project_id, SUM(cost_usd) AS cost_usd, SUM(unpriced_calls) AS unpriced_calls
  FROM v_daily_project_cost GROUP BY local_month, project_id
),
hours AS (
  SELECT local_month, project_id, SUM(hours) AS dev_hours FROM v_dev_hours GROUP BY local_month, project_id
),
months AS (
  SELECT local_month, project_id FROM cost UNION SELECT local_month, project_id FROM hours
),
base AS (
  SELECT
    m.local_month, p.client, m.project_id, COALESCE(p.display_name, m.project_id) AS display_name,
    p.billing_model, p.rate_currency, c.cost_usd, COALESCE(c.unpriced_calls, 0) AS unpriced_calls,
    CAST(COALESCE(h.dev_hours, 0) AS DECIMAL(12, 2)) AS dev_hours,
    CASE
      WHEN p.billing_model = 'hourly' AND p.hourly_rate IS NOT NULL
        THEN CAST(p.hourly_rate * COALESCE(h.dev_hours, 0) AS DECIMAL(18, 4))
      WHEN p.billing_model = 'fixed' AND p.fixed_price IS NOT NULL THEN CAST(p.fixed_price AS DECIMAL(18, 4))
    END AS billable_value,
    (SELECT SUM(c2.cost_usd) FROM cost c2 WHERE c2.project_id = m.project_id AND c2.local_month <= m.local_month)
      AS cumulative_cost
  FROM months m
  LEFT JOIN projects p ON p.project_id = m.project_id
  LEFT JOIN cost c ON c.local_month = m.local_month AND c.project_id = m.project_id
  LEFT JOIN hours h ON h.local_month = m.local_month AND h.project_id = m.project_id
),
converted AS (
  SELECT
    b.*,
    CASE
      WHEN b.rate_currency = 'USD' THEN b.billable_value
      WHEN b.rate_currency = kv.display_currency AND kv.usd_rate IS NOT NULL
        THEN CAST(ROUND(am_money_div(b.billable_value, kv.usd_rate), 4) AS DECIMAL(18, 4))
    END AS billable_usd
  FROM base b CROSS JOIN kv
)
SELECT
  local_month, client, project_id, display_name, billing_model, rate_currency, cost_usd, unpriced_calls,
  dev_hours, billable_value, billable_usd,
  CASE
    WHEN client IS NULL OR billable_usd IS NULL OR billable_usd = 0 THEN NULL
    WHEN billing_model = 'hourly' AND cost_usd IS NOT NULL
      THEN CAST(ROUND(am_money_div(cost_usd, billable_usd), 4) AS DECIMAL(12, 4))
    WHEN billing_model = 'fixed' AND cumulative_cost IS NOT NULL
      THEN CAST(ROUND(am_money_div(cumulative_cost, billable_usd), 4) AS DECIMAL(12, 4))
  END AS ai_cost_ratio
FROM converted;

CREATE OR REPLACE VIEW v_unpriced_models AS
SELECT host, model_effective, COUNT(*) AS calls, MIN(ts) AS first_ts, MAX(ts) AS last_ts
FROM v_calls
WHERE priced_model IS NULL
GROUP BY host, model_effective;

CREATE OR REPLACE VIEW v_untracked AS
SELECT host, reason, COUNT(*) AS conversations, MIN(observed_from) AS observed_from, MAX(observed_to) AS observed_to
FROM untracked
GROUP BY host, reason;

CREATE OR REPLACE VIEW v_health AS
WITH hosts AS (
  SELECT host FROM source_units
  UNION SELECT host FROM llm_calls
  UNION SELECT host FROM diagnostics
  UNION SELECT host FROM format_versions
)
SELECT
  h.host,
  (SELECT MAX(s.last_ingested_at) FROM source_units s WHERE s.host = h.host) AS last_ingested_at,
  (SELECT COUNT(*) FROM source_units s WHERE s.host = h.host) AS units,
  (SELECT COUNT(*) FROM format_versions f WHERE f.host = h.host AND NOT f.known) AS unknown_formats,
  (SELECT COALESCE(SUM(d.count), 0) FROM diagnostics d
    WHERE d.host = h.host AND d.run_at >= now() - INTERVAL 7 DAY) AS diagnostics_7d,
  (SELECT MIN(c.ts) FROM llm_calls c WHERE c.host = h.host) AS earliest_call_ts
FROM hosts h;
