# Python Backend Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-python--backend-green?style=flat-square)](file:///./)

The `python-backend` plugin is a specialized customization package for **Google Antigravity** designed to automate quality gates, enforce branch safety constraints (Gitflow), validate test execution, govern Python backend applications through Graph Engineering, and link external GCP and Firebase resources through the Model Context Protocol (MCP).

- **Google Antigravity**: Install via `agy plugin install ./plugins/antigravity/python-backend`. Subagent in `agents/` declares native Antigravity tools (`run_command`, `write_to_file`, `replace_file_content`, `view_file`, `invoke_subagent`, `manage_subagents`, `send_message`) with `commandExecutionPolicy: auto`.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog, kept self-contained so the plugin folder can be distributed on its own. After editing any bundled skill under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy — don't hand-edit both. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/antigravity/python-backend/
├── README.md                       # This usage manual
├── plugin.json                     # Antigravity plugin manifest
├── .claude-plugin/
│   └── plugin.json                 # Manifest compatibility marker
├── .mcp.json                       # MCP definitions (Cloud Run, Firebase)
├── mcp_config.json                 # Antigravity MCP definitions
├── hooks.json                      # Hook registrations
├── hooks/
│   ├── python-backend-activate.js  # Environment and credentials initialization
│   ├── pre-tool-gate.js            # PreToolUse: intercepts git & cloud deployments
│   └── stop-gate.js                # Stop: quality gate checking test suite
├── agents/
│   └── python-backend-orchestrator.md # Senior Python Backend Orchestrator
├── rules/
│   ├── python-backend-rules.md     # Quality checklists and coding patterns
│   └── git-hooks.md                # Blueprints for pre-commit & commit-msg hooks
└── skills/                         # Bundled developer skills
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
    └── build-and-ci-gates/
```

---

## 2. The Orchestrator & Execution Policy

| Agent | Role | Execution Policy | Typical Tools |
| :--- | :--- | :--- | :--- |
| **`python-backend-orchestrator`** | Senior Python Backend Orchestrator | `auto` | `run_command`, `write_to_file`, `replace_file_content`, `view_file`, `invoke_subagent`, `manage_subagents`, `send_message` |

### Inviolable Orchestration Boundaries:
1. **Plan First**: Author `PLAN.md` documenting API routes, Pydantic/dataclass schemas, and database entity relationships before writing code.
2. **Branch Safety (Gitflow)**: Never commit directly to `main` or `develop`. Work on isolated `feature/` or `bugfix/` branches.
3. **Strict TDD & Migration Protocol**: Schema changes must always include an Alembic/Django migration file and a corresponding unit/integration test suite.

---

## 3. Model Context Protocol (`.mcp.json` / `mcp_config.json`)

Registers secure, lazy-loaded cloud management tools:
- **`cloudrun`**: Enables listing services, fetching service details, viewing deployment logs, and running container deployments.
- **`firebase-mcp-server`**: Enables Cloud Firestore collection lookups, document mutations, and real-time database queries.

---

## 4. Lifecycle Hooks & Safety Gates

| Hook Event | Script | Behavior |
| :--- | :--- | :--- |
| **`PreToolUse`** | `hooks/pre-tool-gate.js` | Checks active branch using git command line. Denies commits or pushes directly to `main` or `develop`. Returns `ask` confirmation for cloud deployments or GCP/Firebase mutations. |
| **`Stop`** | `hooks/stop-gate.js` | Runs the test suite via `python3 ./skills/test-driven-development/scripts/verify_tests.py`. If tests fail, it halts termination and forces the loop to continue until resolved. |

---

## 5. Bundled Skills (11 Packaged Modules)

On loading the plugin, the following 11 skills are automatically available:

1. **`python-expert`**: AST analysis, PEP 8 compliance, and memory optimization (`__slots__`).
2. **`test-driven-development`**: AAA execution patterns, Red-Green-Refactor, and pytest parametrization.
3. **`pull-request-expert`**: Diff size checks (<200 lines) and Conventional Commit logs.
4. **`code-smells-expert`**: God classes, high cyclomatic complexity, and coupling diagnostics.
5. **`refactoring-code-expert`**: Safe extraction methods, Martin Fowler catalog, and behavior preservation.
6. **`security-audit`**: OWASP Top 10 scanner, injection prevention, and hardcoded secrets detection.
7. **`performance-scalability`**: CPU/Memory execution profiler, cProfile, and N+1 query diagnostics.
8. **`database-migration-expert`**: Zero-downtime Alembic schema migrations and rollback scripts.
9. **`senior-architect-engineering`**: Architecture Decision Records (ADRs) and system boundary design.
10. **`design-spec-expert`**: Software Design Documents (SDDs) and API contract schemas.
11. **`build-and-ci-gates`**: Pre-commit hooks, linter enforcement, and automated quality gates.

---

## 6. Example Prompts

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

```bash
agy plugin install ./plugins/antigravity/python-backend
agy plugin list      # confirm
```
