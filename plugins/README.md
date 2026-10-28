# Plugin Ecosystem Guide: Google Antigravity & Anthropic Claude Code

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](https://github.com/jggomez/expert-ai-developer-skills)
[![Plugins Count](https://img.shields.io/badge/Plugins-9%20Core%20%2B%201%20Add--on-orange?style=flat-square)](.)
[![Dual Runtime](https://img.shields.io/badge/Runtime-Antigravity%20%7C%20Claude%20Code-green?style=flat-square)](.)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey?style=flat-square)](../LICENSE)

This directory contains the **Dual Plugin Ecosystem** powering production-grade multi-agent software engineering across two premier AI coding hosts: **Google Antigravity (AGY)** and **Anthropic Claude Code**.

---

## 1. Dual Ecosystem Architecture

Every plugin in this repository is engineered as an autonomous, self-contained package providing specialized subagents, deterministic lifecycle safety hooks, MCP server configurations, and bundled skills:

```
plugins/
├── antigravity/                  # Google Antigravity Plugin Ecosystem
│   ├── senior-dev/               # Core SDLC orchestrator + 6 specialized subagents
│   ├── senior-dev-flutter/       # Mobile & web Flutter architecture, profiling & release
│   ├── python-backend/           # FastAPI, Django, Alembic migrations & Cloud Run
│   ├── senior-data-engineer/     # GCP Lakehouse, BigQuery, Datastream CDC & SCD modeling
│   ├── sql-query-optimizer/      # Real-plan SQL optimization & static anti-pattern audit
│   ├── shared-context/           # Cross-AI LLM Wiki working memory (context/memory/)
│   ├── git-workflow/             # Branch governance & Conventional Commits validation
│   ├── docs-and-quality/         # Diátaxis docs, Karpathy guidelines & QA standards
│   ├── multi-agent-ops/          # DAG state machines & parallel loop engineering
│   └── agent-metrics/            # Optional token, cost & latency observability
└── claude/                       # Anthropic Claude Code Plugin Ecosystem
    ├── senior-dev/               # 1:1 Parity Claude Code subagents & hooks
    ├── senior-dev-flutter/       # 1:1 Parity Claude Code subagents & hooks
    ├── python-backend/           # 1:1 Parity Claude Code subagents & hooks
    ├── senior-data-engineer/     # 1:1 Parity Claude Code subagents & hooks
    ├── sql-query-optimizer/      # 1:1 Parity Claude Code subagents & hooks
    ├── shared-context/           # 1:1 Parity Claude Code subagents & hooks
    ├── git-workflow/             # 1:1 Parity Claude Code subagents & hooks
    ├── docs-and-quality/         # 1:1 Parity Claude Code subagents & hooks
    ├── multi-agent-ops/          # 1:1 Parity Claude Code subagents & hooks
    └── agent-metrics/            # 1:1 Parity Claude Code subagents & hooks
```

---

## 2. Zero Tool Bleed & Dual-Host Isolation

A core architectural invariant of this repository is **Zero Cross-Environment Tool Contamination**:
- **Google Antigravity** agents declare and execute only native Antigravity primitives: `run_command`, `view_file`, `write_to_file`, `replace_file_content`, `list_dir`, `grep_search`, `find_by_name`, `ask_question`, `invoke_subagent`, `manage_subagents`, `send_message`.
- **Anthropic Claude Code** agents declare and execute only native Claude Code tools: `Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Agent`.
- **Automated Synchronization**: Running `python3 scripts/sync_agents.py` and `python3 scripts/sync_plugin_skills.py` automatically converts canonical agent definitions and skills into pure, sanitized Claude Code configurations without manual duplication.

---

## 3. Available Plugins Catalog

| Plugin | Primary Focus & Domain | Agents Bundled | Bundled Skills | Native MCP Servers |
| :--- | :--- | :---: | :---: | :--- |
| **[`senior-dev`](antigravity/senior-dev/README.md)** | Full SDLC lead orchestrator, discovery specialists, TDD implementers, QA matrix generation, and adversarial verification. | 10 | 15 | Cloud Run, Firebase |
| **[`senior-dev-flutter`](antigravity/senior-dev-flutter/README.md)** | Senior Flutter & Dart layer on top of official Flutter packs: 60/120fps profiling, Riverpod/Bloc ADRs, release matrices. | 5 | 10 | Dart MCP |
| **[`python-backend`](antigravity/python-backend/README.md)** | Production Python backend: FastAPI/Django vertical slices, zero-downtime Alembic migrations, CI/CD gates. | 1 | 14 | Cloud Run, Firebase |
| **[`senior-data-engineer`](antigravity/senior-data-engineer/README.md)** | Google Cloud Lakehouse architecture, Datastream CDC, BigQuery SCD Type 2 modeling, data contracts, and dry-run cost controls. | 1 | 4 | BigQuery, Cloud SQL, GCS |
| **[`sql-query-optimizer`](antigravity/sql-query-optimizer/README.md)** | SQL performance diagnosis from real execution plans, BigQuery slot/skew tuning, dialect-aware rewrites. | 1 | 4 | BigQuery, Cloud SQL |
| **[`shared-context`](antigravity/shared-context/README.md)** | Cross-AI LLM Wiki memory (`context/memory/MEMORY.md`): zero-amnesia working memory shared between Claude and Antigravity. | 1 | 2 | Shared Context MCP |
| **[`git-workflow`](antigravity/git-workflow/README.md)** | Git branch protection (blocks direct commits to `main`/`develop`), auto-branching, scope drift detection, Conventional Commits. | 0 | 2 | — |
| **[`docs-and-quality`](antigravity/docs-and-quality/README.md)** | Technical documentation standards (Diátaxis), Mermaid diagrams, Karpathy clean-code guidelines, Anti-Lazy code policy. | 0 | 3 | — |
| **[`multi-agent-ops`](antigravity/multi-agent-ops/README.md)** | 3-Tier SDLC DAG execution, parallel fan-out (Mode A: Disjoint Files vs Mode B: Worktrees), finite 3-loop self-correction. | 0 | 2 | — |
| **[`agent-metrics`](antigravity/agent-metrics/README.md)** | *(Optional)* Session and task token, USD cost, cache efficiency, and latency observability via `agent-meter`. | 0 | 1 | — |

---

## 4. Quick Installation Guide

### Option A: Installing in Google Antigravity
Use the `agy` CLI to install individual plugins or the entire suite:

```bash
# Install individual plugins
agy plugin install ./plugins/antigravity/senior-dev
agy plugin install ./plugins/antigravity/senior-dev-flutter
agy plugin install ./plugins/antigravity/python-backend
agy plugin install ./plugins/antigravity/senior-data-engineer
agy plugin install ./plugins/antigravity/sql-query-optimizer

# Install all 9 core plugins in one loop
for p in senior-dev senior-dev-flutter python-backend senior-data-engineer sql-query-optimizer shared-context git-workflow docs-and-quality multi-agent-ops; do
  agy plugin install "./plugins/antigravity/$p"
done
```

### Option B: Installing in Anthropic Claude Code
Install directly from the repository marketplace or local clone:

```bash
# 1. Register the marketplace repository
/plugin marketplace add jggomez/expert-ai-developer-skills

# 2. Install any plugin
/plugin install senior-dev
/plugin install senior-dev-flutter
/plugin install python-backend
/plugin install senior-data-engineer
/plugin install sql-query-optimizer
```

---

## 5. Architectural Standards Enforced by Plugins

1. **Plan-First Mandatory Gate**: Orchestrators are strictly forbidden from modifying source code without authoring an up-to-date `PLAN.md` containing discovery triage and execution tracks.
2. **Dynamic 3-Tier Adaptive SDLC**:
   - **Tier 1 (Fast-Track)**: Single-file bugfixes/docs bypass discovery and alignment modals, delivering **70–85% token & latency savings**.
   - **Tier 2 (Standard)**: 2–4 files, selective discovery in `docs/<feature-name>/`, interactive user approval modal (`ask_question`), parallel Mode A implementation.
   - **Tier 3 (Mission-Critical)**: Full discovery suite, mandatory user sign-off, and parallel dispatch of the **Adversarial Verification Committee** (`qa-tester`, `critic`, `challenger`, `e2e-blackbox-tester`, `compliance-verifier`).
3. **Automated Branch Governance**: Protected base branches (`main`, `master`, `develop`, `dev`) are guarded at the hook level; orchestrators automatically provision dedicated feature branches (`feat/<slug>`, `fix/<slug>`) and proactively detect scope drift via interactive GUI dialogs.
4. **Feature Artifacts Centralization**: Technical specifications, design tokens, architecture ADRs, and QA test matrices reside permanently under `docs/<feature-name>/`.
