---
name: product-analyst
description: Analyzes ambiguous feature requests, clarifies business rules, and authors ultra-concise Product Requirements Documents (docs/<feature-name>/prd.md <= 70 lines) with standard User Stories (US-XX) and testable Acceptance Criteria (AC-XX).
---

# Product Analyst Skill

## Overview
This skill converts underspecified feature requests into crisp, directly testable product specifications stored in **`docs/<feature-name>/prd.md`** (strictly capped at **`<= 70 lines`**, zero filler prose). Every PRD follows a fixed 4-section standard (`Objective`, `Scope`, `User Stories`, `Acceptance Criteria & Edge Cases`) so engineering and QA have exact `US-XX` -> `AC-XX` traceability.

## When to Use
### Capability-Gated Trigger Rules
- **INVOKE ONLY IF** business scope, user stories, or acceptance criteria are ambiguous or missing.
- **SKIP** when the user prompt already defines clear scope/stories, or for bugfixes, refactors, chores, documentation updates, and purely technical CLIs.
- **Delegate Elsewhere**: System schemas & ADRs -> `senior-architect-engineering`; UI tokens & screens -> `ui-ux-designer`; TDD coding -> `code-implementer`.

## Process
### Phase 1: Context Check & Targeted Clarification
1. Inspect existing routes, models, and `docs/` (`docs/specifications/` if present) to avoid asking questions already answered by the codebase.
2. If business rules or boundaries remain genuinely ambiguous, ask concise option-based questions with clear trade-offs (never vague open-ended prompts).

### Phase 2: Author Concise Standard PRD (`docs/<feature-name>/prd.md`, `<= 70 lines`)
Create `docs/<feature-name>/` and write `docs/<feature-name>/prd.md` (`<= 70 lines` hard cap) using the exact 4-section template in [references/prd-template.md](references/prd-template.md):
1. **`## 1. Objective`**: 2–4 lines stating the concrete problem and measurable business outcome.
2. **`## 2. Scope`**: Crisp `In-Scope` and `Out-of-Scope` bullets preventing scope creep.
3. **`## 3. User Stories`**: Numbered `US-01`, `US-02` in strict standard format:
   - **As a** `<role>`, **I want** `<action>`, **so that** `<outcome>` *(or *Como `<rol>`, quiero `<acción>`, para `<beneficio>`*)*.
4. **`## 4. Acceptance Criteria & Edge Cases`**: Numbered `AC-01`, `AC-02` explicitly mapped to `US-XX` (`AC-01 (US-01)`), written as directly testable Given/When/Then or crisp bullets covering validation, permissions, and boundary/failure cases.

*Global Sync*: If the workspace maintains `docs/specifications/` or a global requirements index, update its links to keep documentation synchronized.

## Usage
### Example Prompts
- *"Clarify scope boundaries for workspace invitations and write a concise `docs/workspace-invites/prd.md` (`<= 70 lines`)."*
- *"Extract `US-XX` user stories and testable `AC-XX` acceptance criteria for CSV report exports."*

### Host Execution
- **Claude Code**: Inspect context via `Read`/`Grep`, clarify genuine gaps, and write `docs/<feature-name>/prd.md`.
- **Antigravity**: Use `Read`/`Grep`, align via `ask_question` when needed, and write `docs/<feature-name>/prd.md`.

## Red Flags
- ❌ Writing bloated PRDs (`> 70 lines`), executive-summary fluff, or multi-page tables for straightforward features.
- ❌ Invoking PRD authoring on bugfixes, refactors, chores, or prompts that already specify clear acceptance criteria.
- ❌ Writing untestable criteria (*"must be fast and intuitive"*) or omitting `US-XX` / `AC-XX` identifiers and `Out-of-Scope` bullets.
- ❌ Asking obvious questions answerable from repository code, or writing production source code directly.

## Verification
- [ ] `docs/<feature-name>/prd.md` exists, is strictly `<= 70 lines`, and contains zero filler prose.
- [ ] Uses the exact 4 sections from [references/prd-template.md](references/prd-template.md): `1. Objective`, `2. Scope`, `3. User Stories`, `4. Acceptance Criteria & Edge Cases`.
- [ ] Every story (`US-XX`) uses **As a / I want / so that** (*Como / quiero / para*) format, and every `AC-XX` maps to a `US-XX` with testable validation/permission/edge rules.
- [ ] Existing `docs/specifications/` indexes synchronized if present.

## References
- Concise Standard PRD Template (`<= 45 lines`): [references/prd-template.md](references/prd-template.md)
