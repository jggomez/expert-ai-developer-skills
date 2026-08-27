---
name: cdc-scd-patterns
description: Guides Change Data Capture (CDC) ingestion via Datastream and Slowly Changing Dimension (SCD) modeling in BigQuery/Dataform. Use when replicating an operational database, designing history-tracking dimension tables, or implementing SCD Type 1/2 merge logic.
---

### Role & Mindset
You are a **Senior Data Engineer** specialized in change tracking: capturing what changed in a source system, and modeling how a dimension's history should be represented downstream. Get the semantics right first (what counts as a change, what history must be preserved) — the SQL is secondary.

---

### Part 1: Change Data Capture (CDC) with Datastream

#### How it works
Datastream reads a source database's transaction log (log-based CDC — not polling) and streams inserts/updates/deletes into BigQuery or Cloud Storage as they happen, without impacting the source database's performance. Supported sources include Cloud SQL, AlloyDB, Oracle, and MySQL/PostgreSQL variants.

#### Design checklist
1. **Connection profile**: verify Datastream has network access to the source (private connectivity/VPC peering for most production sources) and read access to the transaction log.
2. **Backfill vs. streaming**: Datastream backfills existing rows once, then streams ongoing changes — confirm the backfill won't overload the source during business hours for large tables.
3. **Landing shape in BigQuery**: Datastream writes a change-log table (one row per change event, with metadata columns like `_metadata_timestamp`, `_metadata_deleted`) — this is your **bronze** layer. It is NOT yet a queryable current-state table.
4. **Materializing current state**: build a **silver** Dataform table on top of the change-log that keeps only the latest version per primary key (see the SCD Type 1 pattern below) — don't query the raw change-log directly from BI tools.
5. **Idempotency**: the merge/dedup step must be safe to re-run — use `MERGE` keyed on primary key + a monotonic change timestamp, never a plain `INSERT`.

---

### Part 2: Slowly Changing Dimensions (SCD)

| Type | Behavior | When to use |
| :--- | :--- | :--- |
| **Type 0** | Never update — original value is permanent (e.g. original signup date) | Attributes that must never change by definition |
| **Type 1** | Overwrite — no history kept, always shows current value | Corrections, attributes where history has no business value (e.g. a fixed typo) |
| **Type 2** | New row per change, with `valid_from`/`valid_to`/`is_current` — full history preserved | The default choice for dimensions where "what did we know at time T" matters (e.g. customer address, product price tier) |
| **Type 3** | Add a `previous_value` column — keeps only the immediately prior value | Rare; only when exactly one prior state must be queryable alongside current |
| **Type 4** | Current table + separate history table | High-churn dimensions where the current table must stay small/fast |
| **Type 6** | Hybrid: Type 2 row versioning + a Type 1 "current value" column on every row | Needed when some queries want history and others want a fast current-value lookup without a self-join |

**Default recommendation**: unless told otherwise, model dimensions as **Type 2** — it's the most broadly useful and the other types are optimizations you adopt when Type 2 proves insufficient (query performance, storage cost), not the starting point.

#### Type 2 merge logic (BigQuery/Dataform)
See the ready-to-adapt template: [SCD Type 2 SQL Reference](references/scd-type2-sql.md). Or scaffold one directly:
```bash
python3 ./skills/cdc-scd-patterns/scripts/scaffold_scd2_dataform.py <table_name> <key_column> <tracked_columns_comma_separated>
```
This generates a parameterized Dataform `.sqlx` file implementing the Type 2 merge — read and adapt it to your actual schema before running it.

---

### Common Mistakes to Avoid
- **Silent duplicate rows**: a Type 2 merge without a proper `MERGE ... WHEN MATCHED` clause can insert a new "current" row on every pipeline run even when nothing changed. Always compare tracked columns before inserting a new version.
- **Comparing NULLs with `=`**: use `IS DISTINCT FROM` (or an explicit `COALESCE`) when diffing tracked columns for changes — `NULL = NULL` is `NULL`, not `TRUE`, in standard SQL.
- **No `valid_to` on the newly-superseded row**: when inserting a new current version, the previous row's `valid_to`/`is_current` must be updated in the *same* transaction/merge, not a separate pass.
- **Treating the Datastream change-log as the serving table**: always materialize a deduplicated, current-state (or SCD2) table on top of it.
