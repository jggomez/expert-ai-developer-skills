---
name: documentation-expert
description: Author and validate Zero-Fluff technical documentation, root AGENTS.md, Google DESIGN.md alignment, Diátaxis guides, and Mermaid diagrams with strict conciseness caps and relative link verification.
---

# Documentation Expert Skill

## Overview
This skill guides the authoring, structuring, and automated validation of Zero-Fluff technical documentation, root `AGENTS.md` guides, official Google `DESIGN.md` references, and Mermaid.js architectural diagrams. Applying the Diátaxis framework (Tutorials, How-To Guides, Reference, Explanation), it enforces strict line budgets, portable relative links, and zero-boilerplate clarity.

## When to Use
### Trigger Scenarios
- Authoring or auditing READMEs, runbooks, API references, and root `AGENTS.md` (`<= 90 lines`).
- Ensuring documentation aligns with official Google 2-layer `DESIGN.md` (`<= 110 lines`) and `docs/<feature-name>/` line caps.
- Modeling architectures, sequence flows, or schemas with syntax-safe Mermaid.js diagrams.
- Validating markdown heading hierarchy, relative links, and path portability.

### When NOT to Use
- **Authoring MADR architectural decisions (`adr-NNN-*.md`)**: Route to `senior-architect-engineering`.
- **Authoring UI token systems (`DESIGN.md`)**: Route to `ui-ux-designer`.
- **Automated codebase cartography (`project-context.md`)**: Route to `repo-research`.

## Process
### Phase 1: Diátaxis Pillar & Zero-Fluff Budget Alignment
1. Select one Diátaxis mode per section — never mix tutorials, how-to steps, reference tables, and explanations together.
2. Enforce strict **Zero-Fluff** conciseness caps across project and feature artifacts:
   - Root `AGENTS.md <= 90 lines` (verified build/lint/test commands, conventions, links to `DESIGN.md` & `context/memory/MEMORY.md`).
   - Root Google `DESIGN.md <= 110 lines` (YAML tokens + 8 sections) and feature delta `docs/<feature-name>/design.md <= 35 lines`.
   - Feature specs in `docs/<feature-name>/`: `prd.md <= 70 lines`, `adr-NNN-*.md <= 55 lines`, `architecture.md <= 70 lines`, `test-matrix.md <= 80 lines`, verification reports `<= 50 lines`.

### Phase 2: Syntax-Safe Mermaid.js Diagramming
Use concise Mermaid blocks (`flowchart TD`, `flowchart LR`, `sequenceDiagram`, `stateDiagram-v2`, `erDiagram`) instead of prose walls. Always quote labels containing spaces, slashes, brackets, or parentheses (e.g., `api["Auth API (v2)"]`).

### Phase 3: Link Portability & Automated Validation
Use portable repository-relative links (never machine-local paths) and run the validator script:
```bash
python3 ./skills/documentation-expert/scripts/validate_docs.py
```

## Usage
### Commands & Automation Scripts
```bash
# Audit markdown heading hierarchy, relative links, and local path leaks
python3 ./skills/documentation-expert/scripts/validate_docs.py
```

### Host Execution Instructions
- **Claude Code**: Run `validate_docs.py` via Bash after authoring or editing markdown docs.
- **Antigravity**: Verify Mermaid quoting, line caps, and relative links via `validate_docs.py`.

## Red Flags
- Bloated prose walls exceeding artifact line budgets (`AGENTS.md > 90`, `DESIGN.md > 110`, reports `> 50` lines).
- Blending How-To recipes with deep theoretical Explanations in the same section.
- Leaking local machine paths or leaving broken relative `.md` links.
- Unquoted parentheses or brackets in Mermaid node labels causing render failures.

## Verification
- [ ] Document matches its target Diátaxis pillar and stays within its Zero-Fluff line cap.
- [ ] Root `AGENTS.md` and `DESIGN.md` cross-links resolve cleanly when present.
- [ ] Validator script exits with code `0`:
  ```bash
  python3 ./skills/documentation-expert/scripts/validate_docs.py
  ```
- [ ] Zero broken relative links, skipped heading levels, or local path leaks.

## References
- [Diátaxis Documentation Framework Reference](references/diataxis-framework.md)
- [Mermaid.js Graphic Reference Guide](references/mermaid-guide.md)
