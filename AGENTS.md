# AGENTS.md - Universal AI Coding Agent Constitution & Instructions

> **Target Audience**: All AI Coding Agents operating within this repository, including Google Antigravity, Anthropic Claude Code, Cursor, Codex, Gemini CLI, and related autonomous coding engines.
>
> **Authority**: This document serves as the supreme operational constitution and governance framework. All agents must comply with the rules, boundaries, and lifecycles defined herein without exception.

---

## 1. Inviolable Core Principles

### 1.1. Plan-First Mandatory Gate
* **No Unplanned Code Changes**: Before any application code modification, refactoring, or implementation begins, an up-to-date `PLAN.md` file **MUST** be authored or updated and committed/saved to disk in the repository root.
* **Granular Task Breakdown**: The plan must detail exact tracks, phases, actionable verification criteria, and affected components.
* **Lifecycle Synchronization**: As milestones progress, agents must keep `PLAN.md` strictly synchronized with the true system state.

### 1.2. Orchestrator Role Boundary
* **Technical Director & Coordinator**: Orchestrator agents (e.g., `senior-dev-orchestrator`, `flutter-feature-orchestrator`) are coordinators and systems directors.
* **Strict Non-Execution Constraint**: Orchestrators are **STRICTLY PROHIBITED** from directly editing application code, libraries, or tests (`src/`, `lib/`, `tests/`, etc.).
* **Tool Permissions**: File editing and writing tools (`write_to_file`, `replace_file_content`, `Write`, `Edit`) in an orchestrator session are reserved **exclusively** for governance and design artifacts: `PLAN.md`, architectural decision records (`ADR-*.md`), `.agents/` rules, and markdown documentation in `docs/`.
* **Mandatory Delegation**: All code generation, feature construction, bug fixes, refactoring, and test modifications **MUST** be delegated to specialized worker subagents (`code-implementer`, `flutter-implementer`, `qa-tester`).

### 1.3. Graph Engineering State Machine (DAG)
All multi-agent execution flows follow a deterministic Directed Acyclic Graph (DAG) state machine:

```mermaid
flowchart TD
    GATE["[PLAN FIRST GATE]<br/>PLAN.md created/updated"] --> DISCOVERY["[DISCOVERY (Optional)]<br/>product-analyst | architect-engineer"]
    DISCOVERY --> BUILD["[BUILD (Mandatory)]<br/>code-implementer | flutter-implementer"]
    GATE --> BUILD
    BUILD --> TEST["[TEST (Mandatory)]<br/>qa-tester (exit code 0 proof)"]
    TEST -->|Fail: Red State| BUILD
    TEST -->|Pass: Green State| AUDIT["[AUDIT (Mandatory)]<br/>compliance-verifier (APPROVED verdict)"]
    AUDIT -->|Reject: Gap Found| BUILD
    AUDIT -->|Pass: Approved| SHIP["[SHIP]<br/>git commit & finish"]
```

#### State Transition Definitions:
1. **PLAN FIRST GATE**: Assess goals, write/update `PLAN.md`, verify scope and dependencies.
2. **DISCOVERY (Optional)**: Engage `product-analyst` for ambiguity or formal PRDs; engage `architect-engineer` for system architecture, ADRs, or database schemas.
3. **BUILD (Mandatory)**: Execute code changes via `code-implementer` or `flutter-implementer`. No shortcuts.
4. **TEST (Mandatory)**: Verify implementation via `qa-tester`. Test execution must yield verified exit code 0 (`pytest`, `flutter test`, `node --check`).
5. **AUDIT (Mandatory)**: Subject changes to `compliance-verifier`. Requires explicit `APPROVED` verdict against all repository invariants.
6. **SHIP**: Finalize git staging, commit using Conventional Commits, clean temporary artifacts.

### 1.4. Test-Driven Development (TDD)
* **Red-Green-Refactor Cycle**:
  1. **Red**: Write a failing test capturing the requirement or defect before writing production code. Confirm expected failure.
  2. **Green**: Implement the minimal, clean solution necessary to turn the test green.
  3. **Refactor**: Clean up and optimize while ensuring all tests continue to pass.
* **Tests are Empirical Proof**: Never claim a task is completed, fixed, or verified without actual test output showing `exit code 0`.
* **Arrange-Act-Assert (AAA)**: Tests must follow explicit Arrange, Act, Assert structure with isolated mocks at network/database/external API boundaries.
* **Zero Assertion Tampering**: Never delete assertions, alter tests to mask bugs, relax threshold rules, or return hardcoded stub values to fake passing test suites.

