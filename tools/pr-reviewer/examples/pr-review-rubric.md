# Review criteria

Copy to `.github/pr-review-rubric.md`, edit it, merge it to your default branch, and set
`rubric-file: .github/pr-review-rubric.md`. This file replaces the default criteria. To add a few rules
instead, use the `instructions` input.

Findings must use one of these categories: **security**, **performance**, **scalability**, **design**,
**best_practice** or **cost**. Remove the ones you do not want.

## What to look for

**security**: authorization on every endpoint, and queries built only with bound parameters.

**performance**: N+1 queries and work inside request handlers that belongs in a job.

**scalability**: missing pagination, timeouts and limits.

**design**: business logic that depends directly on the framework or on a vendor SDK.

**best_practice**: swallowed exceptions, and money stored as floats.

**cost**: paid API calls in loops, and queries with no limit.

## Rules

- Report concrete problems in the changed code and explain the impact.
- Skip style and formatting.
- Return no findings when nothing matters.

## Severity

- **critical**: exploitable, or causes an outage or data loss.
- **high**: a likely vulnerability or a clear problem on a frequent path.
- **medium**: a real improvement with moderate impact.
- **low**: worthwhile but minor.
