---
trigger: always_on
description: SQL optimization rules enforcing 3-Tier Triage, Selective Artifact Gating, Target AGENTS.md, LLM Wiki Memory, BigQuery dry-runs, and Fail-Honest STATIC_ANALYSIS_ONLY / BLOCKED plan reporting.
---

# SQL Optimization Rules & Performance Protocol

**Identifier**: `sql-optimization-rules`

## 1. 3-Tier SQL Optimization Triage & Selective Artifact Gating
Classify every task at State 0 in `PLAN.md` (`<= 50 lines`) and maintain root `AGENTS.md` (`<= 90 lines` + `context/memory/MEMORY.md`) when auditing target repositories:

| Phase | Tier 1: Fast-Track | Tier 2: Standard | Tier 3: Mission-Critical |
| :--- | :--- | :--- | :--- |
| **Scope** | Inline single-query anti-pattern, index hint, syntax fix (`< 2` files). | Multi-table JOIN/CTE/window rewrite (`2–4` files/queries). | Repo-wide SQL audit, partition/cluster restructure, high-skew core query refactor. |
| **State 1 & 1.5** | **SKIP** `execution-plan.md` & `ask_question` modal (70–85% savings). | Gated `docs/<feature-name>/execution-plan.md` (`<= 50 lines`) + `ask_question` modal. | `lint_sql_query.py` + `execution-plan.md` (`<= 50 lines`) + strict `ask_question` sign-off. |
| **Rewrite & QA** | Inline 3-part rewrite + syntax/`--dry_run` check. | Plan-verified rewrite + `docs/<feature-name>/optimization-report.md` (`<= 55 lines`). | Parity/skew validation + `docs/<feature-name>/optimization-report.md` (`<= 55 lines`). |

- **Selective Artifact Gating**: **SKIP** `docs/<feature-name>/execution-plan.md` (`<= 50 lines`) for inline single-query rewrites. Cap `docs/<feature-name>/optimization-report.md` at `<= 55 lines` (Zero-Fluff before/after metrics table + Original / Optimized / Engine-Grounded Reasoning).

## 2. Inviolable Safety, Branch Governance & Fail-Honest Plan Rule
- **Git Branch Governance & Scope Drift**: Never edit query files on protected branches (`main`, `master`, `develop`, `dev`). Inspect `git symbolic-ref --short HEAD` and auto-create `feat/<descriptive-slug>` (or `fix/<slug>`). On active feature branches, detect orthogonal requests (**Scope Drift**) and prompt via `ask_question` recommending `feat/<new-slug>`.
- **Strict Fail-Honest Execution Plan Rule (`STATIC_ANALYSIS_ONLY` / `BLOCKED`)**: If `bq query --dry_run` or DB `EXPLAIN` fails due to missing credentials or unreachable DB, explicitly mark the report `STATIC_ANALYSIS_ONLY` / `BLOCKED: Live plan not executed — <exact error>` and NEVER invent byte-scan numbers, slot times, or `EXPLAIN ANALYZE` latencies!
- **Read-Only & BigQuery Dry-Run Invariants**: Never run destructive DDL/DML (`DROP TABLE`, `DROP SCHEMA`, `DROP DATABASE`, `TRUNCATE TABLE`, bulk `DELETE FROM ... WHERE 1=1`). Always run `--dry_run` before BigQuery analytical queries.
- **Dialect Isolation & Semantic Equivalence**: Strictly separate BigQuery MPP broadcast/partition rules from PostgreSQL/MySQL B-tree/heap rules. Preserve output schemas, filters, and row-count semantics unless explicitly authorized.

## 3. Structured 3-Part Output & LLM Wiki Memory Persistence
- **3-Part Rewrite Format**: Present every rewrite as **1. Original Query**, **2. Optimized Query**, and **3. Engine-Grounded Reasoning** (citing exact scan, partition pruning, index, or join stage mechanics).
- **State 5 Memory Update**: Upon completing an audit or optimization milestone, sync root `AGENTS.md` (`<= 90 lines`) if needed and update `context/memory/MEMORY.md` (`<= 80-100 lines`), `context/memory/architecture.md` (index/partition keys), and `context/memory/log/YYYY-MM-DD.md` (`5-8 lines`).