### 1.5. Anti-Lazy Code Policy
* **Zero Tolerance for Placeholders**: Absolute prohibition against AI shortcuts, lazy stubs, partial implementations, or omitted logic:
  - ❌ `// TODO: Implement later`
  - ❌ `# ... rest of existing code ...`
  - ❌ `pass  # placeholder`
  - ❌ Empty catch/except blocks swallowing exceptions (`except Exception: pass`).
* **Production Completeness**: Every file modified or created must contain full, production-ready code with exhaustive error handling, input validation, type annotations, and clean logging.
* **Keep Existing Intact**: Do not overwrite or delete existing working code, comments, or docstrings unless explicitly tasked with refactoring them.

### 1.6. Git Hygiene & Branch Safety
* **Branch Protection**: **NEVER** commit or push directly to `main`, `master`, or `develop`. All development occurs in dedicated feature or bugfix branches (`feature/*`, `bugfix/*`).
* **Conventional Commits**: Every commit message must strictly follow the Conventional Commits specification:
  - Format: `<type>(<optional-scope>): <description>`
  - Types: `feat:`, `fix:`, `refactor:`, `test:`, `docs:`, `chore:`, `perf:`, `build:`, `ci:`.
  - Imperative mood, lowercase description, no trailing period.
* **Merge Conflicts**: Never leave conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) or unresolved merge states (`UU`, `AA`) in any branch.
* **Atomic Commits**: Stage files selectively (`git add <file>`); never run blanket `git add .` on dirty workspaces.

---

## 2. Dual Ecosystem Architecture

This repository is built as an open multi-agent framework supporting two premier AI agent platforms simultaneously: **Google Antigravity** and **Anthropic Claude Code**.

```
repository-root/
├── plugins/
│   ├── antigravity/                  # Antigravity Plugin Ecosystem
│   │   ├── docs-and-quality/
│   │   ├── git-workflow/
│   │   ├── multi-agent-ops/
│   │   ├── python-backend/
│   │   ├── senior-data-engineer/
│   │   ├── senior-dev/
│   │   ├── senior-dev-flutter/
│   │   ├── shared-context/
│   │   └── sql-query-optimizer/
│   └── claude/                       # Claude Code Plugin Ecosystem
│       ├── docs-and-quality/
│       ├── git-workflow/
│       ├── multi-agent-ops/
│       ├── python-backend/
│       ├── senior-data-engineer/
│       ├── senior-dev/
│       ├── senior-dev-flutter/
│       ├── shared-context/
│       └── sql-query-optimizer/
├── skills/                           # Canonical Skills Catalog (35 Skills)
├── .agents/                          # Shared Agent Rules & Workflows
│   ├── rules/                        # Living repo context & loop engineering
│   └── workflows/                    # Operational task workflows
└── scripts/                          # Synchronization & validation automation
```

### 2.1. Tool Boundaries & Strict Isolation
Each ecosystem uses its native tool definitions. Tools **MUST NOT** bleed across ecosystem boundaries.

| Attribute | Google Antigravity Ecosystem (`plugins/antigravity/`) | Anthropic Claude Code Ecosystem (`plugins/claude/`) |
| :--- | :--- | :--- |
| **Native Execution Tools** | `run_command`, `call_mcp_tool` | `Bash` |
| **File Operation Tools** | `write_to_file`, `replace_file_content`, `view_file` | `Read`, `Write`, `Edit`, `Glob`, `Grep` |
| **Agent Delegation** | `invoke_subagent`, `manage_subagents`, `send_message` | `Agent` |
| **Plugin Manifest** | `plugin.json` (root of plugin) | `.claude-plugin/plugin.json` |
| **Lifecycle Hooks** | `hooks.json` supporting stdin/stdout JSON protocol | `hooks.json` supporting Claude Hook event payloads |
| **Tool Bleed Policy** | Zero Claude tools (`Bash`, `Agent`) inside Antigravity agent definitions | Zero Antigravity tools (`run_command`, `invoke_subagent`) inside Claude agent frontmatters |

