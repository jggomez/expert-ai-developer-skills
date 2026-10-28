---
trigger: always_on
description: SQL optimization engineering rules enforcing grounded execution plan diagnosis, 3-Tier SQL Optimization Triage, BigQuery dry-runs, partition pruning, structured query rewrites, and LLM Wiki Memory continuity.
---

# SQL Optimization Rules & Performance Protocol

**Identifier**: `sql-optimization-rules`

## 1. The Optimization Execution DAG

Every SQL tuning task must transition through this explicit 6-state sequence:

```
[INIT / USER REQUEST]
         │
         ▼
[STATE 0: MEMORY RESTORE, BRANCH GOVERNANCE & OPTIMIZATION TRIAGE GATE (MANDATORY)]
  ├── 1. Check Git Branch: If base (main/develop), auto-create 'feat/<slug>'; if Scope Drift, ask user
  ├── 2. Derive `<feature-name>` slug & ensure `docs/<feature-name>/` directory is created
  ├── 3. Read `context/memory/MEMORY.md` silently (+ `architecture.md` on demand for keys/indexes)
  └── 4. Author/Update `PLAN.md` with 3-Tier SQL Optimization Triage
         │
         ├───► [TIER 1: FAST-TRACK (Single query anti-pattern / index hint / syntax fix < 2 files)]
         │        ├── Skip discovery & Skip interactive alignment modal (70-85% token & latency savings)
         │        ├── Fast execution: Immediate structured rewrite (Original / Optimized / Reasoning)
         │        └── Quick syntax / dry-run check -> [STATE 5]
         │
         ├───► [TIER 2: STANDARD (Multi-table JOIN / CTE rewrite / window functions)]
         │        ├── STATE 1: Dialect detection & plan capture in docs/<feature-name>/execution-plan.md
         │        ├── STATE 1.5: INTERACTIVE USER ALIGNMENT GATE (ask_question modal before modifying prod SQL)
         │        ├── STATE 2 & 3: Structured rewrite + EXPLAIN / EXPLAIN ANALYZE plan verification
         │        └── STATE 4: Equivalence & Cost Validation in docs/<feature-name>/optimization-report.md -> [STATE 5]
         │
         └───► [TIER 3: MISSION-CRITICAL / COMPLEX (Project-wide SQL audit / partition restructure / skew stress)]
                  ├── STATE 1: Full static linting & baseline profiling in docs/<feature-name>/execution-plan.md
                  ├── STATE 1.5: INTERACTIVE USER ALIGNMENT GATE (ask_question modal sign-off)
                  ├── STATE 2 & 3: Deep refactor (partition pruning, join reordering, skew mitigation)
                  └── STATE 4: ADVERSARIAL VALIDATION:
                           ├── Semantic equivalence & row-count parity check
                           ├── Data skew & boundary stress testing
                           ├── Byte scan & slot reduction verification in docs/<feature-name>/optimization-report.md
                           └── Compliance sign-off
         │
         ▼
[STATE 5: SHIP & LLM WIKI MEMORY UPDATE (MANDATORY)]
  ├── 1. Finalize `PLAN.md` with optimization deliverables
  └── 2. Persist optimization baselines & index/partition recommendations into `context/memory/`
```

## 2. 3-Tier SQL Optimization Triage Specification

At State 0, the optimizer must classify the task into one of three execution tiers and document the triage in `PLAN.md`:

