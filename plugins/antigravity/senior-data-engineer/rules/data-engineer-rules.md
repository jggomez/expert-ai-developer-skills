---
trigger: always_on
description: Google Cloud data engineering rules enforcing Lakehouse Graph Engineering DAG, 3-Tier Data Engineering SDLC, LLM Wiki Memory continuity, parallel Silver/Gold mart & SQL audit fan-out, BigQuery partition/clustering, data safety, and CDC/SCD modeling.
---

# Google Cloud Data Engineering Rules & Graph Protocol

**Identifier**: `data-engineer-rules`

## 1. The Lakehouse Graph Engineering DAG

Every analytical, CDC, or streaming pipeline must transition through this explicit 7-state Directed Acyclic Graph (DAG):

```
[INIT / USER REQUEST]
         │
         ▼
[STATE 0: MEMORY RESTORE, BRANCH GOVERNANCE & LAKEHOUSE TRIAGE GATE (MANDATORY)]
  ├── 1. Check Git Branch: If base (main/master/develop/dev), auto-create 'feat/<slug>'; if Scope Drift, ask user
  ├── 2. Derive `<feature-name>` slug & ensure `docs/<feature-name>/` directory is created
  ├── 3. Read `context/memory/MEMORY.md` silently (+ `architecture.md` on demand for BQ layouts/keys/SLAs)
  └── 4. Author/Update `PLAN.md` with 3-Tier Data Engineering SDLC Triage & Parallel Tracks
         │
         ├───► [TIER 1: FAST-TRACK (Single query / typo / DTS config / param adjust < 2 files)]
         │        ├── Skip discovery & Skip interactive alignment modal (70-85% token & latency savings)
         │        ├── Fast execution: 1 implementer / direct edit
         │        └── Scoped test runner / validation -> [STATE 6]
         │
         ├───► [TIER 2: STANDARD (New Silver/Gold mart / Dataform .sqlx / ETL/ELT / schema change)]
         │        ├── STATE 1: Selective discovery in docs/<feature-name>/ (data-contracts.md, pipeline-lineage.md)
         │        ├── STATE 1.5: INTERACTIVE USER ALIGNMENT GATE (ask_question modal sign-off)
         │        ├── STATE 2, 3 & 4: PARALLEL PIPELINE BUILD & QUALITY GATES:
         │        │     ├── Track Build (Mode A: Disjoint Files): Independent Silver/Gold .sqlx marts
         │        │     ├── Track QA: `dataform compile` + assertions in docs/<feature-name>/data-test-matrix.md
         │        │     └── Track Audit: Parallel `sql-query-optimizer` review
         │        └── STATE 5: Governance & Cost Audit -> [STATE 6]
         │
         └───► [TIER 3: MISSION-CRITICAL / COMPLEX (Full CDC/SCD-2 architecture / Composer DAG / major restructure)]
                  ├── STATE 1: Full discovery in docs/<feature-name>/ (data-contracts.md, pipeline-lineage.md, adrs)
                  ├── STATE 1.5: INTERACTIVE USER ALIGNMENT GATE (ask_question modal sign-off)
                  ├── STATE 2, 3 & 4: BUILD & DATA CHALLENGER / COST AUDITOR GATES:
                  │     ├── Parallel mart build under Mode A or Mode B (Git Worktree Isolation)
                  │     ├── Dataform compilation + full pyramid assertions in docs/<feature-name>/data-test-matrix.md
                  │     ├── Data Challenger checks: null injection, schema drift, idempotency, duplicate records
                  │     └── Cost Auditor checks: BigQuery dry-run slot costs & byte scan upper bounds
                  └── STATE 5: Enterprise Governance Audit (IAM, CMEK, VPC-SC, column masking) -> [STATE 6]
         │
         ▼
[STATE 6: SHIP & LLM WIKI MEMORY UPDATE (MANDATORY)]
  ├── 1. Finalize Cloud Composer / Airflow DAG & mark tasks complete in `PLAN.md`
  └── 2. Persist Bronze/Silver/Gold table contracts, partition/cluster keys, and SLA decisions into `context/memory/`
```

## 2. 3-Tier Data Engineering SDLC Specification

At State 0, the engineer must classify the task into one of three execution tiers and document the triage in `PLAN.md`:

