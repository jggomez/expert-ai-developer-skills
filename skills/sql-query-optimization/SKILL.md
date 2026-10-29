---
name: sql-query-optimization
description: Diagnoses and rewrites slow SQL on traditional engines (Postgres, MySQL, SQL Server, etc.) using EXPLAIN/EXPLAIN ANALYZE — indexing strategy, WHERE clause selectivity, avoiding functions on indexed columns, JOIN vs. subquery vs. CTE tradeoffs, and pagination. Use for any query slowness outside BigQuery, or when a query needs an index.
---

# SQL Query Optimization Skill

## Overview
Diagnoses, profiles, and optimizes slow SQL queries across traditional relational engines (PostgreSQL, MySQL, SQL Server, SQLite, Oracle) under the rule: **start from the execution plan, never from intuition**. Analyzes `EXPLAIN ANALYZE` plans, designs selective composite indexes, rewrites non-sargable predicates and deep `OFFSET` pagination, and enforces concise artifact caps and fail-honest plan reporting.

## When to Use
### Trigger Scenarios
- Query latency spikes, timeouts, sequential scan bottlenecks, or high CPU/buffer reads on OLTP RDBMS engines.
- Analyzing `EXPLAIN (ANALYZE, BUFFERS)` (Postgres) or `EXPLAIN ANALYZE` (MySQL/SQL Server) execution trees.
- Designing composite/covering indexes, unwrapping indexed predicates, and converting `OFFSET` to keyset pagination.

### When NOT to Use
- **Google Cloud BigQuery MPP queries**: Route to `bigquery-query-optimization`.
- **Schema migrations and DDL lock safety**: Route to `database-migration-expert`.
- **Application-layer caching**: Route to `performance-scalability`.

## Process
### Phase 1: Fail-Honest Execution Plan Diagnostics
1. **Obtain the Live Plan**: Run `EXPLAIN (ANALYZE, BUFFERS, VERBOSE) <query>;` (or read-only `EXPLAIN` for mutating statements wrapped in `BEGIN; ... ROLLBACK;`).
2. **Fail-Honest Fallback (`STATIC_ANALYSIS_ONLY` / `BLOCKED`)**: If DB `EXPLAIN` fails due to missing credentials or an unreachable database, explicitly mark the output `STATIC_ANALYSIS_ONLY` / `BLOCKED: Live plan not executed — <exact error>` and **NEVER** invent row counts, buffer reads, or `EXPLAIN ANALYZE` latencies.
3. **Locate Bottlenecks**: Inspect unexpected `Seq Scan` nodes, massive estimated-vs-actual row skew (run `ANALYZE <table>;` if stale), and disk-spilling external sorts/hashes.

### Phase 2: Indexing & Query Rewriting Patterns
1. **Composite Index Ordering**: Index `WHERE`, `JOIN ... ON`, and `ORDER BY` columns ordered equality predicates first, then range/sort columns; avoid over-indexing write-heavy tables.
2. **Sargable Predicates**: Unwrap indexed columns (`WHERE created_at >= '2026-09-01' AND created_at < '2026-09-02'` instead of `WHERE DATE(created_at) = '2026-09-01'`).
3. **Keyset Pagination & Decorrelation**: Replace `OFFSET 50000` with `WHERE id > :last_seen_id ORDER BY id ASC LIMIT 20`; convert correlated subqueries into explicit `JOIN`s; replace `SELECT *` to enable Index-Only Scans.

### Phase 3: Concise Reporting & Repo Memory Sync
- **Selective Artifacts**: Author `PLAN.md` (`<= 50 lines`); **skip** `docs/<feature-name>/execution-plan.md` (`<= 50 lines`) for inline single-query rewrites; cap `docs/<feature-name>/optimization-report.md` at `<= 55 lines` (Zero-Fluff before/after metrics table + **Original / Optimized / Engine-Grounded Reasoning**).
- When auditing target repositories, maintain root `AGENTS.md` (`<= 90 lines`) and persist index baselines to `context/memory/MEMORY.md`.

## Usage
```bash
# PostgreSQL execution plan with buffer metrics
psql -d mydb -c "EXPLAIN (ANALYZE, BUFFERS) SELECT id, email FROM users WHERE created_at >= '2026-01-01' LIMIT 50;"

# MySQL execution plan
mysql -u root -p -e "EXPLAIN ANALYZE SELECT id, email FROM users WHERE status = 'active';"
```
- **Host Execution**: Run `psql`/`mysql` via shell (`Bash` in Claude Code; `run_command` in Antigravity) or explicitly label `STATIC_ANALYSIS_ONLY` / `BLOCKED` if DB access is unavailable.

## Red Flags
- Fabricating `EXPLAIN ANALYZE` execution latencies or buffer counts when no live database ran.
- Suggesting indexes without checking plan selectivity or wrapping indexed columns in `LOWER(...)` / `DATE(...)` without expression indexes.
- Using deep `LIMIT/OFFSET` pagination or creating `execution-plan.md` bloat for single-query rewrites.

## Verification
- [ ] Live `EXPLAIN ANALYZE` plan verified before/after, OR report explicitly marked `STATIC_ANALYSIS_ONLY` / `BLOCKED: Live plan not executed — <exact error>`.
- [ ] Sequential scans replaced by Index / Index-Only Scans with semantic equivalence preserved.
- [ ] Indexed columns unwrapped in `WHERE` predicates and deep `OFFSET` replaced by keyset filters.
- [ ] `optimization-report.md` (`<= 55 lines`) includes before/after table + Original / Optimized / Engine-Grounded Reasoning.
