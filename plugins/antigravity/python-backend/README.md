# python-backend

> Production Python backend engineering for Google Antigravity: FastAPI/Django/Flask orchestration, TDD, migrations, CI gates and Cloud Run / Firebase guardrails.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Antigravity-4285F4)](../../../README.md)

`python-backend` adds a Python backend orchestrator, backend skills and quality gates.
Its hooks require a plan before Python edits, block git writes on protected branches and ask before deployments.
It bundles copies of the `senior-dev` specialists, so it works without `senior-dev` installed, and registers the Cloud Run and Firebase MCP servers.

## Requirements

| Requirement | Why |
| :--- | :--- |
| Antigravity CLI (`agy`) | Plugin host |
| `node` and `npx` on `PATH` | Hook scripts and MCP servers |
| Python 3 | Test runs and the stop gate script |

## Installation

```bash
agy plugin install ./plugins/antigravity/python-backend
agy plugin list      # confirm
```

## Quick start

`python-backend-orchestrator` is the plugin's main agent (`mainAgent: true`). Example prompts:

- "Write a zero-downtime Alembic migration that adds a NOT NULL column."
- "Run a security audit on this codebase for hardcoded secrets and OWASP Top 10 issues."
- "Draft an ADR for choosing between REST and gRPC for this internal service."

The gates apply once the plugin is installed. Try "commit this directly to main" to see the branch gate deny it.

## What's included

### Agents

All agents use `model: inherit` and `commandExecutionPolicy: auto`.

| Agent | Role |
| :--- | :--- |
| `python-backend-orchestrator` | Main agent. Plans and governs FastAPI, Django and Flask work; writes `PLAN.md` and delegates |
| `product-analyst` | Bundled specialist: `## Product` section of `docs/<feature-name>/spec.md` |
| `ui-ux-designer` | Bundled specialist: root `DESIGN.md` and `## Design` deltas |
| `architect-engineer` | Bundled specialist: MADR ADRs and `## Architecture` |
| `code-implementer` | Bundled specialist: TDD build tracks |
| `qa-tester` | Bundled specialist: `test-matrix.md` with exit-code-0 proof |
| `compliance-verifier` | Bundled specialist: static analysis and security sign-off |
| `critic` | Bundled specialist: independent code review |
| `challenger` | Bundled specialist: stress, fuzzing and failure-path probes |
| `e2e-blackbox-tester` | Bundled specialist: Playwright browser verification of a live web UI |

The nine specialists are synced copies of the `senior-dev` agents (`scripts/sync_agents.py`). Edit them in [`../senior-dev/agents/`](../senior-dev/agents/), not here.

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`python-expert`** | PEP 8, modern type hints, generators, `__slots__`/dataclasses, `asyncio` TaskGroup |
| **`test-driven-development`** | Red-Green-Refactor cycles, mocks and testable design |
| **`database-migration-expert`** | Schema migrations, seed data and table versioning (Alembic, SQL) |
| **`design-spec-expert`** | Concise API specs and design documents before coding new endpoints or services |
| **`senior-architect-engineering`** | MADR ADRs and the `## Architecture` section |
| **`security-audit`** | Security review of code, IaC and designs (injection, access control, secrets) |
| **`performance-scalability`** | Slow queries, caching, memory leaks and scaling limits |
| **`build-and-ci-gates`** | Linters, formatters and CI pipelines that stop failing builds |
| **`pull-request-expert`** | Concise pull requests with Conventional Commits validation |
| **`code-smells-expert`** | Diagnose code smells and technical debt |
| **`refactoring-code-expert`** | Behavior-preserving structural refactoring |
| **`context-capture`** | Write cross-session memory to `context/memory/` at the end of a milestone |
| **`context-restore`** | Read `context/memory/MEMORY.md` at session start |
| **`loop-engineering`** | Tier routing, parallel isolation (disjoint files or git worktree) and bounded fix loops |
| **`product-analyst`** | Used by the bundled `product-analyst` agent |
| **`ui-ux-designer`** | Used by the bundled `ui-ux-designer` agent |
| **`code-implementer`** | Used by the bundled `code-implementer` agent |
| **`qa-tester`** | Used by the bundled `qa-tester` agent |
| **`compliance-verifier`** | Used by the bundled `compliance-verifier` agent |
| **`code-critic`** | Used by the bundled `critic` agent |
| **`adversarial-challenger`** | Used by the bundled `challenger` agent |
| **`blackbox-tester`** | Used by the bundled `e2e-blackbox-tester` agent |

