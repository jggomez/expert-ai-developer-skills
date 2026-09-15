---
name: bigquery-query-optimization
description: Diagnoses and rewrites slow BigQuery SQL using the query plan (stages, shuffle, workers) — partitioning/clustering pruning, JOIN ordering and broadcast vs. shuffle joins, skewed JOINs, WHERE clause selectivity, and approximate/SQL-vs-JS function choices. Use when a BigQuery query is slow, expensive, or hitting Resources Exceeded, or when reviewing a query plan.
---

# BigQuery Query Optimization Skill

## Overview
This skill diagnoses and optimizes slow, expensive, or resource-constrained Google Cloud BigQuery SQL queries. It acts as a BigQuery Performance Specialist operating under the core principle: **less work → faster query**. It focuses on reducing I/O (bytes read), shuffle (data transfer across stages), sorting/grouping overhead, and slot CPU consumption by analyzing execution stages, worker distributions, and pruning mechanics rather than guessing from SQL text alone.

## When to Use
### Trigger Scenarios
- BigQuery queries that run slowly, consume excessive slot time, or hit `Resources Exceeded` errors.
- Diagnosing execution stage statistics, shuffle bottlenecks, and data skew across workers.
- Optimizing table scans via partition pruning, clustering alignment, and column selection.
- Statically scanning SQL files and embedded application queries for BigQuery anti-patterns.

### When NOT to Use
- **Traditional relational databases (PostgreSQL, MySQL, SQL Server)**: Route to `sql-query-optimization`.
- **High-level GCP lakehouse and storage design**: Route to `gcp-data-engineering`.
- **CDC and dimensional SCD Type 2 modeling**: Route to `cdc-scd-patterns`.

## Process
### Phase 1: Diagnosing the Execution Plan
Inspect stage-level execution statistics via BigQuery UI or `INFORMATION_SCHEMA.JOBS`:
1. **Significant gap between average and max worker compute time**: Indicates data skew. Confirm skew with `APPROX_TOP_COUNT` on the suspect key and pre-filter or split queries.
2. **High wait/read time in intermediate stages**: Indicates excessive data passing through stages. Push filters earlier to reduce shuffle volume.
3. **High CPU time relative to I/O**: Check for expensive JavaScript UDFs, unneeded regex evaluation, or exact `COUNT(DISTINCT)` on massive cardinalities.

### Phase 2: Query Optimization Rules
1. **Column Pruning**: Replace `SELECT *` with explicit columns or `SELECT * EXCEPT(...)`.
2. **Partition & Cluster Pruning**: Filter on the partitioned date/timestamp and order `WHERE`/`JOIN` conditions to match clustered columns.
3. **Nested & Repeated Fields**: Model one-to-many relationships as `ARRAY<STRUCT>` instead of flat tables requiring expensive `GROUP BY` operations.
4. **JOIN Ordering (BigQuery-Specific)**: Place the **largest table first** in the `FROM` clause, followed by decreasing table sizes (allowing BigQuery to broadcast the smaller tables to worker slots).
5. **Filter Before JOINs**: Push filters into explicit subqueries before joining; do not rely solely on optimizer pushdown.
6. **ORDER BY with LIMIT**: Unbounded `ORDER BY` serializes data onto a single worker node and causes `Resources Exceeded`. Always supply a `LIMIT`.
7. **Approximate Aggregations**: Use `APPROX_COUNT_DISTINCT(col)` instead of `COUNT(DISTINCT col)` when ~1% error margin is acceptable.
8. **Native SQL UDFs**: Avoid JavaScript UDFs (which instantiate V8 subprocesses per call) in favor of native SQL UDFs.

### Phase 3: Automated Static Anti-Pattern Linting
Scan project SQL files or embedded SQL strings in application code (`.py`, `.js`, `.ts`, `.java`, `.go`):
```bash
python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py [optional_path]
```

## Usage
### Commands & Automation Scripts
```bash
# Scan whole repository or specific SQL directory for BigQuery anti-patterns
python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py .
python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py queries/

# Dry run a rewritten query to verify byte reduction
bq query --use_legacy_sql=false --dry_run < optimized_query.sql
```

### Example Prompts
- *"This BigQuery query is throwing 'Resources Exceeded' during a large JOIN — diagnose the query plan and rewrite it."*
- *"Scan our repository for SQL anti-patterns like SELECT * or ORDER BY without LIMIT."*
- *"Rewrite this JavaScript UDF as a native BigQuery SQL function to reduce slot time."*

### Host Execution Instructions
- **Claude Code**: Run `lint_sql_query.py` in the workspace shell and execute dry-run estimations with `bq`.
- **Antigravity**: Analyze queries using `lint_sql_query.py` and inspect query execution jobs via GCP tools.

## Red Flags
- Putting small tables first in `FROM` clauses (violates BigQuery broadcast join optimization).
- Executing unbounded `ORDER BY` queries on multi-million row datasets.
- Querying partition-enabled tables without a filter on the partition column in `WHERE`.
- Using `REGEXP_CONTAINS` when a simple `LIKE` wildcard search is sufficient.
- Recomputing expensive, repetitive aggregations instead of leveraging Materialized Views.

## Verification
- [ ] Automated SQL linter reports zero high-severity anti-patterns:
  ```bash
  python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py .
  ```
- [ ] BigQuery dry-run demonstrates measurable byte reduction compared to original query.
- [ ] No unbounded `ORDER BY` queries without `LIMIT`.
- [ ] Largest table appears first in multi-table `JOIN` statements.

## References
For before/after SQL query pairs and execution plan blueprints:
- [BigQuery Optimization Patterns Reference](references/bigquery-optimization-patterns.md)

