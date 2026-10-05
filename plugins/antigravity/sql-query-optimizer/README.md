# SQL Query Optimizer Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-sql--query--optimizer-green?style=flat-square)](file:///./)

The `sql-query-optimizer` plugin finds and rewrites slow SQL — standalone `.sql` files and queries embedded in application code — for **Google Antigravity**: one subagent, two skills (BigQuery-specific and generic SQL for traditional engines), direct MCP access to BigQuery and Cloud SQL for real query plans, and deterministic safety gates.

- **Google Antigravity**: Install via `agy plugin install ./plugins/antigravity/sql-query-optimizer`. Subagent in `agents/` declares native Antigravity tools (`run_command`, `write_to_file`, `replace_file_content`, `view_file`, `call_mcp_tool`) with `commandExecutionPolicy: auto`.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing either skill under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/antigravity/sql-query-optimizer/
├── README.md                       # This usage manual
├── plugin.json                     # Antigravity plugin manifest
├── .claude-plugin/
│   └── plugin.json                 # Manifest compatibility marker
├── .mcp.json                       # BigQuery + Cloud SQL MCP servers
├── mcp_config.json                 # Same 2 servers, Antigravity format
├── hooks.json                      # Hook definitions
├── hooks/
│   └── sql-safety-gate.js          # PreToolUse gate blocking destructive DDL/DML
├── agents/
│   └── sql-query-optimizer.md      # Specialized subagent
├── rules/
│   └── sql-optimization-rules.md   # SQL rewrite & execution rules
└── skills/
    ├── bigquery-query-optimization/  # Query plan diagnosis, JOIN/skew/partitioning rules, static SQL linter
    └── sql-query-optimization/       # EXPLAIN ANALYZE, indexing, pagination for Postgres/MySQL/etc.
```

---

## 2. The Agent

| Agent | Role | Execution Policy | Typical Tools |
| :--- | :--- | :--- | :--- |
| **`sql-query-optimizer`** | Scans codebases for `.sql` files and embedded queries, identifies SQL dialects, diagnoses from real plans via MCP, and rewrites queries in structured Original / Optimized / Reasoning format. | `auto` | `run_command`, `write_to_file`, `replace_file_content`, `view_file`, `call_mcp_tool` |

---

## 3. Lifecycle Hooks & Safety Gates

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`PreToolUse`** | `hooks/sql-safety-gate.js` | Blocks destructive operations (`DROP DATABASE`, `TRUNCATE TABLE`, `DELETE` without `WHERE`); enforces `--dry_run` on `bq query` invocations. |

---

## 4. Bundled Skills (2 Packaged Modules)

1. **`bigquery-query-optimization`**: Query plan diagnosis, partitioning/clustering filter pruning, broadcast join rules, and `lint_sql_query.py`.
2. **`sql-query-optimization`**: EXPLAIN ANALYZE, indexing strategies, and pagination patterns for Postgres/MySQL.

---

## 5. Installation

```bash
agy plugin install ./plugins/antigravity/sql-query-optimizer
```
