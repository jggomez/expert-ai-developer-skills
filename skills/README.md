# Expert AI Agent Skills Catalog

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Skills Count](https://img.shields.io/badge/Skills-26%20Optimized-orange?style=flat-square)](file:///./)

This directory contains a premium catalog of **26 agent skills** designed to automate code quality checks, enforce programming best practices, detect code smells, validate commit history, and implement self-correcting development loops. Every `SKILL.md` here is platform-neutral (no Antigravity- or Claude-Code-specific tool names in its instructions), so the same catalog works whether you're on Google Antigravity (AGY) or Claude Code.

Seven plugins in this repository bundle physical copies of a subset of these skills so they can be distributed standalone: [`python-backend`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/python-backend) (11 backend skills), [`senior-dev`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/senior-dev) (8 SDLC-orchestration skills), [`git-workflow`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/git-workflow) (2), [`docs-and-quality`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/docs-and-quality) (3), [`multi-agent-ops`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/multi-agent-ops) (2), [`senior-data-engineer`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/senior-data-engineer) (2, GCP-focused), and [`sql-query-optimizer`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/sql-query-optimizer) (2, BigQuery + generic SQL). Edit skills here, then run `python3 scripts/sync_plugin_skills.py` to re-sync all of them.

---

## 1. Quick Installation & Setup

These skills fully comply with the [**Open Agent Skills Standard** (`agentskills.io`)](https://agentskills.io). Therefore, you can install any of these 26 skills out-of-the-box using Vercel's official, standard `skills` CLI.

### Option A: Standard Installation (Recommended)
This is the recommended and simplest way to discover, add, and manage these skills. There's no need for local configuration or downloading extra packages. Simply run:

```bash
# List all 26 skills available in our repository
npx skills add jggomez/expert-ai-developer-skills --list

# Install a specific skill (e.g. python-expert) in the active project (.agents/skills)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert

# Install a specific skill globally on your system (so all your workspaces can load it)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert -g

# Install ALL 26 skills in the active project
npx skills add jggomez/expert-ai-developer-skills
```

### Option B: Manual Copy (Fallback)
If you prefer to copy the directories manually:

```bash
# Manual global installation
mkdir -p ~/.gemini/config/skills
cp -r ./skills/* ~/.gemini/config/skills/
```

---

## 2. In-Depth Skills Catalog Reference

This table provides a comprehensive overview of every modular skill, its core purpose, included reference materials, and accompanying automated execution scripts:

| Skill Directory | Core Purpose & Best Practices | Reference Guides | Key Automation Scripts & Usage |
| :--- | :--- | :--- | :--- |
| **`product-analyst`** | Defines features, gaps, and writes Product Requirements Documents (PRDs). | `SKILL.md` | Requirement discovery workflows. |
| **`qa-tester`** | Constructs End-to-End test suites and maps requirements to E2E tracing. | `SKILL.md` | Executable E2E traceability matrices. |
| **`senior-dev-orchestrator`** | Orchestrates subagents across SDLC (Requirements, Architecture, Code, Test, Audit). | `SKILL.md` | Agent manager workflows. |
| **`code-implementer`** | Writes production code utilizing strict TDD Red-Green-Refactor cycles. | `SKILL.md` | TDD implementation guides. |
| **`compliance-verifier`** | Audits NFRs, security gates, and performs final release readiness checks. | `SKILL.md` | Compliance checklist workflows. |
| **`python-expert`** | Enforces PEP 8 styling, static typing (`mypy`), generator stream tuning, and `__slots__` memory footprint reduction. | `references/python-patterns.md` | Guides AST-based memory checks and object tuning. |
| **`test-driven-development`** | Establishes the Red-Green-Refactor testing lifecycle and Arrange-Act-Assert (AAA) pattern implementation. | `references/testing-patterns.md` | `verify_tests.py` (Runs test suite and prints coverage summaries). |
| **`loop-engineering`** | Orchestrates manager-worker topologies, parallel execution in isolated workspaces, and automated code review crons. | `references/loop-architecture.md` | `run_parallel_agents.py` (Manager orchestrator)<br>`pr_cron_reviewer.py` (30-min review cron). |
| **`documentation-expert`** | Standardizes structural hierarchy and graphical representations using the Diátaxis framework and Mermaid.js. | `references/diataxis-framework.md`<br>`references/mermaid-guide.md` | `validate_docs.py` (Statically checks markdown layouts and verifies 0 absolute path leaks). |
| **`testing-expert`** | BDD Gherkin specs and general testing best practices (AAA, hermeticity, mocking borders). | `references/testing-best-practices.md`<br>`references/gherkin-syntax.md` | `validate_gherkin.py` (Statically checks Gherkin `.feature` syntax consistency). |
| **`pull-request-expert`** | Enforces atomic code integration, size limit constraints, and standard PR templates. | `references/pr-best-practices.md` | `validate_pr_content.py` (Audits branch naming conventions and conventional commits). |
| **`commit-expert`** | Configures git history quality checkpoints and local commit-msg hooks. | `references/commit-guidelines.md`<br>`references/git-hooks-setup.md` | `validate_commit_msg.py` (Checks commit formats against Conventional Commits standards). |
| **`code-smells-expert`** | Identifies God classes, long methods, high conditional complexities, and coding anti-patterns. | `references/smells-catalog.md` | `detect_smells.py` (AST-based static analyzer for code smell scanning). |
| **`refactoring-code-expert`** | Outlines safe structural improvements (extract function, introduce parameter object). | `references/refactoring-techniques.md` | `run_tests.py` (Detects and executes tests before/after refactoring). |
| **`security-audit`** | Scans code against OWASP Top 10 vulnerabilities, injection flaws, and hardcoded API tokens. | `references/owasp-checklist.md` | `secret_scanner.py` (Regex scanner to audit code for leaked credentials). |
| **`performance-scalability`**| Diagnoses database N+1 queries, nested loop complexities, and blocking calls. | `references/scalability-patterns.md` | `measure_performance.py` (Execution profiler for CPU and memory usage). |
| **`database-migration-expert`**| Outlines safe, zero-downtime database migrations (Alembic) and idempotent seeding. | `references/migration-patterns.md` | Prevents locking production databases during schema updates. |
| **`senior-architect-engineering`**| Standardizes Architectural Decision Records (ADRs) and structural patterns. | `references/architecture-patterns.md` | `create_adr.py` (Scaffolds standardized markdown ADR files). |
| **`design-spec-expert`** | Scaffolds high-level Software Design Documents (SDDs) before starting coding tasks. | `references/design-standards.md` | `create_sdd.py` (Generates design templates). |
| **`build-and-ci-gates`** | Enforces local check gates, multi-stage Docker builds, and Git pre-commit triggers. | `references/ci-templates.md` | `run_checks.py` (Black/Ruff linter gate wrapper)<br>`pre_commit_quality_gate.py` (Pre-commit hook). |
| **`repo-research`** | Automatically maps workspace packages, dependency trees, and sitemaps. | `references/research-patterns.md` | `repo_analyzer.py` (Statically generates up-to-date repository indexes). |
| **`guidelines-karpathy`** | Behavioral quality checklist to reduce common LLM coding pitfalls. | `references/karpathy-checklist.md` | Prevents over-engineering and keeps logic atomic. |
| **`gcp-data-engineering`** | Architecture decisions for GCP pipelines: lake/warehouse design, batch vs. streaming, orchestration tool choice, BigQuery cost/performance. | `references/gcp-data-stack.md` | Guides Datastream/Dataform/Pub-Sub/Airflow selection via a decision checklist. |
| **`cdc-scd-patterns`** | Change Data Capture via Datastream and Slowly Changing Dimension (Type 0-6) modeling in BigQuery/Dataform. | `references/scd-type2-sql.md` | `scaffold_scd2_dataform.py` (Generates a parameterized SCD Type 2 `.sqlx` template). |
| **`bigquery-query-optimization`** | Diagnoses BigQuery query plans (skew, shuffle) and rewrites queries: partition/cluster pruning, JOIN ordering, approximate functions, SQL vs. JS UDFs. | `references/bigquery-optimization-patterns.md` | `lint_sql_query.py` (Scans directories/code for SQL anti-patterns, no live connection needed). |
| **`sql-query-optimization`** | EXPLAIN ANALYZE, indexing strategy, and pagination for Postgres/MySQL/SQL Server and other traditional engines. | `SKILL.md` | Diagnostic workflow for reading execution plans. |

---

## 3. Automation Scripts Reference Manual

Every script in the catalog is self-contained, executable, and designed to run from the command line:

### 3.1 Gherkin Feature Validator
Checks Gherkin feature files for syntax errors:
```bash
python3 ./skills/testing-expert/scripts/validate_gherkin.py
```

### 3.2 PR and Commit Validator
Validates local git branches and recent commit histories:
```bash
python3 ./skills/pull-request-expert/scripts/validate_pr_content.py
```

### 3.3 Commit Message Hook Validator
Validates formatting of commit message files (used as a Git `commit-msg` hook):
```bash
python3 ./skills/commit-expert/scripts/validate_commit_msg.py .git/COMMIT_EDITMSG
```

### 3.4 Pre-Commit Quality Gate
Runs all linting, testing, and secret scanner checks on staged changes:
```bash
python3 ./skills/build-and-ci-gates/scripts/pre_commit_quality_gate.py
```

### 3.5 Documentation Link & Hierarchy Validator
Checks markdown layout nesting and validates relative paths:
```bash
python3 ./skills/documentation-expert/scripts/validate_docs.py
```

---

## 4. Example Activation Prompts

A skill activates when its `description` matches what you ask for — you don't need to name it explicitly, but doing so (as in these examples) guarantees the right one loads. Type any of these directly in a Claude Code or Antigravity chat:

| Skill | Example Prompt |
| :--- | :--- |
| `product-analyst` | "Use the product-analyst skill to turn this feature request into a PRD with functional and non-functional requirements." |
| `qa-tester` | "Write an E2E test suite for the checkout flow and map each test to its requirement." |
| `senior-dev-orchestrator` | "Orchestrate the full SDLC for adding a password-reset feature — requirements, design, implementation, tests, and a final audit." |
| `code-implementer` | "Implement the new /invoices endpoint using strict TDD — write the failing test first." |
| `compliance-verifier` | "Audit this branch for release readiness: NFRs, security gates, and test coverage." |
| `python-expert` | "Review this Python module for PEP 8 compliance, type hints, and memory efficiency." |
| `test-driven-development` | "Add a new feature to the billing module following Red-Green-Refactor." |
| `loop-engineering` | "Provision isolated worktrees for these 3 features so I can dispatch a subagent per branch." |
| `documentation-expert` | "Write a README for this service following the Diátaxis framework, with a Mermaid architecture diagram." |
| `testing-expert` | "Write Gherkin BDD scenarios for the user login flow." |
| `pull-request-expert` | "Prepare this branch for a pull request — check size, commit style, and generate the PR description." |
| `commit-expert` | "Write a Conventional Commits message for these staged changes." |
| `code-smells-expert` | "Scan this module for code smells — God classes, long methods, high complexity." |
| `refactoring-code-expert` | "Refactor this function to extract the validation logic, without changing its behavior." |
| `security-audit` | "Run a security audit on this codebase for OWASP Top 10 issues and hardcoded secrets." |
| `performance-scalability` | "Profile this endpoint for N+1 queries and suggest caching opportunities." |
| `database-migration-expert` | "Write a zero-downtime Alembic migration to add a NOT NULL column to the users table." |
| `senior-architect-engineering` | "Draft an ADR comparing event-driven vs. request-response for this integration." |
| `design-spec-expert` | "Scaffold a Software Design Document for the new notifications service." |
| `build-and-ci-gates` | "Set up a GitHub Actions workflow that runs lint, tests, and the pre-commit quality gate." |
| `repo-research` | "Analyze this repository and generate a project context document." |
| `guidelines-karpathy` | "Before implementing this, check it against the Karpathy guidelines — are we overcomplicating it?" |
| `gcp-data-engineering` | "Design the architecture for a pipeline that lands daily CSV exports into BigQuery." |
| `cdc-scd-patterns` | "Design a CDC pipeline from Cloud SQL into BigQuery and model the customer dimension as SCD Type 2." |
| `bigquery-query-optimization` | "Scan this repo for slow BigQuery queries and optimize whatever you find." |
| `sql-query-optimization` | "Run EXPLAIN ANALYZE on this query and tell me if it needs an index." |
