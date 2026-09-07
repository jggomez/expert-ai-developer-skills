---
trigger: model_decision
description: 9-stage engineering execution cycle (/spec, /plan, /build, /test, /constraints, /review, /perf, /code-simplify, /ship) with dynamic orchestrator sizing and subagent delegation.
---

# Rule: Engineering Execution Workflow

**Identifier**: `loop-engineering-workflow`

## 1. The 9-Stage Cycle & Key Principles

Every software modification follows this standardized command lifecycle:

| What you're doing | Command | Key Principle | Primary Focus |
| :--- | :--- | :--- | :--- |
| **Define what to build** | `/spec` | Spec before code | Requirements, PRD, scope boundaries, acceptance criteria |
| **Plan how to build it** | `/plan` | Small, atomic tasks | Architecture ADRs, task decomposition, subagent delegation |
| **Build incrementally** | `/build` | One slice at a time | TDD implementation, vertical slices, official skills |
| **Prove it works** | `/test` | Tests are proof | Unit, widget, integration tests, AAA pattern, empirical exit 0 |
| **Set the quality bar** | `/constraints` | Decide it once, enforce it everywhere | NFRs, security gates, secrets, linter rules, branch protection |
| **Review before merge** | `/review` | Improve code health | PR review, static analysis, leaks, code smells, blocking verdicts |
| **Audit performance** | `/perf` | Measure before you optimize | Profiling first, jank/slots/query bottlenecks, benchmarks |
| **Simplify the code** | `/code-simplify` | Clarity over cleverness | Dead code elimination, cyclomatic complexity reduction, DRY/KISS |
| **Ship to production** | `/ship` | Faster is safer | Conventional commits, changelog, versioning, CI matrix, PR/deploy |

## 2. Dynamic Entry Points & Orchestrator Sizing

Orchestrators **MUST** size the workflow dynamically based on task nature. **NEVER** run all 9 stages blindly:

- **Trivial Fix / Bug**: Jump to `/test` (write reproducing test) -> `/build` (minimal fix) -> `/review` -> `/ship`.
- **New Feature / Subsystem**: Full sequence starting at `/spec`.
- **Refactoring / Debt**: Jump to `/code-simplify` -> `/test` (regression check) -> `/review` -> `/ship`.
- **Performance Tuning**: Jump to `/perf` (profile first) -> `/build` (targeted optimization) -> `/test` -> `/perf` (re-profile) -> `/review` -> `/ship`.
- **Direct Command Invocation**: When the user invokes a slash command directly (e.g. `/review` or `/test`), immediately execute that phase.

## 3. Mandatory Execution Gates

- **Tests are Proof**: Never declare victory without empirical execution evidence (`exit code 0`).
- **Isolation Protocol**: Never allow parallel subagents to concurrently edit overlapping files without isolated workspaces.
- **Verification Guarantee**: Always re-run automated tests after integrating subagent outputs.
