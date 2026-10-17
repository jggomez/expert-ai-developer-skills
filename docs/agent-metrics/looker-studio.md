# agent-meter — Looker Studio dashboard (Option B)

> Companion to `ADR-001-agent-meter.md` §3.11 and `contracts.md` §6–§7. The dashboard reads **only** the BigQuery views that `agent-meter setup --cloud` creates. They have the same names and columns as the local DuckDB views, so Looker shows the same numbers as `agent-meter report`.
>
> Status: the manual setup below is the supported path. Items marked **to verify at L4** need a real run against `devhack-3f0c2` before Milestone B ships.

## 1. Before you start

1. `agent-meter setup --cloud` has finished: the dataset (default `agent_metrics`) exists in your project, with tables, dedup views and `v_*` views, and at least one `agent-meter sync` has completed.
2. `agent-meter verify --reconcile --cloud --from <d1> --to <d2>` reports **0 differences**. If it doesn't, fix that first: Looker can only be as right as the replica.
3. The Google account you use in Looker Studio has `roles/bigquery.dataViewer` on the dataset and `roles/bigquery.jobUser` on the project. Use the same account as ADC, or share the dataset with it.

How to read the data:

- **Cost is API-equivalent** (`≈`). Subscription plans (Claude Pro/Max, Gemini plans) are not billed per token (BR-01). Put this note in the report header.
- **`cost_usd` excludes unpriced calls.** Always show `unpriced_calls` next to a cost total. Render the total as "≥ $X" when `unpriced_calls > 0` (BR-02, invariant I-6). Never replace a NULL cost with 0.
- **Dates are local.** `local_date` and `local_month` use `settings.timezone` (uploaded with every sync), not the Looker viewer's time zone. Filter and group on these fields, not on `ts` or `started_at`.
- **Anonymized datasets.** With `anonymize_projects = true`, `project_id`, `display_name`, `client`, `remote_url` and work-item `tag` are 16-character hashes. Only the local CLI can map them back. Use `agent-meter projects` to read them.
- Prices are recomputed at query time from the uploaded `pricing` tables, so a price fix shows up in Looker after the next sync (PC-08).

## 2. Data sources

Create one **BigQuery** data source per view: *Create → Data source → BigQuery → My projects → `<project>` → `<dataset>` → `<view>`*. Use these settings for each one:

| Setting | Value |
| :--- | :--- |
| Billing project | your project (e.g. `devhack-3f0c2`) |
| Data freshness | 1 hour (the scheduler syncs every 15 min; 12 h is fine for monthly reviews and scans less) |
| Date range dimension | `local_date` where it exists |
| Field types | `cost_usd`, `billable_value`, `billable_usd` → *Currency (USD)*; `*_ms` → *Number* (or *Duration* after dividing by 1000); `cache_hit_ratio`, `cost_share`, `ai_cost_ratio` → *Percent*; `local_month` → *Text* (`YYYY-MM`) |
| Aggregation | `SUM` for counts, tokens and cost; **never `AVG` of `cost_usd`** across days (use calculated fields instead) |

| Data source name | View | Used on pages |
| :--- | :--- | :--- |
| `am_daily_cost` | `v_daily_project_cost` | Overview, Efficiency |
| `am_client_month` | `v_client_month` | Overview, Efficiency |
| `am_sessions` | `v_sessions` | Traceability, Performance |
| `am_tasks` | `v_tasks` | Traceability, Tasks & Agents, Performance |
| `am_agent_runs` | `v_agent_runs` | Traceability, Tasks & Agents |
| `am_agent_type_cost` | `v_agent_type_cost` | Tasks & Agents, Efficiency |
| `am_tool_counts` | `v_tool_counts` | Tasks & Agents |
| `am_calls` | `v_calls` | Traceability, Performance |
| `am_task_latency` | `v_task_latency` | Performance |
| `am_dev_hours` | `v_dev_hours` | Efficiency |
| `am_unpriced` | `v_unpriced_models` | Efficiency (data quality) |
| `am_untracked` | `v_untracked` | Efficiency (data quality) |
| `am_health` | `v_health` | Efficiency (data quality) |

Do **not** point Looker at `raw_*` tables. They hold every uploaded version of a row. The dedup views (`llm_calls`, `tasks`, …) and the `v_*` views on top of them return exactly one row per key.

Cost guard: the views are small (about 10^5 calls a year) and partitions are monthly with no required partition filter. BQ-09 keeps every view's full-history dry run ≤ 1 GiB at 10x the current volume, so normal dashboard use stays inside the 1 TiB/month free query tier.

## 3. Pages

