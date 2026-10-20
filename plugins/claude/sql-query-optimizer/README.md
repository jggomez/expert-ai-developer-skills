# SQL Query Optimizer Plugin (Claude Code)

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](https://github.com/jggomez/expert-ai-developer-skills)
[![Plugin](https://img.shields.io/badge/Plugin-sql--query--optimizer-green?style=flat-square)](.)

The `sql-query-optimizer` plugin finds and rewrites slow SQL — standalone `.sql` files and queries embedded in application code — for **Claude Code**: one subagent, four bundled skills (BigQuery-specific optimization, generic SQL optimization for traditional engines, and cross-AI LLM Wiki memory restore/capture), and deterministic safety gates.

- **LLM Wiki Memory (`context/memory/`)**: At the start of an audit, `sql-query-optimizer` silently reads `context/memory/MEMORY.md` (and `architecture.md` on demand) to leverage known table partitioning/clustering keys and indexes. Upon completing a codebase SQL audit, it records significant query optimization baselines and index/partition recommendations into `context/memory/`.

---

## 1. Directory Tree & Architecture

```
plugins/claude/sql-query-optimizer/
├── README.md                       # This usage manual
├── .claude-plugin/
│   └── plugin.json                 # Claude Code plugin manifest
├── .mcp.json                       # BigQuery + Cloud SQL MCP servers
├── hooks.json                      # Hook definitions
├── hooks/
│   └── sql-safety-gate.js          # PreToolUse gate blocking destructive DDL/DML
├── agents/
│   └── sql-query-optimizer.md      # Specialized subagent for Claude Code
└── skills/                         # Physical copy of the 4 bundled skills (sanitized for Claude)
    ├── bigquery-query-optimization/  # Query plan diagnosis, JOIN/skew/partitioning rules, static SQL linter
    ├── sql-query-optimization/       # EXPLAIN ANALYZE, indexing, pagination for Postgres/MySQL/etc.
    ├── context-capture/              # Persist SQL optimization baselines & index/partition recommendations
    └── context-restore/              # Restore known table partitioning/clustering keys from context/memory/
```

---

## 2. The Agent & Role Boundaries

| Agent | Role | Invocation | Allowed Tools |
| :--- | :--- | :--- | :--- |
| **`sql-query-optimizer`** | Restores known schema/partition keys from `context/memory/`, scans codebases, identifies dialects, diagnoses plans, rewrites queries in Original / Optimized / Reasoning format, and persists optimization baselines to `context/memory/`. | `Agent` | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep` |

---

## 3. Lifecycle Hooks & Safety Gates

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`PreToolUse`** | `hooks/sql-safety-gate.js` | Blocks destructive operations (`DROP DATABASE`, `TRUNCATE TABLE`, `DELETE` without `WHERE`); enforces `--dry_run` on `bq query` invocations. |

---

## 4. Bundled Skills (4 Packaged Modules)

1. **`bigquery-query-optimization`**: Query plan diagnosis, partitioning/clustering filter pruning, broadcast join rules, and `lint_sql_query.py`.
2. **`sql-query-optimization`**: EXPLAIN ANALYZE, indexing strategies, and pagination patterns for Postgres/MySQL.
3. **`context-capture`**: Persists significant query optimization baselines and index/partition recommendations into `context/memory/` (`MEMORY.md`, `architecture.md`, `log/YYYY-MM-DD.md`).
4. **`context-restore`**: Silently reads `context/memory/MEMORY.md` (and `architecture.md` on demand) at audit start to leverage known table partitioning and clustering keys.

---

## 5. Installation

```bash
/plugin install sql-query-optimizer
# or local:
claude plugin install plugins/claude/sql-query-optimizer
```
