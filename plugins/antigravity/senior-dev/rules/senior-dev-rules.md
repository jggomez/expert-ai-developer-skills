---
trigger: model_decision
description: Senior developer engineering rules enforcing the 9-stage cycle (/spec, /plan, /build, /test, /constraints, /review, /perf, /code-simplify, /ship) and dynamic subagent orchestration.
---

# Senior Dev Engineering Rules

**Identifier**: `senior-dev-rules`

## 1. The 9-Stage Command Lifecycle

Follow this command cycle for feature delivery, bug fixes, and refactoring:

| What you're doing | Command | Key Principle | Assigned Agent / Skill |
| :--- | :--- | :--- | :--- |
| **Define what to build** | `/spec` | Spec before code | `product-analyst` |
| **Plan how to build it** | `/plan` | Small, atomic tasks | `architect-engineer` |
| **Build incrementally** | `/build` | One slice at a time | `code-implementer` |
| **Prove it works** | `/test` | Tests are proof | `qa-tester` |
| **Set the quality bar** | `/constraints` | Decide it once, enforce it everywhere | `compliance-verifier` |
| **Review before merge** | `/review` | Improve code health | `compliance-verifier` |
| **Audit performance** | `/perf` | Measure before you optimize | `performance-scalability` |
| **Simplify the code** | `/code-simplify` | Clarity over cleverness | `code-implementer` (`refactor-codebase`) |
| **Ship to production** | `/ship` | Faster is safer | `pull-request-expert`, `commit-expert` |

## 2. Dynamic Entry Points & Sizing

The orchestrator (`senior-dev-orchestrator`) sizes the required stages dynamically:
- **Trivial Fix / Bug**: Route directly to `/test` (failing test) -> `/build` (minimal fix) -> `/review` -> `/ship`.
- **New Feature / Architecture**: Full sequence starting at `/spec`.
- **Refactoring / Debt**: Start at `/code-simplify` with regression `/test`.
- **Performance Profiling**: Start at `/perf` with benchmark verification.
- **Direct Slash Command**: Immediately delegate to the designated subagent.

## 3. Engineering Constraints

- **Strict TDD**: Write failing test before writing production code.
- **Clean Architecture**: Domain logic must never depend on database drivers or transport protocols.
- **Zero Raw Secrets**: Never write credentials or API keys into code or logs.
- **Empirical Validation**: Code is only complete when tests pass with `exit code 0`.
