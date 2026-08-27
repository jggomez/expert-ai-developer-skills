# Expert AI Developer Skills

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=for-the-badge&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Antigravity](https://img.shields.io/badge/Antigravity-Customizations-orange?style=for-the-badge)](https://github.com/google/antigravity)
[![License](https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge)](LICENSE)

Welcome to **expert-ai-developer-skills**, the premium community repository for Google Antigravity (AGY) and Claude Code agent customizations. This workspace houses a professional-grade suite of **26 platform-neutral developer skills**, refactored RFC 2119 rules, and **seven bundled Claude Code plugins** — each a self-contained slice of the skills catalog, reusing what already exists rather than duplicating capability: `python-backend` (quality gates, Gitflow, security/MCP for Cloud Run & Firebase), `senior-dev` (the full SDLC orchestration topology), `git-workflow` (commit/PR hygiene + Gitflow gate), `docs-and-quality` (documentation & testing standards), `multi-agent-ops` (parallel-agent orchestration & repo research), `senior-data-engineer` (GCP pipeline design, CDC/SCD, with live BigQuery/Datastream/Dataform/Pub-Sub MCP access), and `sql-query-optimizer` (finds and rewrites slow SQL across a codebase, BigQuery-specific and generic).

---

## 1. Quick Clone & Setup

To use or contribute to this suite of skills and plugins, clone the repository using the following SSH endpoint:

```bash
git clone git@github.com:jggomez/expert-ai-developer-skills.git
cd expert-ai-developer-skills
```

---

## 2. Directory Structure & Sitemap

The workspace is cleanly structured into modular **skills** (discrete instructions and automation scripts), **rules** (system constraints for AI agents), **workflows** (playbooks for SDLC processes), **sidecars** (background processes and schedules), and **plugins** (seven self-contained Claude Code plugins, each bundling a subset of the skills catalog):

```
expert-ai-developer-skills/
├── README.md                           # Main community reference guide (this file)
├── agents/                             # Subagent configurations (Orchestrator, Architect, etc.)
├── images/                             # Instagram post design graphics (Overview, Skills, Rules, etc.)
├── rules/
│   ├── README.md                       # Guide on integrating rules into AI agents
│   ├── testing-after-changes.md        # Enforcement rules for running automated tests
│   ├── conventional-commits.md        # Rules for semantic conventional commits and branch safety
│   ├── clean-code-and-principles.md   # Guidelines for SOLID, DRY, KISS, and code smells
│   ├── deployment-restrictions.md     # Production protection and deployment guidelines
│   ├── skills-and-mcp-awareness.md     # Rules for discovering/using Skills & MCP servers
│   ├── secure-coding-and-secrets.md    # Secrets protection and secure coding rules
│   ├── context-and-token-optimization.md # Prompt token minimization and local script execution
│   ├── documentation-and-diagrams.md   # Comment, docstring, README, and Mermaid integrity
│   ├── pull-requests.md                # Pull Request line limits and self-review checklists
│   ├── loop-engineering-workflow.md    # 7-stage cycle with subagent parallelization & auditing
│   └── tdd-best-practices.md           # TDD Red-Green-Refactor enforcement & agent verification
├── tests/
│   ├── README.md                       # Test architecture, subdirectories, & pytest commands
│   ├── structure/                      # Static YAML frontmatter, broken links, & path leak tests
│   ├── unit/                           # Script unit tests (commit-expert, secret_scanner, etc.)
│   ├── behavioral/                     # Trigger description coverage & catalog sync tests
│   └── integration/                    # End-to-end multi-skill integration tests
├── workflows/
│   ├── README.md                       # Guide on executing workflows with AI agents
│   ├── pull-request-workflow.md        # Branch creation and PR preparation playbook
│   ├── commit-workflow.md              # Staging, semantic committing, and pushing workflow
│   ├── test-execution-workflow.md      # Locating, running, and debugging test suites
│   ├── code-smell-review-workflow.md   # Static analysis and SOLID refactoring playbook
│   ├── secure-code-review-workflow.md  # SAST scanning and credentials auditing workflow
│   ├── feature-development-workflow.md # End-to-end SDLC new feature development cycle
│   └── grill-me-alignment-workflow.md   # Interactive design review and requirements gathering playbook
├── sidecars/
│   ├── README.md                       # Guide on deploying Antigravity sidecar daemons
│   ├── pr-reviewer-cron/               # Hourly scheduled PR diff auditor configuration
│   ├── incoming-reviews-alert/         # 30-min scheduled review request monitor configuration
│   └── workspace-daemon/               # Persistent file-watching and auto-formatting daemon
├── skills/
│   ├── README.md                       # Detailed skills catalog & usage instructions
│   ├── python-expert/                  # PEP 8/604, Protocols, slots dataclasses, TaskGroups
│   ├── test-driven-development/        # Red-Green-Refactor cycles & coverage gates
│   ├── loop-engineering/               # Manager-Worker topologies & PR review cron scripts
│   ├── documentation-expert/           # Technical doc validation & Mermaid guides
│   ├── testing-expert/                 # Language-agnostic BDD Gherkin & QA standards
│   ├── pull-request-expert/            # Git branching conventions & atomic PR standards
│   ├── commit-expert/                  # Git commit guidelines & commit-msg hooks
│   ├── code-smells-expert/             # Code debt, high complexity, AST static detectors
│   ├── refactoring-code-expert/        # Standardized refactoring steps & automated tests
│   ├── security-audit/                 # OWASP Top 10 auditing & secrets regex scanner
│   ├── performance-scalability/        # N+1 query checks & CPU/memory profiling tools
│   ├── database-migration-expert/      # Alembic schemas, seeding, & table lock checks
│   ├── senior-architect-engineering/   # SEI Architectural Tactics, ATAM trade-offs, ADRs
│   ├── design-spec-expert/             # Software Design Documents (SDD) scaffolds
│   ├── build-and-ci-gates/             # Pre-commit quality hooks & linter gates
│   ├── repo-research/                  # AST repo trees & dependency path mapping
│   ├── guidelines-karpathy/            # Critical behavioral checks to avoid LLM bugs
│   ├── product-analyst/                # PRD generation and requirement analysis
│   ├── qa-tester/                      # E2E test suites and integration verification
│   ├── senior-dev-orchestrator/        # Subagent orchestration and SDLC lifecycle
│   ├── code-implementer/               # TDD code implementation rules
│   ├── compliance-verifier/            # Final quality, security, and NFR auditing
│   ├── gcp-data-engineering/           # GCP pipeline architecture: storage, batch/streaming, orchestration, BQ cost
│   ├── cdc-scd-patterns/               # Datastream CDC checklist + SCD Type 0-6 + Dataform SCD2 scaffolder
│   ├── bigquery-query-optimization/    # Query plan diagnosis, JOIN/skew/partitioning rules, static SQL linter
│   └── sql-query-optimization/         # EXPLAIN ANALYZE, indexing, pagination for Postgres/MySQL/etc.
└── plugins/
    ├── python-backend/
    │   ├── README.md                   # Plugin installation, hooks, & mcp configurations
    │   ├── plugin.json                 # Required plugin metadata descriptor
    │   ├── .mcp.json                   # Cloud Run + Firebase MCP, Claude Code's format
    │   ├── mcp_config.json             # Same MCP servers, Antigravity's format
    │   ├── hooks.json                  # Lifecycle hooks for both hosts, in one file
    │   ├── hooks/                      # SessionStart, PreToolUse, & Stop event scripts (host-aware JS)
    │   ├── rules/                      # System-wide architecture rules & hook policies
    │   └── skills/                     # Local backend-compatible copy of the skills catalog
    ├── senior-dev/
    │   ├── README.md                   # Plugin installation & subagent panel
    │   ├── plugin.json                 # Required plugin metadata descriptor
    │   ├── .mcp.json                   # Reused Cloud Run / Firebase MCP servers, Claude Code's format
    │   ├── mcp_config.json             # Same MCP servers, Antigravity's format
    │   ├── agents/                     # 6 bundled subagents (orchestrator + 5 specialists) — Claude Code only, see agents/ at root for Antigravity
    │   └── skills/                     # Local copy of the 8 skills those agents depend on
    ├── git-workflow/
    │   ├── README.md                   # Plugin installation & Gitflow gate details
    │   ├── plugin.json                 # Required plugin metadata descriptor
    │   ├── hooks.json                  # PreToolUse hook for both hosts, in one file
    │   ├── hooks/                      # Gitflow branch safety gate (host-aware, extracted from python-backend)
    │   └── skills/                     # commit-expert + pull-request-expert
    ├── docs-and-quality/
    │   ├── README.md                   # Plugin installation & skill summaries
    │   ├── plugin.json                 # Required plugin metadata descriptor
    │   └── skills/                     # documentation-expert + testing-expert + guidelines-karpathy
    ├── multi-agent-ops/
    │   ├── README.md                   # Plugin installation & platform-gap notes
    │   ├── plugin.json                 # Required plugin metadata descriptor
    │   └── skills/                     # loop-engineering + repo-research
    ├── senior-data-engineer/
    │   ├── README.md                   # Plugin installation, MCP servers, known gaps
    │   ├── plugin.json                 # Required plugin metadata descriptor
    │   ├── .mcp.json                   # BigQuery, Datastream, Dataform, Pub/Sub, Claude Code's format
    │   ├── mcp_config.json             # Same 4 servers, Antigravity's format
    │   ├── agents/                     # 1 subagent — Claude Code only, see agents/ at root for Antigravity
    │   └── skills/                     # gcp-data-engineering + cdc-scd-patterns
    └── sql-query-optimizer/
        ├── README.md                   # Plugin installation, MCP servers, example prompts
        ├── plugin.json                 # Required plugin metadata descriptor
        ├── .mcp.json                   # BigQuery + Cloud SQL, Claude Code's format
        ├── mcp_config.json             # Same 2 servers, Antigravity's format
        ├── agents/                     # 1 subagent — Claude Code only, see agents/ at root for Antigravity
        └── skills/                     # bigquery-query-optimization + sql-query-optimization
```

---

## 3. In-Depth Developer Skills (26 Packaged Modules)

Each skill represents an isolated capability loaded with professional guidelines, architectural references, and self-contained command-line automation scripts:

| Skill Directory | Target Capability & Purpose | Key Automated Scripts |
| :--- | :--- | :--- |
| **`product-analyst`** | Generates PRDs, analyzes requirements, and asks clarifying questions. | *Requirement mapping rules* |
| **`qa-tester`** | Constructs End-to-End (E2E) suites and validates business workflows. | *E2E testing guides* |
| **`senior-dev-orchestrator`** | Orchestrates subagents across the SDLC using strict quality gates. | *Orchestration workflow* |
| **`code-implementer`** | Writes production code utilizing strict TDD Red-Green-Refactor cycles. | *TDD guides* |
| **`compliance-verifier`** | Audits NFRs, security gates, and performs final release readiness checks. | *Compliance checklists* |
| **`python-expert`** | PEP 8 styling, static typing (`mypy`), generator stream tuning, and `__slots__` memory footprint reduction. | *AST-based memory checks* |
| ****`test-driven-development`**** | Red-Green-Refactor cycle gatekeeping and Arrange-Act-Assert (AAA) testing standards. | `verify_tests.py` (Coverage checks & runner gate) |
| **`loop-engineering`** | Implements self-correcting agent execution loops, multi-agent parallel workflows, and automated cron auditing. | `run_parallel_agents.py` (Orchestrator)<br>`pr_cron_reviewer.py` (Review cron) |
| **`documentation-expert`** | Enforces structured tech doc hierarchy using the Diátaxis framework and Mermaid.js diagrams. | `validate_docs.py` (Markdown link and absolute path checker) |
| **`testing-expert`** | QA standards, hermetic test boundary guides, and standard Gherkin BDD test suites. | `validate_gherkin.py` (Statically checks Gherkin `.feature` syntax) |
| **`pull-request-expert`** | Atomic integrations, pull request templates, and local/remote integration checks. | `validate_pr_content.py` (Branch naming and commit style parser) |
| **`commit-expert`** | Git history styling, automated conventional commit specifications, and commit hooks. | `validate_commit_msg.py` (Commit message standard validator) |
| **`code-smells-expert`** | Diagnostics for Fowler/Beck code smells (God classes, long methods, high complexity). | `detect_smells.py` (AST-based static code smell analyzer) |
| **`refactoring-code-expert`** | Safe code modification strategies (extract function, introduce parameter object). | `run_tests.py` (Automatic test finder & validator) |
| **`security-audit`** | Code auditing against OWASP Top 10 vulnerabilities and leaked configuration credentials. | `secret_scanner.py` (Regex credential and injection scanner) |
| **`performance-scalability`** | Profiling database N+1 patterns, nested loop complexities, and lockups. | `measure_performance.py` (Execution CPU/Memory profiler) |
| **`database-migration-expert`** | Secure schema migrations (Alembic), zero-downtime alterations, and idempotent seeding. | *Production table locking preventer* |
| **`senior-architect-engineering`**| Standards for writing and organizing Architectural Decision Records (ADRs). | `create_adr.py` (Scaffolds markdown ADR records) |
| **`design-spec-expert`** | Structural specs and templates for producing complete Software Design Documents (SDD). | `create_sdd.py` (Scaffolds professional markdown SDD documents) |
| **`build-and-ci-gates`** | Automated formatting, static checks, linting, and local git pre-commit triggers. | `run_checks.py` (Black, Ruff wrapper)<br>`pre_commit_quality_gate.py` (Hook) |
| **`repo-research`** | Automatically analyzes file tree structures, packages, and dependency maps. | `repo_analyzer.py` (Generates comprehensive workspace indexes) |
| **`guidelines-karpathy`** | Critical checklists to avoid common model generation pitfalls and keep changes surgical. | *Behavioral validation checklist* |
| **`gcp-data-engineering`** | Architecture decisions for GCP pipelines: storage layer, batch vs. streaming, orchestration tool choice, BigQuery cost/performance. | *GCP data stack decision checklist* |
| **`cdc-scd-patterns`** | Change Data Capture via Datastream and Slowly Changing Dimension (Type 0-6) modeling in BigQuery/Dataform. | `scaffold_scd2_dataform.py` (Generates a parameterized SCD Type 2 template) |
| **`bigquery-query-optimization`** | Diagnoses BigQuery query plans (skew, shuffle) and rewrites queries: partition/cluster pruning, JOIN ordering, approximate functions. | `lint_sql_query.py` (Scans directories/embedded code for SQL anti-patterns) |
| **`sql-query-optimization`** | EXPLAIN ANALYZE, indexing strategy, and pagination for Postgres/MySQL/SQL Server and other traditional engines. | *Execution plan diagnostic workflow* |

---

## 4. Python Backend Unified Plugin

The `python-backend` plugin acts as a central control panel that bundles rules, hooks, and configurations to enforce repository-wide safety gates during live sessions.

### 4.1 Global MCP Integrations
Exposes pre-configured, lazy-loaded cloud management integrations:
* **GCP Cloud Run**: Connects `@google-cloud/cloud-run-mcp` to list/deploy services, view logs, and audit revisions.
* **Firebase & Firestore**: Connects `firebase-tools mcp` to query collections, modify documents, and audit security rules.

### 4.2 Editor Execution Hooks
Intercepts editor actions and terminal executions to protect critical assets:
* **Gitflow Branch Safety Gate**: The `PreToolUse` hook intercepts terminal commands. It blocks additions, commits, or pushes directly on protected branches (`main`, `develop`), forcing development into isolated feature branches.
* **Deployment Safety Lock (Force Ask)**: Automatically pauses execution when terminal commands contain deployment keywords or call mutating MCP services. It asks for explicit user approval before proceeding.
* **Quality Gate Stop Gate**: Intercepts task finalization. Before permitting the agent to mark a task complete, it executes the project's unit and integration tests. If tests fail, task termination is blocked.

---

## 5. Senior Dev Orchestration Plugin

This workspace ships the same Loop Engineering subagent topology (Orchestrator + Product Analyst + Architect + Code Implementer + QA Tester + Compliance Verifier) as **two parallel, natively-formatted entry points** over the same shared skills catalog — pick whichever matches your platform, or use both:

| Platform | Entry Point | Format |
| :--- | :--- | :--- |
| **Google Antigravity (AGY)** | root [**`agents/`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents) directory | Antigravity subagent frontmatter (`subagent`, `mainAgent`, `commandExecutionPolicy`, `model: pro/flash`) |
| **Claude Code** | [**`plugins/senior-dev/`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/senior-dev) plugin | Claude Code plugin subagent frontmatter (`tools`, `model: sonnet/haiku`, auto-discovered `agents/` + `skills/`) |

Both entry points reuse the exact same 8 skills, the same agent roles, and the same scaled-pipeline philosophy (the orchestrator sizes the process to the task instead of always running all five subagents) — only the packaging format differs per platform's actual plugin/subagent schema. The `plugins/senior-dev/.mcp.json` reuses the same Cloud Run / Firebase MCP servers already defined for `python-backend`.

---

## 6. Additional Utility Plugins

Three smaller Claude Code plugins split the remaining skills catalog into focused, independently-installable slices — each reuses existing skills/hooks verbatim, adding no new capability of its own:

| Plugin | Bundles | Notes |
| :--- | :--- | :--- |
| [**`git-workflow`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/git-workflow) | `commit-expert`, `pull-request-expert` + a Gitflow branch safety hook | The hook is the Gitflow-check portion of `python-backend`'s `pre-tool-gate.js`, extracted standalone since it has no Python/cloud dependency — usable in any stack. |
| [**`docs-and-quality`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/docs-and-quality) | `documentation-expert`, `testing-expert`, `guidelines-karpathy` | Skills-only, no hooks/MCP — documentation and testing standards for any language. |
| [**`multi-agent-ops`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/multi-agent-ops) | `loop-engineering`, `repo-research` | The two catalog skills not yet bundled anywhere else. Its README documents a real platform gap: Claude Code plugins have no static equivalent to the cron-scheduled `sidecars/` daemons below (§14) — verified against current plugin docs, not assumed. |

---

## 7. Senior Data Engineer Plugin

The [**`senior-data-engineer`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/senior-data-engineer) plugin packages a Google Cloud data engineering expert: one subagent, two skills (`gcp-data-engineering` for architecture decisions, `cdc-scd-patterns` for Change Data Capture and Slowly Changing Dimension modeling specifically), and direct MCP access to **BigQuery, Datastream, Dataform, and Pub/Sub** — Google's own hosted "remote MCP servers" (HTTP + native OAuth; Claude Code handles the browser consent flow itself, no embedded credentials needed).

Researched before building, not assumed: there is no dedicated Dataflow MCP server as of this writing — custom Beam pipelines still go through `gcloud`/Terraform/the Beam SDK directly, and the agent says so rather than pretending otherwise. For a fully autonomous, deployable data agent (not just a chat-based design assistant), the natural next step is Google's [Agent Development Kit](https://adk.dev) (`agents-cli scaffold create`) — a separate, heavier build than this plugin.

---

## 8. SQL Query Optimizer Plugin

The [**`sql-query-optimizer`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/sql-query-optimizer) plugin finds and rewrites slow SQL — both standalone `.sql` files and queries embedded in application code — as one subagent, two skills, and direct MCP access to BigQuery and Cloud SQL for real query plans.

Built from Google Cloud's own "Query Processing and Optimization" training material (`bigquery-query-optimization`: partition/cluster pruning, JOIN ordering, shuffle/skew, approximate functions, SQL vs. JS UDFs) plus generic cross-engine practices (`sql-query-optimization`: EXPLAIN ANALYZE, indexing, keyset pagination) so the same agent handles BigQuery and traditional engines without misapplying one engine's advice to the other. Its bundled `lint_sql_query.py` recursively scans a whole project — `.sql` files and SQL string literals inside `.py`/`.js`/`.ts`/`.java`/`.go`/`.rb`/`.scala` — for text-detectable anti-patterns before any live database connection is needed.

---

## 9. Generic AI Developer Rules (10 Constraint Profiles)

This workspace provides a root-level [**`rules/`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules) directory containing generic, modular developer rules. These rules are designed to be copied directly into AI Agent configuration files (like Cursor `.cursorrules` or Claude Code `.claudecodesettings`) to govern coding, testing, and deployment behavior:

| Rule File | Key Enforcement Constraint | Primary Quality Gate |
| :--- | :--- | :--- |
| [**`testing-after-changes.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/testing-after-changes.md) | Enforces running unit and integration tests after any code edit or feature addition. | Mandatory regression testing + 100% success rate. |
| [**`conventional-commits.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/conventional-commits.md) | Enforces structured semantic commit messages and isolates changes to feature branches. | Gitflow validation + Conventional Commit 1.0 specifications. |
| [**`clean-code-and-principles.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/clean-code-and-principles.md) | Mandates SOLID, DRY, and KISS compliance, actively preventing Fowler/Beck code smells. | God class detection, method length limits, complexity checks. |
| [**`deployment-restrictions.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/deployment-restrictions.md) | Restricts direct local deployment to production/staging and requires sandboxed verification. | Clean workspace verification + environment checks. |
| [**`skills-and-mcp-awareness.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/skills-and-mcp-awareness.md) | Mandates active lookup of local Skills catalog and integration of connected MCP servers. | Prioritizing existing tools over ad-hoc script generation. |
| [**`secure-coding-and-secrets.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/secure-coding-and-secrets.md) | Prevents committing credentials/API tokens and aligns code with OWASP secure design. | Secrets scanning + parameterized SQL injections prevention. |
| [**`context-and-token-optimization.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/context-and-token-optimization.md) | Optimizes token-window consumption through incremental surgical edits and local scripts. | Minimal file views + offloading logic parsing to local runs. |
| [**`documentation-and-diagrams.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/documentation-and-diagrams.md) | Ensures docstrings, README files, and Mermaid diagrams are updated concurrently with changes. | Mermaid diagram validation + comment alignment. |
| [**`pull-requests.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/pull-requests.md) | Mandates PR size limits, structured templates, and agent self-review checklist boundaries. | Local lint/test sweeps + 200-line change target limits. |
| [**`loop-engineering-workflow.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/loop-engineering-workflow.md) | 7-stage cycle (`PLAN->TASK->BUILD->TEST->VERIFICATION->DOCUMENTATION->COMMIT`), scaled to task size, with subagent parallelization. | Manager audit checklist + empirical runtime validation. |
| [**`tdd-best-practices.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/tdd-best-practices.md) | Enforces TDD Red-Green-Refactor cycles, empirical runtime verification, and clean mock boundaries. | 100% test pass + empirical execution proof. |

---

## 10. Generic AI Developer Workflows (7 Execution Playbooks)

This workspace provides a root-level [**`workflows/`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows) directory containing step-by-step developer execution playbooks. These workflows guide developers and AI Agents sequentially through complex tasks:

| Workflow File | Core Execution Sequence | Primary Quality Gate |
| :--- | :--- | :--- |
| [**`pull-request-workflow.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/pull-request-workflow.md) | Branch creation, self-audit sweeps, conflict rebase, and template compilation. | Conflict-free rebase + linted PR template documentation. |
| [**`commit-workflow.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/commit-workflow.md) | Selective file staging, conventional commit header validation, and push triggers. | Pre-commit quality hooks + Conventional Commit alignment. |
| [**`test-execution-workflow.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/test-execution-workflow.md) | Test runner discovery, isolated local targeted runs, and coverage report sweeps. | 100% test pass rate + coverage threshold met. |
| [**`code-smell-review-workflow.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/code-smell-review-workflow.md) | Static metrics scans, class/method size checks, and TDD-backed refactoring. | Cyclomatic Complexity score < 10 (A/B rating). |
| [**`secure-code-review-workflow.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/secure-code-review-workflow.md) | Credentials leaks scanning, SAST tool triggers, and dependency CVE analysis. | 0 credentials staged + 0 SAST severity findings. |
| [**`feature-development-workflow.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/feature-development-workflow.md) | End-to-end SDLC lifecycle from planning/spec design to staging, TDD, and merge. | SDD specifications + full regression checks. |
| [**`grill-me-alignment-workflow.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/workflows/grill-me-alignment-workflow.md) | Codebase pre-research, sequential design tree interview, recommendation matching. | Codebase context verification + resolved design ADR/SDD. |

---

## 11. Custom Loop Engineering Agents (Antigravity Subagents)

This workspace provides a root-level [**`agents/`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents) directory containing definitions for custom agents explicitly designed for execution within the Google Antigravity (AGY) system. They form a complete **Loop Engineering** topology using highly specialized subagents. For the Claude Code equivalent of this same topology, see [**§5 Senior Dev Orchestration Plugin**](#5-senior-dev-orchestration-plugin) and [**`plugins/senior-dev/`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/senior-dev).

| Agent Profile | Role & Specialization | Execution Policy | Assigned Capabilities |
| :--- | :--- | :--- | :--- |
| [**`senior-dev-orchestrator`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents/senior-dev-orchestrator.md) | **Main Orchestrator**: Manages the overarching SDLC lifecycle and tracks final release readiness. | `off` | `invoke_subagent`, `manage_subagents` |
| [**`product-analyst`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents/product-analyst.md) | **Requirements Engineer**: Clarifies ambiguities with the user and constructs detailed PRDs. | `off` | `ask_question`, `write_to_file` |
| [**`architect-engineer`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents/architect-engineer.md) | **System Designer**: Evaluates Quality Attribute Drivers (QADs) and drafts architecture blueprints. | `sandbox` | `write_to_file`, `replace_file_content` |
| [**`code-implementer`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents/code-implementer.md) | **TDD Implementer**: Executes strict Red-Green-Refactor cycles to write production code. | `sandbox` | `write_to_file`, `run_command` |
| [**`qa-tester`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents/qa-tester.md) | **E2E Tester**: Traces requirements back to End-to-End integration test suites. | `sandbox` | `run_command`, `grep_search` |
| [**`compliance-verifier`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents/compliance-verifier.md) | **Quality Auditor**: Verifies strict compliance with NFRs, security gates, and code smells. | `sandbox` | `run_command`, `list_dir` |

---

## 12. Comprehensive Installation Guide

This repository fully adheres to the official [**Open Agent Skills Standard** (`agentskills.io`)](https://agentskills.io). Therefore, other teams or users can install any of these 26 skills out-of-the-box using Vercel's official, standard `skills` CLI.

### 12.1 Standard Skills Installation (Using Vercel's `npx skills`)
This is the recommended and simplest way to discover, add, and manage these skills. They don't need any local setups, just run:

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

### 12.2 Plugin & Hooks Installation (Manual Setup)

**Platform coverage at a glance** — every plugin now installs for both hosts, verified against the official schema for each (`antigravity.google/docs`, `code.claude.com/docs`), not assumed:

| Plugin | Antigravity CLI | Claude Code |
| :--- | :--- | :--- |
| `python-backend` | ✅ same folder — `hooks.json` carries both hosts' hook groups in one file; scripts detect the host and emit the right decision format; `mcp_config.json` added | ✅ same folder — `.mcp.json` |
| `senior-dev` | ✅ via the separate root [`agents/`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents) directory (§11) for the 6 subagents — **not** this plugin folder; `mcp_config.json` added to this plugin folder for the MCP servers | ✅ this plugin folder |
| `git-workflow` | ✅ same folder — `hooks.json` carries both hosts' hook groups; script detects the host | ✅ same folder |
| `docs-and-quality`, `multi-agent-ops` | ✅ same folder — skills-only, no host-specific format to port | ✅ same folder |
| `senior-data-engineer`, `sql-query-optimizer` | ✅ via the root `agents/` directory for the single subagent, plus `mcp_config.json` added to the plugin folder | ✅ this plugin folder |

**Why this took real verification, not a guess**: earlier in this repo's history, `python-backend`'s `hooks.json`/`mcp_config.json` were rewritten to Claude Code's schema (`{"hooks": {...}}`, `.mcp.json` with `type`+`url`) without realizing the *original* format was already correct Antigravity — a real regression, since Antigravity's actual schema (confirmed: named hook groups with an `enabled` flag, events `PreToolUse`/`PostToolUse`/`PreInvocation`/`PostInvocation`/`Stop` — no `SessionStart`; `mcp_config.json` with `serverUrl`/`authProviderType`) is genuinely different from Claude Code's. Both are now supported side by side: `hooks.json` carries a `"hooks"` key for Claude Code and separate named keys for Antigravity in the same file (each host reads only the key it understands); MCP config ships as two separate files (`.mcp.json` and `mcp_config.json`) since the filenames don't collide.

**Two more verified findings, folded in below**:
- **Claude Code's plugin manifest lives at `.claude-plugin/plugin.json`**, a subdirectory — not `plugin.json` at the plugin root. Every plugin here now ships *both*: root `plugin.json` for Antigravity, `.claude-plugin/plugin.json` (same content) for Claude Code. Without the subdirectory copy, Claude Code does not recognize the directory as a plugin at all.
- **Antigravity's real global install path is `~/.gemini/antigravity-cli/plugins/<name>/`**, populated by the `agy plugin install <path>` CLI command — not a path you `mkdir`/`cp` into by hand. Use the command below; let `agy` manage the destination.

**Antigravity CLI — global install, any plugin** (full plugins are global-only on this host; there is no project-scoped equivalent for a bundled plugin):
```bash
agy plugin install ./plugins/python-backend
agy plugin install ./plugins/git-workflow
agy plugin install ./plugins/docs-and-quality
agy plugin install ./plugins/multi-agent-ops
agy plugin install ./plugins/senior-dev            # installs the plugin's mcp_config.json only — see below for its agents
agy plugin install ./plugins/senior-data-engineer   # same: mcp_config.json only, agent comes from root agents/
agy plugin install ./plugins/sql-query-optimizer    # same: mcp_config.json only, agent comes from root agents/
agy plugin list      # confirm
agy plugin enable|disable|uninstall <name>
```

**`senior-dev`, `senior-data-engineer`, `sql-query-optimizer` (Antigravity CLI)** — these plugins' subagents use Claude-Code-only frontmatter, so on Antigravity the equivalent subagents ship separately as plain `.md` files at the repo root `agents/`. Two ways to use them:
- **Project-scoped** (no global state): `mkdir -p .agents/agents && cp agents/senior-dev-orchestrator.md agents/product-analyst.md agents/architect-engineer.md agents/code-implementer.md agents/qa-tester.md agents/compliance-verifier.md agents/senior-data-engineer.md agents/sql-query-optimizer.md .agents/agents/` — Antigravity auto-discovers agents from `.agents/agents/` in the current project.
- **Global**: same, but into `~/.gemini/config/agents/`.

**Project-scoped Antigravity pieces, without installing a full plugin**: skills → `.agents/skills/<skill-name>/` (global: `~/.gemini/config/skills/`), agents → `.agents/agents/` (global: `~/.gemini/config/agents/`), MCP servers → `.agents/mcp_config.json` (global: `~/.gemini/config/mcp_config.json`). These three are the only Antigravity mechanisms that work per-project; the plugin bundle itself (`agy plugin install`) is global-only.

**All 7 plugins (Claude Code) — global install**:
```bash
cp -r ./plugins/python-backend ~/.claude/plugins/python-backend
cp -r ./plugins/senior-dev ~/.claude/plugins/senior-dev
cp -r ./plugins/git-workflow ~/.claude/plugins/git-workflow
cp -r ./plugins/docs-and-quality ~/.claude/plugins/docs-and-quality
cp -r ./plugins/multi-agent-ops ~/.claude/plugins/multi-agent-ops
cp -r ./plugins/senior-data-engineer ~/.claude/plugins/senior-data-engineer
cp -r ./plugins/sql-query-optimizer ~/.claude/plugins/sql-query-optimizer
```

**Claude Code — project-scoped, no install needed**: load any plugin for just the current session with
```bash
claude --plugin-dir ./plugins/python-backend
```
(repeat the flag per plugin to load several at once). This is the direct Claude Code answer to "install it in the project" — no copy, no marketplace registration, scoped to that invocation.

---

## 13. Usage and Workflows

Once installed, the agent skills and hooks are completely automatic:
1. **Writing Code**: When you prompt the agent to perform edits or checkouts, the rules in `python-backend-rules.md` guide the coding standard (PEP 8, strict types).
2. **Making Commits**: The pre-commit gate hooks check the staged files against AST smells, linting limits, and secret exposures before allowing git commits to proceed.
3. **Closing Tasks**: When you or the agent finish a task, the Stop lifecycle hook runs `verify_tests.py` and stops completion if tests fail.

---

## 14. Antigravity Sidecars (Loop Engineering Background Processes)

This workspace provides a root-level [**`sidecars/`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars) directory containing configurations for background processes and schedules that run alongside Antigravity:

| Sidecar Directory | Type / Schedule | Primary Automation Goal |
| :--- | :--- | :--- |
| [**`pr-reviewer-cron`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/pr-reviewer-cron/sidecar.json) | Cron (`0 * * * *`) | Automatically scans open PR branches for credentials leakage and TODO declarations every hour. |
| [**`incoming-reviews-alert`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/incoming-reviews-alert/sidecar.json) | Cron (`*/30 * * * *`) | Prompts the agent to fetch pending review requests from GitHub, keeping the developer up to date. |
| [**`workspace-daemon`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/workspace-daemon/sidecar.json) | Daemon (Continuous) | Monitored by Antigravity; uses Python (`daemon_monitor.py`) to auto-format and lint modified code. |

To install sidecars globally or per-plugin, review the [**Sidecars Installation Guide**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/README.md#2-installation-guide).

---

## 15. License
This repository is open-sourced under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for more details.
