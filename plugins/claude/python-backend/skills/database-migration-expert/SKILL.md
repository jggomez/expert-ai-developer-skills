---
name: database-migration-expert
description: Manages database schema migrations, seed data scripts, and table versioning in Python backends (Alembic, SQL). Use this skill when asked to change DB schemas, write migrations, or write seeding scripts.
---

# Database Migration Expert Skill

## Overview
This skill guides the safe, zero-downtime evolution of relational database schemas and data seeding pipelines. It acts as a Database Administrator and Data Reliability Engineer, ensuring that every schema modification preserves data integrity, avoids destructive table locks, implements clean reversibility, and supports continuous deployment without service outages.

## When to Use
### Trigger Scenarios
- Creating, reviewing, or executing schema migrations (Alembic, SQL DDL).
- Adding new columns, indexes, foreign keys, or table constraints to existing databases.
- Executing phased column renames or type migrations using expand-contract patterns.
- Authoring idempotent database seeding and fixture scripts.

### When NOT to Use
- **Application database query tuning**: Route to `sql-query-optimization` or `bigquery-query-optimization`.
- **General application backend logic**: Route to `python-expert` or `fastapi-expert`.
- **System-level architectural boundaries**: Route to `senior-architect-engineering`.

## Process
### Phase 1: Pre-Migration Lock & Safety Analysis
1. Inspect proposed changes against production locking risks:
   - **Adding NOT NULL columns**: Never add `NOT NULL` without a default value in one step; follow expand-contract (add nullable, backfill data, add constraint).
   - **Adding Indexes**: Use concurrent index creation (`CREATE INDEX CONCURRENTLY` in Postgres) to prevent locking table reads/writes.
   - **Renaming Columns**: Never rename a column directly; create new column, double-write, migrate, and clean up.

### Phase 2: Migration Authoring & Autogeneration Guard
1. Generate the migration revision:
   ```bash
   alembic revision --autogenerate -m "add_user_status_column"
   ```
2. **Autogeneration Guard**: Manually audit the generated Python migration script. Autogenerate often misses custom constraints, enums, or index variants.
3. **Reversibility Requirement**: Ensure the `downgrade()` function completely and cleanly restores the previous schema state without orphaned artifacts.

### Phase 3: Idempotent Seeding & Dry-Run
1. Write data seeds with upsert semantics (`ON CONFLICT DO UPDATE` or checking existing keys) so they can be run multiple times safely.
2. Test both directions locally: upgrade to head, verify schema, downgrade one step, and re-upgrade.

## Usage
### Migration Commands
```bash
# Generate auto migration
alembic revision --autogenerate -m "describe_change"

# Apply migrations
alembic upgrade head

# Test downgrade safety
alembic downgrade -1
alembic upgrade head
```

### Example Prompts
- *"Write an Alembic migration to add an email verification timestamp to users without locking the table in production."*
- *"Design a safe expand-and-contract migration strategy to rename the 'amount' column to 'amount_cents'."*
- *"Create an idempotent seeding script for system permissions that can run safely in CI and staging."*

### Host Execution Instructions
- **Claude Code**: Generate and edit Alembic scripts, then run migrations against local dev databases via bash.
- **Antigravity**: Audit migration files and verify both upgrade and downgrade paths execute cleanly.

## Red Flags
- Adding a `NOT NULL` column without a default to a populated table in production.
- Leaving `downgrade()` as `pass` or throwing `NotImplementedError`.
- Direct `ALTER TABLE ... RENAME COLUMN` on active high-traffic tables.
- Non-idempotent seed files that crash or produce duplicate rows when rerun.
- Running DDL transactions without setting appropriate lock timeouts.

## Verification
- [ ] Migration script passes manual inspection; autogeneration verified.
- [ ] Both `upgrade` and `downgrade` execute cleanly and reversibly on local/staging environments.
- [ ] Heavy index creations specify concurrent or non-blocking creation modes.
- [ ] Seeding scripts execute idempotently without primary key or unique constraint violations.

## References
For safe migration patterns, expand-contract templates, and zero-downtime checklists:
- [Database Migration & Schema Design Reference](references/migration-patterns.md)

