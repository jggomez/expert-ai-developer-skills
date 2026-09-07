---
name: cdc-scd-patterns
description: Guides Change Data Capture (CDC) ingestion via Datastream and Slowly Changing Dimension (SCD) modeling in BigQuery/Dataform. Use when replicating an operational database, designing history-tracking dimension tables, or implementing SCD Type 1/2 merge logic.
---

# CDC & SCD Patterns Skill

## Overview
This skill guides the design and implementation of Change Data Capture (CDC) replication pipelines and Slowly Changing Dimension (SCD) modeling in Google Cloud BigQuery and Dataform. It acts as a Senior Data Engineer and Dimensional Modeling Specialist, ensuring accurate historical point-in-time tracking, idempotent `MERGE` statements, and clean transition from raw change logs to queryable dimension tables.

## When to Use
### Trigger Scenarios
- Replicating relational databases (Cloud SQL, AlloyDB, Oracle, Postgres) into BigQuery using Datastream.
- Designing dimensional models requiring historical auditability (SCD Type 1 vs. Type 2).
- Authoring Dataform `.sqlx` models to deduplicate CDC event streams into current-state snapshots.
- Generating automated SCD Type 2 merge SQL statements.

### When NOT to Use
- **High-level GCP cloud architecture and tool selection**: Route to `gcp-data-engineering`.
- **Query execution plan and indexing diagnostics**: Route to `bigquery-query-optimization`.
- **Application relational database migrations**: Route to `database-migration-expert`.

## Process
### Phase 1: Datastream CDC Ingestion & Bronze Landing
1. **Log-based CDC**: Datastream streams inserts, updates, and deletes from the database transaction log into BigQuery bronze tables without impacting source database CPU.
2. **Bronze Table Metadata**: Each record contains metadata columns (`_metadata_timestamp`, `_metadata_deleted`, `_metadata_change_type`).
3. **Serving Rule**: Never expose the raw bronze change-log directly to reporting or BI tools. Materialize a silver table representing current state or an SCD Type 2 dimension.

### Phase 2: Dimension Classification Matrix (SCD Types 0–6)
| Type | Behavior | Business Use Case |
| :--- | :--- | :--- |
| **Type 0** | Retain original value permanently. | Original signup timestamp, initial creation dates. |
| **Type 1** | Overwrite in place; no history preserved. | Typo corrections, attributes where history has zero analytical value. |
| **Type 2** | New row per change with `valid_from`, `valid_to`, `is_current`. | **Default choice**: Customer addresses, pricing tiers, account statuses. |
| **Type 3** | Add `previous_value` column. | Tracking only the immediately prior state alongside current. |
| **Type 4** | Separate current table and historical log table. | Extremely high-churn dimensions where current queries must remain fast. |
| **Type 6** | Hybrid: Type 2 versioning with a Type 1 current column. | Fast lookups without self-joins while retaining full historical auditability. |

### Phase 3: Type 2 Merge Implementation & Scaffolding
Scaffold the parameterized Dataform `.sqlx` model implementing atomic SCD Type 2 merge logic:
```bash
python3 ./skills/cdc-scd-patterns/scripts/scaffold_scd2_dataform.py <table_name> <key_column> <tracked_columns_comma_separated>
```
The script implements proper `MERGE ... WHEN MATCHED` logic, updates `valid_to` timestamps, and sets `is_current = FALSE` on superseded records in a single atomic transaction.

## Usage
### Commands & Automation Scripts
```bash
# Scaffold an SCD Type 2 Dataform model for a customer dimension
python3 ./skills/cdc-scd-patterns/scripts/scaffold_scd2_dataform.py dim_customer customer_id name,email,address,tier
```

### Example Prompts
- *"Design an SCD Type 2 dimension in Dataform for tracking customer address changes replicated via Datastream."*
- *"How should we handle soft deletes from Cloud SQL in our BigQuery silver layer?"*
- *"Generate an idempotent MERGE statement to maintain current state from Datastream change logs."*

### Host Execution Instructions
- **Claude Code**: Run `scaffold_scd2_dataform.py` in the workspace shell to generate SQLX models.
- **Antigravity**: Generate Dataform pipelines and compile with Dataform CLI to verify SQL syntax.

## Red Flags
- Comparing nullable columns with `=` instead of `IS DISTINCT FROM` (treating `NULL = NULL` as `NULL`, missing changes).
- Forgetting to close historical rows (`valid_to = current_timestamp, is_current = FALSE`) when inserting a new version.
- Querying raw append-only Datastream logs in BI dashboards, producing duplicate row counts.
- Running non-idempotent insert pipelines that create duplicates on backfill reruns.

## Verification
- [ ] SCD model generated using automation script:
  ```bash
  python3 ./skills/cdc-scd-patterns/scripts/scaffold_scd2_dataform.py <table_name> <key_column> <tracked_columns>
  ```
- [ ] Change detection uses `IS DISTINCT FROM` across all tracked columns.
- [ ] Every natural key has exactly one row where `is_current = TRUE` and `valid_to IS NULL`.
- [ ] Re-running the pipeline with unchanged data produces zero new rows.

## References
For full SQL templates and production-ready merge queries:
- [SCD Type 2 SQL Reference](references/scd-type2-sql.md)

