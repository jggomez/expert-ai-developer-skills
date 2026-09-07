---
trigger: model_decision
description: Google Cloud data engineering rules enforcing the 9-stage cycle, batch-first SLAs, BigQuery partition/clustering, and CDC/SCD modeling.
---

# Google Cloud Data Engineering Rules

**Identifier**: `data-engineer-rules`

## 1. The Data Engineering 9-Stage Command Lifecycle

Follow this command cycle for Google Cloud analytical and streaming data platforms:

| What you're doing | Command | Key Principle | Primary Focus |
| :--- | :--- | :--- | :--- |
| **Define what to build** | `/spec` | Spec before code | Data sources, SLAs (batch vs stream), schema contracts |
| **Plan how to build it** | `/plan` | Small, atomic tasks | Bronze/Silver/Gold Lakehouse, SCD Type 1/2 modeling |
| **Build incrementally** | `/build` | One slice at a time | Dataform `.sqlx`, Datastream CDC, BigQuery DDL |
| **Prove it works** | `/test` | Tests are proof | Data quality assertions, idempotency checks, mock runs |
| **Set the quality bar** | `/constraints` | Decide it once, enforce it everywhere | IAM governance, CMEK, VPC-SC, column masking |
| **Review before merge** | `/review` | Improve code health | Schema drift audit, pipeline lineage, DAG dependencies |
| **Audit performance** | `/perf` | Measure before you optimize | BigQuery slots, shuffle latency, partition pruning |
| **Simplify the code** | `/code-simplify` | Clarity over cleverness | Eliminate redundant CTEs/joins, clean Dataform models |
| **Ship to production** | `/ship` | Faster is safer | Cloud Composer DAG release, CI/CD deployment |

## 2. Dynamic Entry Points & Sizing

The data engineer sizes the workflow dynamically:
- **Ad-hoc Query / Transformation Fix**: Start at `/build` (SQL rewrite) -> `/test` -> `/perf` -> `/ship`.
- **New Lakehouse Pipeline**: Full sequence starting at `/spec` (SLAs & source schemas).
- **Expensive / Slow Query**: Start at `/perf` (dry-run & execution timeline) -> `/code-simplify` -> `/test`.

## 3. Data Engineering Constraints

- **Batch-First SLA**: Default to batch (daily/hourly). Introduce streaming (Pub/Sub/Dataflow) only when sub-hour latency is mandatory.
- **Partitioning & Clustering**: Every BigQuery table must specify partitioning and clustering keys.
- **No Unbounded Scans**: Never run `SELECT *` without partition filters on production datasets.
- **Idempotency**: All merge operations and SCD Type 2 pipelines must be deterministic and replayable.
- **Inspect via MCP**: Verify actual schemas via `bigquery` and `datastream` MCP tools before proposing mutations.
