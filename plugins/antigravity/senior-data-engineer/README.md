# Senior Data Engineer Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-senior--data--engineer-green?style=flat-square)](file:///./)

The `senior-data-engineer` plugin packages Google Cloud data engineering expertise for **Google Antigravity**: one specialized subagent, two bundled skills (architecture decisions and CDC/SCD patterns), direct MCP access to GCP data services, and deterministic lifecycle safety gates.

- **Google Antigravity**: Install via `agy plugin install ./plugins/antigravity/senior-data-engineer`. Subagent in `agents/` declares native Antigravity tools (`run_command`, `write_to_file`, `replace_file_content`, `view_file`, `call_mcp_tool`) with `commandExecutionPolicy: auto`.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing `gcp-data-engineering` or `cdc-scd-patterns` under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/antigravity/senior-data-engineer/
├── README.md                       # This usage manual
├── plugin.json                     # Antigravity plugin manifest
├── .claude-plugin/
│   └── plugin.json                 # Manifest compatibility marker
├── .mcp.json                       # BigQuery, Datastream, Dataform, Pub/Sub MCP servers
├── mcp_config.json                 # Same 4 servers, Antigravity format
├── hooks.json                      # Hook definitions
├── hooks/
│   ├── data-safety-gate.js         # PreToolUse gate preventing destructive operations
│   └── data-quality-gate.js        # Stop hook validating Dataform/ETL compile
├── agents/
│   └── senior-data-engineer.md     # Specialized subagent
├── rules/
│   └── data-engineer-rules.md      # GCP data architecture & 9-stage pipeline rules
└── skills/
    ├── gcp-data-engineering/       # Architecture decisions: storage, batch/streaming, BQ cost/perf
    └── cdc-scd-patterns/           # Datastream CDC checklist + SCD Type 0-6 + Dataform scaffolder
```

---

## 2. The Agent & 9-Stage Pipeline Integration

| Agent | Role | Execution Policy | Typical Tools |
| :--- | :--- | :--- | :--- |
| **`senior-data-engineer`** | Designs pipelines, enforces simple architecture, implements CDC/SCD, inspects real schemas via MCP. | `auto` | `run_command`, `write_to_file`, `replace_file_content`, `view_file`, `call_mcp_tool` |

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
agy plugin install ./plugins/antigravity/senior-data-engineer
```
