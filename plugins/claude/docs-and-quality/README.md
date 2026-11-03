# docs-and-quality

> Documentation standards, testing practices, Karpathy guidelines and an anti-lazy code gate for Claude Code.

[![License](https://img.shields.io/badge/license-Apache--2.0-blue?style=flat-square)](../../../LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude%20Code-orange?style=flat-square)](../../../docs/claude-code-installation.md)

`docs-and-quality` bundles three stack-agnostic skills: technical documentation, automated testing,
and behavioral guidelines that keep changes small and verifiable. A `Stop` hook scans added code lines
for placeholder stubs and keeps Claude working until they are replaced.

## Requirements

- Claude Code with plugin support.
- `node` on `PATH` (the hook is a Node.js script).
- `git` (the hook reads `git diff HEAD`). Python 3 to run the skill validator scripts.

## Installation

```bash
claude plugin marketplace add jggomez/expert-ai-developer-skills
claude plugin install docs-and-quality@expert-ai-developer-skills
```

Updates, project scope and local development: [docs/claude-code-installation.md](../../../docs/claude-code-installation.md).

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
| `Stop` | `hooks/anti-lazy-code-gate.js` | Scans lines added in `git diff HEAD` and blocks the stop when a placeholder stub is found. |

Patterns the gate rejects in added lines:

| Pattern | Example |
| :--- | :--- |
| TODO deferral | `TODO: implement later`, `TODO: finish later`, `TODO: add later` |
| Elided code | `// ... rest of code`, `# ... rest of the code` |
| Placeholder `pass` | `pass  # placeholder` |
| Unimplemented marker | `// unimplemented`, `/* unimplemented */`, `# unimplemented` |

## How it works

1. On `Stop`, the gate (30 s timeout) fingerprints the changed code files (HEAD plus file contents).
2. It does nothing when no code file changed, or when the same code state already passed.
3. Added lines in `.md`, `.txt`, `.rst`, `.json`, `.yaml` and `.yml` files are never scanned.
4. On a match it exits 2 and lists each `file: "line"` on stderr, so Claude keeps working.
5. It blocks at most 3 times per turn, then lets the turn end with a notice.

## Troubleshooting

| Symptom | Cause | Fix |
| :--- | :--- | :--- |
| `[ANTI-LAZY CODE GATE VIOLATION]` | An added code line matches a stub pattern. | Replace the stub with a full implementation. |
| Notice "still failing after 3 fix attempts" | Gate hit its per-turn limit. | Fix the listed lines, then start a new turn. |
| A stub in a new file was not caught | Untracked files are not part of `git diff HEAD`. | Stage the file (`git add <file>`) so the gate sees it. |
| Gate never runs | Folder is not a git repository, or `node` is missing. | Run inside a git repo with Node.js installed. |

## Related plugins

- [senior-dev](../senior-dev/README.md): orchestrated SDLC that relies on these standards.
- [git-workflow](../git-workflow/README.md): branch safety and Conventional Commits gates.
- [multi-agent-ops](../multi-agent-ops/README.md): parallel loops and context guard.

## License

Apache-2.0. See [LICENSE](../../../LICENSE).
