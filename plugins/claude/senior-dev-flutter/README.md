# senior-dev-flutter

> Senior Flutter orchestration, architecture decisions, review, profiling and release engineering for Claude Code.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-orange)](../../../docs/claude-code-installation.md)

The Flutter and Dart teams publish official agent skills and an MCP server that cover *how* to build layouts, routing, serialization, tests and analysis.
This plugin does not duplicate the official packs. It installs on top of them and adds the senior layer: planning, deciding, reviewing and shipping.
For any "how-to" step, its agents call the official `flutter-*` / `dart-*` skills.

## Requirements

| Requirement | Why |
| :--- | :--- |
| Claude Code | Plugin host |
| `node` on `PATH` | Runs the hook scripts |
| Dart / Flutter SDK (`dart` on `PATH`) | `dart mcp-server` and the `dart analyze` stop gate |
| Official Flutter and Dart skill packs | Required companion; this plugin routes to them |
| `senior-dev` plugin | Declared dependency; installed automatically |

## Installation

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install senior-dev-flutter@expert-ai-developer-skills
```

`.claude-plugin/plugin.json` declares `"dependencies": ["senior-dev"]`, so Claude Code installs `senior-dev` too.
This plugin does not ship copies of the `senior-dev` agents or skills.

Install the required official packs. The Dart MCP server ships with the Dart SDK:

```bash
npx skills add flutter/agent-plugins --skill '*' --agent universal --yes
npx skills add dart-lang/skills      --skill '*' --agent universal --yes
dart --version   # `dart mcp-server` comes with the SDK
```

Updates, per-project settings, local development and limitations: [Claude Code installation guide](../../../docs/claude-code-installation.md).
Official docs: [agent skills](https://docs.flutter.dev/ai/agent-skills) · [MCP server](https://docs.flutter.dev/ai/mcp-server).

## Quick start

Run the orchestrator as the main thread so it can ask you for approval at the alignment gate:

```bash
claude --agent senior-dev-flutter:flutter-feature-orchestrator
```

Example prompts:

- "Build a profile-edit feature end to end."
- "Have the flutter-architect agent choose state management for this app and write the ADR."
- "Ask the flutter-reviewer agent to review this PR for rebuild scope, leaks and accessibility."

## What's included

### Agents

| Agent | Role | Model |
| :--- | :--- | :--- |
| `flutter-feature-orchestrator` | Sizes the request, writes `PLAN.md`, sequences official skills and delegates to subagents | `inherit` |
| `flutter-architect` | State management choice, module boundaries, MADR ADRs | `inherit` |
| `flutter-implementer` | Flutter/Dart changes with TDD and `DESIGN.md` token fidelity | `inherit` |
| `flutter-reviewer` | Rebuild scope, `const`, keys, dispose/leaks, async `BuildContext`, ADR conformance | `inherit` |
| `flutter-release-engineer` | Flavors, `--dart-define-from-file`, signing, build matrix, versioning, Shorebird OTA, upgrades | `sonnet` |

The orchestrator also dispatches `senior-dev` specialists by their namespaced type, for example `senior-dev:product-analyst`, `senior-dev:qa-tester` and `senior-dev:critic`.
The full list is in the *Claude Code Runtime Notes* of [`agents/flutter-feature-orchestrator.md`](agents/flutter-feature-orchestrator.md).

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`flutter-senior-orchestration`** | Run a feature or fix end to end: context restore, tier routing, gated dispatch via `PLAN.md` |
| **`flutter-architecture-decisions`** | Choose state management (Riverpod, Bloc, signals, setState), module boundaries, ADRs |
| **`flutter-review-checklist`** | Senior review checklist and a file-only project audit script |
| **`flutter-test-strategy`** | What to test at unit, widget, golden and integration level; coverage gates |
| **`flutter-performance-profiling`** | Diagnose jank and slow startup with DevTools, profile mode and startup tracing |
| **`flutter-release-engineering`** | Flavors, environment config, signing, build matrix, versioning, store metadata |
| **`flutter-upgrade-migration`** | SDK upgrades, major dependency bumps and deprecation sweeps |
| **`context-capture`** | Write cross-session memory to `context/memory/` at the end of a milestone |
| **`context-restore`** | Read `context/memory/MEMORY.md` at session start |
| **`loop-engineering`** | Tier routing, parallel isolation (disjoint files or git worktree) and bounded fix loops |

Specialist skills (product, design, QA, critic, challenger, black-box) come from `senior-dev`.

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `PreToolUse` (`Write`, `Edit`) | `hooks/flutter-pre-tool-gate.js` | Denies `.dart` / `pubspec.yaml` edits on `main`, `master`, `develop` or `dev`. Denies `.dart` edits without a `PLAN.md` unless the edit is small |
| `PreToolUse` (`Bash`) | `hooks/flutter-pre-tool-gate.js` | In a Flutter repo on a protected branch, denies `flutter build appbundle\|aab\|ipa` and `pub upgrade --major-versions` |
| `Stop` | `hooks/flutter-stop-gate.js` | If `pubspec.yaml` exists and `dart` is available, runs `dart analyze` and blocks finishing on findings |

### MCP servers

| Server | Command | Purpose |
| :--- | :--- | :--- |
| `dart` | `dart mcp-server` | Official Dart and Flutter MCP server (analyzer, symbols, tests, runtime inspection) |

## How it works

1. The orchestrator restores `context/memory/MEMORY.md` and writes a short `PLAN.md` with a tier (1 fast-track, 2 standard, 3 mission-critical).
2. Tier 2 and 3 run only the discovery specialists the plan justifies, then pause for your approval.
3. Shared files (`pubspec.yaml`, router, DI, generated code) change first in one committed step; then up to 3 `flutter-implementer` tracks run in parallel on disjoint files, without git writes or `build_runner`. Worktrees are a last resort.
4. `flutter-reviewer`, `qa-tester` and, when needed, `flutter-release-engineer` and adversarial reviewers verify the work.
5. The milestone is saved to `context/memory/`.

The full lifecycle is described in the root [README](../../../README.md) and [AGENTS.md](../../../AGENTS.md).

## Configuration

To make the orchestrator the default agent for a project, add this to `.claude/settings.json`:

```json
{
  "agent": "senior-dev-flutter:flutter-feature-orchestrator"
}
```

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| Edit to a `.dart` file is denied with `PLAN-FIRST VIOLATION` | No `PLAN.md` at the repo root, `docs/`, `.agents/` or `.claude/` | Create `PLAN.md`. Small `Edit` calls (10 lines or fewer per side) are allowed without it |
| Dart edit denied on `main` | Protected branch (`main`, `master`, `develop`, `dev`) | `git checkout -b feat/<slug>` |
| `flutter build ipa` or `pub upgrade --major-versions` denied | Store builds and major bumps are blocked on protected branches | Run them from a release or chore branch, or in CI |
| Agent cannot finish: "`dart analyze` is not clean" | Stop gate found analyzer issues | Fix the findings. The gate blocks at most 3 times per turn and skips if code is unchanged since the last pass |
| Stop gate never runs | No `pubspec.yaml` in the workspace or `dart` not on `PATH` | Install the Dart SDK and run from the Flutter project root |
| Orchestrator does not ask for approval | It was started as a subagent, where it cannot prompt you | Start it with `claude --agent senior-dev-flutter:flutter-feature-orchestrator` |

## Related plugins

- [senior-dev](../senior-dev/README.md): general SDLC orchestrator and specialists (required dependency).
- [shared-context](../shared-context/README.md): cross-agent memory in a committed `context/` directory.
- [git-workflow](../git-workflow/README.md): branch and commit workflow.
- [Antigravity variant](../../antigravity/senior-dev-flutter/README.md) of this plugin.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
