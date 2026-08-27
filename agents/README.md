# Antigravity Custom Agents & Loop Engineering

This directory contains definitions for **Custom Agents and Subagents** explicitly designed for execution within the Google Antigravity (AGY) system. These agents form a robust "Loop Engineering" lifecycle topology, leveraging extreme specialization to orchestrate end-to-end software delivery.

**Using Claude Code instead?** The same six agents, reusing the same skills, are packaged as a native Claude Code plugin at [`plugins/senior-dev/`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/plugins/senior-dev) — Claude Code's subagent frontmatter is not compatible with Antigravity's, so the two are kept as separate, natively-formatted directories rather than one shared file.

---

## 1. Loop Engineering Topology

The loop engineering process is driven by a single **Main Agent** (the Orchestrator) which recursively invokes and manages an array of strict, single-purpose **Subagents**. This ensures that complex tasks are isolated, context windows remain clean, and execution policies (such as `sandbox` vs `off`) are tightly governed.

### The Subagent Panel

| Agent Profile | Role & Specialization | Execution Policy | Assigned Capabilities |
| :--- | :--- | :--- | :--- |
| **`senior-dev-orchestrator`** | **Main Orchestrator**: Manages the overarching SDLC lifecycle, delegates sub-tasks, and tracks final release readiness. | `off` | `invoke_subagent`, `manage_subagents` |
| **`product-analyst`** | **Requirements Engineer**: Clarifies ambiguities with the user and constructs detailed PRDs. | `off` | `ask_question`, `write_to_file` |
| **`architect-engineer`** | **System Designer**: Evaluates Quality Attribute Drivers (QADs) and drafts the system architecture blueprints. | `sandbox` | `write_to_file`, `replace_file_content` |
| **`code-implementer`** | **TDD Implementer**: Executes strict Red-Green-Refactor cycles to write production code. | `sandbox` | `write_to_file`, `run_command` |
| **`qa-tester`** | **E2E Tester**: Traces requirements back to End-to-End integration test suites. | `sandbox` | `run_command`, `grep_search` |
| **`compliance-verifier`** | **Quality Auditor**: Verifies strict compliance with NFRs, security gates, and code smells. | `sandbox` | `run_command`, `list_dir` |

---

## 2. Using these Agents with Antigravity

These configurations can be directly loaded into an Antigravity workspace or global configuration directory (`~/.gemini/config/agents/`). 

### Key Features
* **Cost Optimization**: Complex reasoning agents (Orchestrator, Architect, Implementer) operate using the `pro` model, whereas validation agents (QA Tester, Verifier) utilize the faster, cost-efficient `flash` model.
* **Security & Sandboxing**: The orchestrator is restricted from running terminal commands directly (`commandExecutionPolicy: off`), forcing it to delegate to the sandboxed worker agents.
* **Skill Integration**: Each agent's system prompt is intentionally thin — it points to its bundled skill (e.g. `skills/code-implementer`, `skills/senior-architect-engineering`) for the actual workflow/templates instead of restating them, so the skill stays the single source of truth.
* **Scaled, Not Fixed, Pipeline**: The Orchestrator does not run all five subagents for every request. It sizes the pipeline to the task — a trivial fix goes straight to `code-implementer`, while a new feature or system-level change runs the full Product → Architect → Implement → QA → Verify sequence. Each subagent mirrors this: it scales its own deliverable (PRD, ADR, E2E suite, audit) to what the change actually warrants, avoiding over-engineering on small tasks while still covering the full lifecycle on larger ones.

---

## 3. Example Prompts

**Full pipeline, via the orchestrator**:
- "Use the senior-dev-orchestrator agent to build a password-reset feature end to end."
- "Orchestrate a fix for this bug report — keep it lightweight, no full design phase needed."

**Individual subagents, invoked directly**:
- "Ask the product-analyst agent to turn this feature request into a PRD." (`product-analyst`)
- "Have the architect-engineer agent draft an ADR comparing sync vs. async processing for this endpoint." (`architect-engineer`)
- "Use the code-implementer agent to build the new endpoint with TDD." (`code-implementer`)
- "Have the qa-tester agent write E2E tests for the checkout flow." (`qa-tester`)
- "Ask the compliance-verifier agent for a release-readiness verdict on this branch." (`compliance-verifier`)

---

## 4. Standalone Domain Experts

Two more agents live in this directory, outside the Loop Engineering topology — each a single area of expertise, not part of the orchestrator's panel:

| Agent | Role | MCP Servers |
| :--- | :--- | :--- |
| **`senior-data-engineer`** | Google Cloud data pipeline design: lake/warehouse architecture, CDC via Datastream, SCD modeling in BigQuery/Dataform. | `bigquery`, `datastream`, `dataform`, `pubsub` (via `plugins/senior-data-engineer/mcp_config.json`) |
| **`sql-query-optimizer`** | Finds and rewrites slow SQL — `.sql` files and queries embedded in application code — for both BigQuery and traditional engines. | `bigquery`, `cloudsql` (via `plugins/sql-query-optimizer/mcp_config.json`) |

Their Claude Code equivalents live in `plugins/senior-data-engineer/` and `plugins/sql-query-optimizer/` respectively — same skills, same reasoning, packaged per-platform for the same incompatible-schema reason as the Loop Engineering panel above.

