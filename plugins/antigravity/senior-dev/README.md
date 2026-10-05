# Senior Dev Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-senior--dev-green?style=flat-square)](file:///./)

The `senior-dev` plugin packages the repository's Graph Engineering subagent topology — a Senior Developer Orchestrator plus five specialized subagents (Product Analyst, Architect, Code Implementer, QA Tester, Compliance Verifier) — as a self-contained plugin for **Google Antigravity**.

- **Google Antigravity**: Install via `agy plugin install ./plugins/antigravity/senior-dev`. Subagents in `agents/` declare native Antigravity tools (`run_command`, `write_to_file`, `replace_file_content`, `view_file`, `invoke_subagent`, `manage_subagents`, `send_message`) with `commandExecutionPolicy: auto`.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog, kept self-contained so the plugin folder can be distributed on its own. After editing any bundled skill under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy — don't hand-edit both. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/antigravity/senior-dev/
├── README.md               # This usage manual
├── plugin.json             # Required plugin metadata descriptor (Antigravity, plugin root)
├── .claude-plugin/
│   └── plugin.json         # Manifest compatibility marker
├── .mcp.json               # MCP definitions (GCP Cloud Run, Firebase)
├── mcp_config.json         # Same MCP servers, Antigravity format
├── hooks.json              # Lifecycle hook definitions
├── hooks/
│   ├── orchestrator-role-gate.js # PreToolUse gate preventing orchestrator from editing code
│   └── universal-quality-gate.js # Stop hook executing test suites and linters
├── agents/                 # 6 bundled subagents
│   ├── senior-dev-orchestrator.md  # Main orchestrator; governs DAG & PLAN.md
│   ├── product-analyst.md          # Requirements & PRDs
│   ├── architect-engineer.md       # Architecture & ADRs
│   ├── code-implementer.md         # Strict TDD implementation
│   ├── qa-tester.md                # E2E / integration testing
│   └── compliance-verifier.md      # Final NFR / security audit
├── rules/                  # Senior dev 9-stage cycle & tool execution rules
│   └── senior-dev-rules.md
└── skills/                 # Physical copy of the 8 skills these agents depend on
    ├── senior-dev-orchestrator/
    ├── product-analyst/
    ├── senior-architect-engineering/
    ├── code-implementer/
    ├── code-smells-expert/
    ├── refactoring-code-expert/
    ├── qa-tester/
    └── compliance-verifier/
```

---

## 2. Subagent Panel & Inviolable Boundaries

| Agent | Role | Execution Policy | Responsibilities |
| :--- | :--- | :--- | :--- |
| **`senior-dev-orchestrator`** | Lead Orchestrator | `auto` | Authors `PLAN.md`, monitors DAG state machine. **Prohibited from writing code directly.** |
| **`product-analyst`** | Requirements Engineer | `auto` | Clarifies ambiguities, drafts PRDs, defines user stories and acceptance criteria. |
| **`architect-engineer`** | System Designer | `auto` | QADs, SEI tactics, ADRs, database schemas, and interface boundaries. |
| **`code-implementer`** | TDD Implementer | `auto` | **MANDATORY worker**: Writes and refactors production code using strict Red-Green-Refactor. |
| **`qa-tester`** | Test Engineer | `auto` | **MANDATORY worker**: Executes unit, integration, and regression suites; requires `exit code 0`. |
| **`compliance-verifier`** | Release Auditor | `auto` | **MANDATORY worker**: Audits linters, OWASP, code smells; issues `APPROVED` verdict. |

---

## 3. The 9-Stage Command Framework

The subagents and orchestrator execute along the standardized 9-stage engineering cycle, governed by `rules/senior-dev-rules.md`:

| Phase | Command | Key Principle | Responsible Role |
| :--- | :--- | :--- | :--- |
| **Define what to build** | `/spec` | Spec before code | `product-analyst` (PRD, user stories, acceptance criteria) |
| **Plan how to build it** | `/plan` | Small, atomic tasks | `senior-dev-orchestrator` / `architect-engineer` (ADR, task sizing) |
| **Build incrementally** | `/build` | One slice at a time | `code-implementer` (Red-Green-Refactor, vertical slices) |
| **Prove it works** | `/test` | Tests are proof | `qa-tester` (unit, integration, regression verification) |
| **Set the quality bar** | `/constraints` | Decide once, enforce everywhere | `compliance-verifier` (security gates, OWASP, linter rules) |
| **Review before merge** | `/review` | Improve code health | `compliance-verifier` / peer review (code smells, debt) |
| **Audit performance** | `/perf` | Measure before you optimize | `code-implementer` / orchestrator (profiling, bottlenecks) |
| **Simplify the code** | `/code-simplify` | Clarity over cleverness | `code-implementer` (dead code elimination, KISS) |
| **Ship to production** | `/ship` | Faster is safer | `senior-dev-orchestrator` (conventional commits, release) |

---

## 4. Lifecycle Hooks & Deterministic Gates

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`PreToolUse`** | `hooks/orchestrator-role-gate.js` | Enforces Inviolable Role Boundaries: intercepts file edit tools (`write_to_file`, `replace_file_content`) when called by `senior-dev-orchestrator` on production code files, mandating delegation to `code-implementer`. |
| **`Stop`** | `hooks/universal-quality-gate.js` | Enforces that tests pass (`exit code 0`) and no critical quality defects remain before session termination. |

---

## 5. Bundled Skills (8 Packaged Modules)

On loading the plugin, the following 8 skills are automatically loaded as the agents' skill dependencies:

1. **`senior-dev-orchestrator`**: Phase breakdown, DAG state machine, and routing logic for the orchestrator.
2. **`product-analyst`**: Requirement discovery workflow and PRD template.
3. **`senior-architect-engineering`**: SEI quality attribute scenarios, tactics, ATAM, ADR template.
4. **`code-implementer`**: Red-Green-Refactor TDD workflow.
5. **`code-smells-expert`**: AST-based code smell detection.
6. **`refactoring-code-expert`**: Safe, test-guarded refactoring steps.
7. **`qa-tester`**: E2E/integration test-plan construction and RTM template.
8. **`compliance-verifier`**: Final NFR/security/coverage audit and verdict format.

---

## 6. Example Prompts

**Full pipeline via the orchestrator**:
- "Use the senior-dev-orchestrator agent to build a password-reset feature end to end — requirements, design, implementation, tests, and a final audit."
- "Orchestrate a fix for this bug report using senior engineering best practices."

**Individual subagents, invoked directly**:
- "Ask the product-analyst agent to turn this feature request into a PRD." (`product-analyst`)
- "Have the architect-engineer agent draft an ADR comparing sync vs. async processing for this endpoint." (`architect-engineer`)
- "Use the code-implementer agent to build the new endpoint with TDD." (`code-implementer`)
- "Have the qa-tester agent write tests for the checkout flow and map them to requirements." (`qa-tester`)
- "Ask the compliance-verifier agent for a release-readiness verdict on this branch." (`compliance-verifier`)

---

## 7. Installation

**Antigravity CLI**:
```bash
agy plugin install ./plugins/antigravity/senior-dev
```
