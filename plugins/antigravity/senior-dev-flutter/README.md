# senior-dev-flutter

> Senior Flutter orchestration, architecture decisions, review, profiling and release engineering for Google Antigravity.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Antigravity-4285F4)](../../../README.md)

The Flutter and Dart teams publish official agent skills and an MCP server that cover *how* to build layouts, routing, serialization, tests and analysis.
This plugin does not duplicate the official packs. It installs on top of them and adds the senior layer: planning, deciding, reviewing and shipping.
It bundles copies of the `senior-dev` specialists, so it works without `senior-dev` installed.

## Requirements

| Requirement | Why |
| :--- | :--- |
| Antigravity CLI (`agy`) | Plugin host |
| `node` on `PATH` | Runs the hook scripts |
| Dart / Flutter SDK (`dart` on `PATH`) | `dart mcp-server` and the `dart analyze` stop gate |
| Official Flutter and Dart skill packs | Required companion; this plugin routes to them |

## Installation

```bash
agy plugin install ./plugins/antigravity/senior-dev-flutter
agy plugin list      # confirm
```

Install the required official packs. The Dart MCP server ships with the Dart SDK:

```bash
npx skills add flutter/agent-plugins --skill '*' --agent universal --yes
npx skills add dart-lang/skills      --skill '*' --agent universal --yes
dart --version   # `dart mcp-server` comes with the SDK
```

