# senior-data-engineer

> Google Cloud data engineering subagent with BigQuery, Datastream, Dataform and Pub/Sub MCP access, for Google Antigravity.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Antigravity-4285F4?style=flat-square)](.)

`senior-data-engineer` designs and builds data pipelines on Google Cloud: lake/warehouse architecture, CDC through Datastream, SCD modeling in BigQuery and Dataform, and orchestration.
It ships one subagent, four skills, an always-on rules file, two safety hooks and four MCP servers.
The hooks block destructive data operations and stop the session when a Dataform project fails to compile or Python pipeline tests fail.

## Requirements

| Needs | For |
| :--- | :--- |
| `node` on `PATH` | Running the two hooks |
| Google Cloud project and credentials (`gcloud` / `bq` with Application Default Credentials) | Live queries, dry runs and the MCP servers (`google_credentials` auth) |
| `dataform` CLI (optional) | The Stop-hook compile check in Dataform projects |
| `pytest` (optional) | The Stop-hook test run in Python pipeline projects |

## Installation

```bash
agy plugin install ./plugins/antigravity/senior-data-engineer
```

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
| `senior-data-engineer` | Designs, builds and audits GCP pipelines: Medallion layers, Datastream CDC, SCD Type 1/2, Composer/Airflow DAGs, BigQuery cost and performance. `commandExecutionPolicy: auto`. | `inherit` |

### Rules

| File | Trigger | Purpose |
| :--- | :--- | :--- |
| `rules/data-engineer-rules.md` | `always_on` | Lakehouse workflow, 3-tier triage, memory handling and fail-honest verification |

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `PreToolUse` (`run_command`, `call_mcp_tool`, `write_to_file`, `replace_file_content`) | `hooks/data-safety-gate.js` | Denies `DROP TABLE/SCHEMA/DATABASE`, `TRUNCATE TABLE`, `DELETE FROM ... WHERE 1=1`, `bq rm -f/-r`, `gsutil rm -r` and `gcloud storage rm --recursive`. Denies MCP `delete_table`, `delete_instance` and `delete_database`. Denies `.sql`, `.sqlx`, `.py` and `workflow_settings.yaml` writes on `main`, `master`, `develop` or `dev`, and without `PLAN.md` or `docs/PLAN.md`. |
| `Stop` | `hooks/data-quality-gate.js` | On a model stop, runs `dataform compile` in Dataform projects and `pytest -q` in projects with `tests/` (or `test/`) plus `requirements.txt` or `pyproject.toml`. Asks the agent to continue on failure. Skips each check when its CLI is not installed. |

### MCP servers

| Server | Command | Purpose |
| :--- | :--- | :--- |
| `bigquery` | `https://bigquery.googleapis.com/mcp` | BigQuery datasets, schemas and query plans |
| `datastream` | `https://datastream.googleapis.com/mcp` | Datastream CDC streams |
| `dataform` | `https://dataform.us-central1.rep.googleapis.com/mcp` | Dataform repositories and workflows |
| `pubsub` | `https://pubsub.googleapis.com/mcp` | Pub/Sub topics and subscriptions |

All four are defined in `mcp_config.json` with `authProviderType: google_credentials`.

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`gcp-data-engineering`** | Lake/warehouse/lakehouse design, batch vs. streaming, orchestration choice (Dataform, Composer/Airflow, Dataflow), BigQuery partitioning, clustering and slots |
| **`cdc-scd-patterns`** | Datastream CDC ingestion and SCD Type 1/2 merge logic in BigQuery/Dataform; includes `scaffold_scd2_dataform.py` |
| **`context-restore`** | Reads `context/memory/MEMORY.md` at session start to reuse known datasets, keys and SLAs |
| **`context-capture`** | Writes table contracts, partition/cluster keys and SLA decisions to `context/memory/` when a task ships |

Bundled skills are copies of the root `/skills` catalog. After editing a skill there, run `python3 scripts/sync_plugin_skills.py` from the repo root.

## How it works

1. The agent reads `context/memory/MEMORY.md` if it exists, then writes a short `PLAN.md` that classifies the task as Tier 1, 2 or 3.
2. Tier 2 and 3 tasks pause on an `ask_question` prompt for your approval of data contracts, lineage and partitioning.
3. Independent Silver/Gold `.sqlx` marts can be built in parallel on disjoint files.
4. Verification uses `dataform compile` and `bq query --dry_run`. If a CLI or credentials are missing, the agent reports `BLOCKED` instead of inventing results.
5. When the task ships, `context-capture` records durable decisions in `context/memory/`.

Heavy SQL tuning is handed to [`sql-query-optimizer`](../sql-query-optimizer/README.md).

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `[DATA SAFETY GATE VIOLATION]` on a command or MCP call | `DROP`, `TRUNCATE`, `WHERE 1=1` delete, forced/recursive `bq rm`, recursive storage delete, or an MCP delete call | Run it yourself after review |
| `[DATA GRAPH GATE - PLAN FIRST]` when writing pipeline code | No `PLAN.md` in the workspace root or `docs/` | Create `PLAN.md`, then retry |
| `[GIT BRANCH GOVERNANCE]` when writing pipeline code | You are on `main`, `master`, `develop` or `dev` | `git checkout -b feat/<slug>` |
| Session continues with `[DATA QUALITY GATE VIOLATION]` | `dataform compile` or `pytest -q` failed | Fix the model or test; the output is included in the message |
| Compile or test check never runs | `dataform` or `pytest` not on `PATH` | Install the CLI in the environment the hooks run in |

## Related plugins

- [`sql-query-optimizer`](../sql-query-optimizer/README.md): diagnoses and rewrites slow BigQuery and relational SQL.
- [`shared-context`](../shared-context/README.md): the `context/memory/` store shared across sessions and hosts.
- [Claude Code version](../../claude/senior-data-engineer/README.md) of this plugin.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
