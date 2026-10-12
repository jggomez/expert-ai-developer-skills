# Expert AI Agent Skills Catalog

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Skills Count](https://img.shields.io/badge/Skills-35%20Canonical%20Skills-orange?style=flat-square)](file:///./)
[![Ecosystem](https://img.shields.io/badge/Distribution-Antigravity%20%26%20Claude-green?style=flat-square)](../plugins)

This directory contains a premium catalog of **35 canonical agent skills** designed to automate code quality checks, enforce programming best practices, detect code smells, validate commit history, and implement self-correcting development loops. Every `SKILL.md` in `/skills/` is platform-neutral, adhering to the open [Agent Skills Standard (`agentskills.io`)](https://agentskills.io).

---

## 1. Dual-Plugin Distribution & Synchronization

All 9 plugins across both runtime ecosystems bundle physical copies of the skills they need to stay completely self-contained when installed:

* **Google Antigravity**: `plugins/antigravity/<plugin>/skills/` (receives exact physical copies of canonical skills).
* **Anthropic Claude Code**: `plugins/claude/<plugin>/skills/` (receives physical copies with automated tool sanitization, mapping Antigravity tools to native Claude Code tools: `run_command` &rarr; `Bash`, `write_to_file` &rarr; `Write`, `replace_file_content` &rarr; `Edit`, `invoke_subagent` &rarr; `Agent`).

### Bundled Skills per Plugin (9 Plugins)
1. **`senior-dev`** (11 skills): `senior-dev-orchestrator`, `product-analyst`, `senior-architect-engineering`, `code-implementer`, `code-smells-expert`, `refactoring-code-expert`, `qa-tester`, `compliance-verifier`, `context-capture`, `context-restore`, `loop-engineering`.
2. **`senior-dev-flutter`** (10 skills): `flutter-senior-orchestration`, `flutter-architecture-decisions`, `flutter-review-checklist`, `flutter-test-strategy`, `flutter-performance-profiling`, `flutter-release-engineering`, `flutter-upgrade-migration`, `context-capture`, `context-restore`, `loop-engineering`.
3. **`python-backend`** (14 skills): `python-expert`, `test-driven-development`, `pull-request-expert`, `code-smells-expert`, `refactoring-code-expert`, `security-audit`, `performance-scalability`, `database-migration-expert`, `senior-architect-engineering`, `design-spec-expert`, `build-and-ci-gates`, `context-capture`, `context-restore`, `loop-engineering`.
4. **`senior-data-engineer`** (4 skills): `gcp-data-engineering`, `cdc-scd-patterns`, `context-capture`, `context-restore`.
5. **`sql-query-optimizer`** (4 skills): `bigquery-query-optimization`, `sql-query-optimization`, `context-capture`, `context-restore`.
6. **`shared-context`** (2 skills): `context-capture`, `context-restore`.
7. **`git-workflow`** (2 skills): `commit-expert`, `pull-request-expert`.
8. **`docs-and-quality`** (3 skills): `documentation-expert`, `testing-expert`, `guidelines-karpathy`.
9. **`multi-agent-ops`** (2 skills): `loop-engineering`, `repo-research`.

### Synchronization Command
Canonical skills are authored and edited in `/skills/`. Run the synchronization script to propagate edits to all 18 plugin locations across both ecosystems:

```bash
python3 scripts/sync_plugin_skills.py
```

---

## 2. Quick Installation & Setup via Skills CLI

These skills fully comply with the [**Open Agent Skills Standard** (`agentskills.io`)](https://agentskills.io). Therefore, you can install any of these 35 skills out-of-the-box using Vercel's official, standard `skills` CLI.

### Option A: Standard Installation (Recommended)
This is the simplest way to discover, add, and manage these skills:

```bash
# List all 35 skills available in our repository
npx skills add jggomez/expert-ai-developer-skills --list

# Install a specific skill (e.g. python-expert) in the active project (.agents/skills)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert

# Install a specific skill globally on your system
npx skills add jggomez/expert-ai-developer-skills --skill python-expert -g

# Install ALL 35 skills in the active project
npx skills add jggomez/expert-ai-developer-skills
```

### Option B: Manual Setup
```bash
# Manual global installation
mkdir -p ~/.gemini/config/skills
cp -r ./skills/* ~/.gemini/config/skills/
```

---

## 3. In-Depth Skills Catalog Reference (35 Skills)

| Skill Directory | Core Purpose & Best Practices | Reference Guides | Key Automation Scripts & Usage |
| :--- | :--- | :--- | :--- |
| **`product-analyst`** | Defines features, gaps, and writes Product Requirements Documents (PRDs). | `SKILL.md` | Requirement discovery workflows. |
| **`qa-tester`** | Constructs End-to-End test suites and maps requirements to E2E tracing. | `SKILL.md` | Executable E2E traceability matrices. |
| **`senior-dev-orchestrator`** | Orchestrates subagents across the 6-State SDLC DAG (Memory Restore & Triage Gate, Upfront Discovery, Parallel Build, Parallel QA & Audit, Ship). | `SKILL.md` | Agent manager workflows. |
| **`code-implementer`** | Writes production code utilizing strict TDD Red-Green-Refactor cycles. | `SKILL.md` | TDD implementation guides. |
| **`compliance-verifier`** | Audits NFRs, security gates, and performs final release readiness checks. | `SKILL.md` | Compliance checklist workflows. |
| **`python-expert`** | Enforces PEP 8 styling, static typing (`mypy`), generator stream tuning, and `__slots__` memory footprint reduction. | `references/python-patterns.md` | Guides AST-based memory checks and object tuning. |
| **`test-driven-development`** | Establishes the Red-Green-Refactor testing lifecycle, AAA patterns, cross-language patterns (`pytest`, Flutter `testWidgets`, Dataform). | `references/testing-patterns.md` | `verify_tests.py` (Runs test suite and prints coverage summaries). |
| **`loop-engineering`** | Orchestrates manager-worker topologies, parallel execution via Mode A (Disjoint File Partitioning) and Mode B (Git Worktree Isolation), self-correction protocol with 3-loop cap, and PR review crons. | `references/loop-architecture.md` | `run_parallel_agents.py` (Manager orchestrator)<br>`pr_cron_reviewer.py` (PR review cron). |
| **`documentation-expert`** | Standardizes structural hierarchy and graphical representations using the Diátaxis framework and Mermaid.js. | `references/diataxis-framework.md`<br>`references/mermaid-guide.md` | `validate_docs.py` (Statically checks markdown layouts and verifies 0 absolute path leaks). |
| **`testing-expert`** | BDD Gherkin specs and general testing best practices (AAA, hermeticity, mocking borders). | `references/testing-best-practices.md`<br>`references/gherkin-syntax.md` | `validate_gherkin.py` (Statically checks Gherkin `.feature` syntax consistency). |
| **`pull-request-expert`** | Enforces atomic code integration, size limit constraints, and standard PR templates. | `references/pr-best-practices.md` | `validate_pr_content.py` (Audits branch naming conventions and conventional commits). |
| **`commit-expert`** | Configures git history quality checkpoints, Conventional Commits regex, and local commit-msg hooks aligned with branch gates. | `references/commit-guidelines.md`<br>`references/git-hooks-setup.md` | `validate_commit_msg.py` (Checks commit formats against Conventional Commits standards). |
| **`code-smells-expert`** | Identifies God classes, long methods, high conditional complexities, and coding anti-patterns. | `references/smells-catalog.md` | `detect_smells.py` (AST-based static analyzer for code smell scanning). |
| **`refactoring-code-expert`** | Outlines safe structural improvements (extract function, introduce parameter object). | `references/refactoring-techniques.md` | `run_tests.py` (Detects and executes tests before/after refactoring). |
| **`security-audit`** | Scans code against OWASP Top 10 vulnerabilities, injection flaws, and hardcoded API tokens. | `references/owasp-checklist.md` | `secret_scanner.py` (Regex scanner to audit code for leaked credentials). |
| **`performance-scalability`**| Diagnoses database N+1 queries, nested loop complexities, and blocking calls. | `references/scalability-patterns.md` | `measure_performance.py` (Execution profiler for CPU and memory usage). |
| **`database-migration-expert`**| Outlines safe, zero-downtime database migrations (Alembic) and idempotent seeding. | `references/migration-patterns.md` | Prevents locking production databases during schema updates. |
| **`senior-architect-engineering`**| Standardizes Architectural Decision Records (ADRs) and structural patterns. | `references/architecture-patterns.md` | `create_adr.py` (Scaffolds standardized markdown ADR files). |
| **`design-spec-expert`** | Scaffolds high-level Software Design Documents (SDDs) before starting coding tasks. | `references/design-standards.md` | `create_sdd.py` (Generates design templates). |
| **`build-and-ci-gates`** | Enforces local check gates, multi-stage Docker builds, and Git pre-commit triggers. | `references/ci-templates.md` | `run_checks.py` (Black/Ruff linter gate wrapper)<br>`pre_commit_quality_gate.py` (Pre-commit hook). |
| **`repo-research`** | Automatically maps workspace packages, dependency trees, and sitemaps. | `references/research-patterns.md` | `repo_analyzer.py` (Statically generates up-to-date repository indexes). |
| **`guidelines-karpathy`** | Behavioral quality checklist, Anti-Lazy Code policy (anti-lazy-code-gate.js), and Anti-Premature Abstraction rules. | `references/karpathy-checklist.md` | Prevents over-engineering and keeps logic atomic. |
| **`gcp-data-engineering`** | Architecture decisions for GCP pipelines: lake/warehouse design, batch vs. streaming, orchestration tool choice, BigQuery cost/performance. | `references/gcp-data-stack.md` | Guides Datastream/Dataform/Pub-Sub/Airflow selection via a decision checklist. |
| **`cdc-scd-patterns`** | Change Data Capture via Datastream and Slowly Changing Dimension (Type 0-6) modeling in BigQuery/Dataform. | `references/scd-type2-sql.md` | `scaffold_scd2_dataform.py` (Generates a parameterized SCD Type 2 `.sqlx` template). |
| **`bigquery-query-optimization`** | Diagnoses BigQuery query plans (skew, shuffle) and rewrites queries: partition/cluster pruning, JOIN ordering, approximate functions, SQL vs. JS UDFs. | `references/bigquery-optimization-patterns.md` | `lint_sql_query.py` (Scans directories/code for SQL anti-patterns, no live connection needed). |
| **`sql-query-optimization`** | EXPLAIN ANALYZE, indexing strategy, and pagination for Postgres/MySQL/SQL Server and other traditional engines. | `SKILL.md` | Diagnostic workflow for reading execution plans. |
| **`context-capture`** | Updates the 2-tier Cross-AI LLM Wiki (`context/memory/MEMORY.md`, `architecture.md`, `conventions.md`, `log/YYYY-MM-DD.md`) at task completion (`State 5`) and optionally archives heavy session snapshots into `context/sessions/`. | `references/record-schema.md` | `context_snapshot.py` (scaffold + git snapshot)<br>`context_pack.py` (compress/decompress)<br>`context_rollup.py` (architecture log + retention). |
| **`context-restore`** | Silently loads `context/memory/MEMORY.md` at `State 0` (Memory Restore & Triage Gate) and fetches relevant topic pages (`architecture.md`, `conventions.md`) or legacy `context/sessions/` archives on demand. | `references/restore-checklist.md` | `context_list.py` (read-only session listing; `exists` boolean for hooks). |
| **`flutter-architecture-decisions`** | Choosing Flutter state management (Riverpod/Bloc/signals/setState), drawing package/module boundaries, and recording Flutter ADRs. Complements the official `flutter-apply-architecture-best-practices`. | `references/state-management-decision-matrix.md`<br>`references/adr-template.md` | Decision matrix + ADR template. |
| **`flutter-review-checklist`** | Senior Flutter code review: rebuild scope, `const`, keys, dispose/leaks, `BuildContext` after `await`, list/image perf, `RepaintBoundary`, a11y semantics, golden coverage. | `references/flutter-review-checklist.md` | `flutter_project_audit.py` (file-only project audit: SDK constraints, lint strictness, test/coverage, flavors, `lib/` smells). |
| **`flutter-test-strategy`** | Deciding what to test at which layer (unit/widget/golden/integration) and setting coverage gates. Routes to the official Flutter/Dart how-to test skills. | `references/test-pyramid-flutter.md` | Layer decision matrix + worked examples. |
| **`flutter-performance-profiling`** | Diagnosing Flutter jank and slow startup with DevTools timeline, profile mode, the UI/raster thread split, shader jank, and `--trace-startup`; fix by symptom. | `references/jank-hunting-playbook.md` | Symptom→cause→fix table + step-by-step playbook. |
| **`flutter-release-engineering`** | Shipping a Flutter app: build flavors + `--dart-define-from-file`, signing, the `flutter build` matrix, version/build-number, store metadata, and the OTA (Shorebird) decision. | `references/flavors-and-config.md` | Build matrix + `AppConfig` pattern. |
| **`flutter-upgrade-migration`** | Project-scale Flutter/Dart SDK upgrades, dependency major bumps, and deprecation sweeps — the ordered upgrade plan around `dart fix` / `dart-resolve-package-conflicts`. | `SKILL.md` | Ordered upgrade sweep + deprecation triage. |
| **`flutter-senior-orchestration`** | The phase map for running a Flutter feature/fix end to end — sizes the task, sequences the official skills, routes phases to the Flutter subagents. | `SKILL.md` | Task-sizing table + phase breakdown. |

---

## 4. Automation Scripts Reference Manual

Every script in the catalog is self-contained, executable, and designed to run from the command line:

### 4.1 Gherkin Feature Validator
Checks Gherkin feature files for syntax errors:
```bash
python3 ./skills/testing-expert/scripts/validate_gherkin.py
```

### 4.2 PR and Commit Validator
Validates local git branches and recent commit histories:
```bash
python3 ./skills/pull-request-expert/scripts/validate_pr_content.py
```

### 4.3 Commit Message Hook Validator
Validates formatting of commit message files (used as a Git `commit-msg` hook):
```bash
python3 ./skills/commit-expert/scripts/validate_commit_msg.py .git/COMMIT_EDITMSG
```

### 4.4 Pre-Commit Quality Gate
Runs all linting, testing, and secret scanner checks on staged changes:
```bash
python3 ./skills/build-and-ci-gates/scripts/pre_commit_quality_gate.py
```

### 4.5 Documentation Link & Hierarchy Validator
Checks markdown layout nesting and validates relative paths:
```bash
python3 ./skills/documentation-expert/scripts/validate_docs.py
```

### 4.6 Shared Context Store (cross-agent hand-off)
Records/loads what a session did, decided, and how, so a different AI agent can resume it. Stdlib-only; `context/` defaults to the current repo:
```bash
python3 ./skills/context-capture/scripts/context_snapshot.py --task "<one line>" --agent "<model id>"
python3 ./skills/context-capture/scripts/context_rollup.py     # decisions -> architecture.md + retention
python3 ./skills/context-capture/scripts/context_pack.py --auto # compress all but the newest sessions
python3 ./skills/context-restore/scripts/context_list.py --json # what prior sessions exist (used by the hooks)
```

### 4.7 Flutter Project Audit
File-only audit of a Flutter/Dart project (no `flutter`/`dart` binary needed): SDK constraints, lint strictness, test & coverage setup, flavors, and `lib/` smells:
```bash
python3 ./skills/flutter-review-checklist/scripts/flutter_project_audit.py [PROJECT_DIR] [--json] [--strict]
```