All pages share a **date range control** (dimension `local_date`) and filter controls for `display_name`, `client` and `host`. Turn on *Report-level* filters so the selection follows you across pages. Cross-source filtering works because every source uses the same field names (`project_id`, `session_id`, `task_id`, `agent_run_id`). **To verify at L4**: cross-filtering between different data sources on these shared names.

### 3.1 Overview

| Chart | Source | Dimensions | Metrics / notes |
| :--- | :--- | :--- | :--- |
| Scorecards: cost, calls, unpriced calls, error calls | `am_daily_cost` | — | `SUM(cost_usd)` shown as "≥ $" when `SUM(unpriced_calls) > 0`; `SUM(calls)`; `SUM(unpriced_calls)`; `SUM(error_calls)` |
| Time series: cost per day by host | `am_daily_cost` | `local_date`, breakdown `host` | `SUM(cost_usd)` |
| Bar: cost by project | `am_daily_cost` | `display_name` | `SUM(cost_usd)`, `SUM(unpriced_calls)` |
| Table: tokens by model | `am_daily_cost` | `priced_model` (NULL = unpriced) | `SUM(input_tokens)`, `SUM(output_tokens)`, `SUM(cache_read_tokens)`, `SUM(cache_write_tokens)`, `SUM(estimated_calls)`, `SUM(inferred_calls)` |
| Table: month by client | `am_client_month` | `local_month`, `client`, `display_name` | `cost_usd`, `dev_hours`, `billable_usd`, `ai_cost_ratio` |

Footnotes on the page: `*` = estimated price (`estimated_calls`), `†` = inferred model (`inferred_calls`).

### 3.2 Traceability (drill-down project → session → task → agent run → call)

Set up four tables stacked top to bottom. On each table, turn on *Chart interactions → Cross-filtering*, so clicking a row filters the tables below it.

| Level | Source | Dimensions | Metrics |
| :--- | :--- | :--- | :--- |
| Sessions | `am_sessions` | `display_name`, `host`, `session_id`, `started_at`, `status` | `tasks`, `calls`, `cost_usd`, `unpriced_calls`, `active_ms`, `wall_clock_ms`, `cache_hit_ratio` |
| Tasks | `am_tasks` | `session_id`, `task_id`, `seq_in_session`, `status`, `work_item_tag` | `calls`, `cost_usd`, `unpriced_calls`, `active_ms`, `latency_ms`, `agent_runs`, `retries` |
| Agent runs | `am_agent_runs` | `task_id`, `agent_run_id`, `parent_agent_run_id`, `agent_type`, `spawn_depth`, `status` | `calls`, `cost_usd`, `active_ms`, `tool_calls`, `errors` |
| Calls | `am_calls` | `agent_run_id`, `call_id`, `ts`, `model_effective`, `priced_model` | `input_tokens`, `output_tokens`, `cache_read_tokens`, `cost_usd`, `latency_ms` |

The project level is the report-wide `display_name` filter. No prompt text exists anywhere in BigQuery (BR-16), so tasks are identified by `task_id` and `seq_in_session`, never by a label.

### 3.3 Tasks & Agents

| Chart | Source | Dimensions | Metrics / notes |
| :--- | :--- | :--- | :--- |
| Gantt of agent runs for the selected task | `am_agent_runs` | `agent_type` (rows), `started_at` → `ended_at` | Use the **Timeline** chart if your Looker Studio has it (**to verify at L4**). Fallback: a horizontal stacked bar where the first, transparent series is `start offset = DATETIME_DIFF(started_at, MIN(started_at), SECOND)` and the second is `active_ms / 1000` |
| Bar: cost by agent type | `am_agent_type_cost` | `agent_type` | `SUM(cost_usd)`, `SUM(runs)`, `SUM(unpriced_calls)` |
| Table: per-task rollup | `am_tasks` | `task_id`, `critical_path`, `retry_summary`, `work_item_tag` | `agent_runs`, `max_spawn_depth`, `parallelism`, `critical_path_ms`, `retries`, `cost_usd`, `test_runs`, `test_failures`, `files_touched` |
| Table: agent type share inside a task | `am_agent_type_cost` | `task_id`, `agent_type` | `cost_share`, `active_ms`, `tool_calls`, `test_failures` |
| Bar: tools used | `am_tool_counts` | `tool_name` | `SUM(calls)`, `SUM(errors)` |

### 3.4 Performance

