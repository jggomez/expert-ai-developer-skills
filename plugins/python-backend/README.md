# Python Backend Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-python--backend-green?style=flat-square)](file:///./)

The `python-backend` plugin is a unified customization package designed to automate quality gates, enforce branch safety constraints (Gitflow), validate test execution, and link external GCP and Firebase resources through the Model Context Protocol (MCP).

Its `plugin.json`/`hooks.json`/`${CLAUDE_PLUGIN_ROOT}` layout follows the **Claude Code plugin format**, which is the platform it is verified against. The hook scripts also detect and emit the payload shape expected by Antigravity/Gemini, GitHub Copilot, and Codex hosts, so the same plugin folder can be dropped into those environments — but only the Claude Code path has been validated end-to-end.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog, kept self-contained so the plugin folder can be distributed on its own. After editing any bundled skill under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy — don't hand-edit both. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/python-backend/
├── README.md             # This usage and configuration manual
├── plugin.json           # Required marker containing metadata
├── .mcp.json             # MCP definitions (GCP, Firebase)
├── hooks.json            # Dynamic lifecycle hook registrations
├── hooks/                # Node.js hook event handlers
│   ├── python-backend-activate.js  # Runs on SessionStart; audits environment
│   ├── pre-tool-gate.js            # Runs on PreToolUse; intercepts git & cloud deployments
│   └── stop-gate.js                # Runs on Stop; quality gate checking test suite
├── rules/                # Central system guidelines
│   ├── python-backend-rules.md     # Quality checklists and coding patterns
│   └── git-hooks.md                # Blueprints for pre-commit & commit-msg hooks
└── skills/               # Bundled developer skills loaded globally
    ├── python-expert/
    ├── test-driven-development/
    ├── pull-request-expert/
    ├── security-audit/
    ├── senior-architect-engineering/
    └── ... (and 6 other backend-compatible skills, totaling 11)
```

---

## 2. Integrated Configuration Assets

### 2.1 Model Context Protocol (`.mcp.json`)
Registers secure, lazy-loaded cloud management tools:
- **`google-cloud-run`**: Enables listing services, fetching service details, viewing deployment logs, and running deployments.
- **`firebase-tools`**: Enables Cloud Firestore collection lookups, document mutations, and real-time database queries.

### 2.2 Lifecycle Hook Mappings (`hooks.json`)
Registers Node.js triggers to intercept editor operations:
- **`SessionStart`**: Runs `python-backend-activate.js` on startup to load rules and check cloud credentials.
- **`PreToolUse`**: Runs `pre-tool-gate.js` before executing command line tools or calling MCP tools to inspect arguments.
- **`Stop`**: Runs `stop-gate.js` before finishing a request to verify the test suite state.

---

## 3. Operations & Safety Gates Detail

### 3.1 Gitflow Branch Block (Intercepts commits/pushes)
- **Goal**: Protect staging (`develop`) and production (`main`) branches.
- **Mechanism**: The `PreToolUse` hook checks the active branch using git command lines. If the developer tries to commit or push directly to `main` or `develop`, it returns a `deny` decision, blocking the execution immediately.

### 3.2 Deployment Lock (Ask)
- **Goal**: Avoid accidental modifications or deployments to cloud targets.
- **Mechanism**: If a command contains deployment keywords (`deploy`, `kubectl apply`) or calls GCP/Firebase MCP modification APIs, the `PreToolUse` hook returns an `ask` permission decision. This pauses execution and displays a confirmation dialog asking the user for explicit approval.

### 3.3 Test Verification Gate (Request finalization blocker)
- **Goal**: Ensure 0 regressions are delivered.
- **Mechanism**: When the agent attempts to stop or complete a task, the `Stop` hook runs the project's test suite via `python3 ./skills/test-driven-development/scripts/verify_tests.py`. If tests fail, it halts termination, outputs the traceback, and forces the developer/agent loop to continue until resolved.

---

## 4. Bundled Skills (11 Packaged Modules)

On loading the plugin, the following 11 skills are automatically loaded into the agent's context:

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

---

## 5. Example Prompts

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

Try triggering a gate directly to see it in action: "Commit and push directly to main" (the Gitflow hook should deny it) or "Deploy this service to Cloud Run" (the deployment hook should ask for explicit approval first).