| Dimension / Phase | Tier 1: Fast-Track (Low Complexity) | Tier 2: Standard (Medium Complexity) | Tier 3: Mission-Critical (Complex) |
| :--- | :--- | :--- | :--- |
| **Scope & Triggers** | Single query anti-pattern, index hint, typo, or syntax fix (< 2 files affected). Localized query rewrite. | Multi-table JOIN / CTE rewrite, window functions, complex aggregations, or migration queries (2–4 files/queries). | Project-wide SQL audit across repository, schema partitioning/clustering restructure, core reporting query refactoring. |
| **Discovery (State 1)** | **SKIPPED**: Zero discovery overhead; no `execution-plan.md` or `optimization-report.md` authored. | **SELECTIVE**: Baseline query execution plans documented in `docs/<feature-name>/execution-plan.md`. | **FULL**: Static linting (`lint_sql_query.py`), baseline plan profiling, and skew analysis in `docs/<feature-name>/execution-plan.md`. |
| **Interactive Alignment (State 1.5)** | **SKIPPED**: Auto-proceeds directly to structured rewrite. | **MANDATORY**: Interactive modal (`ask_question`) presenting baseline plan and proposed rewrite strategy. | **MANDATORY**: Strict interactive modal (`ask_question`) requiring explicit user sign-off on plan analysis and index recommendations. |
| **Build & Optimization Mode** | Direct structured rewrite (Original / Optimized / Reasoning). | Plan-verified rewrite with before/after plan comparison. | Deep refactoring, index/partition recommendations, and data skew mitigation. |
| **Verification (State 4)** | Scoped syntax check / BigQuery `--dry_run` verification. | EXPLAIN / EXPLAIN ANALYZE verification + validation documented in `docs/<feature-name>/optimization-report.md`. | Full Adversarial Validation: semantic equivalence proofs, row-count parity, data skew stress, and byte scan bounds in `docs/<feature-name>/optimization-report.md`. |
| **Token & Latency Impact** | **70–85% token & latency savings**. | Balanced overhead with rigorous plan verification. | Maximum depth, empirical verification, and zero regression tolerance. |

## 3. Inviolable Safety & Grounding Boundaries

- **Dry-Run Mandatory for BigQuery**: Never run live analytical queries on BigQuery without performing a `--dry_run` first to assess bytes scanned.
- **Read-Only Invariant**: The optimizer is strictly forbidden from executing destructive DDL or DML (`DROP TABLE`, `DROP SCHEMA`, `DROP DATABASE`, `TRUNCATE TABLE`, bulk `DELETE FROM ... WHERE 1=1`). Optimization modifies query text and recommends indexes, not database schema.
- **Grounding Invariant**: Never guess bottlenecks. Diagnose using actual execution plans, shuffle stages, skew metrics, or explain trees. Avoid vague statements like "this might be faster."
- **Semantic Equivalence Invariant**: Output schema, column names, ordering guarantees, and row-count results must be preserved unless the user explicitly requested behavioral modification.
- **Dialect Isolation**: Strictly distinguish between MPP analytical engines (BigQuery) and row-based relational OLTP engines (PostgreSQL, MySQL). Do not apply BigQuery broadcast rules to PostgreSQL, or PostgreSQL index assumptions to BigQuery.
- **Git Branch Governance**: Never develop or modify query files on protected base branches (`main`, `master`, `develop`, `dev`). Auto-provision a dedicated feature branch (`feat/<slug>` or `fix/<slug>`).

## 4. Mandatory Structured Output Format

Every rewritten query MUST be presented in this explicit 3-part format:
1. **Original Query**: The existing baseline SQL.
2. **Optimized Query**: The rewritten, performant SQL.
3. **Engine-Grounded Rationale**: Exactly which plan stage, partition filter pushdown, index mechanism, or join order improved performance.

## 5. Feature Directory & LLM Wiki Memory Persistence

- **Deliverables**: For Tier 2 and Tier 3 tasks, persist intermediate artifacts into `docs/<feature-name>/`:
  * `docs/<feature-name>/execution-plan.md`
  * `docs/<feature-name>/optimization-report.md`
- **State 5 Memory Persistence**: Upon completing an audit or significant query optimization milestone, update `context/memory/`:
  * Update `context/memory/MEMORY.md` in-place (<= 80-100 lines).
  * Update `context/memory/architecture.md` with new table indexing and partition rules.
  * Append a 5-8 line milestone entry into `context/memory/log/YYYY-MM-DD.md`.
