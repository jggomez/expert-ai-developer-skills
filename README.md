# Expert AI Developer Skills

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=for-the-badge&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Antigravity](https://img.shields.io/badge/Antigravity-Customizations-orange?style=for-the-badge)](https://github.com/google/antigravity)
[![Skills Standard](https://img.shields.io/badge/AgentSkills.io-35%20Verified-green?style=for-the-badge)](skills)
[![License](https://img.shields.io/badge/License-Apache%202.0-lightgrey?style=for-the-badge)](LICENSE)

Production-grade engineering customizations, subagents, and modular skills for **Google Antigravity (AGY)** and **Claude Code**.

This repository organizes software engineering best practices into **installable plugins**, **modular skills**, **quality rules**, and **execution workflows**.

---

## 1. Repository Overview

At a high level, the repository provides 4 core components:

* **[Plugins](plugins/)**: Self-contained bundles containing specialized subagents, native tools, MCP servers, and lifecycle hooks.
* **[Skills](skills/README.md)**: 35 modular skills adhering to the open [Agent Skills Standard](https://agentskills.io) with deterministic Python automation scripts.
* **[Rules](rules/README.md)**: 10 passive constraint rule profiles enforcing clean code, TDD, branch safety, token optimization, and security.
* **[Workflows](workflows/README.md)**: 16 step-by-step operational playbooks guiding complex tasks (including the 9-stage `/spec` to `/ship` framework).
* **[Sidecars](sidecars/README.md)**: Background daemons and cron schedules for continuous monitoring and automated reviews.

> For in-depth technical details, subagent prompts, or script documentation, refer to the README file in each component's directory.

---

## 2. Installing Plugins in Google Antigravity

Plugins are the fastest and most complete way to customize Antigravity, automatically wiring agents, tools, and MCP servers.

### Install via CLI (`agy`)

Install any plugin globally in Antigravity (`~/.gemini/antigravity-cli/plugins/`):

```bash
# Available plugins in ./plugins/antigravity/
agy plugin install ./plugins/antigravity/senior-dev
agy plugin install ./plugins/antigravity/senior-dev-flutter
agy plugin install ./plugins/antigravity/senior-data-engineer
agy plugin install ./plugins/antigravity/sql-query-optimizer
agy plugin install ./plugins/antigravity/shared-context
agy plugin install ./plugins/antigravity/python-backend
agy plugin install ./plugins/antigravity/git-workflow
agy plugin install ./plugins/antigravity/docs-and-quality
agy plugin install ./plugins/antigravity/multi-agent-ops
```

### Useful Plugin Management Commands

```bash
agy plugin list                    # List installed plugins
agy plugin enable <name>           # Enable a plugin
agy plugin disable <name>          # Temporarily disable a plugin
agy plugin uninstall <name>        # Uninstall a plugin
```

---

## 3. Installing and Using Skills in Google Antigravity

**Skills** provide on-demand capabilities and scripts (progressive disclosure) that the agent activates when relevant.

### Option A: Standard Install via Vercel Skills CLI (Recommended)

You can install any skill directly into your current project without manual cloning:

```bash
# Discover all 35 skills
npx skills add jggomez/expert-ai-developer-skills --list

# Install a specific skill (e.g. python-expert) in the active project (.agents/skills)
npx skills add jggomez/expert-ai-developer-skills --skill python-expert

# Install a specific skill globally on your system
npx skills add jggomez/expert-ai-developer-skills --skill python-expert -g

# Install all 35 skills in the active project
npx skills add jggomez/expert-ai-developer-skills
```

### Option B: Manual Setup

If you have cloned this repository, copy the desired skills:

* **Project-level (version-controlled with team)**:
  ```bash
  mkdir -p .agents/skills/
  cp -r skills/<skill-name> .agents/skills/
  ```
* **Global machine-level (available across all projects)**:
  ```bash
  mkdir -p ~/.gemini/config/skills/
  cp -r skills/<skill-name> ~/.gemini/config/skills/
  ```

---

## 4. Using Rules in Google Antigravity

**Rules** are passive system constraints that Antigravity loads to govern coding style, test enforcement, security checks, and token budgets.

### Where to Place Rules

1. **Project Scope (Recommended)**:
   Copy rules to `.agents/rules/`:
   ```bash
   mkdir -p .agents/rules/
   cp rules/*.md .agents/rules/
   ```
   Antigravity automatically discovers and applies these rules for anyone working in the repository.

2. **Global Scope**:
   Copy rules to your user configuration directory:
   ```bash
   mkdir -p ~/.gemini/config/rules/
   cp rules/*.md ~/.gemini/config/rules/
   ```

### How Rules Activate
Rules require no manual invocation. Antigravity activates them contextually based on your prompt (e.g., enforcing TDD during code changes, blocking direct commits to `main`, or requiring secrets scans).

---

## 5. Using Workflows in Google Antigravity

**Workflows** are active, step-by-step playbooks for standard engineering procedures.

### How to Use Workflows in Sessions

1. **Direct Reference in Prompt**:
   Instruct the agent to follow a specific playbook using `@` or the relative path:
   ```text
   "Follow the workflow @workflows/spec-workflow.md to draft requirements for this feature."
   "Execute @workflows/code-smell-review-workflow.md on the auth module."
   ```

2. **The 9-Stage Command Framework**:
   The workflows implement the end-to-end SDLC lifecycle:
   * `/spec` (`workflows/spec-workflow.md`): Clarify requirements and write PRD before code.
   * `/plan` (`workflows/plan-workflow.md`): Decompose into atomic tasks and define architecture.
   * `/build` (`workflows/build-workflow.md`): Incremental TDD implementation.
   * `/test` (`workflows/test-workflow.md`): Empirical testing and proof of functionality.
   * `/constraints` (`workflows/constraints-workflow.md`): NFR checks, linter rules, and safety gates.
   * `/review` (`workflows/review-workflow.md`): Code smell and architecture health review.
   * `/perf` (`workflows/perf-workflow.md`): Profiling before optimization.
   * `/code-simplify` (`workflows/code-simplify-workflow.md`): Clarity over cleverness, dead code pruning.
   * `/ship` (`workflows/ship-workflow.md`): Conventional commit, release packaging, and merge.

---

## 6. Claude Code Compatibility

All plugins and skills in this repository also support **Claude Code**:

```bash
# Add the marketplace
/plugin marketplace add jggomez/expert-ai-developer-skills

# Install plugins directly
/plugin install senior-dev
/plugin install senior-dev-flutter
```

---

## 7. License

This repository is open-sourced under the [Apache License, Version 2.0](LICENSE).
