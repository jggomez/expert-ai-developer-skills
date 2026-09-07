# Antigravity Custom Agents & Loop Engineering

This directory contains definitions for **Custom Agents and Subagents** explicitly designed for execution within the Google Antigravity (AGY) system. These agents form a robust "Loop Engineering" lifecycle topology, leveraging extreme specialization to orchestrate end-to-end software delivery.

> ### ⚠️ Which agent files load where
>
> There are **two copies** of every agent in this repo. They are **not** interchangeable:
>
> | Location | Claude Code | Antigravity CLI | Why |
> | :--- | :---: | :---: | :--- |
> | **this directory** (`agents/*.md`) | ❌ **no** | ✅ yes | frontmatter is Antigravity-only: `model: pro`/`flash` are not valid Claude Code model values, and skills are referenced as `skills/<name>` paths |
> | **`plugins/<name>/agents/*.md`** | ✅ yes | ✅ yes | host-neutral frontmatter: `model: inherit`, bare skill names, explicit `subagent`/`mainAgent`, no `tools` key |
>
> **On Claude Code, always use the plugin copy** ([`plugins/senior-dev/`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/senior-dev), `plugins/senior-dev-flutter/`, `plugins/senior-data-engineer/`, `plugins/sql-query-optimizer/`, `plugins/shared-context/`) — never copy a file from *this* directory into a Claude Code project.
> This directory exists so Antigravity keeps its per-agent `model: pro`/`flash` cost tiering, which a dual-host file can't carry. Neither copy declares a `tools` list; each host applies its own default tool set.

---

## 1. Loop Engineering Topology

The loop engineering process is driven by a single **Main Agent** (the Orchestrator) which recursively invokes and manages an array of strict, single-purpose **Subagents**. This ensures that complex tasks are isolated, context windows remain clean, and execution policies (such as `auto` vs `off`) are tightly governed. Agents execute directly on the workspace filesystem (no container sandbox).

### The Subagent Panel (General Software Development)

| Agent Profile | Role & Specialization | Execution Policy | Typical Actions |
| :--- | :--- | :--- | :--- |
| **`senior-dev-orchestrator`** | **Main Orchestrator**: Manages the overarching SDLC lifecycle, delegates sub-tasks, and tracks final release readiness. | `off` | `invoke_subagent`, `manage_subagents` |
| **`product-analyst`** | **Requirements Engineer**: Clarifies ambiguities with the user and constructs detailed PRDs. | `off` | `ask_question`, `write_to_file` |
| **`architect-engineer`** | **System Designer**: Evaluates Quality Attribute Drivers (QADs) and drafts the system architecture blueprints. | `auto` | `write_to_file`, `replace_file_content` |
| **`code-implementer`** | **TDD Implementer**: Executes strict Red-Green-Refactor cycles to write production code. | `auto` | `write_to_file`, `run_command` |
| **`qa-tester`** | **E2E Tester**: Traces requirements back to End-to-End integration test suites. | `auto` | `run_command`, `grep_search` |
| **`compliance-verifier`** | **Quality Auditor**: Verifies strict compliance with NFRs, security gates, and code smells. | `auto` | `run_command`, `list_dir` |

### Flutter & Dart Development Panel

| Agent Profile | Role & Specialization | Execution Policy | Typical Actions |
| :--- | :--- | :--- | :--- |
| **`flutter-feature-orchestrator`** | **Flutter Orchestrator**: Sizes tasks, sequences official Dart/Flutter skills, and delegates lifecycle phases. | `off` | `invoke_subagent`, `send_message` |
| **`flutter-architect`** | **State & Boundaries**: Selects state management (Riverpod/Bloc/Signals) and commits ADRs. | `auto` | `write_to_file`, `run_command` |
| **`flutter-implementer`** | **TDD & Performance**: Implements UI/logic via official skills, profiles jank, and ensures green tests. | `auto` | `run_command`, `replace_file_content` |
| **`flutter-reviewer`** | **Code & Quality Audit**: Checks rebuild loops, memory leaks, accessibility semantics, and ADR conformance. | `auto` | `run_command`, `replace_file_content` |
| **`flutter-release-engineer`** | **Build & Ship**: Manages `--dart-define-from-file`, flavors, signing, store readiness, and toolchain upgrades. | `auto` | `run_command`, `replace_file_content` |

