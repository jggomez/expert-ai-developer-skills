---
name: sql-query-optimization
description: Diagnoses and rewrites slow SQL on traditional engines (Postgres, MySQL, SQL Server, etc.) using EXPLAIN/EXPLAIN ANALYZE — indexing strategy, WHERE clause selectivity, avoiding functions on indexed columns, JOIN vs. subquery vs. CTE tradeoffs, and pagination. Use for any query slowness outside BigQuery, or when a query needs an index.
---

### Role & Mindset
You are a **Database Performance Engineer** working across traditional relational engines. Start from the execution plan, not intuition — `EXPLAIN ANALYZE` tells you what the planner actually did, not what you assume it did. This skill covers dialect-agnostic patterns; for BigQuery specifically, use the `bigquery-query-optimization` skill instead — the two engines' cost models are different enough that the same fix isn't always right on both.

---

### Diagnostic Workflow

1. **Run the real plan**: `EXPLAIN ANALYZE` (Postgres/MySQL) or the equivalent for your engine. Never optimize from reading the SQL alone if you can get the actual plan.
2. **Look for the expensive nodes**: a sequential/table scan on a large table where an index scan was expected, a nested loop join with a high row estimate, a sort spilling to disk, or a mismatch between estimated and actual row counts (stale statistics).
3. **Check statistics freshness**: stale statistics after bulk loads, large deletes, or schema changes cause the planner to pick bad plans (e.g. a sequential scan when an index scan would win). Re-run `ANALYZE` (Postgres) or the engine's equivalent before trusting the plan.

---

### Optimization Rules

1. **Index the right columns**: add indexes on columns used in `WHERE`, `JOIN ON`, and `ORDER BY` — not on every column. For composite indexes, order columns by selectivity (most selective/most-filtered-on first), matching how the query actually filters.
2. **Don't wrap indexed columns in functions**: `WHERE DATE(created_at) = '2024-01-01'` can't use an index on `created_at`; rewrite as a range (`created_at >= '2024-01-01' AND created_at < '2024-01-02'`) so the index applies.
3. **SELECT only needed columns**: avoid `SELECT *`, especially when it forces the planner off a covering index and back to the full table.
4. **Filter as early and as selectively as possible**: put the most restrictive condition where the planner can use it first — verify with `EXPLAIN`, don't assume the planner reorders for you.
5. **JOIN vs. correlated subquery**: a correlated subquery re-executes per outer row; the same logic as a `JOIN` (or a decorrelated subquery / CTE) usually lets the planner pick a single efficient join strategy instead.
6. **Avoid N+1 queries**: one query per row in a loop is an application-layer anti-pattern, not just a database one — see the `performance-scalability` skill for eager-loading fixes.
7. **Paginate with keyset pagination for large offsets**: `LIMIT 20 OFFSET 100000` forces the database to scan and discard 100,000 rows. For deep pagination, use a keyset (`WHERE id > :last_seen_id ORDER BY id LIMIT 20`) instead.
8. **Verify every index change empirically**: an index that isn't used is pure write overhead. After adding one, re-run `EXPLAIN ANALYZE` and confirm the planner actually picked it up and that timing improved — don't assume from the DDL alone.

---

### Running Automations
For queries running on BigQuery specifically (partitioning/clustering, JOIN ordering, shuffle mechanics, skewed JOINs), switch to the `bigquery-query-optimization` skill — its `lint_sql_query.py` script also works against files using standard SQL syntax, but its optimization rules are BigQuery-specific and won't all apply here.