Official docs: [agent skills](https://docs.flutter.dev/ai/agent-skills) · [MCP server](https://docs.flutter.dev/ai/mcp-server).

## Quick start

`flutter-feature-orchestrator` is the plugin's main agent (`mainAgent: true`). Example prompts:

- "Use the flutter-feature-orchestrator agent to build a profile-edit feature end to end."
- "Have the flutter-architect agent choose state management for this app and write the ADR."
- "Get flutter-release-engineer to set up dev/staging/prod flavors and a signed build matrix."

## What's included

### Agents

`product-analyst`, `ui-ux-designer`, `qa-tester`, `e2e-blackbox-tester` and `flutter-release-engineer` run on `model: flash`; the rest use `model: inherit`. All agents use `commandExecutionPolicy: auto`.

| Agent | Role |
| :--- | :--- |
| `flutter-feature-orchestrator` | Main agent. Sizes the request, writes `docs/<feature-name>/PLAN.md`, sequences official skills and delegates |
| `flutter-architect` | State management choice, module boundaries, MADR ADRs |
| `flutter-implementer` | Flutter/Dart changes with TDD and `DESIGN.md` token fidelity |
| `flutter-reviewer` | Rebuild scope, `const`, keys, dispose/leaks, async `BuildContext`, ADR conformance |
| `flutter-release-engineer` | Flavors, `--dart-define-from-file`, signing, build matrix, versioning, Shorebird OTA, upgrades |
| `product-analyst` | Bundled specialist: `## Product` section of `docs/<feature-name>/spec.md` |
| `ui-ux-designer` | Bundled specialist: root `DESIGN.md` and `## Design` deltas |
| `qa-tester` | Bundled specialist: `test-matrix.md` with exit-code-0 proof |
| `critic` | Bundled specialist: independent code review |
| `challenger` | Bundled specialist: stress, fuzzing and failure-path probes |
| `e2e-blackbox-tester` | Bundled specialist: Playwright browser verification of a live web UI |

The six specialists are synced copies of the `senior-dev` agents (`scripts/sync_agents.py`). Edit them in [`../senior-dev/agents/`](../senior-dev/agents/), not here.

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`flutter-senior-orchestration`** | Run a feature or fix end to end: context restore, tier routing, gated dispatch via `docs/<feature-name>/PLAN.md` |
| **`flutter-architecture-decisions`** | Choose state management (Riverpod, Bloc, signals, setState), module boundaries, ADRs |
| **`flutter-review-checklist`** | Senior review checklist and a file-only project audit script |
| **`flutter-test-strategy`** | What to test at unit, widget, golden and integration level; coverage gates |
| **`flutter-performance-profiling`** | Diagnose jank and slow startup with DevTools, profile mode and startup tracing |
| **`flutter-release-engineering`** | Flavors, environment config, signing, build matrix, versioning, store metadata |
| **`flutter-upgrade-migration`** | SDK upgrades, major dependency bumps and deprecation sweeps |
| **`context-capture`** | Write cross-session memory to `context/memory/` at the end of a milestone |
| **`context-restore`** | Read `context/memory/MEMORY.md` at session start |
| **`loop-engineering`** | Tier routing, parallel isolation (disjoint files or git worktree) and bounded fix loops |
| **`product-analyst`** | Used by the bundled `product-analyst` agent |
| **`ui-ux-designer`** | Used by the bundled `ui-ux-designer` agent |
| **`qa-tester`** | Used by the bundled `qa-tester` agent |
| **`code-critic`** | Used by the bundled `critic` agent |
| **`code-smells-expert`** | Smell taxonomy for the `critic` agent |
| **`refactoring-code-expert`** | Refactoring catalog for the `critic` agent |
| **`adversarial-challenger`** | Used by the bundled `challenger` agent |
| **`test-driven-development`** | Red-Green-Refactor guidance for the `challenger` agent |
| **`blackbox-tester`** | Used by the bundled `e2e-blackbox-tester` agent (Flutter Web targets) |

Skills are copies of the root [`skills/`](../../../skills/) catalog. Edit them there and run `python3 scripts/sync_plugin_skills.py`.

### Hooks

Registered in the `senior-dev-flutter-gates` group of `hooks.json`.

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `PreToolUse` (`write_to_file`, `replace_file_content`, `multi_replace_file_content`) | `hooks/flutter-pre-tool-gate.js` | In a Flutter repo: denies `.dart` / `pubspec.yaml` edits on `main`, `master`, `develop` or `dev`; denies `.dart` edits without `PLAN.md` (edits of 10 lines or fewer are exempt); denies `.dart` edits by the orchestrator itself |
| `PreToolUse` (`run_command`) | `hooks/flutter-pre-tool-gate.js` | On a protected branch, denies `flutter build appbundle\|aab\|ipa` and `pub upgrade --major-versions` |
| `Stop` | `hooks/flutter-stop-gate.js` | On `model_stop`, if `pubspec.yaml` exists and `dart` is available, runs `dart analyze` and returns `continue` on findings. A green result is cached until the code changes; after 3 blocks per message it lets the agent stop |

### MCP servers

| Server | Command | Purpose |
| :--- | :--- | :--- |
| `dart` | `dart mcp-server` | Official Dart and Flutter MCP server, declared in `mcp_config.json` |

### Rules

[`rules/flutter-rules.md`](rules/flutter-rules.md) (`trigger: glob`, loaded only while touching `*.dart` or `pubspec.yaml`) holds the frame budget, lifecycle, shared-file and secrets constraints. The workflow lives in the orchestrator agent.

## How it works

1. The orchestrator restores `context/memory/MEMORY.md` and writes a short `docs/<feature-name>/PLAN.md` with a tier (1 fast-track, 2 standard, 3 mission-critical).
2. Tier 2 and 3 run only the discovery specialists the plan justifies, then pause for your approval.
3. Shared files (`pubspec.yaml`, router, DI, generated code) change first in one committed step; then up to 3 `flutter-implementer` tracks run in parallel on disjoint files, without git writes or `build_runner`. Worktrees are a last resort.
4. `flutter-reviewer`, `qa-tester` and, when needed, `flutter-release-engineer` and adversarial reviewers verify the work.
5. The milestone is saved to `context/memory/`.

The full lifecycle is described in the root [README](../../../README.md) and [AGENTS.md](../../../AGENTS.md).

**Worktrees in Antigravity.** No setting is needed: when two tracks must edit the same files, the orchestrator runs each worker with subagent workspace `branch`. The docs do not say which commit that branch starts from, so each worker first runs `git merge-base --is-ancestor <feature HEAD> HEAD` and stops if your feature commits are missing; the orchestrator then sequences the tracks or creates the worktrees from your current `HEAD` with `run_parallel_agents.py` (loop-engineering skill). A worktree is a fresh checkout, so the worker installs dependencies inside it before testing.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `.dart` edit denied with `PLAN FIRST` | No `PLAN.md` in `docs/<feature-name>/` (or the legacy root / `doc/` locations) | Create `docs/<feature-name>/PLAN.md` before editing Dart code |
| `.dart` edit denied with `GRAPH INVARIANT VIOLATION` | The orchestrator tried to edit Dart code directly | Delegate the change to `flutter-implementer` |
| Dart edit denied on `main` | Protected branch (`main`, `master`, `develop`, `dev`) | `git checkout -b feat/<slug>` |
| `flutter build ipa` or `pub upgrade --major-versions` denied | Store builds and major bumps are blocked on protected branches | Run them from a release or chore branch, or in CI |
| Agent cannot finish: "`dart analyze` is not clean" | Stop gate found analyzer issues | Fix the findings, then run `flutter test` (the hook does not) |
| Gates never fire | All gates need `pubspec.yaml` in the workspace root; the stop gate also needs `dart` on `PATH` | Run from the Flutter project root with the Dart SDK installed |

## Related plugins

- [senior-dev](../senior-dev/README.md): general SDLC orchestrator and the source of the bundled specialists.
- [shared-context](../shared-context/README.md): cross-agent memory in a committed `context/` directory.
- [git-workflow](../git-workflow/README.md): branch and commit workflow.
- [Claude Code variant](../../claude/senior-dev-flutter/README.md) of this plugin.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
