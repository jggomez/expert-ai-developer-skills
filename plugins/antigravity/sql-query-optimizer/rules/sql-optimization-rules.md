---
trigger: always_on
description: SQL optimization engineering rules enforcing grounded execution plan diagnosis, BigQuery dry-runs, partition pruning, and structured query rewrites.
---

# SQL Optimization Rules & Performance Protocol

**Identifier**: `sql-optimization-rules`

## 1. The Optimization Execution DAG

Every SQL tuning task must transition through this explicit sequence:

```
[PLAN & DIALECT DETECTION (Postgres, BigQuery, MySQL)]
          │
          ▼
[DIAGNOSE FROM LIVE PLAN (EXPLAIN ANALYZE or BigQuery Dry-Run / Timeline)]
          │
          ▼
[REWRITE & REFACTOR (Prune Partitions, Eliminate Unnecessary Joins/CTEs)]
          │
          ▼
[VALIDATE EQUIVALENCE (Verify output schema and row parity)]
          │
          ▼
[DELIVERY IN STRUCTURED FORMAT (Original, Optimized, Rationale)]
```

## 2. Inviolable Safety & Verification Boundaries

- **Dry-Run Mandatory for BigQuery**: Never run live analytical queries on BigQuery without performing a `--dry_run` first to assess bytes scanned.
- **Read-Only Invariant**: The optimizer is strictly forbidden from executing destructive DDL or DML (`DROP`, `TRUNCATE`, bulk `DELETE`). Optimization modifies query text, not database schema.
- **Grounding Invariant**: Never guess bottlenecks. Diagnose using actual execution plans, shuffle stages, skew metrics, or explain trees.

## 3. Mandatory Structured Output

Every rewritten query MUST be presented in this 3-part format:
1. **Original Query**: The existing baseline SQL.
2. **Optimized Query**: The rewritten, performant SQL.
3. **Engine-Grounded Rationale**: Exactly which plan stage, partition filter, or join order improved performance.
