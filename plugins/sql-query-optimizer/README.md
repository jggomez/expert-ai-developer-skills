# SQL Query Optimizer Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-sql--query--optimizer-green?style=flat-square)](file:///./)

The `sql-query-optimizer` plugin finds and rewrites slow SQL — standalone `.sql` files and queries embedded in application code — for **both Antigravity CLI and Claude Code**: one subagent, two skills (BigQuery-specific, and generic SQL for traditional engines), and direct MCP access to BigQuery and Cloud SQL for real query plans.

**Antigravity CLI users**: the subagent installs from the root [`agents/sql-query-optimizer.md`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents/sql-query-optimizer.md) — not this plugin folder's `agents/` — since Claude Code and Antigravity use incompatible subagent frontmatter. This plugin folder's `mcp_config.json` (Antigravity's MCP format) still applies either way.

Built from Google Cloud's own "Query Processing and Optimization" training material (partitioning/clustering pruning, JOIN ordering, shuffle/skew, broadcast vs. hash joins, approximate functions) plus general cross-engine practices (EXPLAIN ANALYZE, indexing, avoiding functions on indexed columns).

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog. After editing either skill under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/sql-query-optimizer/
├── README.md                       # This usage manual
├── plugin.json                     # Required plugin metadata descriptor
├── .mcp.json                       # BigQuery + Cloud SQL — Claude Code's remote MCP format
├── mcp_config.json                 # Same 2 servers, Antigravity's format (serverUrl + authProviderType)
├── agents/
│   └── sql-query-optimizer.md      # The subagent (Claude Code only — Antigravity's copy lives at the repo root)
└── skills/
    ├── bigquery-query-optimization/  # Query plan diagnosis, JOIN/skew/partitioning rules, a static SQL linter
    └── sql-query-optimization/       # EXPLAIN ANALYZE, indexing, pagination — for Postgres/MySQL/etc.
```

---

## 2. The Agent

| Agent | Role | Model | Tools |
| :--- | :--- | :--- | :--- |
| `sql-query-optimizer` | Scans directories for `.sql` files and embedded queries, identifies the SQL dialect, diagnoses from the real query plan when it can reach one via MCP, and rewrites queries with an Original/Optimized/Reasoning explanation. | `sonnet` | Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion |

One agent, not a panel — this is a single area of expertise. It picks the right skill (`bigquery-query-optimization` vs. `sql-query-optimization`) based on the SQL dialect it finds, rather than applying BigQuery-specific advice (like "put the largest JOIN table first") to a Postgres query or vice versa.

---

## 3. Finding Queries in a Codebase

Point the agent at a project directory (not just a single pasted query) and it runs the bundled static linter first to find every candidate before diagnosing anything:
```bash
python3 ./skills/bigquery-query-optimization/scripts/lint_sql_query.py [path]   # defaults to "."
```
This recursively finds standalone `.sql` files **and** SQL embedded as string literals in `.py`, `.js`, `.ts`, `.java`, `.go`, `.rb`, and `.scala` files, flagging `SELECT *`, unbounded `ORDER BY`, avoidable `REGEXP_CONTAINS`, `COUNT(DISTINCT ...)`, and JavaScript UDFs — all detectable from the SQL text alone, no live database connection required.

What the static linter **can't** catch — JOIN ordering, skewed JOINs, missing indexes, partition/cluster pruning — needs the real query plan. That's what the MCP servers below are for.

---

## 4. Model Context Protocol (`.mcp.json` / `mcp_config.json`)

Two of Google's own **remote** MCP servers, registered for both hosts:

| Server | Covers |
| :--- | :--- |
| `bigquery` | Dry-run query cost estimates, `INFORMATION_SCHEMA.JOBS` for real query plan stats, dataset/table metadata |
| `cloudsql` | Read-only query execution — run `EXPLAIN ANALYZE` against a real Postgres/MySQL instance |

The `bigquery` server here is the same one already used by `plugins/senior-data-engineer` — reused, not duplicated.

**Auth differs by host**: Claude Code handles OAuth natively (browser consent flow, no embedded credentials needed). Antigravity's `mcp_config.json` uses `authProviderType: "google_credentials"` instead, relying on Application Default Credentials (`gcloud auth application-default login`).

---

## 5. Bundled Skills (2 Packaged Modules)

1. **`bigquery-query-optimization`**: 16 optimization rules distilled from Google Cloud's official training material — query plan diagnosis (skew, shuffle, CPU-bound stages), partitioning/clustering pruning, JOIN ordering and broadcast vs. shuffle joins, join explosions, `WHERE` clause selectivity, `ORDER BY`+`LIMIT`, approximate functions, SQL vs. JS UDFs, persistent UDFs, and query cache mechanics. Includes `lint_sql_query.py`, a static anti-pattern scanner for directories and embedded code.
2. **`sql-query-optimization`**: dialect-agnostic practices for Postgres/MySQL/SQL Server and similar engines — reading `EXPLAIN ANALYZE`, indexing strategy, avoiding functions on indexed columns, JOIN vs. correlated subquery, and keyset pagination for deep offsets.

---

## 6. Example Prompts

- "Scan this repo for slow SQL and optimize whatever you find." (directory-wide scan via the linter, then diagnosis per query)
- "Optimize this BigQuery query — it's scanning 2 TB and I don't know why." (paste the query; `bigquery-query-optimization` applies)
- "Why is this query hitting Resources Exceeded?" (`bigquery-query-optimization` — likely an unbounded ORDER BY)
- "This report generator has a query embedded in it somewhere — find it and check it for anti-patterns." (uses `lint_sql_query.py`'s embedded-SQL detection)
- "Run EXPLAIN ANALYZE on this query against our Postgres instance and tell me if it needs an index." (uses the `cloudsql` MCP tool, `sql-query-optimization` skill)
- "Review the JOIN order in this query — is it BigQuery-optimal?" (`bigquery-query-optimization`'s largest-table-first rule)

---

## 7. Installation

**Claude Code**:
```bash
cp -r ./plugins/sql-query-optimizer ~/.claude/plugins/sql-query-optimizer
```

**Antigravity CLI** — the subagent comes from the root `agents/` directory, not this plugin folder:
```bash
mkdir -p ~/.gemini/config/agents/ ~/.gemini/config/plugins/sql-query-optimizer
cp agents/sql-query-optimizer.md ~/.gemini/config/agents/
cp plugins/sql-query-optimizer/mcp_config.json plugins/sql-query-optimizer/plugin.json ~/.gemini/config/plugins/sql-query-optimizer/
cp -r plugins/sql-query-optimizer/skills ~/.gemini/config/plugins/sql-query-optimizer/
```
