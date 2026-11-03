# python-backend

> Production Python backend engineering for Claude Code: FastAPI/Django/Flask orchestration, TDD, migrations, CI gates and Cloud Run / Firebase guardrails.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-orange)](../../../docs/claude-code-installation.md)

`python-backend` adds a Python backend orchestrator, backend skills and quality gates on top of `senior-dev`.
Its hooks require a plan before Python edits, block git writes on protected branches, ask before deployments, and run the test suite before a turn ends.
It also registers the Cloud Run and Firebase MCP servers.

## Requirements

| Requirement | Why |
| :--- | :--- |
| Claude Code | Plugin host |
| `node` and `npx` on `PATH` | Hook scripts and MCP servers |
| Python 3 (`pytest` recommended) | The stop gate runs `pytest`, or `unittest` as a fallback |
| `senior-dev` plugin | Declared dependency; installed automatically |

## Installation

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install python-backend@expert-ai-developer-skills
```

`.claude-plugin/plugin.json` declares `"dependencies": ["senior-dev"]`, so Claude Code installs `senior-dev` too.
This plugin does not ship copies of the `senior-dev` agents or skills.

Updates, per-project settings, local development and limitations: [Claude Code installation guide](../../../docs/claude-code-installation.md).

## Quick start

Run the orchestrator as the main thread so it can ask you for approval at the alignment gate:

```bash
claude --agent python-backend:python-backend-orchestrator
```

Example prompts:

- "Add a `GET /orders/{id}` endpoint, test-first, with a zero-downtime Alembic migration."
- "Run a security audit on this service for hardcoded secrets and OWASP Top 10 issues."
- "Profile this endpoint for N+1 queries and memory usage."

The gates apply in any session once the plugin is installed. Try "commit this directly to main" to see the branch gate deny it.

## What's included

### Agents

| Agent | Role | Model |
| :--- | :--- | :--- |
| `python-backend-orchestrator` | Plans and governs FastAPI, Django and Flask work; writes `PLAN.md` and delegates to specialists | `inherit` |

The orchestrator dispatches `senior-dev` specialists by their namespaced type: `senior-dev:product-analyst`, `senior-dev:ui-ux-designer`, `senior-dev:architect-engineer`, `senior-dev:code-implementer`, `senior-dev:qa-tester`, `senior-dev:compliance-verifier`, `senior-dev:critic`, `senior-dev:challenger` and `senior-dev:e2e-blackbox-tester`.

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`python-expert`** | PEP 8, modern type hints, generators, `__slots__`/dataclasses, `asyncio` TaskGroup |
| **`test-driven-development`** | Red-Green-Refactor cycles, mocks and testable design |
| **`database-migration-expert`** | Schema migrations, seed data and table versioning (Alembic, SQL) |
| **`design-spec-expert`** | Concise API specs and design documents before coding new endpoints or services |
| **`security-audit`** | Security review of code, IaC and designs (injection, access control, secrets) |
| **`performance-scalability`** | Slow queries, caching, memory leaks and scaling limits |
| **`build-and-ci-gates`** | Linters, formatters and CI pipelines that stop failing builds |
| **`pull-request-expert`** | Concise pull requests with Conventional Commits validation |
| **`context-capture`** | Write cross-session memory to `context/memory/` at the end of a milestone |
| **`context-restore`** | Read `context/memory/MEMORY.md` at session start |
| **`loop-engineering`** | Tier routing, parallel isolation (disjoint files or git worktree) and bounded fix loops |

Architecture, refactoring, code-smell and specialist skills come from `senior-dev`.

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `SessionStart` | `hooks/python-backend-activate.js` | Injects `rules/python-backend-rules.md` as context if present. This package ships no `rules/` directory, so it currently injects nothing |
| `PreToolUse` (`Write`, `Edit`) | `hooks/pre-tool-gate.js` | Denies `.py` edits on `main`, `master`, `develop` or `dev`. Denies `.py` edits without `PLAN.md` unless the edit is small |
| `PreToolUse` (`Bash`) | `hooks/pre-tool-gate.js` | Asks before deploy commands (`deploy`, `apply -f`). Denies `git add/commit/push/merge` on protected branches |
| `PreToolUse` (MCP) | `hooks/pre-tool-gate.js` | Asks before Cloud Run `deploy_*` tools and Firebase add/update/delete/set tools |
| `Stop` | `hooks/stop-gate.js` | If tests exist, runs `pytest` (or `unittest`) and blocks finishing on failures |

### MCP servers

| Server | Command | Purpose |
| :--- | :--- | :--- |
| `cloudrun` | `npx -y @google-cloud/cloud-run-mcp` | List, inspect, deploy and read logs of Cloud Run services |
| `firebase-mcp-server` | `npx -y firebase-tools@latest mcp` | Firebase projects, Firestore, Auth and related tools |

## How it works

1. The orchestrator restores `context/memory/MEMORY.md` and writes a short `PLAN.md` with a tier and an API / migration triage table.
2. Tier 2 and 3 run only the discovery specialists the plan justifies, then pause for your approval.
3. Vertical slices (router, service, repository, tests) run in parallel on disjoint files, or in git worktrees when they touch migrations or shared settings.
4. QA, compliance and, for high-risk changes, adversarial reviewers verify the work.
5. The milestone is saved to `context/memory/`.

The full lifecycle is described in the root [README](../../../README.md) and [AGENTS.md](../../../AGENTS.md).

## Configuration

To make the orchestrator the default agent for a project, add this to `.claude/settings.json`:

```json
{
  "agent": "python-backend:python-backend-orchestrator"
}
```

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `.py` edit denied with `PLAN-FIRST VIOLATION` | No `PLAN.md` at the repo root, `docs/`, `.agents/` or `.claude/` | Create `PLAN.md`. Small `Edit` calls (10 lines or fewer per side) are allowed without it |
| `git commit` denied with `Gitflow Safety Blocked` | Protected branch (`main`, `master`, `develop`, `dev`) | Work on a `feature/` or `bugfix/` branch and merge via pull request |
| A command containing `deploy` asks for approval | Deployment guardrail | Approve it if the deployment is intended |
| Agent cannot finish: `PYTHON QUALITY GATE FAILURE` | Stop gate ran the tests and they failed | Fix the tests or code. The gate blocks at most 3 times per turn and skips if code is unchanged since the last pass |
| Stop gate never runs tests | No `tests/`, `test/`, `pytest.ini`, `setup.cfg` or `test_*.py` at the workspace root | Add a test suite at the project root |

## Related plugins

- [senior-dev](../senior-dev/README.md): general SDLC orchestrator and specialists (required dependency).
- [sql-query-optimizer](../sql-query-optimizer/README.md): diagnose and rewrite slow SQL queries.
- [git-workflow](../git-workflow/README.md): branch and pull request workflow.
- [shared-context](../shared-context/README.md): cross-agent memory in a committed `context/` directory.
- [Antigravity variant](../../antigravity/python-backend/README.md) of this plugin.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
