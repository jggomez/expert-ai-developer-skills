# Senior Data Engineer Plugin (Claude Code)

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-senior--data--engineer-green?style=flat-square)](file:///./)

The `senior-data-engineer` plugin packages Google Cloud data engineering expertise for **Claude Code**: one specialized subagent, two bundled skills (architecture decisions and CDC/SCD patterns), and direct MCP access to GCP data services.

---

## 1. Directory Tree & Architecture

```
plugins/claude/senior-data-engineer/
├── README.md                       # This usage manual
├── .claude-plugin/
│   └── plugin.json                 # Claude Code plugin manifest
├── .mcp.json                       # BigQuery, Datastream, Dataform, Pub/Sub MCP servers
├── hooks.json                      # Hook definitions
├── hooks/
│   ├── data-safety-gate.js         # PreToolUse gate preventing destructive operations
│   └── data-quality-gate.js        # Stop hook validating Dataform/ETL compile
├── agents/
│   └── senior-data-engineer.md     # Specialized subagent for Claude Code
└── skills/
    ├── gcp-data-engineering/       # Architecture decisions: storage, batch/streaming, BQ cost/perf
    └── cdc-scd-patterns/           # Datastream CDC checklist + SCD Type 0-6 + Dataform scaffolder
```

---

## 2. The Agent & Role Boundaries

| Agent | Role | Invocation | Allowed Tools |
| :--- | :--- | :--- | :--- |
| **`senior-data-engineer`** | Designs pipelines, models CDC/SCD, optimizes BigQuery, validates plans. | `Agent` | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep` |

---

## 3. Lifecycle Hooks & Safety Gates

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`PreToolUse`** | `hooks/data-safety-gate.js` | Enforces Plan-First; blocks destructive BigQuery/GCS operations (`DROP TABLE`, `DELETE FROM` without WHERE, recursive bucket deletion). |
| **`Stop`** | `hooks/data-quality-gate.js` | Validates Dataform compilation (`dataform compile`) and SQL syntax before session completion. |

---

## 4. Bundled Skills (2 Packaged Modules)

1. **`gcp-data-engineering`**: Guides Lakehouse vs Data Warehouse decisions, batch vs streaming tradeoffs, Cloud Composer vs Workflows vs Dataform selection, and BigQuery slot/partition optimization.
2. **`cdc-scd-patterns`**: Datastream replication setup, BigQuery staging design, MERGE vs append patterns, and Slowly Changing Dimensions (Type 0-6) modeling.

---

## 5. Installation

```bash
/plugin install senior-data-engineer
# or local:
claude plugin install plugins/claude/senior-data-engineer
```
