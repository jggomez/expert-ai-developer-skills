---
trigger: always_on
description: Google Cloud data engineering rules enforcing Lakehouse DAG, 3-Tier SDLC, Capability-Gated Dispatch, Target AGENTS.md, LLM Wiki Memory, IEEE/ISTQB data-test-matrix.md, and Fail-Honest verification.
---

# Google Cloud Data Engineering Rules & Graph Protocol

**Identifier**: `data-engineer-rules`

## 1. Lakehouse DAG & 3-Tier Data Engineering SDLC
Classify every task at State 0 in `PLAN.md` (`<= 50 lines`) and maintain root `AGENTS.md` (`<= 90 lines` linking `dataform`/`bq` commands & `context/memory/MEMORY.md`):

| Phase | Tier 1: Fast-Track | Tier 2: Standard | Tier 3: Mission-Critical |
| :--- | :--- | :--- | :--- |
| **Scope** | Single query/typo, minor DTS config, param tweak (`< 2` files; existing schema). | New Silver/Gold mart, Dataform `.sqlx`, ETL/ELT, schema change (`2–4` files). | Full CDC/SCD-2 architecture, dataset restructure, backfill, Composer/Airflow DAG. |
| **State 1 & 1.5** | **SKIPPED** (70–85% token/latency savings). | **Capability-Gated** `docs/<feature-name>/` + mandatory `ask_question` modal. | **Capability-Gated** contracts/lineage/ADRs + strict `ask_question` sign-off. |
| **Build & QA** | 1 Mode A edit + scoped syntax/dry-run check. | Parallel Mode A `.sqlx` build + `dataform compile` (`exit 0`) + `data-test-matrix.md` (`<= 75 lines`). | Mode A/B (`Git Worktree`) build + `data-test-matrix.md` + gated **Data Challenger** & IAM/CMEK/Cost audit. |

## 2. Capability-Gated Dispatch (`Invoke / SKIP`)
Evaluate each artifact and specialist individually in State 0 `PLAN.md`—never over-invoke:
- **`docs/<feature-name>/data-contracts.md` (`<= 60 lines`)**: **INVOKE ONLY IF** new/modified table schemas or SLAs are introduced; **SKIP** if schemas already exist.
- **`docs/<feature-name>/pipeline-lineage.md` (`<= 45 lines`)**: **INVOKE ONLY IF** multi-layer Bronze/Silver/Gold flows change; **SKIP** for single-mart edits.
- **`sql-query-optimizer`**: Delegate **ONLY IF** queries scan large partitioned tables or introduce multi-table JOIN/window shuffle risks; **SKIP** on trivial DDL/configs.
- **`Data Challenger` (Tier 3)**: **INVOKE ONLY IF** CDC/SCD-2 merges, late-arriving deduplication, or destructive/backfill logic is modified.

## 3. Governance, Fail-Honest Verification & Modeling Standards
- **Git Branch Governance & Scope Drift**: Never work or commit on protected branches (`main`, `master`, `develop`, `dev`). Inspect `git symbolic-ref --short HEAD` and auto-create `feat/<descriptive-slug>` (or `fix/<slug>`). On active feature branches, detect orthogonal requests (**Scope Drift**) and prompt via `ask_question` recommending `feat/<new-slug>`.
- **Memory Restore & Capture**: Silently read `context/memory/MEMORY.md` (+ `architecture.md` on demand) at State 0. At State 6, persist table contracts, partition/cluster keys, and SLAs into `context/memory/MEMORY.md` (`<= 80-100 lines`), `architecture.md`, and `context/memory/log/YYYY-MM-DD.md` (`5-8 lines`), and sync root `AGENTS.md` (`<= 90 lines`).
- **Scoped Inner-Loop Isolation**: Parallel Mode A builders compile/test ONLY their assigned action (`dataform compile --actions <action>`) during inner loops before full State 3 verification.
- **Standardized `docs/<feature-name>/data-test-matrix.md` (`<= 75 lines`)**: Use IEEE/ISTQB per-case rows (`TC-01`...) with explicit `ID`, `Ref`, `Level`, `Objective`, `Steps`, `Expected Result`, `Assertion / Query`, and `Status`.
- **Strict Fail-Honest Protocol (`BLOCKED`)**: If `dataform compile`, `bq query --dry_run`, or GCP ADC credentials are unavailable or failing, **STOP** and report `BLOCKED: Not executed — <exact CLI error>`. NEVER fabricate dry-run byte counts or pretend `dataform compile` ran!
- **Data Safety & Partitioning**: Never execute `DROP TABLE`, `DROP SCHEMA`, `DROP DATABASE`, `TRUNCATE TABLE`, unpartitioned `DELETE FROM ... WHERE 1=1`, `bq rm -f`, or `gcloud storage rm --recursive` without user consent. Require explicit partitioning (`require_partition_filter = true` on large tables) and clustering (up to 4 columns) on all production BigQuery tables.
- **SCD & CDC Modeling**: Default historical tracking to **SCD Type 2** (`valid_from`, `valid_to`, `is_current`) with deterministic hash surrogate keys (`SHA256` / `FARM_FINGERPRINT`), idempotent merges, and event-time ordering (`_metadata_timestamp`).
