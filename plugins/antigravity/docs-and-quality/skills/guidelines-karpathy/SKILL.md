---
name: guidelines-karpathy
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
---

# Karpathy Guidelines Skill

## Overview
This skill enforces behavioral and architectural restraint to prevent common LLM coding pitfalls, derived from Andrej Karpathy's observations on LLM developer tendencies. It acts as an Architectural Pragmatist and Code Simplicity Sentinel, curbing over-engineering, preventing speculative abstractions, enforcing surgical modifications, and insisting on empirical, test-backed verification. It is deterministically backed by the Anti-Lazy Code Gate (`anti-lazy-code-gate.js`) to block placeholder stubs before session completion.

## When to Use
### Trigger Scenarios
- Pre-implementation sanity checks before generating code or designing solutions.
- Code reviews to evaluate whether a proposed solution is overcomplicated or speculative.
- Debugging and fixing targeted defects where touching adjacent code risks regressions.
- Refactoring tasks to ensure changes remain strictly minimal and goal-driven.

### When NOT to Use
- **Product requirement definition**: Route to `product-analyst`.
- **Automated AST-based code smell detection**: Route to `code-smells-expert`.
- **High-level enterprise architecture frameworks**: Route to `senior-architect-engineering`.
- **CI/CD pipeline and git hook setups**: Route to `build-and-ci-gates`.

## Process
### Rule 1: Think Before Coding
- State technical assumptions explicitly before modifying files. If genuine ambiguity exists, ask the user directly.
- If multiple valid architectural interpretations exist, present them with trade-offs rather than guessing silently.
- If a simpler, lower-code approach exists, propose it. Actively push back against unnecessary complexity.

### Rule 2: Simplicity First (YAGNI)
- Implement the absolute minimum amount of code necessary to solve the problem cleanly.
- Never introduce speculative configurability, unused parameters, or generic abstractions for single-use code.
- Avoid writing defensive error handling for logically impossible internal scenarios.

### Rule 3: Surgical, Minimal Changes
- Touch only the files and lines strictly required to satisfy the goal.
- Match existing repository styling, conventions, and idioms.
- Do NOT "improve", reformat, or refactor adjacent working code or comments unrelated to the task.
- Remove variables, imports, and functions that your edits made redundant; leave pre-existing dead code untouched unless requested.

### Rule 4: Anti-Lazy Code Policy (Deterministic Gate)
- Enforce **zero tolerance** for lazy placeholders or incomplete stubbed code:
  * Prohibited patterns include `TODO: implement later`, `# ... rest of code`, `// ... rest of code`, `pass # placeholder`, `/* unimplemented */`, or bare `raise NotImplementedError`.
- Provide 100% complete, fully implemented, working code in every single edit.
- In both runtime ecosystems, this rule is guarded deterministically by `anti-lazy-code-gate.js`: any diff containing placeholder stubs immediately fails the Stop gate with exit code 2.

### Rule 5: Anti-Premature Abstraction (Premature Abstraction Smell)
- Guard against the **Premature Abstraction Smell**: avoid over-engineering interfaces, generic base classes, factory layers, or strategy patterns when a simple, pure function suffices.
- Follow the Rule of Three: do not extract an abstraction until at least three concrete instances exist and the duplication causes demonstrable maintenance friction.
- Three slightly similar lines of transparent code are far superior to a premature indirection layer that complicates debugging.

### Rule 6: Goal-Driven Execution & Loop Verification
- Establish concrete, verifiable success criteria (e.g. specific tests that must pass) before editing.
- Loop and iterate until tests pass; never assume victory without running the verification command.

## Usage
### Example Prompts
- *"Review this proposed solution against the Karpathy guidelines: are we overcomplicating the architecture?"*
- *"Fix this bug surgically without touching or refactoring any adjacent functions."*
- *"Implement the simplest possible solution for this feature without speculative abstractions or lazy stubs."*

### Host Execution Instructions
- **Claude Code**: Keep changes atomic and surgical. The plugin's Stop hook (`anti-lazy-code-gate.js`) automatically guarantees no lazy placeholder stubs are committed.
- **Antigravity**: Apply Karpathy principles during the PLAN and BUILD phases, verified by `anti-lazy-code-gate.js` before task completion.

## Red Flags
- Leaving `TODO: implement later` or placeholder comments instead of writing full implementations.
- Adding "future-proofing" flags, hooks, or interfaces for features not explicitly requested.
- Prematurely creating multi-tiered class hierarchies or factory patterns when a pure function suffices.
- Refactoring or reformatting adjacent working functions during a focused bug fix.
- Declaring a solution complete without executing the relevant test suite.

## Verification
- [ ] Assumptions stated and confirmed before implementing.
- [ ] Minimum lines of code written to solve the problem (zero speculative abstractions).
- [ ] Complete code implementations provided (zero lazy stubs; `anti-lazy-code-gate.js` passes cleanly).
- [ ] Only target files modified; adjacent working code untouched.
- [ ] Automated tests executed and passing cleanly.

## References
For the comprehensive behavioral checklist and review rubrics:
- [Karpathy Behavioral Checklist](references/karpathy-checklist.md)