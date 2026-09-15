# Expert AI Developer Skills

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=for-the-badge&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugins](https://img.shields.io/badge/Plugins-9%20Antigravity%20%7C%209%20Claude-orange?style=for-the-badge)](plugins)
[![Skills Standard](https://img.shields.io/badge/AgentSkills.io-35%20Verified-green?style=for-the-badge)](skills)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey?style=for-the-badge)](LICENSE)

Enterprise-grade customizations, subagents, and modular skills for **Google Antigravity (AGY)** and **Claude Code**.

This repository organizes development practices into **9 ready-to-use plugins**, **35 open agent skills**, **10 constraint rules**, **16 execution workflows**, and **persistent background sidecars**.

---

## 1. Repository Layout

The workspace is structured into dedicated hubs. Each hub maintains its own detailed documentation:

```text
expert-ai-developer-skills/
├── plugins/              # Complete plugins for Google Antigravity & Claude Code
│   ├── antigravity/      # 9 Antigravity plugins (native AGY tools & auto execution)
│   └── claude/           # 9 Claude Code plugins (native Claude tools & marketplace)
├── skills/               # 35 platform-neutral skills compliant with agentskills.io
├── rules/                # 10 constraint rule profiles enforcing code quality and safety
├── workflows/            # 16 step-by-step playbooks including the 9-stage SDLC cycle
├── sidecars/             # Persistent background daemons and cron tasks for Antigravity
└── tests/                # Automated verification test suite (98/98 passing)
```

For in-depth details of each component, explore their dedicated guides:
- [**Plugins Hub**](plugins/antigravity/senior-dev/README.md) — Comprehensive guide to subagents, MCP servers, and hooks.
- [**Skills Catalog**](skills/README.md) — Reference for all 35 skills, scripts, and `agentskills.io` usage.
- [**Rules Guide**](rules/README.md) — Constraint profiles for clean code, security, and TDD.
- [**Workflows Guide**](workflows/README.md) — Playbooks for `/spec`, `/plan`, `/build`, `/test`, `/review`, and `/ship`.
- [**Sidecars Guide**](sidecars/README.md) — Background daemons and cron reviewer setups.

---

## 2. Quick Start & Installation

### Option A: Install via Claude Code Marketplace (Recommended)
Register the repository marketplace and install any of the 9 plugins:

```bash
# 1. Add repository marketplace
/plugin marketplace add jggomez/expert-ai-developer-skills

# 2. Install desired plugin(s)
/plugin install senior-dev
/plugin install senior-dev-flutter
/plugin install senior-data-engineer
/plugin install sql-query-optimizer
/plugin install shared-context
/plugin install python-backend
/plugin install git-workflow
/plugin install docs-and-quality
/plugin install multi-agent-ops
```

*Direct local install is also supported:* `claude plugin install plugins/claude/<plugin-name>`

### Option B: Install via Google Antigravity CLI
Install plugins globally into Antigravity (`~/.gemini/antigravity-cli/plugins/`):

```bash
# Install any plugin directly
agy plugin install ./plugins/antigravity/senior-dev
agy plugin install ./plugins/antigravity/senior-dev-flutter
agy plugin install ./plugins/antigravity/senior-data-engineer
agy plugin install ./plugins/antigravity/sql-query-optimizer
agy plugin install ./plugins/antigravity/shared-context
agy plugin install ./plugins/antigravity/python-backend
agy plugin install ./plugins/antigravity/git-workflow
agy plugin install ./plugins/antigravity/docs-and-quality
agy plugin install ./plugins/antigravity/multi-agent-ops

# Verify installed plugins
agy plugin list
```

### Option C: Install Standalone Skills via Vercel Skills CLI
To install individual skills without plugins into `.agents/skills`:

```bash
# Discover all 35 skills
npx skills add jggomez/expert-ai-developer-skills --list

# Install a specific skill (e.g. python-expert)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert
```

---

## 3. Plugins Catalog

Every plugin is self-contained and pre-configured for both **Google Antigravity** and **Claude Code** with native tool bindings:

| Plugin | Primary Focus | Included Capabilities | Dedicated Documentation |
| :--- | :--- | :--- | :--- |
| **`senior-dev`** | Full SDLC Orchestration | 6 subagents (Orchestrator, Analyst, Architect, Implementer, QA, Verifier) + 8 skills | [Read Guide](plugins/antigravity/senior-dev/README.md) |
| **`senior-dev-flutter`** | Flutter & Dart Engineering | 5 subagents (Orchestrator, Architect, Implementer, Reviewer, Release) + 7 skills + Dart MCP | [Read Guide](plugins/antigravity/senior-dev-flutter/README.md) |
| **`senior-data-engineer`** | Google Cloud Data Engineering | 1 subagent + 2 skills (CDC, SCD Type 2) + BigQuery/Datastream/Dataform MCP | [Read Guide](plugins/antigravity/senior-data-engineer/README.md) |
| **`sql-query-optimizer`** | SQL Plan Optimization | 1 subagent + 2 skills + BigQuery/Cloud SQL query plan diagnosis | [Read Guide](plugins/antigravity/sql-query-optimizer/README.md) |
| **`shared-context`** | Cross-Agent Working Memory | Cross-session memory, `context-keeper` subagent, secret redaction, tar.xz archiving | [Read Guide](plugins/antigravity/shared-context/README.md) |
| **`python-backend`** | Python Backend Production Gates | FastAPI standards, TDD, migrations, CI/CD gates, Cloud Run & Firebase MCP | [Read Guide](plugins/antigravity/python-backend/README.md) |
| **`git-workflow`** | Gitflow Branch Safety | Gitflow branch protection hook, semantic commit checks, PR hygiene | [Read Guide](plugins/antigravity/git-workflow/README.md) |
| **`docs-and-quality`** | Documentation & Quality Standards | Diátaxis documentation, Gherkin BDD testing, Karpathy behavioral guidelines | [Read Guide](plugins/antigravity/docs-and-quality/README.md) |
| **`multi-agent-ops`** | Multi-Agent Operations | Parallel agent orchestration loops, PR cron review, automated repo research | [Read Guide](plugins/antigravity/multi-agent-ops/README.md) |

---

## 4. Skills, Rules & Workflows Hubs

To keep this root guide concise and prevent documentation drift, technical specifications are maintained in their respective directories:

* 📚 [**Skills Catalog (35 Skills)**](skills/README.md): Detailed reference table of all skills, associated Python scripts (`lint_sql_query.py`, `detect_smells.py`, `secret_scanner.py`, etc.), and CLI workflows.
* 🛡️ [**Constraint Rules (10 Profiles)**](rules/README.md): System rules for TDD, clean code, branch safety, token optimization, and security audits.
* 📋 [**Execution Workflows (16 Playbooks)**](workflows/README.md): Step-by-step playbooks for the 9-stage cycle (`/spec`, `/plan`, `/build`, `/test`, `/constraints`, `/review`, `/perf`, `/code-simplify`, `/ship`) and operational tasks.
* ⚙️ [**Antigravity Sidecars**](sidecars/README.md): Background daemons and cron schedules for continuous monitoring and automated code reviews.

---

## 5. Automated Testing & Verification

This repository is backed by an automated test suite and strict schema validation:

```bash
# Run the complete test suite (98 tests)
pytest

# Validate all Claude Code plugins and marketplace
claude plugin validate .claude-plugin/marketplace.json
for p in plugins/claude/*; do claude plugin validate "$p"; done
```

---

## 6. License

This repository is open-sourced under the [Apache License, Version 2.0](LICENSE).
