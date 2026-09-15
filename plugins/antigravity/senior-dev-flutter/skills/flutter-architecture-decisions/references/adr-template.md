# ADR template (Flutter)

One file per decision: `doc/adr/NNNN-short-title.md`. Keep it under a page.
Never delete a superseded ADR — add a new one and link them.

```markdown
# NNNN. <short decision title>

- **Status**: proposed | accepted | superseded by [NNNN](NNNN-....md)
- **Date**: YYYY-MM-DD
- **Deciders**: <names / roles>

## Context

<The forces at play: app size, team, async/data complexity, deadlines,
existing code. 3–6 sentences. State the actual constraints, not adjectives.>

## Decision

<What we will do, in one or two sentences. Name the package/version and the
scope it applies to.>

## Alternatives considered

- **<option>** — rejected because <concrete reason tied to the context above>.
- **<option>** — rejected because ...

## Consequences

- <What gets easier.>
- <What gets harder / what we now have to maintain.>
- <Migration cost if we ever reverse this.>

## Compliance

<How `flutter-reviewer` checks a PR against this: e.g. "no `Bloc` in new
`lib/src/**` outside `legacy/`", "repositories are the only place with `dio`".>
```

## Numbering

Zero-padded, monotonic: `0001`, `0002`, … Do not reuse numbers. If a decision
reverses an earlier one, the new ADR's Status links back and the old ADR's
Status becomes `superseded by`.
