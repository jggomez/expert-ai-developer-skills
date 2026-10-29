---
name: gcp-data-engineering
description: Guides architecture decisions for data pipelines on Google Cloud — lake/warehouse/lakehouse design, batch vs. streaming, orchestration tool selection (Dataform, Cloud Composer/Airflow, Dataflow/Beam), and BigQuery cost/performance tuning (partitioning, clustering, slots). Use when designing a new pipeline, choosing a GCP data service, or optimizing BigQuery cost/performance.
---

# GCP Data Engineering Skill

## Overview
Guides architectural decisions for data pipelines, Medallion lakehouses, and analytical storage on Google Cloud Platform (GCP). Balances data volume, SLA freshness, operational simplicity, and cloud cost—prioritizing warehouse-native ELT (Dataform, BigQuery) over custom streaming (Dataflow/Beam) unless sub-minute SLAs apply, while enforcing capability-gated artifacts and fail-honest CLI verification.

## When to Use
### Trigger Scenarios
- Designing GCP lakehouse platforms (Cloud Storage, BigQuery, Datastream, Pub/Sub, Dataform, Composer).
- Selecting batch vs. log-based CDC vs. streaming ingestion and Dataform vs. Composer vs. Dataflow orchestration.
- Designing BigQuery partitioning, clustering, and Medallion layers (`Bronze` → `Silver` → `Gold`).

### When NOT to Use
- **CDC & SCD Type 2 merge patterns**: Route to `cdc-scd-patterns`.
- **Slow/expensive BigQuery SQL plan tuning**: Route to `bigquery-query-optimization`.
- **Single-node RDBMS SQL tuning**: Route to `sql-query-optimization`.
- **Application backend code**: Route to `python-expert`.

## Process
### Phase 1: Capability-Gated Planning & Target `AGENTS.md`
1. Maintain root `AGENTS.md` (`<= 90 lines`) linking `dataform`/`bq` commands and `context/memory/MEMORY.md`.
2. Author `PLAN.md` (`<= 50 lines`) gating artifacts individually:
   - `docs/<feature-name>/data-contracts.md` (`<= 60 lines`): **ONLY IF** new/modified schemas or SLAs are introduced; **SKIP** if schemas exist.
   - `docs/<feature-name>/pipeline-lineage.md` (`<= 45 lines`): **ONLY IF** multi-layer Bronze/Silver/Gold flows change; **SKIP** for single-mart edits.
   - Delegate `sql-query-optimizer` **ONLY IF** large partitioned scans or multi-table JOIN/window shuffle risks exist; invoke Tier 3 `Data Challenger` **ONLY IF** CDC/SCD-2 merges, late-arriving dedup, or destructive/backfill logic changes.

### Phase 2: Medallion Storage, Ingestion & Orchestration
1. **Storage Layers**: GCS immutable raw landing zone + BigQuery Medallion tables: `Bronze` (append-only raw/CDC), `Silver` (deduplicated, typed, SCD-2), `Gold` (BI star marts).
2. **Ingestion (Default Batch)**: Scheduled loads (GCS/Dataform/Composer); **Datastream** for operational DB CDC; **Pub/Sub → BigQuery** (or **Dataflow** only when windowed stream joins/non-SQL code are required).
3. **Orchestration**: **Dataform** for warehouse-native SQLX & assertions; **Cloud Composer** only for cross-service DAGs.

### Phase 3: BigQuery Cost Governance & Fail-Honest Verification
1. **Partition & Cluster**: Partition by date/timestamp or ingestion time (`require_partition_filter = true` on large tables); cluster up to 4 selective filter/join columns; prune columns (never `SELECT *`).
2. **Fail-Honest CLI Gate**: Run `dataform compile` and `bq query --dry_run`. If CLI binaries or GCP ADC credentials fail/missing, **STOP** and report `BLOCKED: Not executed — <exact CLI error>`—never fabricate byte counts or compile success.
3. **Standardized Test Matrix (`docs/<feature-name>/data-test-matrix.md <= 75 lines`)**: Record IEEE/ISTQB test cases (`TC-01`...) with `ID`, `Ref`, `Level`, `Objective`, `Steps`, `Expected Result`, `Assertion / Query`, and `Status`.

## Usage
```bash
# Estimate scanned bytes via BigQuery dry-run
bq query --use_legacy_sql=false --dry_run "SELECT id, created_at FROM \`my_project.analytics.events\` WHERE event_date = '2026-09-01'"

# Compile Dataform dependency graph (scoped or full)
dataform compile --actions silver_orders
dataform compile
```
- **Host Execution**: Run `bq` and `dataform` via shell (`Bash` in Claude Code; `Bash` in Antigravity) and persist contracts/SLAs to `context/memory/MEMORY.md`.

## Red Flags
- Fabricating `bq query --dry_run` byte counts or pretending `dataform compile` ran when CLI/ADC credentials fail instead of reporting `BLOCKED: Not executed — <exact CLI error>`.
- Using Dataflow/Kafka when batch/Datastream meets SLAs, or Composer for SQL-only transforms Dataform handles natively.
- Querying `SELECT *` or raw CDC tables without partition filters or a Silver deduplication layer.

## Verification
- [ ] Root `AGENTS.md` (`<= 90 lines`), `PLAN.md` (`<= 50 lines`), and capability-gated `docs/<feature-name>/` artifacts respect line caps.
- [ ] Tables define explicit partitioning (`require_partition_filter = true`) and clustering keys across `Bronze`/`Silver`/`Gold`.
- [ ] `dataform compile` and `bq query --dry_run` exit `0`, OR execution halts honestly with `BLOCKED: Not executed — <exact CLI error>`.
- [ ] `docs/<feature-name>/data-test-matrix.md` (`<= 75 lines`) documents `TC-01`... with `ID`, `Ref`, `Level`, `Objective`, `Steps`, `Expected Result`, `Assertion / Query`, and `Status`.

## References
- [GCP Data Stack Reference](references/gcp-data-stack.md)
