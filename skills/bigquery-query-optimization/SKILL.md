---
name: bigquery-query-optimization
description: Diagnoses and rewrites slow BigQuery SQL using the query plan (stages, shuffle, workers) — partitioning/clustering pruning, JOIN ordering and broadcast vs. shuffle joins, skewed JOINs, WHERE clause selectivity, and approximate/SQL-vs-JS function choices. Use when a BigQuery query is slow, expensive, or hitting Resources Exceeded, or when reviewing a query plan.
---

# BigQuery Query Optimization Skill

## Overview
Diagnoses and optimizes slow, expensive, or slot-constrained Google Cloud BigQuery SQL under the principle: **less work → faster query**. Reduces scanned bytes, stage shuffle, and slot CPU via partition/cluster pruning, broadcast JOIN ordering, and native SQL functions while enforcing concise artifact caps and fail-honest `--dry_run` reporting.

## When to Use
### Trigger Scenarios
- BigQuery queries hitting high byte scans, excessive slot time, shuffle bottlenecks, worker skew, or `Resources Exceeded`.
- Optimizing partition pruning, cluster filter alignment, and multi-table JOIN/window patterns.
- Scanning repositories (`.sql`, `.py`, `.js`, `.ts`, `.java`, `.go`) for BigQuery SQL anti-patterns.

### When NOT to Use
- **Traditional OLTP databases (PostgreSQL, MySQL, SQL Server)**: Route to `sql-query-optimization`.
- **Lakehouse architecture & service selection**: Route to `gcp-data-engineering`.
- **Datastream CDC & SCD Type 2 merges**: Route to `cdc-scd-patterns`.

## Process
### Phase 1: Static Linting & Fail-Honest Plan Diagnostics
1. **Static Scan**: Run `python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py [optional_path]` across target directories.
2. **Stage & Dry-Run Inspection**: Check `bq query --use_legacy_sql=false --dry_run` and `INFORMATION_SCHEMA.JOBS` for max-vs-avg worker skew (`APPROX_TOP_COUNT`), intermediate shuffle volume, and CPU-heavy UDFs/distincts.
3. **Fail-Honest Fallback (`STATIC_ANALYSIS_ONLY` / `BLOCKED`)**: If `bq query --dry_run` fails due to missing GCP ADC credentials or permissions, explicitly mark the report `STATIC_ANALYSIS_ONLY` / `BLOCKED: Live plan not executed — <exact error>` and **NEVER** invent byte-scan numbers or slot times.

### Phase 2: BigQuery Optimization Rules
1. **Column, Partition & Cluster Pruning**: Replace `SELECT *` with explicit columns; filter on partition columns and align `WHERE`/`JOIN` predicates with clustered keys.
2. **Broadcast JOIN Ordering & Early Filtering**: Place the **largest table first** in `FROM` followed by decreasing sizes; push filters into CTEs/subqueries before joining; model 1:N structures with `ARRAY<STRUCT>` where appropriate.
3. **Bounded Sorts, Approx Aggs & SQL UDFs**: Always pair `ORDER BY` with `LIMIT`; use `APPROX_COUNT_DISTINCT` when ~1% tolerance fits; replace JS UDFs with native SQL UDFs.

### Phase 3: Concise Reporting & Repo Memory Sync
- **Selective Artifacts**: Author `PLAN.md` (`<= 50 lines`); **skip** `docs/<feature-name>/execution-plan.md` (`<= 50 lines`) for inline single-query rewrites; cap `docs/<feature-name>/optimization-report.md` at `<= 55 lines` (Zero-Fluff before/after metrics table + **Original / Optimized / Engine-Grounded Reasoning**).
- On repo audits, maintain root `AGENTS.md` (`<= 90 lines`) and persist partition/cluster baselines in `context/memory/MEMORY.md`.

## Usage
```bash
# Scan repository or SQL directory for BigQuery anti-patterns
python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py .
python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py queries/

# Verify byte scan reduction via BigQuery dry-run
bq query --use_legacy_sql=false --dry_run < optimized_query.sql
```
- **Host Execution**: Run `lint_sql_query.py` and `bq --dry_run` via shell (`Bash` in Claude Code; `run_command` in Antigravity), reporting `STATIC_ANALYSIS_ONLY` / `BLOCKED` if GCP ADC is unavailable.

## Red Flags
- Fabricating `bq query --dry_run` scanned bytes or slot metrics when GCP credentials fail instead of reporting `STATIC_ANALYSIS_ONLY` / `BLOCKED: Live plan not executed — <exact error>`.
- Placing small tables first in `FROM` JOINs, running unbounded `ORDER BY` without `LIMIT`, omitting partition filters, or using `REGEXP_CONTAINS` where `LIKE` suffices.

## Verification
- [ ] Static linter passes cleanly: `python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py .`
- [ ] `bq query --dry_run` confirms byte scan reduction, OR report explicitly states `STATIC_ANALYSIS_ONLY` / `BLOCKED: Live plan not executed — <exact error>`.
- [ ] Largest table placed first in `JOIN`s, partition filters applied, and no unbounded `ORDER BY` remains.
- [ ] `optimization-report.md` (`<= 55 lines`) presents before/after metrics + Original / Optimized / Engine-Grounded Reasoning.

## References
- [BigQuery Optimization Patterns Reference](references/bigquery-optimization-patterns.md)
