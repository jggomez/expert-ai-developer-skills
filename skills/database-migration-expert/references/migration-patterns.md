# Database Migration & Schema Design Reference

This catalog details patterns for safe, version-controlled, and zero-downtime database migrations.

---

## 1. Alembic (SQLAlchemy) Migrations

### 1.1 Generating Auto-Migrations
- Always run the autogenerate command to bootstrap draft migrations based on ORM changes:
  ```bash
  alembic revision --autogenerate -m "Add description to item"
  ```
- **MANDATORY**: Inspect the generated migration file. Autogenerate misses indexes, type adjustments, and custom checks.

### 1.2 Upgrading and Downgrading
Ensure every migration contains both `upgrade()` and `downgrade()` procedures.

```python
# Alembic revision file example
def upgrade() -> None:
    op.add_column('items', sa.Column('description', sa.String(length=255), nullable=True))

def downgrade() -> None:
    op.drop_column('items', 'description')
```

---

## 2. Zero-Downtime Migration Patterns

When modifying schemas on production databases under active traffic, follow these steps to prevent downtime or database lockouts:

### 2.1 Adding a NOT NULL Column
1. Add the column as `nullable=True`.
2. Deploy the code to write to the column.
3. Run a migration script to populate default/historical values for existing rows in batches.
4. Run a final migration to alter the column to `nullable=False` (this runs instantly without table locks).

### 2.2 Renaming a Column
1. Create the new column.
2. Deploy code to write to **both** the old and new columns.
3. Migrate old data to the new column.
4. Deploy code to read only from the new column.
5. Drop the old column.

---

## 3. Database Seeding Patterns
- Use seed scripts to set up lookups and metadata values required for system operation (e.g. roles, categories).
- Guard seed scripts with check constraints to prevent double-inserting if run repeatedly:
  ```sql
  INSERT INTO roles (name) VALUES ('admin') ON CONFLICT DO NOTHING;
  ```
