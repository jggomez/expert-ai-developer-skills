# Engineering Execution Plan: Antigravity & Claude Code Plugins

## Track 1: Antigravity Plugins Ecosystem Enhancement (COMPLETED)
- [x] Phase 1: `senior-dev-flutter` (Graph DAG, role boundaries, Plan-First pre-tool gate, `flutter-rules.md`).
- [x] Phase 2: `senior-data-engineer` (`hooks.json`, `data-safety-gate.js`, `data-quality-gate.js`, Lakehouse DAG).
- [x] Phase 3: `python-backend` (`python-backend-orchestrator.md`, `python-backend-rules.md`, Plan-First pre-tool gate).
- [x] Phase 4: `sql-query-optimizer` (`sql-optimization-rules.md`, `sql-safety-gate.js`, dry-run enforcement).
- [x] Phase 5: `git-workflow` (`gitflow-rules.md`, Conventional Commits, `git-clean-stop-gate.js`).
- [x] Phase 6: `docs-and-quality` (`docs-and-quality-rules.md`, Karpathy rules, `anti-lazy-code-gate.js`).
- [x] Phase 7: `multi-agent-ops` & `shared-context` (`context-guard-gate.js`, clean hooks schema).
- [x] Phase 8: Verification & Syntax Validation (`node --check`, `JSON.parse` across all plugins).

---

## Track 2: Claude Code Plugins Ecosystem Enhancement (COMPLETED)
- [x] Phase 1: Architecture & Flutter (`senior-dev-flutter`)
- [x] Phase 2: Python Backend (`python-backend`)
- [x] Phase 3: Data Engineering & SQL (`senior-data-engineer` & `sql-query-optimizer`)
- [x] Phase 4: Git Hygiene & Quality Gates (`git-workflow` & `docs-and-quality`)
- [x] Phase 5: Multi-Agent Coordination & Context (`multi-agent-ops` & `shared-context`)
- [x] Phase 6: Verification & Validation (`node --check`, `JSON.parse`, 48 empirical tests, `APPROVED` audit).

---

## Track 3: Unified Agent Governance & Living Repo Context (COMPLETED)
- [x] Phase 1: Universal `AGENTS.md` Constitution
- [x] Phase 2: Cross-Platform Symlinks (`CLAUDE.md`, `AGENT.md`)
- [x] Phase 3: Living Project Context (`.agents/rules/project-context.md`)
- [x] Phase 4: Empirical Testing (`qa-tester`, 91/91 tests pass)
- [x] Phase 5: Compliance Audit (`compliance-verifier`, `APPROVED`)

---

## Track 4: Skill Synchronization Automation (COMPLETED)
- [x] Phase 1: Updated `scripts/sync_plugin_skills.py` for dual synchronization (`plugins/antigravity` & `plugins/claude`).
- [x] Phase 2: Propagated canonical `/skills` into all 18 plugins.

---

## Track 5: Workflows Modernization with Dual-Runner Support (COMPLETED)
- [x] Phase 1: Updated all 16 workflows with dual-runner delegation (`invoke_subagent` for Antigravity & `Agent` for Claude Code).
- [x] Phase 2: Explicitly codified Inviolable Role Boundaries in `build-workflow.md`, `plan-workflow.md`, etc.

---

## Track 6: Functional Enrichment of Core Skills (COMPLETED)
- [x] Phase 1: `loop-engineering`: Topologies (Manager-Worker, Sequential, Review Committee) and 3-loop cap.
- [x] Phase 2: `guidelines-karpathy`: Anti-Lazy Code policy and Anti-Premature Abstraction.
- [x] Phase 3: `test-driven-development`: Multi-language testing patterns (Python pytest, Flutter widget tests, Dataform assertions).
- [x] Phase 4: `commit-expert`: Conventional Commits standard aligned with lifecycle hooks.

---

## Track 7: All READMEs & Documentation Modernized (COMPLETED)
- [x] Root `README.md` updated with full dual ecosystem architecture, `AGENTS.md`, and 35 skills.
- [x] `skills/README.md` updated with sync runbooks.
- [x] All 18 plugin `README.md` files updated across `plugins/antigravity/` and `plugins/claude/`.

---

## Track 8: Global QA & Verification Suite (COMPLETED)
- [x] `pytest tests/structure/`: 36 passed (100%).
- [x] `pytest tests/unit/`: 55 passed (100%).
- [x] Total: 91 passed in full test suite (`exit code 0`).

