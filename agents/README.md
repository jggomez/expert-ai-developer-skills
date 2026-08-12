# Antigravity Custom Agents & Loop Engineering

This directory contains definitions for **Custom Agents and Subagents** explicitly designed for execution within the Google Antigravity (AGY) system. These agents form a robust "Loop Engineering" lifecycle topology, leveraging extreme specialization to orchestrate end-to-end software delivery.

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
* **Skill Integration**: Each agent is hardcoded to load the exact combination of developer skills required for their role (e.g., the Implementer loads `skills/test-driven-development` and `skills/python-expert`).
