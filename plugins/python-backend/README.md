# Antigravity Custom Plugin: Python Backend

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-python--backend-green?style=flat-square)](file:///./)

The `python-backend` plugin is a unified customization package designed to automate quality gates, enforce branch safety constraints (Gitflow), validate test execution, run periodic reviews, and link external GCP and Firebase resources through the Model Context Protocol (MCP).

---

## 1. Directory Tree & Architecture

The plugin is structured according to the official Antigravity plugin layout:

```
plugins/python-backend/
├── README.md             # This usage and configuration manual
├── plugin.json           # Required marker containing metadata
├── mcp_config.json       # MCP definitions (GCP, Firebase)
├── hooks.json            # Dynamic lifecycle hook registrations
├── hooks/                # Node.js hook event handlers
│   ├── python-backend-activate.js  # Runs on SessionStart; audits environment
│   ├── pre-tool-gate.js            # Runs on PreToolUse; intercepts git & cloud deployments
│   └── stop-gate.js                # Runs on Stop; quality gate checking test suite
├── rules/                # Central system guidelines
│   ├── python-backend-rules.md     # Quality checklists and coding patterns
│   └── git-hooks.md                # Blueprints for pre-commit & commit-msg hooks
└── skills/               # Bundled developer skills loaded globally
    ├── documentation-expert/
    ├── testing-expert/
    ├── pull-request-expert/
    ├── commit-expert/
    ├── loop-engineering/
    └── ... (and 13 other backend-compatible skills, totaling 18)
```

---

## 2. Integrated Configuration Assets

### 2.1 Model Context Protocol (`mcp_config.json`)
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

### 3.2 Deployment Lock (Force Ask)
- **Goal**: Avoid accidental modifications or deployments to cloud targets.
- **Mechanism**: If a command contains deployment keywords (`deploy`, `kubectl apply`) or calls GCP/Firebase MCP modification APIs, the `PreToolUse` hook returns a `force_ask` decision. This pauses execution and displays a confirmation dialog asking the user for explicit approval.

### 3.3 Test Verification Gate (Request finalization blocker)
- **Goal**: Ensure 0 regressions are delivered.
- **Mechanism**: When the agent attempts to stop or complete a task, the `Stop` hook runs the project's test suite via `python3 ./skills/test-driven-development/scripts/verify_tests.py`. If tests fail, it halts termination, outputs the traceback, and forces the developer/agent loop to continue until resolved.

---

## 4. Bundled Skills (18 Packaged Modules)

On loading the plugin, the following 18 skills are automatically loaded into the agent's context:

1. **`loop-engineering`**: Manager-worker topology automation.
2. **`python-expert`**: AST analysis and memory optimization check.
3. **`fastapi-expert`**: REST routing and Pydantic v2 schemas.
4. **`test-driven-development`**: AAA execution patterns.
5. **`documentation-expert`**: Diátaxis layouts and Mermaid guide validation.
6. **`testing-expert`**: Language-agnostic BDD Gherkin specifications.
7. **`pull-request-expert`**: Size checks and Conventional Commit logs.
8. **`commit-expert`**: Commit message syntax checkers and hook helpers.
9. **`code-smells-expert`**: Code complexity diagnostics.
10. **`refactoring-code-expert`**: Safe extraction methods.
11. **`security-audit`**: OWASP Top 10 scanner.
12. **`performance-scalability`**: CPU/Memory execution profiler.
13. **`database-migration-expert`**: Alembic schema migrations.
14. **`senior-architect-engineering`**: ADR templates.
15. **`design-spec-expert`**: SDD schemas.
16. **`build-and-ci-gates`**: Pre-commit quality hook gates.
17. **`repo-research`**: Automatically analyzes file tree structures, packages, and dependency maps.
18. **`guidelines-karpathy`**: Model development checklists.
