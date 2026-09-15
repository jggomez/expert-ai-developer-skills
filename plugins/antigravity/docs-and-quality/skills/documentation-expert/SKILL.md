---
name: documentation-expert
description: Establishes guidelines, frameworks, and visual templates to create professional technical documentation, design records, and diagrams. Use this skill when asked to write user manuals, API docs, system overviews, or architectural diagrams.
---

# Documentation Expert Skill

## Overview
This skill guides the authoring, structuring, and validation of technical documentation and architectural diagrams. It acts as a Lead Technical Writer and Information Architect, applying the Diátaxis documentation framework (Tutorials, How-To Guides, Reference, Explanation) to match user intent, rendering visual diagrams with Mermaid.js, and strictly enforcing relative link integrity.

## When to Use
### Trigger Scenarios
- Writing, refactoring, or reviewing project READMEs, user manuals, and API references.
- Visualizing system architectures, sequence flows, or data models using Mermaid.js diagrams.
- Structuring technical docs to eliminate confusion between reference specifications and how-to guides.
- Auditing documentation for broken relative links, heading nesting violations, and absolute path leaks.

### When NOT to Use
- **Scaffolding Software Design Documents for unbuilt features**: Route to `design-spec-expert`.
- **Authoring Architectural Decision Records (ADRs)**: Route to `senior-architect-engineering`.
- **Extracting repo-wide codebase maps into project-context.md**: Route to `repo-research`.

## Process
### Phase 1: Diátaxis Pillar Alignment
Categorize the document into one of the four distinct Diátaxis modes based on reader intent:
1. **Tutorials (Learning-oriented)**: Hand-held, end-to-end beginner lessons with guaranteed successful outcomes.
2. **How-To Guides (Problem-oriented)**: Step-by-step recipes solving specific real-world tasks.
3. **Reference (Information-oriented)**: Accurate, dry, complete descriptions of classes, functions, flags, and APIs.
4. **Explanation (Understanding-oriented)**: High-level architectural discussions, historical context, and design rationales.
*Rule: Do NOT blend multiple pillars into a single document section.*

### Phase 2: Visual Diagramming via Mermaid.js
Insert Mermaid.js diagrams to visually illustrate complex interactions, data flows, or states:
- Use **flowcharts** for component layouts and pipelines.
- Use **sequence diagrams** for API exchanges and multi-agent loops.
- Use **ER diagrams** for data entity relationships.
*Always quote labels containing special characters to prevent rendering syntax errors.*

### Phase 3: Link Portability & Automated Verification
1. Enforce relative link paths (e.g., pointing to relative project files instead of hardcoded machine-specific absolute paths).
2. Execute the documentation validator script to check markdown layout nesting, link validity, and absolute path leaks:
   ```bash
   python3 ./skills/documentation-expert/scripts/validate_docs.py
   ```

## Usage
### Commands & Automation Scripts
```bash
# Validate markdown files, relative links, and heading hierarchies
python3 ./skills/documentation-expert/scripts/validate_docs.py
```

### Example Prompts
- *"Write a comprehensive README for our payments service following the Diátaxis framework, including an architecture diagram."*
- *"Create a Mermaid sequence diagram illustrating the OAuth2 authorization code flow with PKCE."*
- *"Audit the docs/ directory for broken relative links and heading hierarchy violations."*

### Host Execution Instructions
- **Claude Code**: Run `validate_docs.py` via bash to audit markdown files after authoring documentation.
- **Antigravity**: Ensure that diagrams use valid Mermaid blocks and verify links with `validate_docs.py`.

## Red Flags
- Mixing How-To steps with deep theoretical Explanations in the same section.
- Hardcoding user machine absolute paths (such as user home directories) in markdown links or code snippets.
- Creating broken relative markdown links pointing to non-existent files.
- Describing multi-component distributed architectures in walls of text without a diagram.

## Verification
- [ ] Document aligns cleanly to a Diátaxis pillar.
- [ ] Automated documentation validator script passes with zero errors:
  ```bash
  python3 ./skills/documentation-expert/scripts/validate_docs.py
  ```
- [ ] All relative file links point to existing files.
- [ ] Zero absolute user paths leaked.
- [ ] Mermaid diagrams render without syntax errors.

## References
- [Diátaxis Documentation Framework Reference](references/diataxis-framework.md)
- [Mermaid.js Graphic Reference Guide](references/mermaid-guide.md)

