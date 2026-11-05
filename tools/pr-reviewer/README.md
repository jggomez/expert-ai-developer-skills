# pr-reviewer

A GitHub Action that reviews pull requests for security, performance, scalability, design, best
practices and cost. It only comments and never blocks a merge.

[Leer en español](README.es.md)

## What it reviews

| Axis | Examples |
| --- | --- |
| Security | OWASP Top 10 risks: broken access control, injection, XSS, SSRF, weak auth, exposed secrets |
| Performance | N+1 queries, I/O in loops, avoidable complexity, blocking async code |
| Scalability | Unbounded memory, missing pagination or timeouts, single-process state, race conditions |
| Design | SOLID problems and code smells with concrete harm, duplicated logic, unnecessary abstractions |
| Best practice | Swallowed errors, missing transactions, floats for money, breaking API changes |
| Cost | Paid APIs in loops, `SELECT *` on billed warehouses, unbounded retries, oversized LLM prompts, verbose logs |

Style, naming and missing tests are out of scope. Every finding needs a line in the diff, an impact and
a confidence level, and a clean pull request gets a short "no problems found" summary.

This is an AI review, not a security audit: it can miss vulnerabilities, so keep your scanners. On a public
repository its comments are public too, so handle a serious finding before the pull request is widely seen.

## Providers

| | Antigravity | Claude Managed Agents | Claude Code |
| --- | --- | --- | --- |
| Agent runs in | Your GitHub runner | A sandbox hosted by Anthropic, with no network | Your GitHub runner |
| Pays with | Gemini API key | Anthropic API key | Claude Pro or Max plan, or an API key |
| Agent can read | The whole repository (clean copy) | The diff and the changed files | The whole repository (clean copy) |
| Default model | `gemini-3.6-flash` | `claude-opus-5-5` | Claude Code default |
| Spend limit | Tokens, with `max-tokens` | Dollars, with `budget-usd` | 20 turns, and your plan limits |
| Cost in the summary | Estimated from list prices | Reported by the API, including session time | Not shown |
| Status | SDK 0.1.x | Beta API | Official Action |

## Install

1. Save a [Gemini API key](https://aistudio.google.com/apikey) as the `GEMINI_API_KEY` repository secret.
2. Copy [`examples/pr-review.yml`](examples/pr-review.yml) to `.github/workflows/pr-review.yml`.
3. Replace `<commit-sha>` with a full commit SHA of this repository, then open a pull request.

To run it again on a pull request, an owner, member or collaborator comments `/review`.

The **[guide](docs/guide.md)** covers each step, Claude, every setting, the prompt and troubleshooting.

> [!WARNING]
> With the free Gemini API tier, Google may use your code to improve its products, and human reviewers may
> read it. Use a paid key or Vertex AI for anything private. See the
> [Gemini API terms](https://aistudio.google.com/docs/terms).

## Inputs

Every input is optional except the key. Each one also accepts a `PR_REVIEW_*` variable, listed in the
[guide](docs/guide.md#change-the-settings), and the example workflow reads repository variables, so you can
change the model without editing a file.

| Input | Default | Description |
| --- | --- | --- |
| `api-key` | | Gemini or Anthropic API key |
| `provider` | `antigravity` | `antigravity`, `claude`, `claude-code`, or `fake` to try the setup with no AI and no key |
| `model` | Provider default | Model to use |
| `max-shards` | `4` | Most groups a large pull request is split into, reviewed in parallel |
| `fallback-model` | `gemini-3.8-flash` | Model for the last attempt when the first one is overloaded (Antigravity) |
| `max-tokens` | `200000` | Token budget per group of files (Antigravity) |
| `budget-usd` | `1.00` | Hard spend limit for the whole review (Claude) |
| `claude-code-oauth-token` | | Token from `claude setup-token`, to use a Claude plan with `provider: claude-code` |
| `claude-agent-id` | | Printed by `pr-reviewer setup-claude` |
| `claude-environment-id` | | Printed by `pr-reviewer setup-claude` |
| `max-findings` | `10` | Maximum findings to publish |
| `min-severity` | `low` | Lowest severity to publish: `critical`, `high`, `medium` or `low` |
| `exclude` | | Extra path patterns to skip, separated by commas or new lines |
| `max-diff-chars` | Built-in limit | Largest diff to review |
| `rubric-file` | | Markdown file that replaces the review criteria, read from the base commit. See [Change the prompt](docs/guide.md#change-the-prompt) |
| `instructions` | | Text added to the review criteria |
| `github-token` | `github.token` | Token that reads the pull request and posts comments. Keep the default: repeated runs recognize earlier comments by their bot author |

Lockfiles, generated code, build output and vendored code are skipped by default. Pull requests over 60,000 diff
characters are split into groups of neighboring files, reviewed in parallel, and the findings are merged. If a
group fails, the others are still published and the summary lists the files that were not reviewed.

## Cost

Each review is limited by `max-tokens`, and the summary reports tokens and the estimated cost. As a rough,
unmeasured guide, a review of 40k input and 4k output tokens costs about $0.05 on `gemini-3.6-flash`,
$0.12 on `claude-sonnet-5-5` and $0.24 on `claude-opus-5-5`, plus session time on Claude.
Reviews run when a pull request is opened or marked ready, and on `/review`, not on every push.

## Limits

- Pull requests from forks and from Dependabot are skipped, because their runs have no access to secrets.
- If the AI fails, the summary says so and the job stays green. If only part fails, the rest is published.
- Reviewing in groups costs more than one agent, because each group runs its own agent. A real multi-group
  review is the measure to trust, not the estimate above.
- The SDK is at version 0.1.x, so the version is pinned and may need updating.

## Security

The author of a pull request controls the text the agent reads, so that text is treated as hostile.

- The agent has read-only tools: no shell, network, file writes or subagents.
- It reads a clean copy of the repository without `AGENTS.md`, `GEMINI.md`, `.agents/`, `.git` or symlinks.
- With Claude, no repository is mounted, because a mounted repository loads its `.claude/skills` unreviewed.
- The review step holds only the AI key and the publish step holds only the GitHub token.
- Findings are validated against the diff, and secrets, mentions, images and HTML are removed before posting.
- A custom `rubric-file` is read from the base commit, so a pull request cannot rewrite its own review.
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
│   └── providers/    Antigravity, Claude and fake review providers
└── entrypoints/   Command line and composition root
```

To add a provider, implement the `ReviewProvider` port in `adapters/providers/` and register it in
`entrypoints/composition.py`. Nothing else changes.

## Development

```bash
cd tools/pr-reviewer
uv sync --extra dev --extra antigravity --extra claude
uv run pytest && uv run ruff check . && uv run mypy src
```

| Tests | Purpose | Needs |
| --- | --- | --- |
| `tests/unit` | Domain rules, use cases with in-memory ports, and Markdown rendering | Nothing |
| `tests/integration` | Adapters against git, the file system, a fake GitHub API and the real SDK classes | git, `antigravity` and `claude` extras |
| `tests/action` | Security rules of `action.yml` and the workflows | Nothing |
| `tests/architecture` | Dependency rule between layers | Nothing |

None of them call a paid API. Shared test data is in `tests/support`.

Licensed under Apache-2.0.
