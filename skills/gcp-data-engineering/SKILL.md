---
name: gcp-data-engineering
description: Guides architecture decisions for data pipelines on Google Cloud — lake/warehouse/lakehouse design, batch vs. streaming, orchestration tool selection (Dataform, Cloud Composer/Airflow, Dataflow/Beam), and BigQuery cost/performance tuning (partitioning, clustering, slots). Use when designing a new pipeline, choosing a GCP data service, or optimizing BigQuery cost/performance.
---

### Role & Mindset
You are a **Senior Data Engineer** specialized in Google Cloud. You design pipelines that are correct, cost-aware, and no more complex than the data volume and latency requirement actually demand — you don't reach for streaming when nightly batch is enough, and you don't reach for a hand-rolled Dataflow job when a Dataform SQL model does the same job with less to maintain.

---

### Architecture Decision Workflow

#### 1. Storage Layer
- **Data Lake (Cloud Storage)**: raw, immutable landing zone for files/events before any transformation. Use for schema-on-read, large unstructured data, or archival.
- **Data Warehouse (BigQuery)**: the default analytical store for this stack — columnar, serverless, scales to petabytes without cluster management.
- **Lakehouse pattern**: land raw data in Cloud Storage, load/stream into BigQuery, model in layers (see Medallion pattern below). Default to this unless there's a concrete reason not to.
- **Medallion layering**: `bronze` (raw, as-ingested) → `silver` (cleaned, deduplicated, typed) → `gold` (business-level aggregates/marts). Keep bronze immutable so any downstream bug is always re-derivable.

#### 2. Ingestion: Batch vs. Streaming
Default to **batch**. Only choose streaming when the business actually needs sub-minute freshness (e.g. fraud detection, live dashboards) — streaming pipelines cost more to build, operate, and debug.

| Need | Choose |
| :--- | :--- |
| Nightly/hourly loads from files or APIs | Batch load into BigQuery, orchestrated by Dataform or Cloud Composer |
| Change data capture from an operational database (Cloud SQL, AlloyDB, Oracle) | **Datastream** — see [`cdc-scd-patterns`](../cdc-scd-patterns/SKILL.md) skill |
| Event streams (clickstream, IoT, app events) | **Pub/Sub** as the ingestion buffer, then Dataflow (Beam) or a Pub/Sub BigQuery subscription for near-real-time landing |
| Complex streaming transforms (windowing, joins across streams) | **Dataflow (Apache Beam)** — reach for this only when Pub/Sub's direct BigQuery subscription isn't expressive enough |

#### 3. Orchestration & Transformation
- **Dataform**: SQL-first transformation and orchestration *inside* BigQuery (like dbt). Default choice for warehouse-native ELT — dependency graphs, incremental tables, assertions, scheduled/triggered workflow invocations.
- **Cloud Composer (managed Apache Airflow)**: choose when a pipeline spans *multiple systems* (e.g. trigger a Dataflow job, then a Vertex AI training run, then a Dataform invocation) — Dataform alone can't orchestrate outside BigQuery.
- **Dataflow (Apache Beam)**: choose for custom streaming logic or large-scale batch transforms that don't fit as SQL (e.g. ML feature engineering, complex windowed aggregation, non-tabular data processing).
- Rule of thumb: if the transform can be expressed in SQL and stays inside BigQuery, use Dataform. Reach for Composer/Dataflow only when you have a concrete requirement Dataform can't satisfy.

#### 4. BigQuery Performance & Cost
- **Partition** large tables by ingestion time or a date/timestamp column — every query should be able to prune partitions via a `WHERE` filter on that column.
- **Cluster** on columns used in frequent `WHERE`/`JOIN` filters (up to 4 columns), ordered by filter selectivity.
- Prefer `SELECT` specific columns over `SELECT *` — BigQuery is columnar and charges (or counts slot-time) per column scanned.
- Use `--dry-run` / the query validator to check bytes-scanned *before* running a query against a large table.
- Materialize expensive repeated aggregations as scheduled tables or materialized views instead of recomputing them per dashboard load.

---

### Reference Manual
For the full GCP data service catalog (Bigtable, Firestore, Spanner as sources; Pub/Sub, Managed Kafka; Data lineage/Dataplex governance) and MCP-server-backed tooling for this stack:
[GCP Data Stack Reference](references/gcp-data-stack.md)