---

## 2. Standalone Domain Specialists

Additional agents operate in specific domain areas across the development lifecycle:

| Agent | Role | MCP Servers / Tools |
| :--- | :--- | :--- |
| **`senior-data-engineer`** | Google Cloud data pipeline design: lake/warehouse architecture, CDC via Datastream, SCD modeling in BigQuery/Dataform. | `bigquery`, `datastream`, `dataform`, `pubsub` (via `plugins/senior-data-engineer/mcp_config.json`) |
| **`sql-query-optimizer`** | Finds and rewrites slow SQL — `.sql` files and queries embedded in application code — for both BigQuery and traditional engines. | `bigquery`, `cloudsql` (via `plugins/sql-query-optimizer/mcp_config.json`) |
| **`context-keeper`** | Shared AI context store maintainer (`context/`): manages restore, checkpoint capture, architectural rollups, and compression. | Local scripts, `run_command`, `Bash` |

Their plugin equivalents live in `plugins/` respectively — same skills, same reasoning, with host-neutral `agents/*.md` that load in both Claude Code and Antigravity. The copies here are the Antigravity-only variant that keeps `model: pro`/`flash` for cost tiering.

---

## 3. Using these Agents with Antigravity

These are plain `.md` files, not a packaged plugin — Antigravity auto-discovers agents from either scope: copy into `.agents/agents/` inside a project for project-scoped use, or `~/.gemini/config/agents/` to make them available globally. Full plugins (installed via `agy plugin install`) are global-only on Antigravity; these standalone agent files are the project-scoped path when you don't want that.

### Key Features
* **Cost Optimization**: Complex reasoning agents (Orchestrators, Architects, Implementers, Release Engineers) operate using the `pro` model, whereas validation agents (QA Tester, Verifier, Flutter Reviewer) utilize the faster, cost-efficient `flash` model.
* **Execution Policy Control**: Orchestrators are restricted from running terminal commands directly (`commandExecutionPolicy: "off"`), delegating execution to worker agents with direct filesystem access (`commandExecutionPolicy: auto`; no container sandbox).
* **Skill Integration**: Each agent's system prompt points directly to its bundled skill (e.g. `skills/code-implementer`, `skills/senior-architect-engineering`, `skills/flutter-test-strategy`) for the actual workflow/templates instead of restating them, keeping skills as the single source of truth.
* **Scaled, Not Fixed, Pipeline**: Orchestrators dynamically size the pipeline to the task — a trivial fix goes straight to implementer/reviewer, while a new feature runs the full lifecycle.

---

## 4. Example Prompts

**Full pipeline, via the orchestrator**:
- "Use the senior-dev-orchestrator agent to build a password-reset feature end to end."
- "Orchestrate a fix for this bug report — keep it lightweight, no full design phase needed."
- "Use flutter-feature-orchestrator to build the checkout screen end to end."

**Individual subagents, invoked directly**:
- "Ask the product-analyst agent to turn this feature request into a PRD." (`product-analyst`)
- "Have the architect-engineer agent draft an ADR comparing sync vs. async processing for this endpoint." (`architect-engineer`)
- "Use the code-implementer agent to build the new endpoint with TDD." (`code-implementer`)
- "Have the qa-tester agent write E2E tests for the checkout flow." (`qa-tester`)
- "Ask the compliance-verifier agent for a release-readiness verdict on this branch." (`compliance-verifier`)
- "Use context-keeper to restore decisions from past sessions." (`context-keeper`)
- "Ask sql-query-optimizer to review this slow query plan." (`sql-query-optimizer`)

