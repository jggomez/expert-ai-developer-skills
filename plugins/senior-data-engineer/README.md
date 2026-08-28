# Senior Data Engineer Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-senior--data--engineer-green?style=flat-square)](file:///./)

The `senior-data-engineer` plugin packages a Google Cloud data engineering expert for **both Antigravity CLI and Claude Code**: one subagent, two skills (architecture decisions, and CDC/SCD patterns specifically), and direct MCP access to BigQuery, Datastream, Dataform, and Pub/Sub.

**Antigravity CLI users**: the subagent installs from the root [`agents/senior-data-engineer.md`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents/senior-data-engineer.md) — not this plugin folder's `agents/` — since Claude Code and Antigravity use incompatible subagent frontmatter. **Don't run `agy plugin install` on this plugin folder**; copy the agent file and `mcp_config.json` by hand instead — see §7 Installation.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing `gcp-data-engineering` or `cdc-scd-patterns` under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/senior-data-engineer/
├── README.md                       # This usage manual
├── plugin.json                     # Required plugin metadata descriptor (Antigravity, plugin root)
├── .claude-plugin/
│   └── plugin.json                 # Same metadata — Claude Code requires the manifest here, not at plugin root
├── .mcp.json                       # BigQuery, Datastream, Dataform, Pub/Sub — Claude Code's remote MCP format
├── mcp_config.json                 # Same 4 servers, Antigravity's format (serverUrl + authProviderType)
├── agents/
│   └── senior-data-engineer.md     # The subagent (Claude Code only — Antigravity's copy lives at the repo root)
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

## 3. Model Context Protocol (`.mcp.json` / `mcp_config.json`)

Four of Google's own **remote** MCP servers, registered for both hosts:

| Server | Covers |
| :--- | :--- |
| `bigquery` | Query execution, dataset/table metadata and schema |
| `datastream` | CDC streams, connection profiles, replication status |
| `dataform` | Code assets, workflow/pipeline execution, troubleshooting failed runs |
| `pubsub` | Topics, subscriptions, publishing messages |

**Known gap** (verified, not assumed): there is no dedicated Dataflow MCP server as of this research. Custom streaming/batch Beam pipelines are still operated via `gcloud`, Terraform, or the Beam SDK directly — the agent will tell you this rather than pretend an MCP tool covers it.

**Auth differs by host**: Claude Code handles OAuth natively (browser consent flow, PKCE-based dynamic client registration — no embedded credentials needed; see [Claude Code's MCP docs](https://code.claude.com/docs/en/mcp)). Antigravity's `mcp_config.json` instead declares `authProviderType: "google_credentials"` on each server, using Application Default Credentials (`gcloud auth application-default login`) rather than a browser OAuth popup — see [Antigravity's MCP docs](https://antigravity.google/docs/cli/mcp/).

`dataform`'s URL is region-scoped (`https://dataform.<region>.rep.googleapis.com/mcp`). Claude Code's `.mcp.json` uses `${GCP_REGION:-us-central1}` (env var substitution, confirmed supported); Antigravity's `mcp_config.json` hardcodes `us-central1` since variable substitution in that file wasn't independently verified — edit it directly if your Dataform repository is in a different region.

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

**Claude Code** — global:
```bash
cp -r ./plugins/senior-data-engineer ~/.claude/plugins/senior-data-engineer
```
**Claude Code** — project-scoped, no install/copy:
```bash
claude --plugin-dir ./plugins/senior-data-engineer
```

**Antigravity CLI** — **do not** run `agy plugin install ./plugins/senior-data-engineer`: this folder's `agents/` uses Claude Code's frontmatter schema, and whether Antigravity's loader auto-discovers a plugin's `agents/` folder the same way it does `skills/` isn't documented — the install risks it trying (and failing) to parse a file it was never meant to read, for no benefit, since Antigravity doesn't use this folder's agent anyway. Instead, copy the two pieces it needs by hand:
```bash
# 1. Agent — the Antigravity-format copy lives at the repo root, not in this plugin folder:
mkdir -p .agents/agents/          # project-scoped; use ~/.gemini/config/agents/ for global
cp agents/senior-data-engineer.md .agents/agents/

# 2. MCP servers — merge this plugin's mcp_config.json manually:
cat plugins/senior-data-engineer/mcp_config.json   # merge its "mcpServers" into .agents/mcp_config.json
                                                    # (global: ~/.gemini/config/mcp_config.json)
```
