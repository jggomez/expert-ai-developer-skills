---
name: bigquery-query-optimization
description: Diagnoses and rewrites slow BigQuery SQL using the query plan (stages, shuffle, workers) — partitioning/clustering pruning, JOIN ordering and broadcast vs. shuffle joins, skewed JOINs, WHERE clause selectivity, and approximate/SQL-vs-JS function choices. Use when a BigQuery query is slow, expensive, or hitting Resources Exceeded, or when reviewing a query plan.
---

### Role & Mindset
You are a **BigQuery Performance Specialist**. Every optimization reduces to one idea: **less work → faster query**. "Work" means I/O (bytes read), shuffle (bytes passed between stages), grouping (bytes per group), materialization (bytes written), and CPU (UDFs, functions). Diagnose from the query plan before rewriting — don't guess.

---

### Diagnosing the Query Plan

Look at stage-level stats first:
- **Significant gap between avg and max worker time?** → data skew. Confirm with `APPROX_TOP_COUNT` on the suspected key; work around by filtering earlier.
- **Most time in reading from intermediate stages?** → filter earlier in the query so less data reaches later stages.
- **Most time in CPU/compute?** → check for JS UDFs, unnecessary `REGEXP_CONTAINS`, or `COUNT(DISTINCT ...)` that could be approximate.

---

### Optimization Rules (Original → Optimized → Why)

1. **Columns**: `SELECT *` → `SELECT * EXCEPT (unneeded_cols)` or explicit columns. `SELECT *` is cost-inefficient, especially in inner queries/subqueries.
2. **Partitioning & clustering**: filter on the partition column and order `WHERE`/`JOIN` filters to hit clustered columns — this is auto-pruning, and the difference is not incremental (a real example in the source deck: 180 GB → 16 MB processed for the same logical query, just by adding clustering).
3. **Nested/repeated fields**: model one-to-many relationships (e.g. an order and its line items) as a nested repeated field instead of a flat table requiring `GROUP BY` to reconstruct the parent entity.
4. **Late aggregation**: aggregate as late and as seldom as possible — aggregation is costly. **Exception**: if pre-aggregating drastically shrinks a table before a JOIN, aggregate early — but only when both sides of the JOIN are already at the same grain (one row per join-key value); otherwise the JOIN result changes.
5. **JOIN table order**: place the **largest table first**, then decreasing size — this is BigQuery-specific (its optimizer can reorder in some cases, but don't rely on it) and is the opposite of small-table-first folklore from other engines.
6. **Filter before JOINs**: push `WHERE` conditions onto both sides of a JOIN explicitly — BigQuery does not always push filters down automatically. Check the query plan; if filtering isn't happening as early as possible, rewrite with an explicit subquery filter.
7. **Broadcast vs. shuffle JOIN**: a small table JOINed to a large one is broadcast to every worker (cheap). Two large tables force a shuffle/hash JOIN (expensive) — keep this in mind when deciding whether a table needs pre-filtering/pre-aggregating before the JOIN.
8. **Clustered-table JOIN pruning**: if the left table is clustered on the JOIN key and the right-side subquery result is small enough to broadcast, BigQuery uses the right side's key range to prune the left table before joining — a large win, but it requires both conditions (clustered left table + broadcastable right side).
9. **JOIN explosions**: a JOIN with a non-unique key on both sides produces a cartesian product per matching key — output rows can reach `len(left) * len(right)` in the worst case. Diagnose by printing row counts per JOIN key on each side; fix with `GROUP BY` pre-aggregation if the semantics allow it.
10. **Skewed JOINs**: caused by an unbalanced JOIN key sending too much data to one worker. Confirm via the query plan (one worker's compute time far exceeds the average). Workarounds: pre-filter the rows with the unbalanced key, or split into two queries (one for the skewed key, one for the rest) and `UNION ALL` the results.
11. **WHERE clause expression order**: BigQuery does not reorder your `WHERE` expressions — put the most selective condition first (e.g. an equality filter before a `LIKE '%...%'` scan), so the expensive expression runs on less data.
12. **ORDER BY without LIMIT**: final sorting happens on a single slot — a large unbounded `ORDER BY` can throw Resources Exceeded. Always pair a large `ORDER BY` with a `LIMIT`; with a `LIMIT`, intermediate workers can drop values beyond it early instead of shipping everything to one node.
13. **String matching**: prefer `LIKE '%x%'` over `REGEXP_CONTAINS(col, '.*x.*')` when you don't need regex's full power — `REGEXP_CONTAINS` is slower for simple wildcard matching.
14. **Approximate aggregates**: `APPROX_COUNT_DISTINCT(x)` instead of `COUNT(DISTINCT x)` when ~1% error is acceptable — meaningfully faster on large cardinalities.
15. **UDFs**: prefer SQL UDFs over JavaScript UDFs (JS spins up a V8 subprocess per call — substantially slower). For logic reused across queries/views, create a **persistent** UDF in a shared dataset instead of a `CREATE TEMP FUNCTION` per query.
16. **Query cache**: results are cached per-user, keyed by a hash of (data modification times, tables used, query string). Cache is skipped if referenced tables changed, a non-deterministic function is used (e.g. `NOW()`), a permanent destination table is requested, or source tables have a streaming buffer.

---

### Reference Manual
For the full before/after SQL snippets behind each rule above (exact BigQuery syntax), see:
[BigQuery Optimization Patterns Reference](references/bigquery-optimization-patterns.md)

### Running Automations
Statically scan a directory (or a single file) for the anti-patterns above (rules 1, 11-15) without needing a live BigQuery connection. Give it a project directory and it recursively checks every `.sql` file **and** SQL embedded as string literals in application code (`.py`, `.js`, `.ts`, `.java`, `.go`, `.rb`, `.scala`):
```bash
python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py [path]   # defaults to "."
```
For the JOIN/skew/partitioning diagnoses (rules 2, 5-10, 16), you need the actual query plan — use the connected `bigquery` MCP tools (dry-run, `INFORMATION_SCHEMA.JOBS`) rather than guessing from the SQL text alone.
