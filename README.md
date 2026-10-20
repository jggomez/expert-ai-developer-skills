# Expert AI Developer Skills

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=for-the-badge&logo=github)](https://github.com/jggomez/expert-ai-developer-skills)
[![Plugins](https://img.shields.io/badge/Plugins-9%20Core%20%2B%201%20Add--on-orange?style=for-the-badge)](#2-plugins-catalog--installation)
[![Skills Standard](https://img.shields.io/badge/AgentSkills.io-35%20Canonical%20Skills-green?style=for-the-badge)](skills/README.md)
[![Constitution](https://img.shields.io/badge/Constitution-AGENTS.md%20Universal-purple?style=for-the-badge)](AGENTS.md)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey?style=for-the-badge)](LICENSE)

Production-grade engineering plugins, autonomous subagents, deterministic lifecycle hooks, modular skills, and cost/latency observability for **Google Antigravity (AGY)** and **Anthropic Claude Code**.

---

## 1. Repository Overview

At a high level, this repository is organized into 6 modular components—each with its own detailed documentation:

* **[Plugins](#2-plugins-catalog--installation)** (`plugins/antigravity/` & `plugins/claude/`): **9 core self-contained plugins** (+ 1 optional `agent-metrics` add-on) bundling specialized subagents, lifecycle safety gates, MCP servers, and skills for both hosts with zero cross-environment tool contamination.
* **[Skills](skills/README.md)** (`skills/`): **35 canonical skills** (+ optional `agent-metrics`) compliant with the open [Agent Skills Standard (`agentskills.io`)](https://agentskills.io) and backed by deterministic Python scripts.
* **[`agent-meter` Observability](#3-token-cost--latency-observability-agent-meter)** (`tools/agent-meter/`): Local-first, **$0 CLI & dashboard** tracking token usage, API-equivalent USD cost, cache hit ratio, and latency across Claude Code and Antigravity per project, client, task, and subagent.
* **[Rules](rules/README.md)** (`rules/`): **11 RFC 2119 rule profiles** enforcing SOLID/Clean Code, strict TDD, Gitflow branch protection, token budgets, and OWASP security.
* **[Workflows](workflows/README.md)** (`workflows/`): **16 step-by-step operational playbooks** guiding complex engineering tasks, including the 9-stage `/spec` &rarr; `/ship` command framework.
* **[Sidecars](sidecars/README.md)** (`sidecars/`): Background daemons and scheduled cron tasks for automated PR reviews and continuous workspace checks.
* **[Universal Constitution (`AGENTS.md`)](AGENTS.md)**: The supreme governance contract (`CLAUDE.md` / `AGENT.md` symlinks) enforcing Plan-First (`PLAN.md`), Orchestrator Role Boundaries, Anti-Lazy Code, and the 6-State Graph Engineering DAG.

---

## 2. Plugins Catalog & Installation

Plugins are turnkey packages that wire subagents, native host tools, deterministic `PreToolUse`/`Stop` hooks, and MCP servers into your AI coding assistant.

### 2.1 Available Plugins Catalog

| Plugin | Capabilities & Core Purpose | Detailed Guides |
| :--- | :--- | :--- |
| **`senior-dev`** | Full SDLC Graph Engineering topology: Lead Orchestrator, Product Analyst, Architect, TDD Implementer, QA Tester, and Compliance Verifier with `context/memory/` Wiki. | [Antigravity](plugins/antigravity/senior-dev/README.md) · [Claude Code](plugins/claude/senior-dev/README.md) |
| **`senior-dev-flutter`** | Senior Flutter & Dart layer on top of the official Flutter/Dart packs: 6-State DAG, state-management ADRs (Riverpod/Bloc), DevTools jank profiling, release matrix, and Dart MCP. | [Antigravity](plugins/antigravity/senior-dev-flutter/README.md) · [Claude Code](plugins/claude/senior-dev-flutter/README.md) |
| **`python-backend`** | Python backend engineering: FastAPI/Django vertical slices, strict TDD, zero-downtime Alembic migrations, CI/CD gates, and Cloud Run & Firebase MCP. | [Antigravity](plugins/antigravity/python-backend/README.md) · [Claude Code](plugins/claude/python-backend/README.md) |
| **`senior-data-engineer`** | Google Cloud data engineering: Medallion Lakehouse architecture, Datastream CDC, BigQuery SCD Type 2 modeling, data safety gates, and GCP remote MCP. | [Antigravity](plugins/antigravity/senior-data-engineer/README.md) · [Claude Code](plugins/claude/senior-data-engineer/README.md) |
| **`sql-query-optimizer`** | SQL execution plan diagnosis: BigQuery slot/shuffle/skew tuning, Postgres/MySQL/SQL Server indexing strategies, dry-run cost gates, and static SQL linting. | [Antigravity](plugins/antigravity/sql-query-optimizer/README.md) · [Claude Code](plugins/claude/sql-query-optimizer/README.md) |
| **`shared-context`** | Cross-AI LLM Wiki working memory (`context/memory/MEMORY.md` + session archives): captures decisions and handoff state seamlessly between Antigravity and Claude Code. | [Antigravity](plugins/antigravity/shared-context/README.md) · [Claude Code](plugins/claude/shared-context/README.md) |
| **`git-workflow`** | Git safety & hygiene: Gitflow branch protection gate (blocks direct commits/pushes to `main`/`develop`), Conventional Commits validation, and clean-tree stop gates. | [Antigravity](plugins/antigravity/git-workflow/README.md) · [Claude Code](plugins/claude/git-workflow/README.md) |
| **`docs-and-quality`** | Documentation & QA standards: Diátaxis framework, Mermaid.js diagrams, Gherkin BDD testing, Karpathy guidelines, and Anti-Lazy Code stop gate. | [Antigravity](plugins/antigravity/docs-and-quality/README.md) · [Claude Code](plugins/claude/docs-and-quality/README.md) |
| **`multi-agent-ops`** | Multi-agent operations: parallel worker execution (**Mode A: Disjoint Files** & **Mode B: Git Worktrees**), 3-loop self-correction cap, PR cron review, and codebase research. | [Antigravity](plugins/antigravity/multi-agent-ops/README.md) · [Claude Code](plugins/claude/multi-agent-ops/README.md) |
| **`agent-metrics`** *(optional)* | Opt-in hook wrapper + skill for [`agent-meter`](#3-token-cost--latency-observability-agent-meter): automatic session/task token, cost, and latency summaries. | [Antigravity](plugins/antigravity/agent-metrics/README.md) · [Claude Code](plugins/claude/agent-metrics/README.md) |

### 2.2 How Orchestrator Plugins Work (Graph Engineering DAG)

Domain orchestrator plugins (`senior-dev`, `senior-dev-flutter`, `python-backend`, `senior-data-engineer`) don't just run single prompts—they coordinate specialized subagents across a deterministic **6-State Directed Acyclic Graph (DAG)** with hard lifecycle gates:

1. **State 0 — Memory Restore & Discovery Triage Gate**: Silently loads cross-AI memory (`context/memory/MEMORY.md`) and authors `PLAN.md` with a triage rubric before any code can be edited.
2. **State 1 — Upfront Discovery**: Automatically dispatches `product-analyst` (PRDs, edge cases) and/or `architect-engineer` (ADRs, contracts) when triggered by the triage gate.
3. **State 2 — Parallel Build Fan-Out**: Delegates TDD implementation to `1..N` `code-implementer` / `flutter-implementer` workers in parallel using **Mode A (Disjoint File Partitioning)** or **Mode B (Git Worktree Isolation)**. Orchestrators are blocked by `orchestrator-role-gate.js` from writing application code directly.
4. **State 3 & 4 — Parallel QA & Compliance Audit**: Runs `qa-tester` (requiring empirical `exit code 0`) and `compliance-verifier` (requiring an `APPROVED` security/quality verdict) concurrently, with up to 3 self-correction loops.
5. **State 5 — Ship & LLM Wiki Update**: Updates `context/memory/` for the next session (in either Claude Code or Antigravity) and commits using Conventional Commits.

> **Read the full DAG architecture, state machine diagram, and topologies where they are implemented**:
> * [`senior-dev` Plugin Architecture & DAG](plugins/antigravity/senior-dev/README.md) ([Claude Code version](plugins/claude/senior-dev/README.md))
> * [`multi-agent-ops` Parallel Fan-Out & Topologies](plugins/antigravity/multi-agent-ops/README.md) ([Claude Code version](plugins/claude/multi-agent-ops/README.md))
> * [`AGENTS.md` Universal Constitution & Ecosystem Tool Mapping](AGENTS.md)

### 2.3 Installing Plugins in Google Antigravity

Antigravity installs plugins using the `agy` CLI:

```bash
# Install a specific plugin
agy plugin install ./plugins/antigravity/senior-dev
agy plugin install ./plugins/antigravity/senior-dev-flutter
agy plugin install ./plugins/antigravity/python-backend
agy plugin install ./plugins/antigravity/senior-data-engineer
agy plugin install ./plugins/antigravity/sql-query-optimizer
agy plugin install ./plugins/antigravity/shared-context
agy plugin install ./plugins/antigravity/git-workflow
agy plugin install ./plugins/antigravity/docs-and-quality
agy plugin install ./plugins/antigravity/multi-agent-ops

# Install all 9 core plugins in one command
for p in senior-dev senior-dev-flutter python-backend senior-data-engineer sql-query-optimizer shared-context git-workflow docs-and-quality multi-agent-ops; do
  agy plugin install "./plugins/antigravity/$p"
done

# Useful management commands
agy plugin list                    # List installed plugins
agy plugin enable <name>           # Enable a plugin
agy plugin disable <name>          # Temporarily disable a plugin
agy plugin uninstall <name>        # Remove an installed plugin
```

### 2.4 Installing Plugins in Anthropic Claude Code

In Claude Code, install plugins via the repository marketplace or from a local checkout:

```bash
# 1. Add the repository marketplace
/plugin marketplace add jggomez/expert-ai-developer-skills

# 2. Install any plugin(s)
/plugin install senior-dev
/plugin install senior-dev-flutter
/plugin install python-backend
/plugin install senior-data-engineer
/plugin install sql-query-optimizer
/plugin install shared-context
/plugin install git-workflow
/plugin install docs-and-quality
/plugin install multi-agent-ops

# Or install directly from a local clone:
claude plugin install plugins/claude/senior-dev
```

---

## 3. Token, Cost & Latency Observability (`agent-meter`)

How much do your AI agents cost per project, per client, per task, and per subagent—and how fast are they? **`agent-meter`** is a standalone, read-only, privacy-first CLI that reads the transcripts and databases **Claude Code** and **Antigravity** (CLI, IDE, and app) already write to disk:

* **Option A — Local ($0, default, offline)**: Stores metrics in `~/.agent-meter/meter.duckdb`, prints session and per-task subagent rollups in your terminal, and generates a self-contained **offline HTML report** (`agent-meter report --open`).
* **Option B — Cloud ($0 within BigQuery free tier, opt-in)**: Syncs via batch load jobs to your own **BigQuery** dataset (`agent_metrics`) to power a **Looker Studio** dashboard with drill-down from `Project -> Session -> Task -> Subagent -> LLM Call`.

```bash
# 1. Install the CLI (requires uv: https://docs.astral.sh/uv/)
uv tool install "git+https://github.com/jggomez/expert-ai-developer-skills#subdirectory=tools/agent-meter"

# 2. Run the one-time setup wizard (detects hosts, imports history, configures hooks/scheduler)
agent-meter setup --local

# 3. Inspect your metrics
agent-meter last            # Last session summary (+ today / month-to-date for that project)
agent-meter tasks --last 5  # Last 5 tasks with per-subagent cost, calls, parallelism & retries
agent-meter report --open   # Open the interactive offline HTML report in your browser
```

> **Complete Documentation & Guides**:
> * 🇺🇸 **English User Guide (Local & BigQuery + Looker Studio)**: [`tools/agent-meter/README.md`](tools/agent-meter/README.md)
> * 🇪🇸 **Guía Completa en Español (Local y BigQuery + Looker Studio)**: [`tools/agent-meter/README.es.md`](tools/agent-meter/README.es.md)
> * 📐 **Architecture, Contracts & Looker Studio Spec**: [`docs/agent-metrics/README.md`](docs/agent-metrics/README.md) · [`looker-studio.md`](docs/agent-metrics/looker-studio.md)

---

## 4. Installing & Using Skills (35 Canonical Skills)

**Skills** provide on-demand instructions, checklists, and deterministic Python scripts (progressive disclosure) that agents activate only when relevant to your task.

### Option A: Install via Vercel Skills CLI (Recommended)

```bash
# List all available skills in this repository
npx skills add jggomez/expert-ai-developer-skills --list

# Install a specific skill in the active project (.agents/skills)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert

# Install a specific skill globally on your machine
npx skills add jggomez/expert-ai-developer-skills --skill python-expert -g

# Install all skills in the active project
npx skills add jggomez/expert-ai-developer-skills
```

### Option B: Manual Copy

```bash
# Project-level (.agents/skills/)
mkdir -p .agents/skills/ && cp -r skills/<skill-name> .agents/skills/

# Global machine-level (~/.gemini/config/skills/)
mkdir -p ~/.gemini/config/skills/ && cp -r skills/<skill-name> ~/.gemini/config/skills/
```

> **Explore the full 35-skill catalog, plugin bundling matrix, and CLI script manual**: [`skills/README.md`](skills/README.md)

---

## 5. Using Rules, Workflows & Sidecars

### 5.1 Rules (11 Constraint Profiles)
**Rules** are passive RFC 2119 guardrails (`MUST`, `NEVER`, `ALWAYS`) loaded automatically from `.agents/rules/` (project scope) or `~/.gemini/config/rules/` (global scope).

```bash
mkdir -p .agents/rules/
cp rules/*.md .agents/rules/
```
> **Browse all 11 rule profiles and trigger examples**: [`rules/README.md`](rules/README.md)

### 5.2 Operational Workflows (16 Playbooks)
**Workflows** are step-by-step operational playbooks invoked via `@workflows/<name>.md` or registered as slash commands in `.agents/workflows/`:

* **The 9 Core Slash Commands**: [`/spec`](workflows/spec-workflow.md) &rarr; [`/plan`](workflows/plan-workflow.md) &rarr; [`/build`](workflows/build-workflow.md) &rarr; [`/test`](workflows/test-workflow.md) &rarr; [`/constraints`](workflows/constraints-workflow.md) &rarr; [`/review`](workflows/review-workflow.md) &rarr; [`/perf`](workflows/perf-workflow.md) &rarr; [`/code-simplify`](workflows/code-simplify-workflow.md) &rarr; [`/ship`](workflows/ship-workflow.md).
* **7 Specialized Playbooks**: [`feature-development`](workflows/feature-development-workflow.md), [`test-execution`](workflows/test-execution-workflow.md), [`secure-code-review`](workflows/secure-code-review-workflow.md), [`pull-request`](workflows/pull-request-workflow.md), [`commit`](workflows/commit-workflow.md), [`code-smell-review`](workflows/code-smell-review-workflow.md), and [`grill-me-alignment`](workflows/grill-me-alignment-workflow.md).

> **See how to register and run workflows**: [`workflows/README.md`](workflows/README.md)

### 5.3 Sidecars (Background Daemons & Cron Jobs)
**Sidecars** run recurring background tasks alongside Antigravity (`pr-reviewer-cron`, `incoming-reviews-alert`, `workspace-daemon`).

> **See installation and schedule configuration**: [`sidecars/README.md`](sidecars/README.md)

---

## 6. Developer Runbooks (Contributing & Verification)

```bash
# 1. Run the repository test suite (unit, integration, and structural checks)
pytest tests/

# 2. Validate syntax of all Node.js lifecycle hooks across both ecosystems
for hook in plugins/antigravity/*/hooks/*.js plugins/claude/*/hooks/*.js; do
  node --check "$hook" || exit 1
done

# 3. Synchronize canonical /skills and agents across Antigravity and Claude Code plugins
python3 scripts/sync_plugin_skills.py
python3 scripts/sync_agents.py
```

---

## 7. License

This repository is open-sourced under the [Apache License, Version 2.0](LICENSE).
