---
name: repo-research
description: Analyze a repository's structure, technologies, and patterns to create or update a project context document. Use when asked to research, analyze, or understand a codebase.
---

# Repository Research Skill

## Overview
This skill analyzes repository structures, technologies, architectures, and runtime dependencies to produce or update a centralized project context document at `.agents/rules/project-context.md`. It acts as a Repository Intelligence Specialist and Systems Cartographer, minimizing LLM token consumption by prioritizing automated AST and configuration extraction over speculative file reading.

## When to Use
### Trigger Scenarios
- Initial onboarding or orientation when starting work on a new repository.
- Generating or updating `.agents/rules/project-context.md` with current codebase facts.
- Mapping entry points, route handlers, data models, and local development runbooks.
- Resolving inconsistencies between legacy documentation and actual source code.

### When NOT to Use
- **Speculative bulk reading of entire codebases**: Run Phase 1 automated extraction first.
- **Deep code smell diagnosis**: Route to `code-smells-expert`.
- **Software design specification for new features**: Route to `design-spec-expert`.
- **Automated test suite execution**: Route to `test-driven-development`.

## Process
### Phase 1: Automated Repository Analysis
Execute the repository analyzer to map directory trees, detect language frameworks, package configurations, and bootstrap the context document:
```bash
python3 ./skills/repo-research/scripts/repo_analyzer.py
```
Verify that `.agents/rules/project-context.md` was generated or refreshed.

### Phase 2: Targeted Manual Refinement
Using the generated project structure and config summary in `project-context.md`, read **only** the necessary files to fill in placeholders `[...]` or resolve unknown details:
1. **Identify Entry Points**: Read top-level imports in entry files (e.g. `main.py`, `index.ts`, `app.dart`) to resolve *Architectural Patterns* and *Runtime Dependency Graph*.
2. **Scan Route Definitions**: Read routing files (e.g. `routes.py`, `app.js`, controller directories) to map the *API Surface / Route Map*.
3. **Analyze Database / Models**: Read schema files or `models/` directories to compile the *Data Model Overview*.
4. **Compile Runbook**: Confirm actual local run commands in configs (`package.json`, `Makefile`, `pubspec.yaml`) to populate the *Local Dev Runbook*.
5. **Resolve Glossary**: Add definitions for domain-specific terminology encountered during review.

### Phase 3: Inconsistency Resolution & Reporting
If source code contradicts existing documentation:
- Report the contradiction clearly:
  - **Documented**: What the legacy docs state.
  - **Actual**: What the source code actually implements.
  - **Recommendation**: How to reconcile the difference.

## Usage
### Commands & Automation Scripts
```bash
# Analyze workspace and scaffold/update project-context.md
python3 ./skills/repo-research/scripts/repo_analyzer.py
```

### Example Prompts
- *"Analyze this repository and generate an up-to-date project context document in .agents/rules/."*
- *"Map the API route surface and database models for this service."*
- *"Identify what frameworks, build tools, and entry points are used across this codebase."*

### Host Execution Instructions
- **Claude Code**: Run `repo_analyzer.py` via bash, then selectively view only the high-value entry files.
- **Antigravity**: Execute `repo_analyzer.py` as an orientation step before initiating feature development.

## Red Flags
- Bulk-reading dozens of source files speculatively without using automated tooling (wasting context tokens).
- Silently overwriting manually curated project context without merging additions.
- Leaving unverified `[...]` placeholders in `project-context.md`.
- Failing to verify commands listed in the Local Dev Runbook.

## Verification
- [ ] Automated analyzer executed and generated valid output:
  ```bash
  python3 ./skills/repo-research/scripts/repo_analyzer.py
  ```
- [ ] `.agents/rules/project-context.md` exists and contains verified technology stack and entry points.
- [ ] No speculative full-repository file dumps performed.
- [ ] Inconsistencies between documentation and code highlighted and resolved.

## References
For the standardized project context schema and layout:
- [Project Context Template](references/project-context-template.md)


