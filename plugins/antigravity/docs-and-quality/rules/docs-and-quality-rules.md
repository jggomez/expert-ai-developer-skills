---
trigger: always_on
description: Code quality and documentation engineering rules enforcing feature directory conventions (docs/<feature-name>/), Karpathy guidelines, DRY/KISS, self-documenting code, zero lazy placeholders, and valid Mermaid diagram standards.
---

# Code Quality & Documentation Standards

**Identifier**: `docs-and-quality-rules`

## 1. Feature Documentation & Artifact Directory Convention (`docs/<feature-name>/`)
- **Feature Directory Isolation**: All technical documentation, discovery specifications, architecture decision records, and verification artifacts associated with a feature must be stored in a dedicated feature directory: `docs/<feature-name>/` (derived from the task slug, e.g., `docs/user-auth/`, `docs/order-checkout/`).
- **Standard Discovery Artifacts**:
  - `docs/<feature-name>/prd.md`: Product requirements, user personas, edge cases, acceptance criteria, and validation rules.
  - `docs/<feature-name>/design.md`: UI/UX design specifications, component tree, design tokens, responsive layouts, accessibility criteria.
  - `docs/<feature-name>/architecture.md`: Component boundaries, data flow diagrams, API schemas, sequence diagrams, and technology choices.
  - `docs/<feature-name>/adr-*.md`: Architectural Decision Records detailing context, evaluated alternatives, decision, and consequences.
- **Standard Verification Artifacts**:
  - `docs/<feature-name>/test-matrix.md`: Standardized QA Test Matrix mapping requirements to tests across unit, integration, and E2E tiers with empirical terminal proof.
  - `docs/<feature-name>/critic-review.md`: Code smell and SOLID invariant review findings.
  - `docs/<feature-name>/adversarial-report.md`: Adversarial stress and fault-injection findings.
  - `docs/<feature-name>/blackbox-report.md`: E2E user journey and resilience findings.
- **Documentation Synchronization**: If legacy specifications exist in the workspace (e.g. `docs/specifications/`), agents must inspect and synchronize them with the canonical `docs/<feature-name>/` structure. Never leave orphaned or contradictory specifications.

## 2. Karpathy Engineering Guidelines, DRY & KISS
- **Zero Speculative Engineering**: Build only what is immediately required by the current task specifications. Never introduce speculative abstractions, anticipatory base classes, premature generic interfaces, or factories for hypothetical future needs.
- **Clarity over Cleverness**: Prioritize simple, readable, self-documenting code over clever metaprogramming, obscure one-liners, or complex inheritance hierarchies.
- **DRY (Don't Repeat Yourself)**: Eliminate duplicate logic, queries, and configurations cleanly by extracting cohesive, single-purpose functions or modules.
- **KISS (Keep It Simple, Stupid)**: Choose the simplest viable solution that satisfies requirements, passing tests, and performance constraints.
- **English Standard**: All code identifiers (variables, functions, classes, interfaces), comments, commit messages, PR descriptions, and architectural diagrams must be written exclusively in English.

## 3. Anti-Lazy Code Policy & Production Completeness
- **Zero Tolerance for Placeholders**: Absolute prohibition against AI shortcuts, lazy stubs, partial implementations, or omitted logic:
  - ❌ `// TODO: Implement later`
  - ❌ `# ... rest of existing code ...`
  - ❌ `pass  # placeholder`
  - ❌ Empty catch/except blocks swallowing exceptions (`except Exception: pass`).
- **Production Completeness**: Every file modified or created must contain full, production-ready code with exhaustive error handling, input validation, type annotations, and clean logging.
- **Preserve Existing Intact**: Do not overwrite or delete existing working code, comments, or docstrings unless explicitly tasked with refactoring them.

## 4. Technical Documentation & Diagram Invariants
- **GitHub Flavored Markdown**: Maintain clean markdown syntax, valid tables, and consistent heading hierarchies (`#`, `##`, `###`).
- **Mermaid Diagrams**: When modeling architecture, sequence flows, or state transitions, use standard Mermaid diagrams (`flowchart TD`, `flowchart LR`, `sequenceDiagram`, `stateDiagram-v2`).
- **Diagram Syntax Safety**: Always quote node labels containing special characters, brackets, or parentheses (e.g., `id["Label (Extra Info)"]`) to prevent rendering syntax errors. Never use unsupported diagram formats.
