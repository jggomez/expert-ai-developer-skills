---
trigger: always_on
description: Senior developer invariants for every coding task - branch safety, scope discipline, plan-first, test proof, fail-honest reporting and no secrets. The SDLC workflow itself lives in the senior-dev-orchestrator agent.
---

# Senior Dev Rules

- **Workflow lives in the agent**: the tiered SDLC (triage, discovery, parallel build, review, memory) applies only when you run as `senior-dev-orchestrator`; follow that agent and the `loop-engineering` skill. Otherwise just do the task well, with no ceremony.
- **Git Branch Governance**: never edit or commit on `main`, `master`, `develop` or `dev`; create `feat/<slug>` or `fix/<slug>` first. **Scope Drift**: if a request is unrelated to the current feature branch, ask (`ask_question`) whether to open a new branch.
- **Scope discipline**: build exactly what was asked. Project rules and `AGENTS.md` constrain *how*, never *what*; list extra ideas as suggestions instead of implementing them.
- **Plan first**: multi-file code changes need a plan in `docs/<feature-name>/PLAN.md` (`<= 50 lines`), next to the feature's `spec.md`, ADRs and evidence; small surgical edits do not. Never leave a `PLAN.md` in the repository root.
- **Orchestrators never edit code**: they write only `docs/<feature-name>/PLAN.md`, `AGENTS.md`, `DESIGN.md`, ADRs, `docs/`, `.agents/` and `context/memory/`, and delegate code to implementers.
- **Proof, not claims**: "done" means a test command with exit code `0`. Never weaken or delete assertions to get green.
- **Fail-honest**: when a check cannot run (no server, browser, credentials), report `BLOCKED` or `SKIPPED` with the exact reason; never report it as passed.
- **No secrets** in code, logs, commits or memory files.
