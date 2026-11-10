---
name: product-analyst
description: Analyzes ambiguous feature requests, clarifies business rules, and authors the ultra-concise `## Product` section of the single discovery file docs/<feature-name>/spec.md (<= 50 lines) with standard User Stories (US-XX) and testable Acceptance Criteria (AC-XX).
---

# Product Analyst Skill

## Overview
This skill converts underspecified feature requests into crisp, directly testable product specifications stored in the **`## Product`** section of the single discovery file **`docs/<feature-name>/spec.md`** (section strictly capped at **`<= 50 lines`**, zero filler prose). The section follows a fixed 4-part standard (`Objective`, `Scope`, `User Stories`, `Acceptance Criteria & Edge Cases`) so engineering and QA have exact `US-XX` -> `AC-XX` traceability.

## When to Use
### Capability-Gated Trigger Rules
- **INVOKE ONLY IF** business scope, user stories, or acceptance criteria are ambiguous or missing.
- **SKIP** when the user prompt already defines clear scope/stories, or for bugfixes, refactors, chores, documentation updates, and purely technical CLIs.
- **Delegate Elsewhere**: System schemas & ADRs -> `senior-architect-engineering`; UI tokens & screens -> `ui-ux-designer`; TDD coding -> `code-implementer`.

## Process
### Phase 1: Context Check & Targeted Clarification
1. Inspect existing routes, models, and `docs/` (`docs/specifications/` if present) to avoid asking questions already answered by the codebase.
2. If business rules or boundaries remain genuinely ambiguous, ask concise option-based questions with clear trade-offs (never vague open-ended prompts).

### Phase 2: Author the `## Product` Section (`docs/<feature-name>/spec.md`, `<= 50 lines`)
If `docs/<feature-name>/spec.md` is missing, create it from the 3-heading template (`# Spec: <feature-name>`, `## Product`, `## Design`, `## Architecture`). Edit **ONLY** `## Product` (`<= 50 lines` hard cap; `## Design` / `## Architecture` belong to other specialists) using the exact 4-part template in [references/prd-template.md](references/prd-template.md):
1. **`### Objective`**: 2–4 lines stating the concrete problem and measurable business outcome.
2. **`### Scope`**: Crisp `In-Scope` and `Out-of-Scope` bullets preventing scope creep. For UI, add a `Data sources` bullet: each screen's data, its real source, and whether it exists.
3. **`### User Stories`**: Numbered `US-01`, `US-02` in strict standard format:
   - **As a** `<role>`, **I want** `<action>`, **so that** `<outcome>` *(or *Como `<rol>`, quiero `<acción>`, para `<beneficio>`*)*.
4. **`### Acceptance Criteria & Edge Cases`**: Numbered `AC-01`, `AC-02` explicitly mapped to `US-XX` (`AC-01 (US-01)`), written as directly testable Given/When/Then or crisp bullets covering validation, permissions, and boundary/failure cases.

*Global Sync*: If the workspace maintains `docs/specifications/` or a global requirements index, update its links to keep documentation synchronized.

- **Change delta (later requests)**: when `## Product` already exists, read it and add only the new `US`/`AC` for this change, tagged `C-NN`; never rewrite earlier stories. Stay within the line cap by tightening older text, not by dropping it.

## Usage
### Example Prompts
- *"Clarify scope boundaries for workspace invitations and write the `## Product` section of `docs/workspace-invites/spec.md` (`<= 50 lines`)."*
- *"Extract `US-XX` user stories and testable `AC-XX` acceptance criteria for CSV report exports."*

### Host Execution
- **Claude Code**: Inspect context via `Read`/`Grep`, clarify genuine gaps, and edit `## Product` in `docs/<feature-name>/spec.md`.
- **Antigravity**: Use `Read`/`Grep`, align via `AskUserQuestion` when needed, and edit `## Product` in `docs/<feature-name>/spec.md`.
- **Return Contract**: Final message `<= 15 lines` (status, files changed, test command + exit code or `n/a`, next step); no long narratives.

## Red Flags
- ❌ Writing a separate `prd.md`, editing `## Design` / `## Architecture`, or a bloated `## Product` section (`> 50 lines`), executive-summary fluff, or multi-page tables for straightforward features.
- ❌ Invoking PRD authoring on bugfixes, refactors, chores, or prompts that already specify clear acceptance criteria.
- ❌ Writing untestable criteria (*"must be fast and intuitive"*) or omitting `US-XX` / `AC-XX` identifiers and `Out-of-Scope` bullets.
- ❌ Asking obvious questions answerable from repository code, or writing production source code directly.

## Verification
- [ ] `## Product` in `docs/<feature-name>/spec.md` exists, is strictly `<= 50 lines`, and contains zero filler prose; other sections untouched.
- [ ] Uses the exact 4 parts from [references/prd-template.md](references/prd-template.md): `Objective`, `Scope`, `User Stories`, `Acceptance Criteria & Edge Cases`.
- [ ] Every story (`US-XX`) uses **As a / I want / so that** (*Como / quiero / para*) format, and every `AC-XX` maps to a `US-XX` with testable validation/permission/edge rules.
- [ ] Existing `docs/specifications/` indexes synchronized if present.

## References
- Concise `## Product` Section Template (`<= 45 lines`): [references/prd-template.md](references/prd-template.md)
