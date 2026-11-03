---
trigger: glob
globs: "**/*.py, **/pyproject.toml, **/requirements*.txt, **/alembic.ini, **/alembic/**"
description: Python backend constraints applied while editing Python code, dependencies or migrations - branch safety, TDD, static checks, zero-downtime migrations, deploy and secret guards.
---

# Python Backend Rules

- **Git Branch Governance**: never edit `.py` files or commit on `main`, `master`, `develop` or `dev`; create `feat/<slug>` first. **Scope Drift**: ask before mixing an unrelated request into the current branch.
- **TDD**: write the failing test first; "done" means `pytest <affected tests>` exit code `0`. Never weaken assertions to get green.
- **Static checks** before claiming done: `ruff check .`, `mypy .` and `bandit -r <package>` when the project uses them; report `BLOCKED` with the exact error when a tool is missing.
- **Migrations**: never change ORM models without an Alembic/Django migration; verify `alembic upgrade head && alembic downgrade -1 && alembic upgrade head` on an isolated database; use expand-contract for breaking changes. Only one migration head may exist at a time.
- **Boundaries**: keep domain logic framework-independent; validate input with Pydantic at the edges; never build SQL with string formatting.
- **Deploys**: never deploy or run production migrations without explicit user approval.
- **Secrets**: read them from the environment or a secret manager; never commit `.env` files or credentials.
- Documentation for a feature lives in `docs/<feature-name>/`.
