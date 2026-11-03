# senior-data-engineer

> Google Cloud data engineering subagent with BigQuery, Datastream, Dataform and Pub/Sub MCP access, for Claude Code.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-orange?style=flat-square)](../../../docs/claude-code-installation.md)

`senior-data-engineer` designs and builds data pipelines on Google Cloud: lake/warehouse architecture, CDC through Datastream, SCD modeling in BigQuery and Dataform, and orchestration.
It ships one subagent, four skills, two safety hooks and four remote MCP servers.
The hooks block destructive SQL and storage commands, and stop the session when a Dataform or dbt project no longer compiles.

## Requirements

| Needs | For |
| :--- | :--- |
| `node` on `PATH` | Running the two hooks |
| Google Cloud project and credentials (`gcloud` / `bq` with Application Default Credentials) | Live queries, dry runs and the MCP servers |
| `dataform` or `dbt` CLI (optional) | The Stop-hook compile check in Dataform or dbt projects |

## Installation

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install senior-data-engineer@expert-ai-developer-skills
```

Updates, per-project settings, local development and limitations: [Claude Code installation guide](../../../docs/claude-code-installation.md).

## Quick start

```text
Use the senior-data-engineer agent to design a Bronze/Silver/Gold lakehouse for our orders database replicated with Datastream.
```

```text
Model the customers dimension as SCD Type 2 in Dataform and add uniqueness and not-null assertions.
```

```text
Audit the partitioning and clustering of the analytics dataset and estimate the cost impact with bq query --dry_run.
```

## What's included

### Agents

| Agent | Role | Model |
| :--- | :--- | :--- |
| `senior-data-engineer` | Designs, builds and audits GCP pipelines: Medallion layers, Datastream CDC, SCD Type 1/2, Composer/Airflow DAGs, BigQuery cost and performance | `inherit` |

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `PreToolUse` (`Bash`, `Write`, `Edit`) | `hooks/data-safety-gate.js` | Denies `DROP TABLE/SCHEMA/DATABASE/VIEW`, `TRUNCATE`, `DELETE FROM` without `WHERE`, `bq rm -f`, and recursive `gsutil rm` / `gcloud storage rm`. Denies `.sql`, `.sqlx` and pipeline `.py` edits on `main`, `master`, `develop` or `dev`, and without a `PLAN.md` (small `Edit` calls of 10 lines or less are exempt). |
| `Stop` | `hooks/data-quality-gate.js` | Runs `dataform compile` (if `dataform.json` or `workflow_settings.yaml` exists) or `dbt compile` (if `dbt_project.yml` exists). Blocks the stop on failure, at most 3 times per turn. Skips when no code changed. |

### MCP servers

| Server | Command | Purpose |
| :--- | :--- | :--- |
| `bigquery` | HTTP `https://bigquery.googleapis.com/mcp` | BigQuery datasets, schemas and query plans |
| `datastream` | HTTP `https://datastream.googleapis.com/mcp` | Datastream CDC streams |
| `dataform` | HTTP `https://dataform.${GCP_REGION}.rep.googleapis.com/mcp` (OAuth, BigQuery scope) | Dataform repositories and workflows |
| `pubsub` | HTTP `https://pubsub.googleapis.com/mcp` (OAuth, Pub/Sub scope) | Pub/Sub topics and subscriptions |

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`gcp-data-engineering`** | Lake/warehouse/lakehouse design, batch vs. streaming, orchestration choice (Dataform, Composer/Airflow, Dataflow), BigQuery partitioning, clustering and slots |
| **`cdc-scd-patterns`** | Datastream CDC ingestion and SCD Type 1/2 merge logic in BigQuery/Dataform; includes `scaffold_scd2_dataform.py` |
| **`context-restore`** | Reads `context/memory/MEMORY.md` at session start to reuse known datasets, keys and SLAs |
| **`context-capture`** | Writes table contracts, partition/cluster keys and SLA decisions to `context/memory/` when a task ships |

## How it works

1. The agent reads `context/memory/MEMORY.md` if it exists, then writes a short `PLAN.md` that classifies the task as Tier 1, 2 or 3.
2. Tier 2 and 3 tasks pause for your approval of data contracts, lineage and partitioning before any code is written.
3. Independent Silver/Gold `.sqlx` marts can be built in parallel on disjoint files.
4. Verification uses `dataform compile` and `bq query --dry_run`. If a CLI or credentials are missing, the agent reports `BLOCKED` instead of inventing results.
5. When the task ships, `context-capture` records durable decisions in `context/memory/`.

Heavy SQL tuning is handed to [`sql-query-optimizer`](../sql-query-optimizer/README.md).

## Configuration

| Variable | Default | Read by |
| :--- | :--- | :--- |
| `GCP_REGION` | `us-central1` | `.mcp.json`, to build the regional `dataform` MCP endpoint |

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `[DATA SAFETY GATE VIOLATION]` on a shell command | The command contains `DROP`, `TRUNCATE`, an unbounded `DELETE`, `bq rm -f` or a recursive storage delete | Run it yourself after review, or add a `WHERE` clause |
| `[PLAN-FIRST VIOLATION]` when writing SQL | No `PLAN.md` in the project root, `docs/`, `.agents/` or `.claude/` | Create `PLAN.md`, then retry |
| `[GIT BRANCH GOVERNANCE]` when writing SQL | You are on `main`, `master`, `develop` or `dev` | `git checkout -b feat/<slug>` |
| Session will not stop; `[DATAFORM COMPILATION FAILED]` or `[DBT COMPILATION FAILED]` | The project no longer compiles | Fix the model; after 3 blocks in one turn the gate lets the turn end with a notice |
| `dataform` MCP server fails to connect | Wrong region in the endpoint | Set `GCP_REGION` to your Dataform region |

## Related plugins

- [`sql-query-optimizer`](../sql-query-optimizer/README.md): diagnoses and rewrites slow BigQuery and relational SQL.
- [`shared-context`](../shared-context/README.md): the `context/memory/` store shared across sessions and hosts.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
