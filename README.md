# Expert AI Developer Skills

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=for-the-badge&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Antigravity](https://img.shields.io/badge/Antigravity-Customizations-orange?style=for-the-badge)](https://github.com/google/antigravity)
[![License](https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge)](LICENSE)

Welcome to **expert-ai-developer-skills**, the premium community repository for Google Antigravity (AGY) agent customizations. This workspace houses a professional-grade suite of **17 optimized developer skills**, refactored RFC 2119 rules, and a bundled **Python Backend plugin** designed to automate quality gates, enforce branch safety constraints (Gitflow), validate test execution, audit security vulnerabilities (OWASP Top 10), and seamlessly connect native MCP tools for Google Cloud and Firebase.

---

## 1. Quick Clone & Setup

To use or contribute to this suite of skills and plugins, clone the repository using the following SSH endpoint:

```bash
git clone git@github.com:jggomez/expert-ai-developer-skills.git
cd expert-ai-developer-skills
```

---

## 2. Directory Structure & Sitemap

The workspace is cleanly structured into modular **skills** (discrete instructions and automation scripts), **rules** (system constraints for AI agents), **workflows** (playbooks for SDLC processes), **sidecars** (background processes and schedules), and a **plugin** (integrated lifecycle hooks and custom rules):

```
expert-ai-developer-skills/
├── README.md                           # Main community reference guide (this file)
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
│   └── guidelines-karpathy/            # Critical behavioral checks to avoid LLM bugs
└── plugins/
    └── python-backend/
        ├── README.md                   # Plugin installation, hooks, & mcp configurations
        ├── plugin.json                 # Required plugin metadata descriptor
        ├── mcp_config.json             # Configuration for GCP Cloud Run and Firebase MCPs
        ├── hooks.json                  # Editor execution lifecycle hook registrations
        ├── hooks/                      # SessionStart, PreToolUse, & Stop event scripts (JS)
        ├── rules/                      # System-wide architecture rules & hook policies
        └── skills/                     # Local backend-compatible copy of the skills catalog
```

---

## 3. In-Depth Developer Skills (17 Packaged Modules)

Each skill represents an isolated capability loaded with professional guidelines, architectural references, and self-contained command-line automation scripts:

| Skill Directory | Target Capability & Purpose | Key Automated Scripts |
| :--- | :--- | :--- |
| **`python-expert`** | PEP 8 styling, static typing (`mypy`), generator stream tuning, and `__slots__` memory footprint reduction. | *AST-based memory checks* |
| **`fastapi-expert`** | Establishes REST API routing standards, Pydantic v2 schemas, and session dependency injection. | *Safe serialization checkers* |
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

## 5. Generic AI Developer Rules (10 Constraint Profiles)

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
| [**`loop-engineering-workflow.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/loop-engineering-workflow.md) | Mandates 7-stage cycle (`PLAN->TASK->BUILD->TEST->VERIFICATION->DOCUMENTATION->COMMIT`) with subagent parallelization. | Manager audit checklist + empirical runtime validation. |
| [**`tdd-best-practices.md`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/tdd-best-practices.md) | Enforces TDD Red-Green-Refactor cycles, empirical runtime verification, and clean mock boundaries. | 100% test pass + empirical execution proof. |

---

## 6. Generic AI Developer Workflows (7 Execution Playbooks)

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

## 7. Comprehensive Installation Guide

This repository fully adheres to the official [**Open Agent Skills Standard** (`agentskills.io`)](https://agentskills.io). Therefore, other teams or users can install any of these 18 skills out-of-the-box using Vercel's official, standard `skills` CLI.

### 7.1 Standard Skills Installation (Using Vercel's `npx skills`)
This is the recommended and simplest way to discover, add, and manage these skills. They don't need any local setups, just run:

```bash
# List all 18 skills available in our repository
npx skills add jggomez/expert-ai-developer-skills --list

# Install a specific skill (e.g. python-expert) in the active project (.agents/skills)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert

# Install a specific skill globally on your system (so all your workspaces can load it)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert -g

# Install ALL 18 skills in the active project
npx skills add jggomez/expert-ai-developer-skills
```

### 7.2 Plugin & Hooks Installation (Manual Setup)
Since the `python-backend` plugin includes advanced runtime hooks (`hooks.json`, `PreToolUse` gates) that are separate from standard agent skills, you can configure it globally by copying its directory:

```bash
# 1. Create the global plugin directory
mkdir -p ~/.gemini/config/plugins/python-backend

# 2. Copy the plugin folder to your global config
cp -r ./plugins/python-backend/* ~/.gemini/config/plugins/python-backend/
```

---

## 8. Usage and Workflows

Once installed, the agent skills and hooks are completely automatic:
1. **Writing Code**: When you prompt the agent to perform edits or checkouts, the rules in `python-backend-rules.md` guide the coding standard (PEP 8, strict types).
2. **Making Commits**: The pre-commit gate hooks check the staged files against AST smells, linting limits, and secret exposures before allowing git commits to proceed.
3. **Closing Tasks**: When you or the agent finish a task, the Stop lifecycle hook runs `verify_tests.py` and stops completion if tests fail.

---

## 9. Antigravity Sidecars (Loop Engineering Background Processes)

This workspace provides a root-level [**`sidecars/`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars) directory containing configurations for background processes and schedules that run alongside Antigravity:

| Sidecar Directory | Type / Schedule | Primary Automation Goal |
| :--- | :--- | :--- |
| [**`pr-reviewer-cron`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/pr-reviewer-cron/sidecar.json) | Cron (`0 * * * *`) | Automatically scans open PR branches for credentials leakage and TODO declarations every hour. |
| [**`incoming-reviews-alert`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/incoming-reviews-alert/sidecar.json) | Cron (`*/30 * * * *`) | Prompts the agent to fetch pending review requests from GitHub, keeping the developer up to date. |
| [**`workspace-daemon`**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/workspace-daemon/sidecar.json) | Daemon (Continuous) | Monitored by Antigravity; uses Python (`daemon_monitor.py`) to auto-format and lint modified code. |

To install sidecars globally or per-plugin, review the [**Sidecars Installation Guide**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/sidecars/README.md#2-installation-guide).

---

## 10. License
This repository is open-sourced under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for more details.
