# docs-and-quality

> Documentation standards, testing practices, Karpathy guidelines and an anti-lazy code gate for Google Antigravity.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Antigravity-4285F4?style=flat-square)](.)

`docs-and-quality` bundles three stack-agnostic skills: technical documentation, automated testing,
and behavioral guidelines that keep changes small and verifiable. An always-on rule sets artifact
line caps. A `Stop` hook scans added lines for placeholder stubs and keeps the task open until they
are replaced.

## Requirements

- Google Antigravity with the `agy` CLI.
- `node` on `PATH` (the hook is a Node.js script).
- `git` (the hook reads `git diff -U0 HEAD`). Python 3 to run the skill validator scripts.

## Installation

```bash
agy plugin install ./plugins/antigravity/docs-and-quality
```

## Quick start

```text
Write a README for this service using the Diátaxis framework, with a Mermaid architecture diagram.
Write Gherkin scenarios for the password-reset flow, covering the expired-token case.
Before we add this abstraction, check it against the Karpathy guidelines.
```

## What's included

## Bundled Skills

| Skill | Purpose |
| :--- | :--- |
| **`documentation-expert`** | Concise docs, root `AGENTS.md`, `DESIGN.md` alignment, Diátaxis guides, Mermaid diagrams; `validate_docs.py` checks links and absolute path leaks. |
| **`testing-expert`** | Arrange-Act-Assert suites, hermetic tests, `TC-XX` test cases, Gherkin BDD; `validate_gherkin.py` checks `.feature` files. |
| **`guidelines-karpathy`** | Checklist against overcomplication: surgical changes, stated assumptions, verifiable success criteria. |

### Hooks

| Event | Script | Behavior |
| :--- | :--- | :--- |
| `Stop` | `hooks/anti-lazy-code-gate.js` | On a model stop, scans added lines in `git diff -U0 HEAD` and returns `continue` when a placeholder is found. |

Patterns the gate rejects in added lines:

| Pattern | Example |
| :--- | :--- |
| TODO deferral | `TODO: implement later`, `TODO: add later`, `TODO: to be implemented`, `TODO: placeholder` |
| Placeholder `pass` | `pass # placeholder`, `pass # todo`, `pass # implement` |
| Fill-in comment | `// your code here`, `// implement here`, `... # your code here` |
| Unimplemented error | `throw UnimplementedError()` |

### Rules

| File | Purpose |
| :--- | :--- |
| `rules/docs-and-quality-rules.md` | Always-on rule: artifact line caps, Fail-Honest reporting, Karpathy/DRY/KISS, anti-lazy policy, Mermaid safety. |

## How it works

1. The `Stop` hook (30 s timeout) runs only when `terminationReason` is `model_stop`.
2. It skips workspaces without a `.git` entry.
3. Every added line in the diff is checked, including documentation files and new untracked files (up to 200 files, 512 KB each).
4. It returns `{ "decision": "continue", "reason": ... }` with up to 5 offending lines, else `allow`. A clean result is cached until the code changes, and after 3 blocks per message it lets the agent stop.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `[ANTI-LAZY CODE GATE VIOLATION]` | An added line matches a placeholder pattern. | Replace the placeholder with a full implementation. |
| Gate fires on a Markdown example | The Antigravity gate scans all files, docs included. | Reword the example so it does not match the pattern. |
| A stub in a new file was not caught | Untracked files are not part of `git diff HEAD`. | Stage the file (`git add <file>`) so the gate sees it. |
| Gate never runs | No `.git` in the workspace root, or `node` is missing. | Run inside a git repository with Node.js installed. |

## Related plugins

- [senior-dev](../senior-dev/README.md): orchestrated SDLC that relies on these standards.
- [git-workflow](../git-workflow/README.md): branch safety and Conventional Commits gates.
- [multi-agent-ops](../multi-agent-ops/README.md): parallel loops and context guard.

## Maintenance

`skills/` is a copy of the root `/skills` catalog. After editing a skill there, run
`python3 scripts/sync_plugin_skills.py` from the repo root.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
