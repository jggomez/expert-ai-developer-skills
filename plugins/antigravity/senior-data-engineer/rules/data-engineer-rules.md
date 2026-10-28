---
trigger: always_on
description: Google Cloud data engineering rules enforcing Lakehouse Graph Engineering DAG, LLM Wiki Memory continuity, parallel Silver/Gold mart & SQL audit fan-out, BigQuery partition/clustering, data safety, and CDC/SCD modeling.
---

# Google Cloud Data Engineering Rules & Graph Protocol

**Identifier**: `data-engineer-rules`

## 1. The Lakehouse Graph Engineering DAG

Every analytical, CDC, or streaming pipeline must transition through this explicit 7-state DAG:

```
[STATE 0: MEMORY RESTORE, BRANCH GOVERNANCE & LAKEHOUSE TRIAGE GATE (MANDATORY)]
  ├── Check Git Branch: If base (main/master/develop/dev), auto-create 'feat/<slug>'; if Scope Drift, ask user
  ├── Read `context/memory/MEMORY.md` silently (+ `architecture.md` on demand for BQ layouts/keys/SLAs)
  └── Author/Update `PLAN.md` (Sources, Target Contracts, Partition/Cluster Keys, SLAs)
          │
          ▼
[STATE 1: SOURCE DISCOVERY & SLA ANALYSIS (Datastream CDC / Batch / Streaming)]
          │
          ▼
[STATE 2: LAKEHOUSE ARCHITECTURE (Bronze / Silver / Gold & SCD Type 1/2)]
          │
          ▼
[STATE 3 & 4: PARALLEL PIPELINE BUILD & SQL AUDIT FAN-OUT]
  ├── Track Build (Mode A Disjoint Files): Independent Silver/Gold `.sqlx` marts & BigQuery DDL
  ├── Track QA:    `dataform compile`, Quality Assertions, Schema Invariants, Idempotency (exit 0)
  └── Track Audit: `sql-query-optimizer` (parallel SQL plan & slot tuning)
          │
          ▼
[STATE 5: GOVERNANCE & COST AUDIT (IAM, CMEK, VPC-SC, Partition/Cluster Pruning, Dry-Run Bytes)]
          │
          ▼
[STATE 6: SHIP & LLM WIKI MEMORY UPDATE (MANDATORY)]
  ├── Composer / Airflow DAG Release & Finalize `PLAN.md`
  └── Persist Bronze/Silver/Gold contracts, partition/cluster keys & SLAs to `context/memory/`
```

## 2. Inviolable Role Boundaries, Git Branch Governance, Memory & Parallel Execution

- **Git Branch Governance & Auto-Branching**: Never write data pipeline code or commit directly to protected base branches (`main`, `master`, `develop`, `dev`). At State 0, before authoring tasks or modifying pipeline code, inspect the active branch via `git symbolic-ref --short HEAD`. If on a base branch, automatically provision and switch to a dedicated feature branch using Conventional naming (`git checkout -b feat/<descriptive-slug>` or `fix/<slug>`) and notify the user.
- **Proactive Scope Drift Detection**: When already on an existing feature branch and the user requests orthogonal or unrelated data engineering functionality, detect the domain pivot and proactively prompt the user via `ask_question` recommending a dedicated branch (`feat/<new-slug>`). If the user confirms, switch branches; if declined, proceed on the current branch.
- **State 0 — Memory Restore & Plan First**:
  1. Silently read `context/memory/MEMORY.md` (and `context/memory/architecture.md` on demand) to reuse known BigQuery dataset layouts, partition/clustering keys, and SLAs without redundant schema scans.
  2. Never write BigQuery DDL or Dataform `.sqlx` models without `PLAN.md` documenting source schemas, ingestion latency SLAs, and schema contracts.
- **State 3 & 4 — Parallel Mart Build & SQL Audit Fan-Out**:
  - Build independent Silver and Gold `.sqlx` marts in parallel using **Mode A: Disjoint File Partitioning** (non-overlapping `.sqlx` file ownership).
  - Run `sql-query-optimizer` in parallel with Dataform quality assertions (`dataform compile` + row/uniqueness/non-null assertions).
- **Destructive Operation Ban**: Never execute `DROP TABLE`, `DROP SCHEMA`, or unpartitioned `DELETE FROM ... WHERE 1=1` without explicit user permission.
- **Mandatory Partitioning & Clustering**: Every BigQuery table must specify:
  1. Partitioning (ingestion time, timestamp/date column, or integer range) with `require_partition_filter = true` on large tables.
  2. Clustering (up to 4 high-cardinality filter/join columns).
- **State 6 — LLM Wiki Memory Persistence (`context/memory/`)**:
  - Upon milestone completion, update `context/memory/MEMORY.md` in-place (<= 80-100 lines), update `context/memory/architecture.md` with new/modified Bronze/Silver/Gold table contracts, partition/cluster keys, and SLA decisions, and append a 5-8 line milestone entry to `context/memory/log/YYYY-MM-DD.md`.

## 3. SCD & Dimension Modeling Standards

- For historical dimension tracking, default to **SCD Type 2** (`valid_from`, `valid_to`, `is_current`).
- Ensure primary key uniqueness and idempotency on all merge and upsert operations.
