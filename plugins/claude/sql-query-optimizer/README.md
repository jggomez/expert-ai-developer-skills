# sql-query-optimizer

> Diagnoses and rewrites slow BigQuery and relational SQL using real execution plans, for Claude Code.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-orange?style=flat-square)](../../../docs/claude-code-installation.md)

`sql-query-optimizer` finds slow SQL in standalone `.sql` files and in queries embedded in application code.
It diagnoses BigQuery query plans (shuffle, skew, partition pruning) or `EXPLAIN` plans on Postgres, MySQL and SQL Server, then rewrites each query with the reasoning behind the change.
A safety hook keeps it read-only: destructive DDL is denied and every `bq query` must be a dry run.

## Requirements

| Needs | For |
| :--- | :--- |
| `node` on `PATH` | Running the safety hook |
| `python3` | The static linter `lint_sql_query.py` |
| `bq` / `gcloud` with Application Default Credentials (optional) | BigQuery dry runs and the `bigquery` MCP server |
| Database access, e.g. `psql` (optional) | `EXPLAIN` / `EXPLAIN ANALYZE` on relational engines |

Without credentials the agent still works, but marks its report `STATIC_ANALYSIS_ONLY`.

## Installation

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install sql-query-optimizer@expert-ai-developer-skills
```

Updates, per-project settings, local development and limitations: [Claude Code installation guide](../../../docs/claude-code-installation.md).

## Quick start

```text
Use the sql-query-optimizer agent to find why reports/daily_revenue.sql scans so many bytes in BigQuery.
```

```text
Audit all SQL in src/ for missing indexes and slow pagination on Postgres.
```

Run the static BigQuery linter on its own, from the plugin root (no connection needed):

```bash
python3 skills/bigquery-query-optimization/scripts/lint_sql_query.py path/to/sql
```

## What's included

### Agents

| Agent | Role | Model |
| :--- | :--- | :--- |
| `sql-query-optimizer` | Scans `.sql` files and embedded SQL, identifies the dialect, reads plans, and rewrites queries as Original / Optimized / Reasoning | `inherit` |

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `PreToolUse` (`Bash`) | `hooks/sql-safety-gate.js` | Denies `DROP TABLE/VIEW/SCHEMA/DATABASE/INDEX`, `TRUNCATE` and `ALTER TABLE ... DROP`. Denies any `bq query` without `--dry_run`. |

### MCP servers

| Server | Command | Purpose |
| :--- | :--- | :--- |
| `bigquery` | HTTP `https://bigquery.googleapis.com/mcp` | BigQuery schemas and query plans |
| `cloudsql` | HTTP `https://sqladmin.googleapis.com/mcp/query_execution` (OAuth, Cloud SQL scope) | Query execution against Cloud SQL for `EXPLAIN` plans |

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`bigquery-query-optimization`** | Plan-based BigQuery tuning: partition/cluster pruning, JOIN order, broadcast vs. shuffle, skew; includes `lint_sql_query.py` |
| **`sql-query-optimization`** | `EXPLAIN` / `EXPLAIN ANALYZE` tuning for Postgres, MySQL, SQL Server: indexes, selectivity, CTE vs. subquery, pagination |
| **`context-restore`** | Reads `context/memory/MEMORY.md` at audit start to reuse known partition, cluster and index keys |
| **`context-capture`** | Records optimization baselines and index/partition recommendations in `context/memory/` |

## How it works

1. The agent reads `context/memory/MEMORY.md` if it exists and classifies the task as Tier 1, 2 or 3.
2. It locates SQL (files or string literals in `.py`, `.js`, `.ts`, `.java`, `.go`, `.rb`, `.scala`) and identifies the dialect.
3. It runs `bq query --dry_run` or `EXPLAIN` to get a real plan. If that fails, it marks the result `STATIC_ANALYSIS_ONLY` / `BLOCKED` and never invents byte counts or latencies.
4. Each rewrite keeps result semantics and is shown as Original, Optimized and Reasoning.
5. Significant baselines go to `context/memory/` through `context-capture`.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `"bq query" command requires "--dry_run" flag` | The hook denies every live `bq query` | Add `--dry_run`; run the real query yourself if needed |
| `[SQL SAFETY GATE VIOLATION]: Destructive ... statement blocked` | The command contains `DROP`, `TRUNCATE` or `ALTER TABLE ... DROP` | Review and run it outside the agent |
| Report says `STATIC_ANALYSIS_ONLY` | No credentials or the database is unreachable | Configure Application Default Credentials or database access, then rerun |
| Linter finds nothing in a directory | Only `.sql` files and string literals with `SELECT/INSERT/UPDATE/DELETE ... FROM` are scanned | Point it at the file or folder that holds the queries |

## Related plugins

- [`senior-data-engineer`](../senior-data-engineer/README.md): designs the pipelines whose SQL this plugin tunes.
- [`shared-context`](../shared-context/README.md): the `context/memory/` store shared across sessions and hosts.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
