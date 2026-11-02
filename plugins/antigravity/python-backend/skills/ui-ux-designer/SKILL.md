---
name: ui-ux-designer
description: Expert UI/UX designer and design systems architect. Establishes official Google 2-layer DESIGN.md contracts (YAML tokens + 8 concise sections), optional feature UI deltas (docs/<feature-name>/design.md), accessibility (WCAG AA), and responsive component states for web and mobile apps.
---

# UI/UX Designer & Design Systems Skill

## Overview
This skill governs UI/UX design systems using the **official Google Labs / Google Stitch `DESIGN.md` (`google-labs-code/design.md`) 2-layer specification**. It maintains a single concise project-wide root **`DESIGN.md`** (`<= 110 lines`) alongside ultra-compact feature UI deltas (**`docs/<feature-name>/design.md`**, `<= 35 lines`) so visual tokens, WCAG 2.1 AA accessibility, and component states remain deterministic without 200-line per-feature boilerplate.

## When to Use
### Capability-Gated Trigger Rules
- **INVOKE ONLY IF** UI screens/components are created or modified **AND** root `DESIGN.md` is missing or new visual tokens, layouts, or screen states are introduced.
- **SKIP** for backend/APIs, data pipelines, CLIs, SQL, refactors, or minor UI tweaks already covered by root `DESIGN.md`.
- **Delegate Elsewhere**: Backend/API contracts -> `senior-architect-engineering`; production widget/CSS code -> `code-implementer` or `flutter-implementer`; automated UI/E2E runs -> `qa-tester`.

## Process: The Standard `design.md` Lifecycle
1. **Inspect Root `DESIGN.md` (`<= 110 lines`)**:
   - Check if root `DESIGN.md` (or legacy `design.md` / `docs/design/`) exists.
   - **If missing**: Author root `DESIGN.md` (`<= 110 lines`) from [references/design-md-template.md](references/design-md-template.md) following the **Google 2-layer spec**:
     * **Layer 1 (Machine-Readable YAML Frontmatter)**: `name`, `version`, `colors` (`primary`, `surface`, `text`, `error`, etc.), `typography` (`font_sans`, `font_mono`, `scale`), `rounded`, `spacing`, and `components` using `{colors.primary}` token references.
     * **Layer 2 (8 Concise Sections)**: `## Overview`, `## Colors`, `## Typography`, `## Layout`, `## Elevation & Depth`, `## Shapes`, `## Components`, `## Do's and Don'ts`.
   - **If present**: Reuse existing tokens; append new global tokens/components in-place only when genuinely needed.
2. **Author Optional Feature UI Delta (`docs/<feature-name>/design.md`, `<= 35 lines`)**:
   - Create `docs/<feature-name>/design.md` **ONLY** when the feature introduces net-new screen layouts, user flows, or interactive states.
   - Reference root `DESIGN.md` tokens (`{colors.primary}`, `{spacing.md}`) directly—never duplicate full color/typography tables per feature.

## Multi-Platform Guidelines
- **Web (Fluid & Accessible)**: Use CSS Grid/Flexbox and `rem` units across Mobile (`<640px`), Tablet (`768–1023px`), and Desktop (`>=1024px`) with zero horizontal scroll, `:focus-visible` `2px` offset rings, and reserved async media boxes (zero CLS).
- **Mobile (Flutter, iOS, Android)**: Enforce `>= 44x44pt` (iOS) / `48x48dp` (Android) touch targets, Safe Area insets, thumb-zone primary actions, and Material 3 / Cupertino adaptive conventions.
- **States**: Specify `default`, `hover`, `focus-visible`, `active`, `disabled`, `loading`, `empty`, and `error` for every interactive control.

## Usage & Tooling Integration
- **Linting (`@google/design.md`)**: Validate root `DESIGN.md` syntax and token references when Node/npx is available:
  ```bash
  npx @google/design.md lint DESIGN.md
  ```
- **Google Stitch MCP**: Root `DESIGN.md` serves directly as the payload for `upload_design_md` and `create_design_system_from_design_md`.
- **Companion Skills**: Consult `ui-ux-pro-max` for domain palettes/font pairings and `web-design-guidelines` for ergonomic/a11y audits.

## Hand-off Protocol
- **Inputs**: Concise PRD (`docs/<feature-name>/prd.md`) or user prompt + existing root `DESIGN.md`.
- **Outputs**: Root `DESIGN.md` (`<= 110 lines`, Google 2-layer spec) and, only when feature-specific screen states/layouts exist, a `<= 35 lines` delta in `docs/<feature-name>/design.md`.
- **Downstream**: `architect-engineer` (component/state boundaries) and `code-implementer` / `flutter-implementer` (token-accurate UI code).

## Anti-Patterns & Red Flags
- ❌ Repeating 200-line color/typography catalogs inside every `docs/<feature-name>/design.md` instead of referencing root `DESIGN.md`.
- ❌ Hardcoding raw hex codes or magic pixel spacing instead of `{colors.*}` and `{spacing.*}` tokens.
- ❌ Failing WCAG 2.1 AA contrast (`< 4.5:1`), removing `:focus-visible` rings, or omitting `loading`/`empty`/`error` states.
- ❌ Writing production application code (belongs strictly to `code-implementer` / `flutter-implementer`).

## Verification & Quality Gates
- [ ] Root `DESIGN.md` (`<= 110 lines`) conforms to [references/design-md-template.md](references/design-md-template.md) (YAML token frontmatter + 8 standard sections) and is compatible with `npx @google/design.md lint DESIGN.md`.
- [ ] Feature delta `docs/<feature-name>/design.md` (when needed) is `<= 35 lines` and references root `DESIGN.md` tokens without duplication.
- [ ] WCAG 2.1 AA contrast (`>= 4.5:1`), touch targets (`>= 44x44pt` / `48x48dp`), responsive breakpoints, and all interactive states verified.
