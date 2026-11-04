# pr-reviewer

A GitHub Action that comments on pull requests where the code can be more efficient, simpler and
cheaper to run. It only comments and never blocks a merge.

[Leer en español](README.es.md)

## What it reviews

| Axis | Examples |
| --- | --- |
| Efficiency | N+1 queries, I/O in loops, avoidable complexity, unbounded memory, blocking async code |
| Optimality | Duplicated logic, unnecessary abstractions, a poor data structure for the access pattern |
| Cost | Paid APIs in loops, `SELECT *` on billed warehouses, unbounded retries, oversized LLM prompts, verbose logs |

Style, naming, tests and security are out of scope. Every finding needs a line in the diff, an impact and
a confidence level, and a clean pull request gets a short "no problems found" summary.

## Install

1. Create a [Gemini API key](https://aistudio.google.com/apikey) on a project with billing enabled and save
   it as the `GEMINI_API_KEY` repository secret.
2. Copy [`examples/pr-review.yml`](examples/pr-review.yml) to `.github/workflows/pr-review.yml`.
3. Replace `<commit-sha>` with a full commit SHA of this repository, then open a pull request.

To run it again on a pull request, an owner, member or collaborator comments `/review`.

> [!WARNING]
> With the free Gemini API tier, Google may use your code to improve its products, and human reviewers may
> read it. Use a paid key or Vertex AI for anything private. See the
> [Gemini API terms](https://aistudio.google.com/docs/terms).

## Inputs

| Input | Default | Description |
| --- | --- | --- |
| `api-key` | | Gemini API key |
| `provider` | `antigravity` | `antigravity`, or `fake` to try the setup with no AI and no key |
| `model` | `gemini-3.8-flash` | Model to use |
| `max-tokens` | `200000` | Token budget for one review |
| `max-findings` | `10` | Maximum findings to publish |
| `min-severity` | `low` | Lowest severity to publish: `critical`, `high`, `medium` or `low` |
| `exclude` | | Extra path patterns to skip, separated by commas or new lines |
| `github-token` | `github.token` | Token that reads the pull request and posts comments. Keep the default: repeated runs recognize earlier comments by their bot author |

Lockfiles, generated code, build output and vendored code are skipped by default. Large diffs keep source
files first, and the summary lists every file that was not reviewed.

## Cost

Each review is limited by `max-tokens`, and the summary reports tokens and the estimated cost. As a rough,
unmeasured guide, a review of 40k input and 4k output tokens costs about $0.05 on `gemini-3.8-flash`.
Reviews run when a pull request is opened or marked ready, and on `/review`, not on every push.

## Limits

- Pull requests from forks and from Dependabot are skipped, because their runs have no access to secrets.
- If the AI fails, the summary says so and the job stays green.
- The SDK is at version 0.1.x, so the version is pinned and may need updating.

## Security

The author of a pull request controls the text the agent reads, so that text is treated as hostile.

- The agent has read-only tools: no shell, network, file writes or subagents.
- It reads a clean copy of the repository without `AGENTS.md`, `GEMINI.md`, `.agents/`, `.git` or symlinks.
- The review step holds only the AI key and the publish step holds only the GitHub token.
- Findings are validated against the diff, and secrets, mentions, images and HTML are removed before posting.
- Pin this Action to a commit SHA, as the example does.

## Architecture

The code follows clean architecture. Dependencies only point inwards, and
`tests/architecture` fails the build if that rule is broken.

```text
src/pr_reviewer/
├── domain/        Rules with no I/O: diff parsing, file selection, findings, triggers, pricing
├── application/   Use cases (prepare_diff, run_review, publish_review), ports, prompt, criteria
├── adapters/      Port implementations
│   ├── git/          Reads diffs
│   ├── github/       REST client, Markdown rendering, pull request gateway
│   ├── filesystem/   Builds the clean copy
│   └── providers/    Antigravity and fake review providers
└── entrypoints/   Command line and composition root
```

To add a provider, implement the `ReviewProvider` port in `adapters/providers/` and register it in
`entrypoints/composition.py`. Nothing else changes.

## Development

```bash
cd tools/pr-reviewer
uv sync --extra dev --extra antigravity
uv run pytest && uv run ruff check . && uv run mypy src
```

| Tests | Purpose | Needs |
| --- | --- | --- |
| `tests/unit` | Domain rules, use cases with in-memory ports, and Markdown rendering | Nothing |
| `tests/integration` | Adapters against git, the file system, a fake GitHub API and the real SDK classes | git, `antigravity` extra |
| `tests/action` | Security rules of `action.yml` and the workflows | Nothing |
| `tests/architecture` | Dependency rule between layers | Nothing |

None of them call a paid API. Shared test data is in `tests/support`.

Licensed under Apache-2.0.
