# Expert AI Agent Skills Catalog

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Skills Count](https://img.shields.io/badge/Skills-18%20Optimized-orange?style=flat-square)](file:///./)

This directory contains a premium catalog of **18 agent skills** designed to automate code quality checks, enforce programming best practices, detect code smells, validate commit history, and implement self-correcting development loops using the Google Antigravity (AGY) system.

---

## 1. Quick Installation & Setup

These skills fully comply with the [**Open Agent Skills Standard** (`agentskills.io`)](https://agentskills.io). Therefore, you can install any of these 18 skills out-of-the-box using Vercel's official, standard `skills` CLI.

### Option A: Standard Installation (Recommended)
This is the simplest way for other teams or users to install and manage these skills. They don't need any local setups, just the standard command:

```bash
# List all 18 skills available in our repository
npx skills add jggomez/expert-ai-developer-skills --list

# Install a specific skill (e.g. python-expert) in the active project (.agents/skills)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert

# Install a skill globally on your system (so all your workspaces can load it)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert -g

# Install ALL 18 skills in the active project
npx skills add jggomez/expert-ai-developer-skills
```

### Option B: Advanced Installation (Using our Custom CLI)
If you want to use the custom, zero-dependency bulk copy CLI bundled directly in this repository:

```bash
# Add ALL 18 skills locally to your project in bulk
npx expert-ai-developer-skills add all

# Add ALL 18 skills globally
npx expert-ai-developer-skills add all --global
```

### Option C: Manual Copy (Fallback)
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
| **`python-expert`** | Enforces PEP 8 styling, static typing (`mypy`), generator stream tuning, and `__slots__` memory footprint reduction. | `references/python-patterns.md` | Guides AST-based memory checks and object tuning. |
| **`fastapi-expert`** | Enforces REST API routing conventions, dependency injection, and Pydantic validation. | `references/fastapi-patterns.md` | Enforces Pydantic v2 schemas and response models serialization. |
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
