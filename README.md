# Expert AI Developer Skills

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=for-the-badge&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Antigravity](https://img.shields.io/badge/Antigravity-Customizations-orange?style=for-the-badge)](https://github.com/google/antigravity)
[![License](https://img.shields.io/badge/License-Apache%202.0-green?style=for-the-badge)](LICENSE)

Welcome to **expert-ai-developer-skills**, the premium community repository for Google Antigravity (AGY) agent customizations. This workspace houses a professional-grade suite of **18 optimized developer skills** and a bundled **Python Backend plugin** designed to automate quality gates, enforce branch safety constraints (Gitflow), validate test execution, audit security vulnerabilities (OWASP Top 10), and seamlessly connect native MCP tools for Google Cloud and Firebase.

---

## 1. Quick Clone & Setup

To use or contribute to this suite of skills and plugins, clone the repository using the following SSH endpoint:

```bash
git clone git@github.com:jggomez/expert-ai-developer-skills.git
cd expert-ai-developer-skills
```

---

## 2. Directory Structure & Sitemap

The workspace is cleanly structured into modular **skills** (discrete instructions and automation scripts) and a **plugin** (integrated lifecycle hooks and custom rules):

```
expert-ai-developer-skills/
├── README.md                           # Main community reference guide (this file)
├── skills/
│   ├── README.md                       # Detailed skills catalog & usage instructions
│   ├── python-expert/                  # PEP 8 patterns, AST optimizations, memory checks
│   ├── fastapi-expert/                 # FastAPI routing conventions & Pydantic v2 schemas
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
│   ├── senior-architect-engineering/   # Architectural Decision Records (ADR) generators
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

## 3. In-Depth Developer Skills (18 Packaged Modules)

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

## 5. Comprehensive Installation Guide

This repository fully adheres to the official [**Open Agent Skills Standard** (`agentskills.io`)](https://agentskills.io). Therefore, other teams or users can install any of these 18 skills out-of-the-box using Vercel's official, standard `skills` CLI.

### 5.1 Standard Skills Installation (Using Vercel's `npx skills`)
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

### 5.2 Plugin & Hooks Installation (Manual Setup)
Since the `python-backend` plugin includes advanced runtime hooks (`hooks.json`, `PreToolUse` gates) that are separate from standard agent skills, you can configure it globally by copying its directory:

```bash
# 1. Create the global plugin directory
mkdir -p ~/.gemini/config/plugins/python-backend

# 2. Copy the plugin folder to your global config
cp -r ./plugins/python-backend/* ~/.gemini/config/plugins/python-backend/
```

---

## 6. Usage and Workflows

Once installed, the agent skills and hooks are completely automatic:
1. **Writing Code**: When you prompt the agent to perform edits or checkouts, the rules in `python-backend-rules.md` guide the coding standard (PEP 8, strict types).
2. **Making Commits**: The pre-commit gate hooks check the staged files against AST smells, linting limits, and secret exposures before allowing git commits to proceed.
3. **Closing Tasks**: When you or the agent finish a task, the Stop lifecycle hook runs `verify_tests.py` and stops completion if tests fail.

---

## 7. License
This repository is open-sourced under the Apache License, Version 2.0. See the [LICENSE](LICENSE) file for more details.
