# `senior-dev-flutter` Plugin

**The senior Flutter layer on top of the official Flutter & Dart skill packs.**

The Dart and Flutter teams already publish ~23 agent skills that cover *how* to
build layouts, wire routing, serialize JSON, write every kind of test, run the
analyzer, and more — plus the official **Dart & Flutter MCP server**. This
plugin does **not** repeat any of that. It installs *on top* and adds the layer
those packs leave to you: **orchestrating, deciding, and reviewing.**

Its `agents/`, `skills/`, `hooks.json` (`"hooks"` key), `.mcp.json`, and
`${CLAUDE_PLUGIN_ROOT}` layout follow the **Claude Code plugin format**; the
root `plugin.json`, the `senior-dev-flutter-gates` group in `hooks.json`, and
`mcp_config.json` cover **Antigravity CLI**. One folder, `agy plugin install`-safe.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the
> seven `flutter-*` skills in the root `/skills` catalog. After editing any of
> them under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo
> root. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills`
> fails CI if the two drift.

---

## 1. Required companion — the official packs

This plugin is useless on its own. Install the official skills and MCP server first:

```bash
npx skills add flutter/agent-plugins --skill '*' --agent universal --yes
npx skills add dart-lang/skills      --skill '*' --agent universal --yes
```

MCP server (`.mcp.json` / `mcp_config.json` here declare it — you just need `dart` on PATH):

```bash
dart --version          # Dart SDK must be installed; `dart mcp-server` ships with it
```

Docs: [docs.flutter.dev/ai/agent-skills](https://docs.flutter.dev/ai/agent-skills)
· [docs.flutter.dev/ai/mcp-server](https://docs.flutter.dev/ai/mcp-server)

---

## 2. The boundary — what this plugin does *not* touch

| Concern | Owned by the official packs (do not duplicate) | Owned by `senior-dev-flutter` |
| :--- | :--- | :--- |
| **How-to / procedural** | `flutter/agent-plugins` (responsive layout, `go_router`, localization, `json_serialization`, `http`, widget/integration tests, widget previews, layered architecture, fix layout issues) · `dart-lang/skills` (unit tests, mocks, coverage, `dart analyze`, pattern matching, FFI, CLI, docs, pub conflicts, runtime errors) | — |
| **Tools** | official Dart & Flutter **MCP server** (analyzer diagnostics, symbol resolution, test runners, runtime inspection) | — (declared in this plugin's MCP config so install wires it) |
| **Orchestration** | — | size a task, sequence the official skills, route phases |
| **Architecture decisions** | `flutter-apply-architecture-best-practices` teaches the *pattern* | *choosing* state mgmt (Riverpod/Bloc/signals/setState), module boundaries, ADRs |
| **Review judgment** | `flutter-fix-layout-issues` fixes overflow; `dart-run-static-analysis` runs the linter | rebuild scope, `const`, keys, `dispose`, `BuildContext` after `await`, list/image perf, `RepaintBoundary`, a11y semantics, golden coverage, ADR conformance |
| **Test strategy** | skills for *writing* each test type | *what* to test at which layer + coverage gates |
| **Performance** | — | DevTools timeline, jank hunting, profile mode, shader jank, `--trace-startup` |
| **Release engineering** | — | flavors, `--dart-define-from-file`, signing, `flutter build` matrix, store metadata, OTA (Shorebird) decision |
| **Upgrade / migration** | `dart fix`, `dart-resolve-package-conflicts` | project-scale SDK upgrade sweep, deprecation triage, dependency major bumps |

Every agent prompt says the same thing: **for any "how", invoke the official
`flutter-*` / `dart-*` skill; this plugin only decides, sequences, and reviews.**

---

## 3. Directory Tree

```
plugins/senior-dev-flutter/
├── .claude-plugin/plugin.json   # Claude Code manifest
├── plugin.json                  # Antigravity manifest (same content)
├── README.md
├── .mcp.json                    # Claude Code: dart mcp-server (type: stdio)
├── mcp_config.json              # Antigravity: dart mcp-server
├── hooks.json                   # "hooks" key (Claude Code) + "senior-dev-flutter-gates" group (Antigravity)
├── hooks/
│   ├── flutter-pre-tool-gate.js # PreToolUse: block `flutter build appbundle/ipa` and `pub upgrade --major-versions` on main/master/develop
│   └── flutter-stop-gate.js     # Stop: require `dart analyze` clean before finishing (skips if not a Flutter repo / no dart)
├── agents/
│   ├── flutter-feature-orchestrator.md   # mainAgent — sizes + routes; delegates every "how" to official skills
│   ├── flutter-architect.md              # state-mgmt choice, module boundaries, ADRs
│   ├── flutter-implementer.md            # TDD; invokes official flutter-*/dart-* skills; also drives perf fixes
│   ├── flutter-reviewer.md               # the review checklist + dart analyze + ADR conformance
│   └── flutter-release-engineer.md       # flavors, signing, build matrix, versioning, OTA, SDK/dep upgrades
└── skills/                       # physical copy of the 7 root flutter-* skills
```

---

## 4. Bundled Skills (7 Packaged Modules)

| Skill | Role (all *decision / checklist / strategy* — none restate a "how-to") |
| :--- | :--- |
| **`flutter-senior-orchestration`** | The phase map the orchestrator follows: task sizing, phase sequence, which official skill each mechanic goes to. |
| **`flutter-architecture-decisions`** | State-management decision matrix (Riverpod/Bloc/signals/setState), module-boundary checklist, Flutter ADR template. |
| **`flutter-review-checklist`** | Senior Flutter review checklist + `flutter_project_audit.py` (file-only project audit). |
| **`flutter-test-strategy`** | What to test at unit vs widget vs golden vs integration level; coverage gates; routes to the official test-writing skills. |
| **`flutter-performance-profiling`** | Diagnose jank/slow startup with DevTools, profile mode, UI/raster split, shader jank; fix by symptom. |
| **`flutter-release-engineering`** | Flavors + `--dart-define-from-file`, signing, `flutter build` matrix, versioning, store metadata, OTA decision. |
| **`flutter-upgrade-migration`** | Ordered SDK-upgrade sweep, deprecation triage, dependency major bumps — around `dart fix` / `dart-resolve-package-conflicts`. |

---

## 5. The Agents

Five host-neutral subagents (`model: inherit`, explicit `subagent`/`mainAgent`,
no `tools` key — load in both Claude Code and Antigravity):

| Agent | Role |
| :--- | :--- |
| **`flutter-feature-orchestrator`** (`mainAgent`) | Sizes a Flutter task and routes phases. Delegates every "how" to an official skill. `commandExecutionPolicy: off`. |
| **`flutter-architect`** | Chooses state management, draws module boundaries, records ADRs. |
| **`flutter-implementer`** | TDD implementation via the official `flutter-*` / `dart-*` skills; also drives `flutter-performance-profiling`. |
| **`flutter-reviewer`** | Runs the tool baseline, walks `flutter-review-checklist`, checks ADR conformance. |
| **`flutter-release-engineer`** | Config, signing, build matrix, versioning, OTA, and SDK/dependency upgrades. |

---

## 6. Hooks

| Event | Hook | Behavior |
| :--- | :--- | :--- |
| `PreToolUse` (`Bash` / `run_command`) | `flutter-pre-tool-gate.js` | On `main` / `master` / `develop`, **denies** `flutter build appbundle\|aab\|ipa` (store artifacts belong in CI) and `(flutter\|dart) pub upgrade --major-versions` (needs a branch + ADR). Silent on any other command, non-git, or non-Flutter repo. |
| `Stop` | `flutter-stop-gate.js` | If the repo is a Flutter project and `dart` is on PATH, runs `dart analyze`; a failure blocks finishing (Claude Code: exit 2; Antigravity: `{"decision":"continue"}`) with the analyzer output and a reminder to run `flutter test`. No-op otherwise. |

Host is detected via `CLAUDE_PLUGIN_ROOT`; each hook emits the decision shape the
host expects.

---

## 7. Example Prompts

- "Use the flutter-feature-orchestrator agent to build a profile-edit feature end to end."
- "Have the flutter-architect agent choose state management for this app and write the ADR."
- "Ask the flutter-reviewer agent to review this PR for rebuild scope, leaks, and accessibility."
- "This list janks on Android — have flutter-implementer profile and fix it."
- "Get flutter-release-engineer to set up dev/staging/prod flavors and a signed build matrix."

---

## 8. Installation

**Claude Code** — project-scoped (no copy):
```bash
claude --plugin-dir ./plugins/senior-dev-flutter
```
**Claude Code** — global:
```bash
cp -r ./plugins/senior-dev-flutter ~/.claude/plugins/senior-dev-flutter
```

**Antigravity CLI** — global, via `agy`:
```bash
agy plugin install ./plugins/senior-dev-flutter
agy plugin list      # confirm
```

Then install the **required** official packs (see §1) and make sure `node` and
`dart` are on `PATH`.
