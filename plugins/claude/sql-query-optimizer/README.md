# SQL Query Optimizer Plugin (Claude Code)

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-sql--query--optimizer-green?style=flat-square)](file:///./)

The `sql-query-optimizer` plugin finds and rewrites slow SQL — standalone `.sql` files and queries embedded in application code — for **Claude Code**: one subagent, two skills (BigQuery-specific and generic SQL for traditional engines), and deterministic safety gates.

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
└── skills/
    ├── bigquery-query-optimization/  # Query plan diagnosis, JOIN/skew/partitioning rules, static SQL linter
    └── sql-query-optimization/       # EXPLAIN ANALYZE, indexing, pagination for Postgres/MySQL/etc.
```

---

## 2. The Agent & Role Boundaries

| Agent | Role | Invocation | Allowed Tools |
| :--- | :--- | :--- | :--- |
| **`sql-query-optimizer`** | Scans codebases, identifies dialects, diagnoses plans, and rewrites queries with structured Original / Optimized / Reasoning output. | `Agent` | `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep` |

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
/plugin install sql-query-optimizer
# or local:
claude plugin install plugins/claude/sql-query-optimizer
```
