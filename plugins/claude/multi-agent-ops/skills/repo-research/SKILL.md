---
name: repo-research
description: Analyze a repository's structure, stack, commands, and invariants to create a high-signal Codebase Map (.agents/rules/project-context.md <= 80 lines) and bootstrap/sync root AGENTS.md and context/memory/MEMORY.md.
---

# Repository Research Skill

## Overview
This skill maps a repository's stack, directory boundaries, executable commands, and architectural invariants into a concise, high-signal **Codebase Map** at `.agents/rules/project-context.md` (`<= 80 lines`), while bootstrapping or synchronizing target-project root `AGENTS.md` (`<= 90 lines`) and `context/memory/MEMORY.md` (`<= 80-100 lines`). It prioritizes deterministic script extraction over speculative file reading to conserve tokens.

## When to Use
### Trigger Scenarios
- Onboarding onto an unfamiliar repository or refreshing `.agents/rules/project-context.md`.
- Bootstrapping or syncing a target repository's root `AGENTS.md` and `context/memory/MEMORY.md`.
- Verifying build, lint, and test commands alongside entry points and layer invariants.
- Reconciling contradictions between stale documentation and actual source code.

### When NOT to Use
- **Bulk-reading entire source trees without running `repo_analyzer.py` first**.
- **Deep code smell or SOLID auditing**: Route to `code-smells-expert` or `code-critic`.
- **Feature-level PRD, UI design, or MADR authoring**: Route to discovery skills (`docs/<feature-name>/`).

## Process
### Phase 1: Automated Repository Extraction
Run the analyzer script to extract directory layout, languages, package managers, config files, and entry points into `.agents/rules/project-context.md`:
```bash
python3 ./skills/repo-research/scripts/repo_analyzer.py
```

### Phase 2: High-Signal Codebase Map Refinement (`<= 80 lines`)
Inspect **only** high-signal config and entry files (`pyproject.toml`, `package.json`, `Makefile`, `pubspec.yaml`, main entry points) to replace `[...]` placeholders across the 4 core sections — keeping `.agents/rules/project-context.md` strictly `<= 80 lines`:
1. **Stack & Entry Points**: Verified runtime versions, frameworks, data stores, and entry modules.
2. **Directory & Layer Map**: Concise tree plus domain, interface/UI, and test directory ownership.
3. **Run, Build & Test Commands**: Exact, verified install, dev, lint/typecheck, scoped test, and full test commands.
4. **Key Architectural & Env Invariants**: Layer boundaries, required env vars (names only, zero secrets), and runtime constraints.

### Phase 3: Target `AGENTS.md` & `context/memory/MEMORY.md` Bootstrap/Sync
When researching a target repository:
1. **Bootstrap/Sync Root `AGENTS.md` (`<= 90 lines`)**: If missing or stale, create/update root `AGENTS.md` with verified build/lint/test commands, core coding conventions, and explicit links to root `DESIGN.md` (if UI exists) and `context/memory/MEMORY.md`.
2. **Bootstrap/Sync `context/memory/MEMORY.md` (`<= 80-100 lines`)**: Ensure cross-AI handoff state, active branch, and links to `architecture.md` and `conventions.md` are initialized or synchronized without duplicating full codebase trees.
3. **Surface Contradictions**: Report any mismatch as **Documented** vs. **Actual** vs. **Action Taken**.

## Usage
### Commands & Automation Scripts
```bash
# Generate or refresh .agents/rules/project-context.md from workspace configs
python3 ./skills/repo-research/scripts/repo_analyzer.py
```

### Host Execution Instructions
- **Claude Code**: Run `repo_analyzer.py` via Bash, selectively read entry/config files, then refine `project-context.md` (`<= 80 lines`) and sync root `AGENTS.md` + `context/memory/MEMORY.md`.
- **Antigravity**: Execute `repo_analyzer.py` via `Bash` during State 0 orientation, then finalize the Codebase Map and root governance links.

## Red Flags
- Producing bloated 10-section codebase dumps (`> 80 lines`) or speculative prose.
- Reading dozens of source files before running `repo_analyzer.py`.
- Leaving unresolved `[...]` placeholders or unverified run/test commands.
- Failing to bootstrap or synchronize root `AGENTS.md` (`<= 90 lines`) and `context/memory/MEMORY.md` in target projects.

## Verification
- [ ] Analyzer executed cleanly:
  ```bash
  python3 ./skills/repo-research/scripts/repo_analyzer.py
  ```
- [ ] `.agents/rules/project-context.md` is `<= 80 lines` with all 4 sections populated and zero `[...]` placeholders.
- [ ] Target-project root `AGENTS.md` (`<= 90 lines`) and `context/memory/MEMORY.md` (`<= 80-100 lines`) are present and synchronized.
- [ ] All build, lint, and test commands match actual project manifests.

## References
- [Project Context Template](references/project-context-template.md)
