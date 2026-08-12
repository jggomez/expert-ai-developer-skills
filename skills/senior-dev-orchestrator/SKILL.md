---
name: senior-dev-orchestrator
description: Orchestrates full software development lifecycle (requirements analysis, architecture design, TDD implementation, E2E testing, and verification) using specialized subagents. Trigger when the user wants to design, build, or refactor software using senior engineering best practices.
---

# Senior Software Developer Orchestrator

## Overview
This skill provides an end-to-end software engineering workflow. It ensures software is built systematically by breaking the task into five distinct phases executed by specialized subagents.

## Core Workflow Instructions

1. **Phase 1: Product Understanding**
   - Execute product requirements analysis.
   - Ask clarifying questions before proceeding to design.
   - Output: Functional/Non-Functional Requirements.

2. **Phase 2: Architecture & Design**
   - Evaluate Quality Attribute Drivers (QADs).
   - Select design patterns and draft component diagrams.
   - Output: Architecture Blueprint.

3. **Phase 3: Implementation via TDD**
   - Write failing unit tests first.
   - Implement minimal production code to pass tests.
   - Refactor clean code.
   - Output: Source code and unit tests.

4. **Phase 4: E2E Testing**
   - Execute integration and end-to-end test scenarios.
   - Output: E2E test suite & requirement validation.

5. **Phase 5: Verification & Audit**
   - Perform a final readiness audit against QADs and standards.
   - Output: Final Audit Report.

## Architecture & Resources
For detailed prompt templates and routing specs for subagents, refer to the bundled resources. If documentation or rules are missing:
- Proactively use `ask_question` to ask the user where the documentation is located.
- Alternatively, search within the `rules/` or `docs/` directories for project-specific rules and specs.