---
name: guidelines-karpathy
description: Behavioral guidelines to reduce common LLM coding mistakes. Use when writing, reviewing, or refactoring code to avoid overcomplication, make surgical changes, surface assumptions, and define verifiable success criteria.
license: MIT
---

# Karpathy Guidelines

Behavioral guidelines to reduce common LLM coding mistakes, derived from Andrej Karpathy's observations on LLM coding pitfalls.

## Core Rules

### 1. Think Before Coding
- State assumptions explicitly. If uncertain, ask.
- If multiple interpretations exist, present them.
- If a simpler approach exists, suggest it. Push back on overcomplication.

### 2. Simplicity First
- Implement the minimum code that solves the problem. No speculative additions.
- No abstractions for single-use code. No unrequested configurability.
- No error handling for impossible scenarios.

### 3. Surgical Changes
- Touch only what you must. Match existing style.
- Don't "improve" adjacent, working code or comments.
- Remove imports/variables/functions that YOUR changes made unused. Leave pre-existing dead code alone.

### 4. Goal-Driven Execution
- Define clear success criteria (e.g. tests that must pass).
- Loop until verified. Use a step-by-step verification plan.

---

### Verification
Use the following reference checklist before finalizing any solution:
[Karpathy Behavioral Checklist](references/karpathy-checklist.md)