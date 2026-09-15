---
name: sql-query-optimization
description: Diagnoses and rewrites slow SQL on traditional engines (Postgres, MySQL, SQL Server, etc.) using EXPLAIN/EXPLAIN ANALYZE — indexing strategy, WHERE clause selectivity, avoiding functions on indexed columns, JOIN vs. subquery vs. CTE tradeoffs, and pagination. Use for any query slowness outside BigQuery, or when a query needs an index.
---

# SQL Query Optimization Skill

## Overview
This skill diagnoses, profiles, and optimizes slow SQL queries across traditional relational database engines (PostgreSQL, MySQL, SQL Server, SQLite, Oracle). It acts as a Database Performance Engineer operating under the mandate: **always start from the execution plan, never from intuition**. It analyzes `EXPLAIN ANALYZE` outputs, designs targeted composite indexes, rewrites inefficient subqueries, and implements keyset pagination.

## When to Use
### Trigger Scenarios
- Query latency spikes, timeout errors, or high database CPU usage on traditional RDBMS instances.
- Analyzing execution plans (`EXPLAIN (ANALYZE, BUFFERS)` in Postgres, `EXPLAIN ANALYZE` in MySQL).
- Designing single-column and composite indexes to eliminate sequential table scans.
- Rewriting inefficient SQL patterns (correlated subqueries, function-wrapped index filters, deep `OFFSET` pagination).

### When NOT to Use
- **Google Cloud BigQuery queries**: Route to `bigquery-query-optimization` (which uses a distributed columnar slot-based model).
- **Database schema migrations and DDL lock safety**: Route to `database-migration-expert`.
- **Application-level caching architecture**: Route to `performance-scalability`.

## Process
### Phase 1: Execution Plan Diagnostics
1. **Obtain the Actual Plan**: Never optimize SQL from reading text alone. Run `EXPLAIN ANALYZE` with buffer statistics:
   ```sql
   EXPLAIN (ANALYZE, BUFFERS, VERBOSE) <query>;
   ```
2. **Locate Bottleneck Nodes**:
   - **Sequential Scans (Seq Scan)** on large tables where an index scan was expected.
   - **Hash / Nested Loop Joins** with massive differences between estimated and actual row counts.
   - **External Sorts / Hash Aggregates** spilling to disk (indicates low `work_mem` or missing indexes).
3. **Audit Statistics Freshness**: If estimated rows differ from actual rows by orders of magnitude, re-run table statistics analysis (`ANALYZE <table>;`) before changing the query.

### Phase 2: Indexing Strategy
1. **Target Filtering Columns**: Index columns appearing in `WHERE`, `JOIN ... ON`, and `ORDER BY` clauses.
2. **Composite Index Ordering**: Order columns by selectivity: place equality-filtered columns first, followed by range-filtered or sorting columns.
3. **Avoid Over-Indexing**: Every index adds write overhead during `INSERT`/`UPDATE`/`DELETE`. Create covering indexes only when high read frequency justifies it.

### Phase 3: Query Rewriting Patterns
1. **Unwrap Indexed Columns**: Never wrap indexed columns in functions.
   - *Anti-pattern*: `WHERE DATE(created_at) = '2026-09-01'` (disables index scan).
   - *Optimized*: `WHERE created_at >= '2026-09-01' AND created_at < '2026-09-02'`.
2. **Keyset Pagination vs. OFFSET**: Replace deep offsets (`OFFSET 50000`) with keyset pagination (`WHERE id > :last_seen_id ORDER BY id ASC LIMIT 20`) to eliminate scanning discarded rows.
3. **Decorrelate Subqueries**: Convert correlated subqueries (which execute once per outer row) into explicit `JOIN`s or CTEs.
4. **Column Pruning**: Eliminate `SELECT *` to allow the engine to use Index-Only scans without reading heap pages.

### Phase 4: Empirical Verification
Re-run `EXPLAIN ANALYZE` after applying index or query changes. Confirm the planner chose the index scan and that total execution time and buffer read counts dropped.

## Usage
### CLI Invocations
```bash
# PostgreSQL explain plan
psql -d mydb -c "EXPLAIN (ANALYZE, BUFFERS) SELECT id, email FROM users WHERE created_at >= '2026-01-01' LIMIT 50;"

# MySQL explain plan
mysql -u root -p -e "EXPLAIN ANALYZE SELECT id, email FROM users WHERE status = 'active';"
```

### Example Prompts
- *"Run EXPLAIN ANALYZE on this Postgres query and tell me why it's performing a sequential scan."*
- *"Rewrite this paginated query to use keyset pagination instead of LIMIT/OFFSET."*
- *"Design a composite index for this multi-column filter on status, tenant_id, and created_at."*

### Host Execution Instructions
- **Claude Code**: Request or inspect the execution plan output in the shell before proposing SQL rewrites.
- **Antigravity**: Analyze SQL query plans, apply unwrapping rules, and verify execution metrics.

## Red Flags
- Suggesting indexes without reviewing an `EXPLAIN ANALYZE` plan.
- Wrapping filtered columns in functions like `LOWER(email)` or `DATE(timestamp)` without functional indexes.
- Using `LIMIT 20 OFFSET 50000` for infinite scroll or deep pagination.
- Adding single-column indexes on every column instead of targeted composite indexes.

## Verification
- [ ] Query execution plan obtained via `EXPLAIN ANALYZE` before and after modifications.
- [ ] Sequential table scans replaced by Index Scans or Index-Only Scans.
- [ ] No functions wrapping indexed columns in `WHERE` predicates.
- [ ] Deep pagination rewritten using keyset filters (`WHERE id > :last_id`).

