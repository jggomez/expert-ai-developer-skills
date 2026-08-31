# Senior Dev Plugin

[![Repository](https://img.shields.io/badge/Repository-expert--ai--developer--skills-blue?style=flat-square&logo=github)](git@github.com:jggomez/expert-ai-developer-skills.git)
[![Plugin](https://img.shields.io/badge/Plugin-senior--dev-green?style=flat-square)](file:///./)

The `senior-dev` plugin packages the repository's Loop Engineering subagent topology — a Senior Developer Orchestrator plus five specialized subagents (Product Analyst, Architect, Code Implementer, QA Tester, Compliance Verifier) — as a self-contained Claude Code plugin. It bundles nothing new: every agent, skill, and MCP server here already exists in the root `agents/`, `skills/`, and `plugins/python-backend/.mcp.json` of this repository.

Its `plugin.json`/`agents/`/`.mcp.json`/`${CLAUDE_PLUGIN_ROOT}` layout follows the **Claude Code plugin format**. Claude Code auto-discovers each `.md` file under `agents/` as a subagent and each `SKILL.md` under `skills/` as a skill — no separate manifest entry is needed for either.

**Antigravity CLI users**: `agy plugin install ./plugins/senior-dev` works — the `agents/*.md` here use host-neutral frontmatter (`name` + `description`, `model: inherit`, explicit `subagent`/`mainAgent`/`commandExecutionPolicy`, and **no `tools` key** since its values differ per host). `subagent`/`mainAgent` are spelled out on every file because Antigravity does not fall back to their documented `true` defaults — omit them and the agent never registers. The separate root [`agents/`](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/agents) directory keeps the Antigravity-only variant that retains per-agent `model: pro`/`flash` cost tiering, for when you want that or a project-scoped install — see §6. Neither set declares a `tools` list; each host applies its own default.

> **Maintaining the bundled skills**: `skills/` below is a physical copy of the matching directories in the root `/skills` catalog, kept self-contained so the plugin folder can be distributed on its own. After editing any bundled skill under `/skills`, run `python3 scripts/sync_plugin_skills.py` from the repo root to re-sync this copy — don't hand-edit both. `tests/structure/test_plugin_structure.py::test_plugin_skills_match_root_skills` fails CI if the two ever drift.

---

## 1. Directory Tree & Architecture

```
plugins/senior-dev/
├── README.md               # This usage manual
├── plugin.json             # Required plugin metadata descriptor (Antigravity, plugin root)
├── .claude-plugin/
│   └── plugin.json         # Same metadata — Claude Code requires the manifest here, not at plugin root
├── .mcp.json               # MCP servers for Claude Code (GCP Cloud Run, Firebase) — reused from python-backend
├── mcp_config.json         # Same MCP servers, Antigravity's format (alongside .mcp.json for Claude Code)
├── agents/                 # 6 bundled subagents, auto-discovered by Claude Code
│   ├── senior-dev-orchestrator.md  # Main orchestrator; scales the pipeline to the task
│   ├── product-analyst.md          # Requirements & PRDs
│   ├── architect-engineer.md       # Architecture & QADs
│   ├── code-implementer.md         # TDD implementation
│   ├── qa-tester.md                # E2E / integration testing
│   └── compliance-verifier.md      # Final NFR / security audit
└── skills/                 # Physical copy of the 8 skills these agents depend on
    ├── senior-dev-orchestrator/
    ├── product-analyst/
    ├── senior-architect-engineering/
    ├── code-implementer/
    ├── code-smells-expert/
    ├── refactoring-code-expert/
    ├── qa-tester/
    └── compliance-verifier/
```

---

## 2. Subagent Panel

| Agent | Role | Model | Tools |
| :--- | :--- | :--- | :--- |
| `senior-dev-orchestrator` | Main orchestrator: scopes the request and delegates to the subagent(s) the task actually needs. | `sonnet` | Read, Write, Edit, Grep, Glob, TodoWrite, Agent, AskUserQuestion |
| `product-analyst` | Requirements engineer: clarifies ambiguities, drafts PRDs sized to the request. | `sonnet` | Read, Write, Edit, Grep, Glob, AskUserQuestion |
| `architect-engineer` | System designer: QADs, SEI tactics, ADRs — only as heavy as the change warrants. | `sonnet` | Read, Write, Edit, Grep, Glob, Bash, AskUserQuestion |
| `code-implementer` | TDD implementer: Red-Green-Refactor, no speculative abstractions. | `sonnet` | Read, Write, Edit, Grep, Glob, Bash |
| `qa-tester` | E2E/integration tester: test depth proportional to the change. | `haiku` | Read, Write, Edit, Grep, Glob, Bash |
| `compliance-verifier` | Release auditor: final `APPROVED`/`REJECTED` verdict. | `haiku` | Read, Grep, Glob, Bash |

**Scaled pipeline**: the orchestrator does not run all five subagents for every request — see each agent's system prompt for when it's skipped. This mirrors the same scaling rule already documented in the root `agents/README.md`.

**Cost split**: reasoning-heavy agents (orchestrator, architect, implementer) use `sonnet`; validation agents (QA, verifier) use the faster `haiku`.

---

## 3. Model Context Protocol (`.mcp.json` / `mcp_config.json`)

Reuses the exact two MCP servers already defined for `plugins/python-backend`, for both Claude Code (`.mcp.json`) and Antigravity (`mcp_config.json`):
- **`cloudrun`**: list/inspect Cloud Run services and deployments.
- **`firebase-mcp-server`**: query and mutate Firestore collections.

These are available to any subagent whose `tools` include MCP access; none of the six agents require them by default, but the orchestrator or architect may call them when a task touches deployed infrastructure.

---

## 4. Bundled Skills (8 Packaged Modules)

On loading the plugin, the following 8 skills are automatically loaded as the agents' skill dependencies:

1. **`senior-dev-orchestrator`**: Phase breakdown and routing logic for the orchestrator.
2. **`product-analyst`**: Requirement discovery workflow and PRD template.
3. **`senior-architect-engineering`**: SEI quality attribute scenarios, tactics, ATAM, ADR template.
4. **`code-implementer`**: Red-Green-Refactor TDD workflow.
5. **`code-smells-expert`**: AST-based code smell detection.
6. **`refactoring-code-expert`**: Safe, test-guarded refactoring steps.
7. **`qa-tester`**: E2E/integration test-plan construction and RTM template.
8. **`compliance-verifier`**: Final NFR/security/coverage audit and verdict format.

---

## 5. Example Prompts

**Full pipeline, via the orchestrator** (it decides how much of the pipeline the task actually needs):
- "Use the senior-dev-orchestrator agent to build a password-reset feature end to end — requirements, design, implementation, tests, and a final audit."
- "Orchestrate a fix for this bug report — keep it lightweight, this doesn't need a full design phase."

**Individual subagents, invoked directly**:
- "Ask the product-analyst agent to turn this feature request into a PRD." (`product-analyst`)
- "Have the architect-engineer agent draft an ADR comparing sync vs. async processing for this endpoint." (`architect-engineer`)
- "Use the code-implementer agent to build the new endpoint with TDD." (`code-implementer`)
- "Have the qa-tester agent write E2E tests for the checkout flow and map them to requirements." (`qa-tester`)
- "Ask the compliance-verifier agent for a release-readiness verdict on this branch." (`compliance-verifier`)

---

## 6. Installation

**Claude Code** — global, copy the plugin folder (or install via the plugin marketplace if this repository is registered as one):
```bash
cp -r ./plugins/senior-dev ~/.claude/plugins/senior-dev
```
**Claude Code** — project-scoped, no install/copy:
```bash
claude --plugin-dir ./plugins/senior-dev
```
Once installed, invoke `senior-dev-orchestrator` (or any of the five subagents directly) via the `Agent` tool the same way you would any other subagent.

**Antigravity CLI** — global, via `agy` (installs the agents *and* the MCP servers):
```bash
agy plugin install ./plugins/senior-dev
agy plugin list      # confirm
```
**Antigravity CLI** — project-scoped, if you don't want a global plugin install, copy the two pieces by hand:
```bash
# 1. Agents — the host-neutral files in this plugin folder work as-is, or use the
#    richer Antigravity-only copies at the repo root:
mkdir -p .agents/agents/          # project-scoped; use ~/.gemini/config/agents/ for global
cp agents/senior-dev-orchestrator.md agents/product-analyst.md agents/architect-engineer.md \
   agents/code-implementer.md agents/qa-tester.md agents/compliance-verifier.md \
   .agents/agents/

# 2. MCP servers — merge this plugin's mcp_config.json manually:
cat plugins/senior-dev/mcp_config.json   # merge its "mcpServers" into .agents/mcp_config.json
                                          # (global: ~/.gemini/config/mcp_config.json)
```
