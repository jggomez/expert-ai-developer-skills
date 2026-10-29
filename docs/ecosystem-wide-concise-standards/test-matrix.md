# QA Test Matrix: ecosystem-wide-concise-standards

## 1. Execution Summary
- **Runner Command**: `pytest -v tests/` + `node --check` (`plugins/*/*/hooks/*.js`) + `python3 -c` JSON manifest parser
- **Results**: `156 passed, 2 skipped, 0 failed` (`pytest`); `36/36` JS hooks valid; `69/69` JSON manifests valid
- **Exit Code**: `0` (verified empirically across all three validation runners)
- **Date**: `2026-10-29`

## 2. Test Case Matrix

| ID | Ref | Level | Objective | Steps | Expected Result | Automated Test / Assertion | Status |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **TC-01** | `Track 29` / `AC-01` | `Unit` | Enforce Antigravity static subagent tool whitelist and forbid `call_mcp_tool` | 1. Parse YAML frontmatter across all Antigravity `agents/*.md` files. 2. Validate every `tools` entry against the static subagent registry whitelist. 3. Assert `call_mcp_tool` is absent from all subagent definitions. | Zero unwhitelisted tools or `call_mcp_tool` entries exist across all Antigravity subagents. | `tests/structure/test_plugin_structure.py::test_antigravity_subagents_strict_tool_registry_whitelist` | `PASS` |
| **TC-02** | `Track 29` / `AC-02` | `Unit` | Validate concise reference templates (`adr-template.md`, `sdd-template.md`, `project-context-template.md`) | 1. Load `flutter-architecture-decisions` `adr-template.md` (`<= 40`), `design-spec-expert` `sdd-template.md` (`<= 45`), and `repo-research` `project-context-template.md` (`<= 50`). 2. Count lines per template. 3. Assert required section tokens (`Decision & Justification`, `Acceptance Criteria`, `Stack`, `Commands`). | All three reference templates stay within strict line caps and include every required structural heading. | `tests/structure/test_plugin_structure.py::test_track29_ecosystem_wide_concise_standards_and_fail_honest_parity` | `PASS` |
| **TC-03** | `Track 29` / `AC-03` | `Integration` | Verify dual-ecosystem Fail-Honest `BLOCKED` and Google `DESIGN.md`/`AGENTS.md` parity across 8 plugins | 1. Verify `sync_plugin_skills.py` and `sync_agents.py` synchronization across Antigravity and Claude. 2. Inspect synced agents across `senior-data-engineer`, `sql-query-optimizer`, `senior-dev-flutter`, `shared-context`, and sibling plugins (`<= 100`/`125` lines). 3. Assert `BLOCKED`, `DESIGN.md`, and `AGENTS.md` tokens and zero cross-host tool bleed. | All 8 target plugins in both ecosystems satisfy line caps, Fail-Honest `BLOCKED` contracts, `DESIGN.md`/`AGENTS.md` references, and tool isolation. | `tests/structure/test_plugin_structure.py::test_track29_ecosystem_wide_concise_standards_and_fail_honest_parity` | `PASS` |
| **TC-04** | `Track 29` / `AC-04` | `Unit` | Enforce Antigravity `rules/*.md` conciseness caps (`<= 75` lines) and governance tokens | 1. Read `data-engineer-rules.md`, `sql-optimization-rules.md`, `multi-agent-ops-rules.md`, `docs-and-quality-rules.md`, `shared-context-rules.md`, and `gitflow-rules.md`. 2. Measure line count per rule file. 3. Assert required `BLOCKED`, `AGENTS.md`, `DESIGN.md`, and `test-matrix.md` tokens. | All 6 Antigravity rule files remain `<= 75` lines and preserve mandatory Fail-Honest and artifact governance contracts. | `tests/structure/test_plugin_structure.py::test_track29_ecosystem_wide_concise_standards_and_fail_honest_parity` | `PASS` |
| **TC-05** | `Track 29` / `AC-05` | `Integration` | Validate syntax integrity across all JS lifecycle hooks and JSON plugin manifests | 1. Execute `node --check` across every `plugins/*/*/hooks/*.js` script. 2. Parse `.claude-plugin/marketplace.json` and all `plugins/**/*.json` manifests (`plugin.json`, `hooks.json`, `.mcp.json`, `mcp_config.json`) via `python3 -c`. 3. Run behavioral hook contract tests. | `36/36` JS hook scripts and `69/69` JSON manifest files parse cleanly with `exit code 0` and pass dual-host hook contracts. | `tests/unit/test_plugin_hooks_contract.py` + `node --check` + `json.load` | `PASS` |
| **TC-06** | `Track 29` / `AC-06` | `E2E` | Verify optional telemetry add-on decoupling invariants across commits and working tree | 1. Scan all tracked and untracked non-ignored files outside the opt-in add-on allowlist (`DC-01`). 2. Verify exclusive skill bundling (`DC-02`) and commit/working-tree isolation across existing plugins (`DC-04`). 3. Confirm Track 29 artifacts introduce zero forbidden references. | Zero cross-plugin coupling or forbidden identifier leakage exists anywhere outside the isolated add-on paths (`exit code 0`). | `pytest -v tests/structure/ -k "dc01 or dc02 or dc04"` | `PASS` |

## Execution Proof
```text
$ pytest -v tests/
156 passed, 2 skipped in 47.97s (exit code 0)
$ for f in plugins/*/*/hooks/*.js; do node --check "$f" || exit 1; done
Validated hooks: 36 (exit code 0)
$ python3 -c '... json.load(.claude-plugin/marketplace.json + plugins/**/*.json) ...'
Validated JSON files: 69 (exit code 0)
```