| Chart | Source | Dimensions | Metrics / notes |
| :--- | :--- | :--- | :--- |
| Line: task latency percentiles by month | `am_task_latency` | `local_month`, breakdown `host` | `p50_ms`, `p95_ms`, `p99_ms` (exact `PERCENTILE_CONT`, finished tasks only). Don't re-aggregate percentiles across months or projects: filter to a single `project_id` |
| Table: latency by project | `am_task_latency` | `local_month`, `display_name` via a blend with `am_daily_cost` on `project_id`, or `project_id` | `tasks`, `p50_ms`, `p95_ms` |
| Scatter: active vs wall-clock per task | `am_tasks` | `task_id` | X `wall_clock_ms`, Y `active_ms`, bubble `cost_usd` |
| Bar: call latency by model | `am_calls` | `model_effective` | `AVG(latency_ms)`, `COUNT(call_id)` (Antigravity reports latency; Claude Code calls have NULL latency) |
| Table: sessions | `am_sessions` | `session_id`, `host` | `task_p50_ms`, `task_p95_ms`, `active_ms` |

### 3.5 Efficiency

| Chart | Source | Dimensions | Metrics / notes |
| :--- | :--- | :--- | :--- |
| Table: AI cost vs billable value | `am_client_month` | `local_month`, `client`, `display_name`, `billing_model`, `rate_currency` | `cost_usd`, `dev_hours`, `billable_value`, `billable_usd`, `ai_cost_ratio` (NULL when the project has no client or rate, so show "—", not 0%) |
| Bar: dev hours by day | `am_dev_hours` | `local_date`, breakdown `source` (`derived` / `manual`) | `SUM(hours)` |
| Scorecard: cache hit ratio | `am_sessions` | — | Calculated field `SUM(cache_hit_ratio * calls) / SUM(calls)`, or read it per session |
| Pie: cost share by agent type | `am_agent_type_cost` | `agent_type` | `SUM(cost_usd)` |
| Data quality: unpriced models | `am_unpriced` | `host`, `model_effective` | `calls`, `first_ts`, `last_ts`. Fix locally with `agent-meter pricing add …`, then `sync` |
| Data quality: untracked history | `am_untracked` | `host`, `reason` | `conversations`, `observed_from`, `observed_to` |
| Data quality: replica health | `am_health` | `host` | `last_ingested_at` (latest upload), `units`, `earliest_call_ts`. `unknown_formats` and `diagnostics_7d` are always NULL in the cloud: run `agent-meter doctor` locally |

## 4. One-click copy (Linking API) — **to verify at L4**

`setup --cloud` prints a link that copies a public template report and binds it to your dataset (ADR §3.11). The intended form uses one data-source alias per view defined in the template (`ds0` … `ds12`):

```
https://lookerstudio.google.com/reporting/create
  ?c.reportId=<looker_template_id>
  &r.reportName=agent-meter
  &ds.ds0.connector=bigQuery&ds.ds0.type=TABLE
  &ds.ds0.projectId=<project>&ds.ds0.datasetId=<dataset>&ds.ds0.tableId=v_daily_project_cost
  &ds.ds0.billingProjectId=<project>
  &ds.ds1.connector=bigQuery&ds.ds1.type=TABLE
  &ds.ds1.projectId=<project>&ds.ds1.datasetId=<dataset>&ds.ds1.tableId=v_client_month
  … (one block per data source in §2)
```

Check each of these at L4 before documenting the link as supported:

- [ ] The parameter names above (`c.reportId`, `r.reportName`, `ds.<alias>.connector`, `type`, `projectId`, `datasetId`, `tableId`, `billingProjectId`) are accepted.
- [ ] A template report shared publicly ("anyone with the link can view") can be copied by another account, and its id is stored in `config.toml` → `[sinks.bigquery] looker_template_id`.
- [ ] All 13 data sources rebind in one URL (multi-data-source binding), and the URL stays under the browser length limit. If it doesn't, bind the main sources and document the rest as manual steps.
- [ ] After copying, totals on the Overview page equal `agent-meter report` for the same range and timezone (US-14, BQ-08).

Until all boxes are checked, `setup --cloud` should print the manual steps in §2–§3 as the fallback.

## 5. Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Totals differ from `agent-meter report` | Sync lag, or a different timezone/date range | `agent-meter sync`, then `agent-meter verify --reconcile --cloud`; compare on `local_date`, not `ts` |
| A price change doesn't show up | Looker cache | Reduce data freshness, or *View → Refresh data* after `sync` |
| "Access Denied" in a chart | The viewer account lacks dataset access | Grant `roles/bigquery.dataViewer` on the dataset and `roles/bigquery.jobUser` on the project |
| Projects show as hashes | `anonymize_projects = true` | Expected. The clear names stay local |
| Cost total looks low | Unpriced calls | Check the *unpriced models* table; `agent-meter pricing unpriced` lists the exact `pricing add` commands |
