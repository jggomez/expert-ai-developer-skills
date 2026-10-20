# Senior Data Engineer Plugin (Claude Code)

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](https://github.com/jggomez/expert-ai-developer-skills)
[![Plugin](https://img.shields.io/badge/Plugin-senior--data--engineer-green?style=flat-square)](.)

The `senior-data-engineer` plugin packages Google Cloud data engineering expertise for **Claude Code**: one specialized subagent, four bundled skills (GCP lakehouse architecture decisions, CDC/SCD patterns, and cross-AI LLM Wiki memory restore/capture), parallel Silver/Gold mart & SQL audit execution, and direct MCP access to GCP data services.

- **LLM Wiki Memory (`context/memory/`)**: At **State 0**, `senior-data-engineer` silently reads `context/memory/MEMORY.md` (and `architecture.md` on demand) to reuse known BigQuery dataset layouts, partition/clustering keys, and SLAs without redundant schema scans. At **State 6**, it persists Bronze/Silver/Gold table contracts, partition/cluster keys, and SLA decisions into `context/memory/`.
- **Parallel Lakehouse Execution (`State 3 & 4`)**: Supports building independent Silver/Gold `.sqlx` marts in parallel (`Mode A: Disjoint Files`) and delegating slow SQL query tuning to `sql-query-optimizer` in parallel with Dataform quality assertions.

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
│   └── senior-data-engineer.md     # Specialized subagent for Claude Code (State 0-6 Lakehouse DAG)
└── skills/                         # Physical copy of the 4 bundled skills (sanitized for Claude)
    ├── gcp-data-engineering/       # Architecture decisions: storage, batch/streaming, BQ cost/perf
    ├── cdc-scd-patterns/           # Datastream CDC checklist + SCD Type 0-6 + Dataform scaffolder
    ├── context-capture/            # Persist lakehouse table contracts & SLAs to context/memory/
    └── context-restore/            # Restore known BQ datasets, partition keys & SLAs at State 0
```

---

## 2. The Agent & Role Boundaries

| Agent | Role | Invocation | Allowed Tools |
| :--- | :--- | :--- | :--- |
| **`senior-data-engineer`** | Restores/updates `context/memory/`, designs Bronze/Silver/Gold pipelines, models CDC/SCD, builds parallel `.sqlx` marts (`Mode A: Disjoint Files`), and optimizes BigQuery. | `Agent` | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep` |

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
/plugin install senior-data-engineer
# or local:
claude plugin install plugins/claude/senior-data-engineer
```
