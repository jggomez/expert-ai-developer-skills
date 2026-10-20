# Python Backend Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](https://github.com/jggomez/expert-ai-developer-skills)
[![Plugin](https://img.shields.io/badge/Plugin-python--backend-green?style=flat-square)](.)

The `python-backend` plugin is a unified customization package designed to automate quality gates, enforce branch safety constraints (Gitflow), validate test execution, and link external GCP and Firebase resources through the Model Context Protocol (MCP).

This plugin supports **both Antigravity CLI and Claude Code**, each verified against its own official schema (not assumed): `hooks.json` carries a `"hooks"` key for Claude Code and a separate named group for Antigravity in the same file — each host reads only the key it understands. `.mcp.json` (Claude Code) and `mcp_config.json` (Antigravity) ship side by side since the filenames don't collide. The hook scripts detect the host at runtime (via `CLAUDE_PLUGIN_ROOT`) and emit the correct decision format for each — Claude Code's `hookSpecificOutput.permissionDecision`, or Antigravity's top-level `decision` field.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog, kept self-contained so the plugin folder can be distributed on its own. After editing any bundled skill under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy — don't hand-edit both. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/python-backend/
├── README.md             # This usage and configuration manual
├── plugin.json           # Required marker containing metadata (Antigravity reads this at plugin root)
├── .claude-plugin/
│   └── plugin.json       # Same metadata — Claude Code requires the manifest here, not at plugin root
├── .mcp.json             # MCP definitions for Claude Code (GCP, Firebase)
├── mcp_config.json       # Same MCP definitions, Antigravity's format (serverUrl-based entries not needed here — both are stdio)
├── hooks.json            # Lifecycle hook registrations for both hosts, in one file
├── hooks/                # Node.js hook event handlers (host-aware)
│   ├── python-backend-activate.js  # Runs on SessionStart (Claude Code only — Antigravity has no SessionStart event; its rules/ dir auto-loads instead)
│   ├── pre-tool-gate.js            # Runs on PreToolUse; enforces Plan-First, gitflow & cloud deployment guardrails
│   └── stop-gate.js                # Runs on Stop; quality gate checking test suite
├── agents/
│   └── python-backend-orchestrator.md # Senior Python Backend Orchestrator (6-State DAG, Parallel Slices)
├── rules/                # Central system guidelines
│   ├── python-backend-rules.md     # 6-State DAG, API/Migration Triage Gate, Parallel Slices & context/memory/
│   └── git-hooks.md                # Blueprints for pre-commit & commit-msg hooks
└── skills/               # Bundled developer skills loaded globally (14 modules)
    ├── python-expert/
    ├── test-driven-development/
    ├── pull-request-expert/
    ├── code-smells-expert/
    ├── refactoring-code-expert/
    ├── security-audit/
    ├── performance-scalability/
    ├── database-migration-expert/
    ├── senior-architect-engineering/
    ├── design-spec-expert/
    ├── build-and-ci-gates/
    ├── context-capture/
    ├── context-restore/
    └── loop-engineering/
```

---

## 2. 6-State DAG, Triage Gate & Parallel Vertical Slices

1. **`State 0` — Silent LLM Wiki Restore & API/Migration Triage Gate**: Silently reads `context/memory/MEMORY.md` (`~500 tokens`) and authors `PLAN.md` with an `## API & Database Migration Triage Gate` table evaluating when `database-migration-expert`, `senior-architect-engineering`, and `design-spec-expert` must be applied upfront.
2. **Parallel Backend Vertical Slices**: Dispatches independent FastAPI/Django vertical slices in parallel under **Mode A (`Disjoint Files`)** across non-overlapping routers, services, repositories, and unit tests, or **Mode B (`Git Worktree` isolation)** when parallel tracks generate Alembic/Django migrations or edit shared `main.py`/settings.
3. **`State 5` — Token-Conserving LLM Wiki Update**: Updates `context/memory/` (`MEMORY.md`, `architecture.md` for API/schema contracts, `conventions.md`, and `log/YYYY-MM-DD.md`) only upon milestone completion or explicit user handoff.

---

## 3. Integrated Configuration Assets

### 3.1 Model Context Protocol (`.mcp.json` / `mcp_config.json`)
Registers secure, lazy-loaded cloud management tools — for both Claude Code (`.mcp.json`) and Antigravity (`mcp_config.json`):
- **`cloudrun`**: Enables listing services, fetching service details, viewing deployment logs, and running deployments.
- **`firebase-mcp-server`**: Enables Cloud Firestore collection lookups, document mutations, and real-time database queries.

### 3.2 Lifecycle Hook Mappings (`hooks.json`)
One file, two hosts — Claude Code reads the top-level `"hooks"` key, Antigravity reads the separate `"python-backend-safety-gates"` named group (its own schema: `enabled` + event arrays):
- **`SessionStart`** (Claude Code only — this event doesn't exist in Antigravity): runs `python-backend-activate.js` to load rules and check cloud credentials. On Antigravity, `rules/python-backend-rules.md` auto-loads via the plugin's `rules/` directory instead.
- **`PreToolUse`**: runs `pre-tool-gate.js` before executing file modifications, command line tools, or MCP tools.
- **`Stop`**: runs `stop-gate.js` before finishing a request to verify the test suite state.

---

## 4. Operations & Safety Gates Detail

### 4.1 Plan-First & Gitflow Branch Block (Intercepts edits & commits/pushes)
- **Goal**: Require `PLAN.md` before modifying `.py` files (while permitting `context/memory/` and `.agents/` updates) and protect staging (`develop`) and production (`main`) branches.
- **Mechanism**: The `PreToolUse` hook verifies `PLAN.md` exists before Python edits and checks the active git branch before `git add/commit/push/merge`, returning `deny` on `main` or `develop`.

### 4.2 Deployment Lock (Ask)
- **Goal**: Avoid accidental modifications or deployments to cloud targets.
- **Mechanism**: If a command contains deployment keywords (`deploy`, `kubectl apply`) or calls GCP/Firebase MCP modification APIs, the `PreToolUse` hook returns an `ask` permission decision.

### 4.3 Test Verification Gate (Request finalization blocker)
- **Goal**: Ensure 0 regressions are delivered.
- **Mechanism**: When the agent attempts to stop or complete a task, the `Stop` hook runs the project's test suite via `python3 ./skills/test-driven-development/scripts/verify_tests.py`. If tests fail, it halts termination, outputs the traceback, and forces the developer/agent loop to continue until resolved.

---

## 5. Bundled Skills (14 Packaged Modules)

On loading the plugin, the following 14 skills are automatically loaded into the agent's context:

1. **`python-expert`**: AST analysis and memory optimization check.
2. **`test-driven-development`**: AAA execution patterns.
3. **`pull-request-expert`**: Size checks and Conventional Commit logs.
4. **`code-smells-expert`**: Code complexity diagnostics.
5. **`refactoring-code-expert`**: Safe extraction methods.
6. **`security-audit`**: OWASP Top 10 scanner.
7. **`performance-scalability`**: CPU/Memory execution profiler.
8. **`database-migration-expert`**: Alembic schema migrations.
9. **`senior-architect-engineering`**: ADR templates.
10. **`design-spec-expert`**: SDD schemas.
11. **`build-and-ci-gates`**: Pre-commit quality hook gates.
12. **`context-capture`**: Updates the Cross-AI LLM Wiki (`context/memory/MEMORY.md`, `architecture.md`, `conventions.md`, `log/YYYY-MM-DD.md`) at `State 5` or explicit handoff.
13. **`context-restore`**: Progressive disclosure reader (`context/memory/MEMORY.md` at `State 0`, drilling down on demand).
14. **`loop-engineering`**: Bounded 3-strike fix loops for automated test and static-analysis verification.

---

## 6. Example Prompts

The Gitflow/deployment/test-verification gates apply automatically once the plugin is installed — no prompt needed. The skills below activate when you ask for what they cover:

- "Review this Python module for PEP 8 compliance and `__slots__` memory optimization." (`python-expert`)
- "Add a new field to the API and write it test-first, Red-Green-Refactor." (`test-driven-development`)
- "Prepare this branch for a pull request and check it against the 200-line size guideline." (`pull-request-expert`)
- "Scan this service for God classes and high-complexity methods." (`code-smells-expert`)
- "Extract the validation logic from this function without changing its behavior." (`refactoring-code-expert`)
- "Run a security audit on this codebase for hardcoded secrets and OWASP Top 10 issues." (`security-audit`)
- "Profile this endpoint for N+1 queries and memory usage." (`performance-scalability`)
- "Write a zero-downtime Alembic migration that adds a NOT NULL column." (`database-migration-expert`)
- "Draft an ADR for choosing between REST and gRPC for this internal service." (`senior-architect-engineering`)
- "Scaffold a Software Design Document for the new billing service." (`design-spec-expert`)
- "Set up a pre-commit hook that runs lint, tests, and the secret scanner." (`build-and-ci-gates`)

---

## 7. Installation

**Antigravity CLI** — global only, via the CLI (don't hand-copy into `~/.gemini/...`):
```bash
agy plugin install ./plugins/python-backend
```

**Claude Code** — global:
```bash
cp -r ./plugins/python-backend ~/.claude/plugins/python-backend
```
**Claude Code** — project-scoped, no install/copy:
```bash
claude --plugin-dir ./plugins/python-backend
```

Try triggering a gate directly to see it in action: "Commit and push directly to main" (the Gitflow hook should deny it) or "Deploy this service to Cloud Run" (the deployment hook should ask for explicit approval first).
