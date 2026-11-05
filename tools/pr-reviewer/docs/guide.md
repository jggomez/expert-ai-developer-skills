# pr-reviewer guide

Set up the reviewer in a repository, then change what it reviews.

## What you need

- A GitHub repository where you can add secrets and workflows.
- A [Gemini API key](https://aistudio.google.com/apikey) or an
  [Anthropic API key](https://platform.claude.com/settings/keys). You need neither to try the setup.

Nothing runs on your computer or on a server of yours. Reviews run on GitHub Actions runners.

## Set up with Gemini

1. **Save the key.** In your repository, open **Settings → Secrets and variables → Actions → Secrets** and add
   `GEMINI_API_KEY`.
2. **Add the workflow.** Copy [`examples/pr-review.yml`](../examples/pr-review.yml) to
   `.github/workflows/pr-review.yml`.
3. **Pin the version.** Get a commit SHA and replace `<commit-sha>` with it:

   ```bash
   git ls-remote https://github.com/jggomez/expert-ai-developer-skills refs/heads/main
   ```

4. **Merge the workflow to your default branch.** `/review` comments only work from there.
5. **Open a pull request.** After a few minutes it gets inline comments and a summary with the model, tokens
   and estimated cost.

To try the setup with no AI and no key, add `provider: fake` under `with:` for one run.

## Set up with Claude

Claude needs one extra step, once, because Managed Agents stores the agent in your Anthropic account. Nothing
stays running on your computer.

1. Create the agent, from a clone of this repository:

   ```bash
   cd tools/pr-reviewer
   uv sync --extra claude
   export ANTHROPIC_API_KEY=your_key
   uv run pr-reviewer setup-claude
   ```

2. Add the `ANTHROPIC_API_KEY` secret.
3. Add three repository variables: `CLAUDE_AGENT_ID` and `CLAUDE_ENVIRONMENT_ID` with the printed IDs, and
   `PR_REVIEW_PROVIDER` set to `claude`.

Delete `PR_REVIEW_PROVIDER` to go back to Gemini.

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
| `provider` | `PR_REVIEW_PROVIDER` | `antigravity` | `antigravity`, `claude` or `fake` |
| `model` | `PR_REVIEW_MODEL` | `gemini-3.8-flash` or `claude-opus-5-5` | Model to use |
| `max-tokens` | `PR_REVIEW_MAX_TOKENS` | `200000` | Token budget per review (Antigravity) |
| `budget-usd` | `PR_REVIEW_BUDGET_USD` | `1.00` | Spend limit per review (Claude) |
| `max-findings` | `PR_REVIEW_MAX_FINDINGS` | `10` | Most comments per review |
| `min-severity` | `PR_REVIEW_MIN_SEVERITY` | `low` | Lowest severity to publish |
| `exclude` | `PR_REVIEW_EXCLUDE` | | Extra path patterns to skip |
| `max-diff-chars` | `PR_REVIEW_MAX_DIFF_CHARS` | Built-in limit | Largest diff to review |
| `rubric-file` | `PR_REVIEW_RUBRIC_FILE` | | File that replaces the criteria |
| `instructions` | `PR_REVIEW_INSTRUCTIONS` | | Text added to the criteria |
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
| `HTTP 503` or `high demand` in the log | The Gemini model is overloaded. The reviewer retries twice | If it still fails, reopen the pull request later |
| "no structured output after 3 attempts" | Every attempt failed, probably for the same reason | Reopen the pull request later, or try another `model` |
| `/review` does nothing | The workflow is not on the default branch, or the author lacks permission | Merge the workflow. Only owners, members and collaborators can use it |
| A fork's pull request is skipped | Runs from forks have no access to secrets | This is expected |
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
