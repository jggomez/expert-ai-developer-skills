# Senior Data Engineer Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](https://github.com/jggomez/expert-ai-developer-skills)
[![Plugin](https://img.shields.io/badge/Plugin-senior--data--engineer-green?style=flat-square)](.)

The `senior-data-engineer` plugin packages Google Cloud data engineering expertise for **Google Antigravity**: one specialized subagent, four bundled skills (GCP lakehouse architecture decisions, CDC/SCD patterns, and cross-AI LLM Wiki memory restore/capture), direct MCP access to GCP data services, parallel Silver/Gold mart & SQL audit execution, and deterministic lifecycle safety gates.

- **LLM Wiki Memory (`context/memory/`)**: At **State 0**, `senior-data-engineer` silently reads `context/memory/MEMORY.md` (and `architecture.md` on demand) to reuse known BigQuery dataset layouts, partition/clustering keys, and SLAs without redundant schema scans. At **State 6**, it persists Bronze/Silver/Gold table contracts, partition/cluster keys, and SLA decisions into `context/memory/`.
- **Parallel Lakehouse Execution (`State 3 & 4`)**: Supports building independent Silver/Gold `.sqlx` marts in parallel (`Mode A: Disjoint Files`) and delegating slow SQL query tuning to `sql-query-optimizer` in parallel with Dataform quality assertions.
- **Google Antigravity**: Install via `agy plugin install ./plugins/antigravity/senior-data-engineer`. Subagent in `agents/` declares native Antigravity tools (`run_command`, `write_to_file`, `replace_file_content`, `view_file`, `call_mcp_tool`) with `commandExecutionPolicy: auto`.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing any bundled skill under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

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
│   └── senior-data-engineer.md     # Specialized subagent (State 0-6 Lakehouse DAG)
├── rules/
│   └── data-engineer-rules.md      # GCP data architecture, LLM Wiki & parallel mart rules
└── skills/                         # Physical copy of the 4 bundled skills
    ├── gcp-data-engineering/       # Architecture decisions: storage, batch/streaming, BQ cost/perf
    ├── cdc-scd-patterns/           # Datastream CDC checklist + SCD Type 0-6 + Dataform scaffolder
    ├── context-capture/            # Persist lakehouse table contracts & SLAs to context/memory/
    └── context-restore/            # Restore known BQ datasets, partition keys & SLAs at State 0
```

---

## 2. The Agent & Lakehouse DAG Integration

| Agent | Role | Execution Policy | Typical Tools |
| :--- | :--- | :--- | :--- |
| **`senior-data-engineer`** | Restores/updates `context/memory/`, designs Bronze/Silver/Gold pipelines, implements CDC/SCD, builds parallel `.sqlx` marts (`Mode A: Disjoint Files`), and inspects real schemas via MCP. | `auto` | `run_command`, `write_to_file`, `replace_file_content`, `view_file`, `call_mcp_tool` |

---

## 3. Lifecycle Hooks & Safety Gates

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`PreToolUse`** | `hooks/data-safety-gate.js` | Enforces Plan-First; blocks destructive BigQuery/GCS operations (`DROP TABLE`, `DELETE FROM` without WHERE, recursive bucket deletion). |
| **`Stop`** | `hooks/data-quality-gate.js` | Validates Dataform compilation (`dataform compile`) and SQL syntax before session completion. |

---

## 4. Bundled Skills (4 Packaged Modules)

1. **`gcp-data-engineering`**: Guides Lakehouse vs Data Warehouse decisions, batch vs streaming tradeoffs, Cloud Composer vs Workflows vs Dataform selection, and BigQuery slot/partition optimization.
2. **`cdc-scd-patterns`**: Datastream replication setup, BigQuery staging design, MERGE vs append patterns, and Slowly Changing Dimensions (Type 0-6) modeling.
3. **`context-capture`**: Persists Bronze/Silver/Gold table contracts, partition/cluster keys, and SLA decisions into `context/memory/` (`MEMORY.md`, `architecture.md`, and `log/YYYY-MM-DD.md`) at `State 6`.
4. **`context-restore`**: Silently restores `context/memory/MEMORY.md` (and `architecture.md` on demand) at `State 0` to reuse known BigQuery dataset layouts and partition/clustering keys.

---

## 5. Installation

```bash
agy plugin install ./plugins/antigravity/senior-data-engineer
```
