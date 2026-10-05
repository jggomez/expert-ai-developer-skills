---
trigger: always_on
description: Quality and documentation engineering rules enforcing Karpathy guidelines, self-documenting code, and zero lazy placeholders.
---

# Code Quality & Documentation Standards

**Identifier**: `docs-and-quality-rules`

## 1. Karpathy Engineering Guidelines
- **Zero Speculative Engineering**: Never write abstractions, classes, or factories for future hypothetical features. Build only what is immediately required.
- **Clarity over Cleverness**: Write readable, straightforward code. Avoid obfuscated one-liners or premature template metaprogramming.
- **English Standard**: All code identifiers (variables, functions, types), architectural diagrams, comments, and commit messages must be written exclusively in English.

## 2. Anti-Lazy Code Invariant
- **No Incomplete Implementations**: Never leave placeholder comments like `// TODO: implement later`, `pass # placeholder`, or `... # your code here`.
- If a method or endpoint is generated, it must be completely implemented, verified with tests, and functional.

## 3. Documentation & Diagram Invariant
- When documenting architecture or flows, use standard GitHub Flavored Markdown and Mermaid diagrams (`flowchart TD`, `sequenceDiagram`, `stateDiagram-v2`).
- Diagrams must quote node labels containing special characters to prevent rendering syntax errors.