---

## Track 9: Senior-Dev LLM Wiki Memory (`context/memory/`), Mandatory Discovery Triage & Parallel DAG Execution (COMPLETED)
- [x] Phase 1: LLM Wiki Memory Architecture in `context-capture` & `context-restore`.
- [x] Phase 2: Senior-Dev Orchestrator DAG Upgrade (Triage Gate + Parallel Fan-Out/Fan-In + Worktrees + Wiki Memory).
- [x] Phase 3: Synchronization & Automated Tests (`99 passed`, `APPROVED`).

---

## Track 10: Ecosystem-Wide Plugin Upgrade (`senior-dev-flutter`, `python-backend`, `senior-data-engineer`, `sql-query-optimizer`, `shared-context`, `multi-agent-ops`) (COMPLETED)

### Discovery & Architecture Triage
| Specialist Node | Triage Verdict | Justification |
| :--- | :--- | :--- |
| **`product-analyst`** | `COMPLETED IN /plan` | User confirmed full scope across all 5 plugin groups and confirmed silent automatic `context/memory/MEMORY.md` loading without 25-tool-call mid-turn autosave nagging. |
| **`architect-engineer`** | `COMPLETED IN /plan` | Designed Track 10A (`senior-dev-flutter` & `python-backend`) and Track 10B (`senior-data-engineer`, `sql-query-optimizer`, `shared-context`, `multi-agent-ops`) with Mode A Disjoint File Partitioning followed by Fan-In dual-ecosystem synchronization. |

### Parallel Execution Tracks
| Track | Subagent | Isolation Mode | Owned Files |
| :--- | :--- | :--- | :--- |
| **Track 10A** | `code-implementer` #1 | Mode A (`Disjoint Files`, `inherit`) | `skills/flutter-senior-orchestration/SKILL.md`, `plugins/antigravity/senior-dev-flutter/**`, `plugins/antigravity/python-backend/**` |
| **Track 10B** | `code-implementer` #2 | Mode A (`Disjoint Files`, `inherit`) | `plugins/antigravity/senior-data-engineer/**`, `plugins/antigravity/sql-query-optimizer/**`, `plugins/antigravity/shared-context/hooks/*.js`, `plugins/antigravity/multi-agent-ops/rules/multi-agent-ops-rules.md` |
| **Track 10C (Fan-In)** | `code-implementer` | Sequential Fan-In | `scripts/sync_plugin_skills.py`, `scripts/sync_agents.py`, `plugins/claude/**`, `tests/**` |

### Phase Checklist
- [x] **Phase 1 (Track 10A)**: Upgrade `senior-dev-flutter` (`flutter-feature-orchestrator.md`, `skills/flutter-senior-orchestration/SKILL.md`, `flutter-rules.md`, `flutter-pre-tool-gate.js`, `README.md`) and `python-backend` (`python-backend-rules.md`, `pre-tool-gate.js`, `README.md`) with `context/memory/` LLM Wiki, Mandatory Triage Gates, and Parallel Fan-Out/Fan-In (`Disjoint Files` vs `Git Worktree`).
- [x] **Phase 2 (Track 10B)**: Upgrade `senior-data-engineer`, `sql-query-optimizer`, `shared-context/hooks/*.js` (silent `context/memory/MEMORY.md` support + zero 25-call mid-turn nagging when `MEMORY.md` is active), and `multi-agent-ops/rules/multi-agent-ops-rules.md`.
- [x] **Phase 3 (Track 10C — Fan-In & Dual-Host Sync)**: Update `scripts/sync_plugin_skills.py` and `scripts/sync_agents.py`, synchronize all `plugins/antigravity/` and `plugins/claude/` plugins, and add automated unit & structural tests.
- [x] **Phase 4 (State 3 & 4 Parallel Verification)**: Run `qa-tester` (`pytest -v tests/` -> `103 passed`, `exit code 0`; `node --check` -> `34/34 passed`) and `compliance-verifier` (`APPROVED` audit) in parallel.
- [x] **Phase 5 (State 5 Ship, README Sync & Git Push)**: Update root `README.md`, `skills/README.md`, `shared-context/README.md`, and `multi-agent-ops/README.md`, update `context/memory/`, commit with Conventional Commits, and push to `origin feature/unified-agent-governance-and-plugins`.