| Dimension / Phase | Tier 1: Fast-Track (Low Complexity) | Tier 2: Standard (Medium Complexity) | Tier 3: Mission-Critical (Complex) |
| :--- | :--- | :--- | :--- |
| **Scope & Triggers** | Single query/typo, minor DTS transfer config, parameter adjust (< 2 files affected). Architecture and schemas already established. | New Silver/Gold mart, Dataform `.sqlx` model, ETL/ELT transformation, schema change (2–4 files/models). | Full Lakehouse CDC/SCD-2 architecture, major dataset restructure, production Cloud Composer/Airflow DAG release. |
| **Discovery (State 1)** | **SKIPPED**: Zero discovery overhead; no `data-contracts.md` or `pipeline-lineage.md` authored. | **SELECTIVE**: Target data contracts and lineage in `docs/<feature-name>/data-contracts.md` and `pipeline-lineage.md`. | **FULL**: Comprehensive discovery: `docs/<feature-name>/data-contracts.md`, `pipeline-lineage.md`, and `architecture.md` / `adr-*.md`. |
| **Interactive Alignment (State 1.5)** | **SKIPPED**: Auto-proceeds directly to implementation. | **MANDATORY**: Interactive modal (`ask_question`) presenting data contracts and schema changes for user sign-off. | **MANDATORY**: Strict interactive modal (`ask_question`) requiring explicit user sign-off on architecture and SLA terms. |
| **Build Mode (State 2)** | 1 implementer / direct surgical edit under Mode A (Disjoint Files). | Parallel Silver/Gold mart build under Mode A (Disjoint Files). | Parallel mart build under Mode A or Mode B (Git Worktree Isolation). |
| **QA Verification (State 3 & 4)** | Scoped validation (syntax check / single query dry-run). | Full Dataform compilation (`dataform compile` exit code 0) + automated QA assertions in `docs/<feature-name>/data-test-matrix.md`. | Full Dataform compilation + QA assertions + **Data Challenger & Cost Auditor**: null injection, schema drift, idempotency, byte scan ceiling. |
| **Token & Latency Impact** | **70–85% token & latency savings**. | Balanced overhead with rigorous schema verification. | Maximum depth, empirical verification, and zero regression tolerance. |

## 3. Inviolable Role Boundaries, Git Branch Governance & Data Safety

- **Git Branch Governance & Auto-Branching**: Never write data pipeline code or commit directly to protected base branches (`main`, `master`, `develop`, `dev`). At State 0, before authoring tasks or modifying pipeline files, inspect the active branch via `git symbolic-ref --short HEAD`. If on a base branch, automatically provision and switch to a dedicated feature branch using Conventional naming (`git checkout -b feat/<descriptive-slug>` or `fix/<slug>`) and notify the user.
- **Proactive Scope Drift Detection**: When already on an existing feature branch and the user requests orthogonal or unrelated data engineering functionality, detect the domain pivot and proactively prompt the user via `ask_question` recommending a dedicated branch (`feat/<new-slug>`). If confirmed, switch branches; if declined, proceed on the current branch.
- **State 0 — Memory Restore & Plan First**:
  1. Silently read `context/memory/MEMORY.md` (and `context/memory/architecture.md` on demand) to reuse known BigQuery dataset layouts, partition/clustering keys, and SLAs without redundant schema scans.
  2. Never write BigQuery DDL or Dataform `.sqlx` models without `PLAN.md` documenting source schemas, ingestion latency SLAs, and schema contracts.
- **State 1.5 — Interactive User Alignment Gate**:
  - For Tier 2 and Tier 3 tasks, the engineer MUST pause before writing pipeline code and query the user using `ask_question` modal presenting proposed contracts, lineage, and partitioning strategies for explicit approval.
- **State 3 & 4 — Parallel Mart Build & Quality Assertions**:
  - Build independent Silver and Gold `.sqlx` marts in parallel using **Mode A: Disjoint File Partitioning** (strictly non-overlapping `.sqlx` file ownership).
  - Enforce **Scoped Test Execution Isolation**: During inner development loops, execute compilation or assertions ONLY for the assigned model (`dataform compile --actions <action-name>`), never running full pipeline builds until final integration verification.
  - Run `sql-query-optimizer` in parallel with Dataform quality assertions (`dataform compile` + row-count/uniqueness/non-null assertions documented in `docs/<feature-name>/data-test-matrix.md`).
- **Destructive Operation Ban**: Never execute destructive SQL (`DROP TABLE`, `DROP SCHEMA`, `DROP DATABASE`, `TRUNCATE TABLE`, unpartitioned `DELETE FROM ... WHERE 1=1`) or destructive CLI commands (`bq rm -f`, `gsutil rm -r`, `gcloud storage rm --recursive`) without explicit user permission.
- **Mandatory Partitioning & Clustering**: Every BigQuery production table must specify:
  1. Partitioning (ingestion time, timestamp/date column, or integer range) with `require_partition_filter = true` on large tables.
  2. Clustering (up to 4 high-cardinality filter/join columns).
- **State 6 — LLM Wiki Memory Persistence (`context/memory/`)**:
  - Upon milestone completion, update `context/memory/MEMORY.md` in-place (<= 80-100 lines), update `context/memory/architecture.md` with new/modified Bronze/Silver/Gold table contracts, partition/cluster keys, and SLA decisions, and append a 5-8 line milestone entry to `context/memory/log/YYYY-MM-DD.md`.

## 4. SCD & Dimension Modeling Standards

- For historical dimension tracking, default to **SCD Type 2** (`valid_from`, `valid_to`, `is_current`).
- Generate deterministic surrogate keys using cryptographic hashes (`SHA256` or `FARM_FINGERPRINT` over natural keys and effective timestamps).
- Ensure primary key uniqueness, deduplication, and idempotency on all merge and upsert operations.
- Handle late-arriving and out-of-order events using event timestamps (`_metadata_timestamp`) rather than pipeline ingestion timestamps.
