---
name: senior-dev-orchestrator
description: Orchestrates the software development lifecycle (requirements, architecture, TDD implementation, E2E testing, verification), scaling the process to the task instead of running every phase unconditionally. Trigger when the user wants to design, build, or refactor software using senior engineering best practices.
---

# Senior Software Developer Orchestrator

## Overview
This skill provides an end-to-end software engineering workflow, broken into five phases that specialized subagents can execute. Not every task needs all five: scale the phases actually run to the size and risk of the request.

## Core Workflow Instructions

1. **Phase 1: Product Understanding** — skip for a trivial/isolated change.
   - Establish functional/non-functional requirements; ask clarifying questions only for genuine ambiguity.
   - Output: requirements (a short note for small changes; a full PRD for new features).

2. **Phase 2: Architecture & Design** — skip when no real architectural decision is involved.
   - Evaluate Quality Attribute Drivers (QADs) only when they're actually in play; choose the simplest pattern that satisfies them (KISS/YAGNI).
   - Output: a short design note for local changes, a full architecture blueprint for system-level changes.

3. **Phase 3: Implementation via TDD** — always runs when code changes.
   - Red (failing test) → Green (minimal code, no gold-plating) → Refactor (remove smells, keep tests green).
   - Output: source code and tests.

4. **Phase 4: E2E Testing** — skip when unit tests already cover the change.
   - Execute integration/E2E scenarios sized to the change; a full Requirement Traceability Matrix is for new features, not one-line fixes.
   - Output: test results, and an RTM when a PRD exists.

5. **Phase 5: Verification & Audit** — required for anything touching security, production, or release; optional for small internal changes.
   - Audit against QADs and standards that were actually defined for this task.
   - Output: Final Audit Report (`APPROVED`/`REJECTED` with remediation steps).

## Architecture & Resources
For detailed prompt templates and routing specs for subagents, refer to the bundled resources. If documentation or rules are missing:
- Ask the user where the documentation is located.
- Alternatively, search within the `rules/` or `docs/` directories for project-specific rules and specs.