Skills are copies of the root [`skills/`](../../../skills/) catalog. Edit them there and run `python3 scripts/sync_plugin_skills.py`.

### Hooks

Registered in the `python-backend-safety-gates` group of `hooks.json`.

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `PreToolUse` (`write_to_file`, `replace_file_content`) | `hooks/pre-tool-gate.js` | Denies `.py` edits on `main`, `master`, `develop` or `dev`, and `.py` edits without `PLAN.md` |
| `PreToolUse` (`run_command`) | `hooks/pre-tool-gate.js` | Asks before deploy commands (`deploy`, `apply -f`). Denies `git add/commit/push/merge` on protected branches |
| `PreToolUse` (`call_mcp_tool`) | `hooks/pre-tool-gate.js` | Asks before Cloud Run `deploy_*` tools and Firebase add/update/delete/set tools |
| `Stop` | `hooks/stop-gate.js` | If `skills/test-driven-development/scripts/verify_tests.py` exists in the workspace, runs it and returns `continue` on failure |

### MCP servers

| Server | Command | Purpose |
| :--- | :--- | :--- |
| `cloudrun` | `npx -y @google-cloud/cloud-run-mcp` | List, inspect, deploy and read logs of Cloud Run services |
| `firebase-mcp-server` | `npx -y firebase-tools@latest mcp` | Firebase projects, Firestore, Auth and related tools |

### Rules

| File | Content |
| :--- | :--- |
| [`rules/python-backend-rules.md`](rules/python-backend-rules.md) | `trigger: always_on`. Gitflow safety, plan-first lifecycle, migrations and TDD rules |
| [`rules/git-hooks.md`](rules/git-hooks.md) | Reference blueprints for `pre-commit` and `commit-msg` git hooks |

## How it works

1. The orchestrator restores `context/memory/MEMORY.md` and writes a short `PLAN.md` with a tier and an API / migration triage table.
2. Tier 2 and 3 run only the discovery specialists the plan justifies, then pause for your approval.
3. Vertical slices (router, service, repository, tests) run in parallel on disjoint files, or in git worktrees when they touch migrations or shared settings.
4. QA, compliance and, for high-risk changes, adversarial reviewers verify the work.
5. The milestone is saved to `context/memory/`.

The full lifecycle is described in the root [README](../../../README.md) and [AGENTS.md](../../../AGENTS.md).

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `.py` edit denied with `PLAN FIRST` | No `PLAN.md` at the workspace root or `docs/` | Create `PLAN.md` before editing Python code |
| `.py` edit denied with `GIT BRANCH GOVERNANCE` | Protected branch (`main`, `master`, `develop`, `dev`) | `git checkout -b feat/<slug>` |
| `git commit` denied with `Gitflow Safety Blocked` | Git writes are blocked on protected branches | Work on a `feature/` or `bugfix/` branch and merge via pull request |
| A command containing `deploy` asks for approval | Deployment guardrail | Approve it if the deployment is intended |
| Stop gate never runs tests | It only runs `skills/test-driven-development/scripts/verify_tests.py` from the workspace | Run your test suite explicitly before finishing |

## Related plugins

- [senior-dev](../senior-dev/README.md): general SDLC orchestrator and the source of the bundled specialists.
- [sql-query-optimizer](../sql-query-optimizer/README.md): diagnose and rewrite slow SQL queries.
- [git-workflow](../git-workflow/README.md): branch and pull request workflow.
- [shared-context](../shared-context/README.md): cross-agent memory in a committed `context/` directory.
- [Claude Code variant](../../claude/python-backend/README.md) of this plugin.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
