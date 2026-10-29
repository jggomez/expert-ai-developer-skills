---
trigger: always_on
description: Code quality and Zero-Fluff documentation rules enforcing official artifact line caps (AGENTS.md, Google DESIGN.md, docs/<feature-name>/), Fail-Honest reporting, Karpathy/DRY/KISS principles, Anti-Lazy code policy, and Mermaid diagram safety.
---

# Code Quality & Zero-Fluff Documentation Standards

**Identifier**: `docs-and-quality-rules`

## 1. Official Artifact Standards & Hard Line Caps (`3-Tier SDLC`)
All repository governance and `docs/<feature-name>/` deliverables must be Zero-Fluff, high-signal, and strictly within line caps:
- **Root `AGENTS.md` (`<= 90 lines`)**: Verified build/lint/test commands, coding conventions, and links to `DESIGN.md` & `context/memory/MEMORY.md`.
- **Root Google `DESIGN.md` (`<= 110 lines`)**: Official 2-layer spec (YAML design tokens + 8 sections: `Overview`, `Colors`, `Typography`, `Layout`, `Elevation & Depth`, `Shapes`, `Components`, `Do's and Don'ts`), plus optional `docs/<feature-name>/design.md` (`<= 35 lines`) feature delta.
- **`docs/<feature-name>/prd.md` (`<= 70 lines`)**: `Objective`, `Scope`, `User Stories` (`US-XX`), and testable `Acceptance Criteria` (`AC-XX`).
- **`docs/<feature-name>/adr-NNN-*.md` (`<= 55 lines`)**: MADR with `Context`, `Options`, `Decision & Justification`, and `Trade-offs` (optional `docs/<feature-name>/architecture.md <= 70 lines`).
- **`docs/<feature-name>/test-matrix.md` (`<= 80 lines`)**: Per-case `TC-XX` across unit/integration/E2E tiers (`Objective`, `Steps`, `Expected Result`, `Automated Test`, `Status`) + terminal proof.
- **Verification Reports (`<= 50 lines` each)**: `critic-review.md`, `adversarial-report.md`, and `blackbox-report.md` must be Zero-Fluff and **Fail-Honest** — explicitly reporting `BLOCKED` or `SKIPPED` when a runner, server, or browser is unavailable (never fabricating `PASSED`; E2E requires physical `.png` evidence in `docs/<feature-name>/evidence/`).
- **Legacy Sync**: Inspect and synchronize legacy folders (`docs/specifications/`) with `docs/<feature-name>/` so zero contradictory specs remain.

## 2. Karpathy Engineering Guidelines, DRY & KISS
- **Zero Speculative Engineering**: Implement only what current requirements demand; ban premature abstractions, unused factories, or speculative base classes.
- **Clarity, DRY & KISS**: Prefer simple, self-documenting code over clever metaprogramming; extract cohesive single-purpose helpers to eliminate duplication.
- **English Only**: Write all identifiers, comments, commits, PRs, docs, and diagrams exclusively in English.

## 3. Anti-Lazy Code Policy & Production Completeness
- **Zero Placeholders**: Strictly forbid AI shortcuts or partial stubs (`// TODO: Implement later`, `# ... rest of existing code ...`, `pass  # placeholder`, or silent `except Exception: pass`).
- **Complete & Non-Destructive**: Deliver production-ready error handling, input validation, and static types while preserving unrelated existing code, comments, and docstrings intact.

## 4. Markdown Portability & Mermaid Diagram Safety
- **Clean GFM & Relative Links**: Enforce strict heading hierarchy (`#` -> `##` -> `###`), valid tables, and portable relative file links (zero hardcoded machine-local path leaks).
- **Mermaid Syntax Safety**: Use supported Mermaid diagrams (`flowchart TD`, `flowchart LR`, `sequenceDiagram`, `stateDiagram-v2`, `erDiagram`) and always quote node labels containing parentheses or special characters (e.g., `id["Label (Detail)"]`).