### 2.2. Dual Host Hook Compatibility
Hook scripts in `hooks/*.js` are engineered to serve both hosts seamlessly:
* Detect Antigravity execution via tool naming conventions (`run_command`, `write_to_file`) and stdout `{ "decision": "allow" | "deny" }`.
* Detect Claude Code execution via `CLAUDE_PLUGIN_ROOT` or tool naming (`Bash`, `Write`) and structured `{ "hookSpecificOutput": { "permissionDecision": "allow" | "deny" | "ask" } }` responses.

---

## 3. Specialized Subagent Matrix & Roles

| Agent Name | Category | Primary Focus & Domain | Toolset Class |
| :--- | :--- | :--- | :--- |
| `senior-dev-orchestrator` | Orchestrator | Technical direction, task decomposition, pipeline management | Orchestrator Tools (`PLAN.md`, docs only) |
| `flutter-feature-orchestrator` | Orchestrator | Flutter mobile/web pipeline coordination, architecture reviews | Orchestrator Tools (`PLAN.md`, docs only) |
| `product-analyst` | Discovery | Requirements gathering, edge-case identification, PRD drafting | Worker Tools |
| `architect-engineer` | Discovery | High-level system design, database schemas, ADR authoring | Worker Tools |
| `flutter-architect` | Discovery | Flutter state management, widget hierarchy, layer boundaries | Worker Tools |
| `code-implementer` | Implementation | Production code authoring, bug fixes, refactoring in Python/Node/SQL | Full Worker Tools |
| `flutter-implementer` | Implementation | Flutter widgets, BLoC/Riverpod, Dart models, platform channels | Full Worker Tools |
| `qa-tester` | Verification | TDD execution, unit tests, integration tests, empirical proof | Full Worker Tools |
| `flutter-reviewer` | Verification | Flutter code quality, widget rebuild profiling, linting | Full Worker Tools |
| `compliance-verifier` | Audit | Architectural invariant verification, safety audit, final signoff | Read-Only Audit Tools |
| `senior-data-engineer` | Specialist | GCP Lakehouse, BigQuery, Datastream, CDC/SCD pipelines | Worker Tools + MCP |
| `sql-query-optimizer` | Specialist | SQL execution plans, index recommendations, query tuning | Worker Tools |
| `context-keeper` | Operations | Capturing and restoring cross-session architectural context | Worker Tools |
| `flutter-release-engineer` | Operations | Store bundles, signing configs, CI/CD pipeline deployment | Worker Tools |

---

## 4. Essential Runbooks & Tooling Commands

### 4.1. Python Test Suite Execution
Execute the test suite to verify plugins, skills, and governance contracts:
```bash
# Run all unit, integration, and structural tests
pytest tests/

# Run fast unit tests only
pytest tests/unit/

# Run structural consistency tests
pytest tests/structure/

# Run with verbose output and failure stop
pytest -v -x tests/
```

### 4.2. Hook Syntax & Safety Validation
Verify syntax and integrity of all Node.js lifecycle hooks across both plugin ecosystems:
```bash
# Check syntax for all hook scripts in Antigravity plugins
for hook in plugins/antigravity/*/hooks/*.js; do
  node --check "$hook" || exit 1
done

# Check syntax for all hook scripts in Claude Code plugins
for hook in plugins/claude/*/hooks/*.js; do
  node --check "$hook" || exit 1
done
```

### 4.3. JSON Manifest & Configuration Validation
Verify validity of all JSON configs, manifests, and hooks:
```bash
# Validate all JSON files across plugins and repository configs
node -e '
const fs = require("fs");
const files = [
  ".claude-plugin/marketplace.json",
  ...require("child_process").execSync("find plugins -name \"*.json\"").toString().trim().split("\n")
];
for (const file of files) {
  if (!file) continue;
  try {
    JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (err) {
    console.error(`Invalid JSON in ${file}:`, err.message);
    process.exit(1);
  }
}
console.log("All JSON configurations are valid!");
'
```

### 4.4. Skill Synchronization Automation
Synchronize canonical skills from `/skills` into each plugin's bundled copy:
```bash
python3 scripts/sync_plugin_skills.py
```

### 4.5. Claude Code Plugin & Agent Synchronization
Synchronize agents, hooks, and manifests between Antigravity and Claude Code ecosystems:
```bash
python3 scripts/sync_agents.py
```

---

## 5. Summary Compliance Rule for All Agents

> **Any AI agent modifying code without an active `PLAN.md`, any orchestrator attempting direct file edits on `src/` or `lib/`, or any implementation without test proof (`exit code 0`) is in direct violation of repository governance and must immediately halt and delegate.**
