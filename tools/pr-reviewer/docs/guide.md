# pr-reviewer guide

Set up the reviewer in a repository, then change what it reviews.

## What you need

- A GitHub repository where you can add secrets and workflows.
- One of these: a [Gemini API key](https://aistudio.google.com/apikey), a Claude Pro or Max plan, or an
  [Anthropic API key](https://platform.claude.com/settings/keys).

Nothing runs on your computer or on a server of yours. Reviews run on GitHub Actions runners.

## Install

### 1. Add the workflow

From the root of your repository:

```bash
mkdir -p .github/workflows
SHA=$(git ls-remote https://github.com/jggomez/expert-ai-developer-skills refs/heads/main | cut -f1)
curl -fsSL https://raw.githubusercontent.com/jggomez/expert-ai-developer-skills/main/tools/pr-reviewer/examples/pr-review.yml \
  | sed "s/<commit-sha>/$SHA/" > .github/workflows/pr-review.yml
```

This copies [`examples/pr-review.yml`](../examples/pr-review.yml) and pins it to the latest commit of this
repository. To update later, run it again and read the changes first.

### 2. Connect a provider

Follow one option. Secrets and variables are in your repository, under
**Settings → Secrets and variables → Actions**, in the **Secrets** and **Variables** tabs.

| Option | Use it when | Secret | Variable `PR_REVIEW_PROVIDER` |
| --- | --- | --- | --- |
| [Gemini](#gemini) | You are starting out | `GEMINI_API_KEY` | None |
| [Claude Pro or Max plan](#claude-pro-or-max-plan) | The repository is yours and you have a plan | `CLAUDE_CODE_OAUTH_TOKEN` | `claude-code` |
| [Anthropic API key](#anthropic-api-key) | You are a team or have no plan | `ANTHROPIC_API_KEY` | `claude-code` |
| [Claude Managed Agents](#claude-managed-agents) | You want a hosted sandbox and a dollar limit | `ANTHROPIC_API_KEY` | `claude` |

#### Gemini

Create a [key](https://aistudio.google.com/apikey) and add it as the `GEMINI_API_KEY` secret.

#### Claude Pro or Max plan

Reviews use the official [Claude Code Action](https://code.claude.com/docs/en/github-actions) and count against
your plan limits.

1. Create a token on your computer:

   ```bash
   claude setup-token
   ```

2. Add it as the `CLAUDE_CODE_OAUTH_TOKEN` secret.
3. Add the variable `PR_REVIEW_PROVIDER` with the value `claude-code`.

The token belongs to the person who created it, so never share it or paste it in a file. Pull requests from anyone
on the repository use that person's limits. If several people work there, use an API key instead.

#### Anthropic API key

This also uses the Claude Code Action, and it pays per token.

1. Create a key in the [Claude Console](https://platform.claude.com) and add it as the `ANTHROPIC_API_KEY` secret.
2. Add the variable `PR_REVIEW_PROVIDER` with the value `claude-code`.
3. Do not add `CLAUDE_CODE_OAUTH_TOKEN`. If it exists, the token is used instead of the key.

This path has a limit of 20 turns but no dollar limit, so set a spend limit in the Console.

Both Claude Code options review in one pass, without groups, read the whole clean copy with read-only tools, and do
not show a cost. The GitHub token also reaches this step, because the official Action needs one.

#### Claude Managed Agents

This needs one extra step, once, because Managed Agents stores the agent in your Anthropic account. Nothing stays
running on your computer.

1. Create the agent, from a clone of this repository:

   ```bash
   cd tools/pr-reviewer
   uv sync --extra claude
   export ANTHROPIC_API_KEY=your_key
   uv run pr-reviewer setup-claude
   ```

2. Add the `ANTHROPIC_API_KEY` secret.
3. Add three variables: `CLAUDE_AGENT_ID` and `CLAUDE_ENVIRONMENT_ID` with the printed IDs, and
   `PR_REVIEW_PROVIDER` with the value `claude`.

To go back to Gemini, delete `PR_REVIEW_PROVIDER`.

### 3. Merge it and try it

1. Commit `.github/workflows/pr-review.yml` and merge it to your default branch. `/review` comments only work
   from there.
2. Open a pull request, or close and reopen one created after that merge.
3. Look at the results as described below.

## Use it day to day

**When it runs.** When a pull request is opened, reopened or marked ready for review. It does not run on every push.

**How to review again.** Write `/review` as a normal comment on the pull request. Only owners, members and
collaborators can use it. Comments from anyone else are ignored, so strangers cannot spend your budget.

**Where to see the results.**

- Inline comments appear in the **Files changed** tab.
- The summary appears in the **Conversation** tab, with the status and, when available, the model, tokens and cost.
- The run appears in the **Actions** tab, under **AI PR review**.

Running it again updates the summary and does not repeat comments that were already posted.

**Who pays.** The owner of the key or token saved in the repository, whoever opens the pull request.

**Whose pull requests are reviewed.** Those from branches of the same repository, by any author. Pull requests from
forks and from Dependabot are skipped, because GitHub gives those runs no access to secrets.

**A green job does not mean a clean review.** The job stays green even when the review fails, so it can never block
a merge. Read the summary.

## Change the settings

There are three ways to set a value. The first one found wins:

1. An input under `with:` in the workflow.
2. A `PR_REVIEW_*` environment variable in the workflow.
3. The default.

The example workflow connects several inputs to repository variables, so you can change them in
**Settings → Secrets and variables → Actions → Variables** without editing a file. Variables that do not exist
use the default. To set another input from a variable, add a line such as
`max-tokens: ${{ vars.PR_REVIEW_MAX_TOKENS }}`.

| Input | Environment variable | Default | Use |
| --- | --- | --- | --- |
| `api-key` | | | Gemini or Anthropic key, from a secret |
| `provider` | `PR_REVIEW_PROVIDER` | `antigravity` | `antigravity`, `claude` or `claude-code` |
| `model` | `PR_REVIEW_MODEL` | `gemini-3.6-flash` or `claude-opus-5-5` | Model to use |
| `max-shards` | `PR_REVIEW_MAX_SHARDS` | `4` | Most groups for a large pull request, reviewed in parallel |
| `fallback-model` | `PR_REVIEW_FALLBACK_MODEL` | `gemini-3.8-flash` | Model for the last attempt when the first one is overloaded (Antigravity) |
| `max-tokens` | `PR_REVIEW_MAX_TOKENS` | `200000` | Token budget per review (Antigravity) |
| `budget-usd` | `PR_REVIEW_BUDGET_USD` | `1.00` | Spend limit per review (Claude) |
| `max-findings` | `PR_REVIEW_MAX_FINDINGS` | `10` | Most comments per review |
| `min-severity` | `PR_REVIEW_MIN_SEVERITY` | `low` | Lowest severity to publish |
| `exclude` | `PR_REVIEW_EXCLUDE` | | Extra path patterns to skip |
| `max-diff-chars` | `PR_REVIEW_MAX_DIFF_CHARS` | Built-in limit | Largest diff to review |
| `rubric-file` | `PR_REVIEW_RUBRIC_FILE` | | File that replaces the criteria |
| `instructions` | `PR_REVIEW_INSTRUCTIONS` | | Text added to the criteria |
| `claude-code-oauth-token` | `CLAUDE_CODE_OAUTH_TOKEN` | | Token for `provider: claude-code` |
| `claude-agent-id` | `CLAUDE_AGENT_ID` | | From `setup-claude` |
| `claude-environment-id` | `CLAUDE_ENVIRONMENT_ID` | | From `setup-claude` |
| `github-token` | | `github.token` | Keep the default |

If you choose another model, the estimated cost in the summary may be wrong for Antigravity.

## Change the prompt

**Add rules** with `instructions`. This keeps the default criteria:

```yaml
instructions: |
  All money uses Decimal.
  Every endpoint under /admin needs the require_admin decorator.
```

**Replace the criteria** with your own file:

1. Copy [`examples/pr-review-rubric.md`](../examples/pr-review-rubric.md) to `.github/pr-review-rubric.md`.
2. Edit it and merge it to your default branch.
3. Set `rubric-file: .github/pr-review-rubric.md`.

Three rules apply:

- **The file is read from the base commit.** A pull request cannot change its own review, so a change to this
  file takes effect after merging it. Reviewing it in its own pull request still uses the old version.
- **Findings use six fixed categories:** `security`, `performance`, `scalability`, `design`, `best_practice`
  and `cost`. Comments, the output format and the diff check depend on them.
- **The safety rules cannot be removed.** The instruction to treat the code as untrusted data stays in place.

A missing file fails the review, and the summary says why. It does not fall back to the default criteria.
The rubric and the instructions are limited to 20,000 characters each.

## Troubleshooting

| What you see | What it means | What to do |
| --- | --- | --- |
| The job is green but there are no comments | The job stays green even when the review fails | Read the summary comment and the job log |
| `HTTP 503` or `high demand` in the log | The Gemini model is overloaded. The reviewer stops that attempt, retries, then uses `fallback-model` | Nothing, if the review finishes. The summary shows the model used |
| "No structured output after 3 attempts" | Every attempt failed, probably for the same reason | Reopen the pull request later, or choose another `model` or `fallback-model` |
| `/review` does nothing | The workflow is not on the default branch, or the author lacks permission | Merge the workflow. Only owners, members and collaborators can use it |
| A fork's pull request is skipped | Runs from forks have no access to secrets | This is expected |
| The review ignores your API key | `CLAUDE_CODE_OAUTH_TOKEN` exists and takes priority | Delete that secret |
| Claude reports an authentication error | The token or key expired, was revoked, or is not in the secret | Create a new one and update the secret |
| `does not exist in the base commit` | The rubric is not on the target branch yet | Merge the rubric first |

## Run it on your computer

Use this to try a change to the prompt without opening a pull request:

```bash
cd tools/pr-reviewer
uv sync --extra antigravity
export GEMINI_API_KEY=your_key
uv run pr-reviewer diff --repo ../.. --base main --head HEAD --output /tmp/bundle.json
uv run pr-reviewer review --provider antigravity --repo ../.. --bundle /tmp/bundle.json \
  --workspace /tmp/pr-review-ws --output /tmp/report.json
```

Run `rm -rf /tmp/pr-review-ws` between runs. The `PR_REVIEW_*` variables work here too. With `--rubric-file`, also
pass `--base` with a full commit SHA. The result is in `/tmp/report.json`: check `status` and `error`, because the
command exits with 0 even when the review fails.
