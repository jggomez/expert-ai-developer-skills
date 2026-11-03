---
trigger: glob
globs: "**/*.sql, **/*.sqlx, **/workflow_settings.yaml, **/dataform.json, **/dags/**/*.py"
description: Google Cloud data engineering constraints applied while editing SQL, Dataform or Airflow code - data safety, partitioning, SCD/CDC modeling, branch safety and fail-honest verification.
---

# Data Engineering Rules

- **Git Branch Governance**: never edit pipeline code or commit on `main`, `master`, `develop` or `dev`; create `feat/<slug>` first. **Scope Drift**: ask before mixing an unrelated request into the current branch.
- **Data safety**: never run `DROP TABLE/SCHEMA/DATABASE`, `TRUNCATE TABLE`, unbounded `DELETE` (`WHERE 1=1`), `bq rm -f/-r` or `gcloud storage rm --recursive` without explicit user consent. Backfills and destructive merges need a written rollback in `docs/<feature-name>/`.
- **Partitioning**: production BigQuery tables are partitioned (`require_partition_filter = true` on large tables) and clustered (up to 4 columns).
- **SCD & CDC**: default to SCD Type 2 (`valid_from`, `valid_to`, `is_current`) with deterministic hash keys (`SHA256` / `FARM_FINGERPRINT`), idempotent merges and event-time ordering.
- **Verify before claiming done**: `dataform compile` (or `--actions <action>` for one action) and `bq query --dry_run` exit code `0`.
- **Fail-honest**: if `dataform`, `bq` or ADC credentials are unavailable, report `BLOCKED: not executed - <exact error>`; never invent dry-run bytes or compile results.
