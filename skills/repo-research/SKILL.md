---
name: repo-research
description: Analyze a repository's structure, technologies, and patterns to create or update a project context document. Use when asked to research, analyze, or understand a codebase.
---

# Repository Research Skill

## Task
Analyze the repository and create or update the project context at `.agents/rules/project-context.md`.

## Execution Workflow
To minimize token consumption and maximize efficiency, follow this automated and incremental research workflow:

### Phase 1: Automated Initial Analysis
1. Run the repository analyzer script:
   ```bash
   python3 ./skills/repo-research/scripts/repo_analyzer.py
   ```
2. Verify that `.agents/rules/project-context.md` was generated or updated.

### Phase 2: Targeted Manual Refinement
Using the generated project structure and config summary in `project-context.md`, read **only** the necessary files to fill in placeholders `[...]` or resolve unknown details:
1. **Identify Entry Points**: Read top-level imports in entry files (e.g. `main.py`, `index.js`, etc.) to resolve *Architectural Patterns* and *Runtime Dependency Graph*.
2. **Scan Route Definitions**: Read routing files (e.g. `routes.py`, `app.js`, controller directories) to map the *API Surface / Route Map*.
3. **Analyze Database/Models**: Read files in directories like `models/` or schema files to compile the *Data Model Overview*.
4. **Compile Runbook**: Confirm actual local run commands in configs (`package.json`, `Makefile`, etc.) to fill in the *Local Dev Runbook*.
5. **Resolve Glossary**: Add definitions for project-specific terms encountered during your review.

## Guidelines & Rules
- **Incremental Reading Only**: Never bulk-read source code files speculatively. Always use findings from Phase 1 to choose Phase 2 targets.
- **Incremental Updates**: Update the "Last Updated" date and "Updated By" metadata fields. Do not silently overwrite manually added project details; append or merge additions.
- **Inconsistencies**: If code findings contradict existing documentation, report it to the user in this format:
  **Inconsistency in [Section Name]:**
  - Documented: [documented info]
  - Actual: [actual code state]
  - Suggestion: [reconciliation recommendation]
  Wait for confirmation, or add a markdown comment tag `<!-- REVIEW: [details] -->` if the session ends.

