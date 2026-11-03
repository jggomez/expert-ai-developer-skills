---
trigger: model_decision
description: Load when analyzing, tuning or rewriting SQL queries (BigQuery, PostgreSQL, MySQL) - read-only safety, dry runs, semantic equivalence and fail-honest execution plans.
---

# SQL Optimization Rules

- **Read-only by default**: never run `DROP`, `TRUNCATE` or bulk `DELETE`/`UPDATE` while optimizing. Run `bq query --dry_run` before any BigQuery analytical query.
- **Same results**: a rewrite keeps the output schema, filters and row-count semantics unless the user approves a change.
- **Dialect-specific reasoning**: BigQuery (partition pruning, clustering, broadcast vs shuffle joins) and PostgreSQL/MySQL (B-tree indexes, heap scans, `EXPLAIN`) follow different rules; never mix them.
- **Output**: present each rewrite as 1. Original query, 2. Optimized query, 3. Engine-grounded reasoning (scan, pruning, index or join stage). Inline single-query fixes need no artifact; larger work writes `docs/<feature-name>/optimization-report.md` (`<= 55` lines).
- **Fail-honest plans**: if a dry run or `EXPLAIN` cannot run (credentials, unreachable DB), mark the result `STATIC_ANALYSIS_ONLY` or `BLOCKED: live plan not executed - <exact error>`; never invent bytes scanned, slot time or latency.
- **Git Branch Governance**: edit query files only on a `feat/<slug>` branch, never on `main`, `master`, `develop` or `dev`.
