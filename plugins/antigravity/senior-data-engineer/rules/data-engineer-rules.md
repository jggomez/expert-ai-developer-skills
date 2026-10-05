---
trigger: always_on
description: Google Cloud data engineering rules enforcing Graph Engineering DAG, batch-first SLAs, BigQuery partition/clustering, data safety, and CDC/SCD modeling.
---

# Google Cloud Data Engineering Rules & Graph Protocol

**Identifier**: `data-engineer-rules`

## 1. The Lakehouse Graph Engineering DAG

Every analytical or streaming pipeline must transition through this explicit DAG:

```
[PLAN FIRST GATE: PLAN.md] ──(Define Sources, SLAs, Schemas)
          │
          ▼
[ARCHITECTURE (Bronze / Silver / Gold Lakehouse & SCD Type 1/2)]
          │
          ▼
[BUILD DDL & MODELS (.sqlx / Datastream CDC / BigQuery DDL)]
          │
          ▼
[TEST & VALIDATE (Quality Assertions, Schema Invariants, Idempotency)]
          │ (exit 0)
          ▼
[GOVERNANCE & AUDIT (IAM, CMEK, VPC-SC, Partition/Cluster Pruning)]
          │
          ▼
[SHIP (Composer / Airflow DAG Release, CI/CD Deployment)]
```

## 2. Inviolable Role Boundaries & Safety

- **Plan First**: Never write BigQuery DDL or Dataform `.sqlx` models without `PLAN.md` documenting source schemas, ingestion latency SLAs, and schema contracts.
- **Destructive Operation Ban**: Never execute `DROP TABLE`, `DROP SCHEMA`, or unpartitioned `DELETE FROM ... WHERE 1=1` without explicit user permission.
- **Mandatory Partitioning & Clustering**: Every BigQuery table must specify:
  1. Partitioning (ingestion time, timestamp column, or integer range).
  2. Clustering (up to 4 high-cardinality filter/join columns).

## 3. SCD & Dimension Modeling Standards

- For historical dimension tracking, default to **SCD Type 2** (`valid_from`, `valid_to`, `is_current`).
- Ensure primary key uniqueness and idempotency on all merge and upsert operations.
