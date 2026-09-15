# GCP Data Stack Reference

A catalog of Google Cloud data services relevant to pipeline design, and which ones this repository's `senior-data-engineer` agent can reach directly via MCP.

---

## 1. Storage & Serving

| Service | Role | MCP-backed here? |
| :--- | :--- | :--- |
| **Cloud Storage** | Data lake — raw landing zone, archival, unstructured data | Yes |
| **BigQuery** | Analytical warehouse — the default target for modeled data | Yes |
| **Bigtable** | Wide-column NoSQL for high-throughput, low-latency serving (time series, IoT) | Yes |
| **Firestore** | Document NoSQL for application-facing, low-latency reads | Yes |
| **Cloud SQL / AlloyDB / Spanner** | Transactional (OLTP) sources — typically the *source* of a CDC pipeline, not the destination | Yes |

## 2. Ingestion & Movement

| Service | Role | MCP-backed here? |
| :--- | :--- | :--- |
| **Datastream** | Change Data Capture from OLTP databases into BigQuery/Cloud Storage | Yes — see [`cdc-scd-patterns`](../../cdc-scd-patterns/SKILL.md) |
| **Pub/Sub** | Durable pub/sub messaging — the standard streaming ingestion buffer | Yes |
| **BigQuery Data Transfer Service** | Scheduled, managed batch loads from SaaS sources (Google Ads, YouTube, etc.) and cross-region/cross-project copies | Yes |
| **Managed Service for Apache Kafka** | Kafka-compatible streaming, for teams already standardized on Kafka | Yes |

## 3. Transformation & Orchestration

| Service | Role | MCP-backed here? |
| :--- | :--- | :--- |
| **Dataform** | SQL-first ELT and orchestration inside BigQuery (dbt-equivalent) | Yes |
| **Managed Service for Apache Airflow** | Cross-system orchestration (the managed equivalent of Cloud Composer) | Yes |
| **Managed Service for Apache Spark** | Large-scale batch/ML processing when SQL-in-BigQuery isn't a fit | Yes |
| **Dataflow (Apache Beam)** | Custom streaming/batch transform pipelines | **No dedicated MCP server found as of this research** — operate via `gcloud`, Terraform, or the Beam SDK directly. Re-verify before assuming this has changed. |

## 4. Governance & Observability

| Service | Role | MCP-backed here? |
| :--- | :--- | :--- |
| **Data lineage** | Track how data flows and transforms across BigQuery/Dataform jobs | Yes |
| **Knowledge Catalog** (Dataplex's successor branding) | Data discovery, classification, and metadata search | Yes |
| **Cloud Logging / Monitoring** | Pipeline run logs, alerting on job failures or SLA misses | Yes (general-purpose, not data-specific) |

---

## 5. Choosing an Ingestion Path — Decision Checklist

1. Is the source an operational database you don't own the write path to? → **Datastream (CDC)**.
2. Is the source an event stream / application emitting events? → **Pub/Sub**, landed via a BigQuery subscription or Dataflow.
3. Is the source a file drop or a SaaS API on a schedule? → **BigQuery Data Transfer Service** or a scheduled Dataform/Composer load.
4. Does the transform logic fit in SQL, entirely inside BigQuery? → **Dataform**.
5. Does the pipeline need to coordinate steps across multiple GCP services (not just BigQuery)? → **Managed Airflow**.
6. Does the transform need custom code, complex windowing, or non-tabular processing? → **Dataflow (Beam)** — note this one has no MCP server; it's operated via `gcloud`/Terraform/the Beam SDK, not through an agent's MCP tools.
