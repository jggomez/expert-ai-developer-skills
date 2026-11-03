---
trigger: always_on
description: Code completeness and documentation invariants - no placeholders, no speculative code, fail-honest verdicts and hard caps for AGENTS.md, DESIGN.md and docs/<feature-name>/ artifacts.
---

# Docs & Quality Rules

- **No placeholders**: never leave `TODO: implement`, `... rest of code ...`, `pass  # placeholder`, `throw UnimplementedError()` or silent `except: pass`. Deliver complete code with error handling and types, and keep unrelated code and comments intact.
- **No speculative engineering**: implement only what current requirements need; no unused abstractions, factories or base classes. Prefer simple, readable code (KISS, DRY).
- **Language**: write identifiers, comments, commits and docs in English unless the project already uses another language.
- **Artifact caps** (Tier 1 fixes write no docs artifacts; larger work writes only the ones that apply): root `AGENTS.md <= 90` lines, root `DESIGN.md <= 110`, `docs/<feature-name>/spec.md` sections (`## Product <= 50`, `## Design <= 30`, `## Architecture <= 50`), `adr-NNN-*.md <= 55`, `test-matrix.md <= 80`. Reviewer verdicts (`<= 50` lines) go in the final message, never in report files.
- **Fail-honest verdicts**: report `BLOCKED` or `SKIPPED` with the exact reason when a runner, server or browser is unavailable; E2E `PASSED` needs real `.png` evidence in `docs/<feature-name>/evidence/`.
- **Markdown**: relative links only (no machine-local paths); quote Mermaid labels that contain parentheses or symbols (`id["Label (Detail)"]`).
