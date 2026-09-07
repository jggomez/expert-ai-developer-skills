---
name: gcp-data-engineering
description: Guides architecture decisions for data pipelines on Google Cloud — lake/warehouse/lakehouse design, batch vs. streaming, orchestration tool selection (Dataform, Cloud Composer/Airflow, Dataflow/Beam), and BigQuery cost/performance tuning (partitioning, clustering, slots). Use when designing a new pipeline, choosing a GCP data service, or optimizing BigQuery cost/performance.
---

# GCP Data Engineering Skill

## Overview
This skill guides architectural decisions for data pipelines, data lakehouses, and analytical storage on Google Cloud Platform (GCP). It acts as a Senior GCP Data Architect, balancing data volume, ingestion latency, operational complexity, and cloud costs. It prioritizes simple, warehouse-native ELT patterns (Dataform, BigQuery) over complex custom streaming pipelines (Dataflow/Beam) unless business SLAs strictly require sub-minute freshness.

## When to Use
### Trigger Scenarios
- Designing enterprise data platforms on GCP (Cloud Storage, BigQuery, Pub/Sub, Dataflow, Composer).
- Selecting ingestion patterns (Batch loading vs. Log-based CDC vs. Streaming event buffers).
- Choosing orchestration engines (Dataform for warehouse-internal SQL vs. Cloud Composer for multi-service DAGs).
- Designing BigQuery table partitioning, clustering, and Medallion architecture layers (`bronze` → `silver` → `gold`).

### When NOT to Use
- **Replicating operational databases via CDC and SCD Type 2 modeling**: Route to `cdc-scd-patterns`.
- **Tuning slow or expensive BigQuery SQL query plans**: Route to `bigquery-query-optimization`.
- **Traditional single-node RDBMS optimization**: Route to `sql-query-optimization`.
- **General application backend development**: Route to `python-expert`.

## Process
### Phase 1: Storage Layer & Medallion Architecture
1. **Data Lake (Cloud Storage)**: Use GCS as the immutable landing zone for raw external files (CSV, JSON, Parquet, Avro). Retain raw files to ensure re-derivability if downstream bugs occur.
2. **Data Warehouse (BigQuery)**: Serverless, petabyte-scale analytical store.
3. **Medallion Layers**:
   - `Bronze`: Raw, ingested change-log or file dumps (append-only, immutable).
   - `Silver`: Cleaned, deduplicated, schema-validated, and typed tables.
   - `Gold`: High-value business aggregates, metrics marts, and reporting views.

### Phase 2: Ingestion Pattern Selection
Default to **batch** unless business requirements dictate sub-minute SLAs:
- **Nightly / Scheduled Loads**: Batch load into BigQuery via Dataform, Cloud Storage transfer, or Cloud Composer.
- **Operational Database Replication**: Use **Datastream** for log-based CDC into BigQuery.
- **High-throughput Event Streaming**: Use **Pub/Sub** buffer with direct BigQuery subscription (or Dataflow if stream joins/windowing are required).

### Phase 3: Orchestration & Transformation Engine Selection
- **Dataform**: SQLX-native transformation inside BigQuery. Default choice for warehouse-native ELT, assertions, and table dependencies.
- **Cloud Composer (Managed Airflow)**: Use when orchestrating across multiple GCP services (e.g. GCS → Dataflow → Vertex AI → BigQuery).
- **Dataflow (Apache Beam)**: Use exclusively for complex streaming transforms, custom windowed joins, or heavy Python/Java non-SQL transformations.

### Phase 4: BigQuery Cost & Performance Governance
- **Partitioning**: Partition tables by date/timestamp or ingestion time; require partition filters in `WHERE` clauses.
- **Clustering**: Cluster on up to 4 frequently filtered or joined columns, sorted from highest to lowest selectivity.
- **Column Pruning**: Explicitly name required columns; never run `SELECT *` across large analytical tables.
- **Dry-Run Validation**: Always validate query byte consumption before execution.

## Usage
### CLI Invocations & Verification Commands
```bash
# Check query byte scan estimation using bq dry-run
bq query --use_legacy_sql=false --dry_run "SELECT id, created_at FROM \`my_project.analytics.events\` WHERE event_date = '2026-09-01'"

# Validate Dataform project compilation
dataform compile
```

### Example Prompts
- *"Design a cost-effective GCP pipeline to ingest 50M daily events from Cloud Storage into BigQuery."*
- *"Should we use Dataform or Cloud Composer for our daily analytical reporting pipeline?"*
- *"Design the Medallion architecture and clustering strategy for our customer analytics dataset."*

### Host Execution Instructions
- **Claude Code**: Provide architecture blueprints and run `bq` CLI dry-run checks in the workspace.
- **Antigravity**: Formulate GCP architectural designs and integrate with GCP BigQuery tools.

## Red Flags
- Reaching for complex streaming architectures (Dataflow/Kafka) when hourly batch loads satisfy business SLAs.
- Running `SELECT *` queries on multi-terabyte BigQuery tables without partition filters.
- Using Cloud Composer to run pure SQL transformations that Dataform handles natively with lower cost and complexity.
- Querying raw CDC change-log tables directly from BI dashboards without a silver deduplication layer.

## Verification
- [ ] Table designs specify appropriate partitioning column and clustering keys.
- [ ] Medallion layer boundaries (`bronze`, `silver`, `gold`) clearly delineated.
- [ ] Ingestion tool chosen matches data velocity and freshness requirements.
- [ ] BigQuery dry-run confirms scanned bytes comply with cost budgets.

## References
For the full GCP data services matrix, MCP server mappings, and governance blueprints:
- [GCP Data Stack Reference](references/gcp-data-stack.md)

