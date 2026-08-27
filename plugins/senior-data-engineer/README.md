# Senior Data Engineer Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-senior--data--engineer-green?style=flat-square)](file:///./)

The `senior-data-engineer` plugin packages a Google Cloud data engineering expert as a Claude Code plugin: one subagent, two skills (architecture decisions, and CDC/SCD patterns specifically), and direct MCP access to BigQuery, Datastream, Dataform, and Pub/Sub.

**Claude Code only** — no Antigravity equivalent exists in this repo for this plugin (see root README §12.2 for why).

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing `gcp-data-engineering` or `cdc-scd-patterns` under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/senior-data-engineer/
├── README.md                       # This usage manual
├── plugin.json                     # Required plugin metadata descriptor
├── .mcp.json                       # BigQuery, Datastream, Dataform, Pub/Sub — Google-hosted remote MCP servers
├── agents/
│   └── senior-data-engineer.md     # The subagent
└── skills/
    ├── gcp-data-engineering/       # Architecture decisions: storage, batch/streaming, orchestration, BQ cost/perf
    └── cdc-scd-patterns/           # Datastream CDC checklist + SCD Type 0-6 + a Dataform SCD2 scaffolder script
```

---

## 2. The Agent

| Agent | Role | Model | Tools |
| :--- | :--- | :--- | :--- |
| `senior-data-engineer` | Designs pipelines, defaults to the simplest architecture that fits the requirement, implements CDC/SCD correctly, uses the connected MCP tools to inspect real schemas/streams instead of guessing. | `sonnet` | Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion |

This is intentionally a single agent, not a multi-role panel — it's one area of expertise, not an SDLC pipeline with distinct phases. If you later need a separate "pipeline reviewer/auditor" role, that's a natural second agent to add.

---

## 3. Model Context Protocol (`.mcp.json`)

Four of Google's own **remote** MCP servers (HTTP + native OAuth — Claude Code handles the browser consent flow itself, no embedded credentials needed):

| Server | Covers |
| :--- | :--- |
| `bigquery` | Query execution, dataset/table metadata and schema |
| `datastream` | CDC streams, connection profiles, replication status |
| `dataform` | Code assets, workflow/pipeline execution, troubleshooting failed runs |
| `pubsub` | Topics, subscriptions, publishing messages |

**Known gap** (verified, not assumed): there is no dedicated Dataflow MCP server as of this research. Custom streaming/batch Beam pipelines are still operated via `gcloud`, Terraform, or the Beam SDK directly — the agent will tell you this rather than pretend an MCP tool covers it.

The first time you use one of these tools, Claude Code will prompt you to authenticate with your Google account in a browser (standard OAuth, PKCE-based dynamic client registration — see [Claude Code's MCP docs](https://code.claude.com/docs/en/mcp)).

---

## 4. Bundled Skills (2 Packaged Modules)

1. **`gcp-data-engineering`**: Storage layer choice, batch vs. streaming, orchestration tool selection (Dataform/Airflow/Dataflow), and BigQuery partitioning/clustering/cost guidance.
2. **`cdc-scd-patterns`**: Datastream CDC design checklist, SCD Type 0-6 reference, ready-to-adapt SQL/Dataform SCD Type 2 templates, and a `scaffold_scd2_dataform.py` generator script.

---

## 5. What This Plugin Is *Not*

This is a **chat-based expert** for design and implementation help inside a Claude Code session — not a standalone, deployable production agent. If you need an autonomous data agent that runs continuously in GCP (e.g. via Agent Runtime/Cloud Run, with its own eval suite and CI/CD), that's a different, heavier build using Google's [Agent Development Kit](https://adk.dev) (`agents-cli scaffold create`) — a legitimate next step, but a separate project from this plugin.

---

## 6. Example Prompts

- "Use the senior-data-engineer agent to design a pipeline that lands daily sales CSV exports into BigQuery."
- "Design a CDC pipeline from our Cloud SQL orders table into BigQuery, and model it as SCD Type 2."
- "Scaffold an SCD Type 2 Dataform model for the customer dimension, tracking name/address/tier changes."
- "Should this pipeline be batch or streaming? We need the dashboard updated every 15 minutes."
- "List the datasets in this BigQuery project and check the table schema before I design a new mart on top of it." (uses the `bigquery` MCP tool)
- "Check the replication status of our Datastream stream from the orders database." (uses the `datastream` MCP tool)
- "Why did the last Dataform workflow invocation fail?" (uses the `dataform` MCP tool)
- "Review this BigQuery table's partitioning and clustering for a query that always filters by `order_date` and `region`."

---

## 7. Installation

```bash
cp -r ./plugins/senior-data-engineer ~/.claude/plugins/senior-data-engineer
```
