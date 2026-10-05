# Senior Dev Plugin (Claude Code)

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-senior--dev-green?style=flat-square)](file:///./)

The `senior-dev` plugin packages the repository's Graph Engineering subagent topology — a Senior Developer Orchestrator plus five specialized subagents (Product Analyst, Architect, Code Implementer, QA Tester, Compliance Verifier) — as a self-contained plugin for **Claude Code**.

- **Claude Code**: Install via `/plugin install senior-dev` from the marketplace or `claude plugin install plugins/claude/senior-dev`. Subagents use native Claude Code tools (`Bash`, `Read`, `Write`, `Edit`, `Glob`, `Grep`, `Agent`).

---

## 1. Directory Tree & Architecture

```
plugins/claude/senior-dev/
├── README.md               # This usage manual
├── .claude-plugin/
│   └── plugin.json         # Claude Code plugin manifest
├── .mcp.json               # MCP definitions (GCP Cloud Run, Firebase)
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
└── skills/                 # Physical copy of the 8 skills these agents depend on (sanitized for Claude)
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

| Agent | Role | Invocation | Responsibilities |
| :--- | :--- | :--- | :--- |
| **`senior-dev-orchestrator`** | Lead Orchestrator | Main Session | Authors `PLAN.md`, monitors DAG state machine. **Prohibited from writing code directly.** |
| **`product-analyst`** | Requirements Engineer | `Agent` | Clarifies ambiguities, drafts PRDs, defines user stories and acceptance criteria. |
| **`architect-engineer`** | System Designer | `Agent` | QADs, SEI tactics, ADRs, database schemas, and interface boundaries. |
| **`code-implementer`** | TDD Implementer | `Agent` | **MANDATORY worker**: Writes and refactors production code using strict Red-Green-Refactor. |
| **`qa-tester`** | Test Engineer | `Agent` | **MANDATORY worker**: Executes unit, integration, and regression suites; requires `exit code 0`. |
| **`compliance-verifier`** | Release Auditor | `Agent` | **MANDATORY worker**: Audits linters, OWASP, code smells; issues `APPROVED` verdict. |

---

## 3. The 9-Stage Command Framework

The subagents and orchestrator execute along the standardized 9-stage engineering cycle:

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
| **`PreToolUse`** | `hooks/orchestrator-role-gate.js` | Enforces Inviolable Role Boundaries: intercepts file edit tools (`Write`, `Edit`) when called by `senior-dev-orchestrator` on production code files, mandating delegation to `code-implementer`. |
| **`Stop`** | `hooks/universal-quality-gate.js` | Enforces that tests pass (`exit code 0`) and no critical quality defects remain before session termination. |

---

## 5. Bundled Skills (8 Packaged Modules)

1. `senior-dev-orchestrator`
2. `product-analyst`
3. `senior-architect-engineering`
4. `code-implementer`
5. `code-smells-expert`
6. `refactoring-code-expert`
7. `qa-tester`
8. `compliance-verifier`

---

## 6. Installation

**In Claude Code**:
```bash
/plugin install senior-dev
# or local:
claude plugin install plugins/claude/senior-dev
```
