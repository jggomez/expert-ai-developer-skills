# AI Developer Rules Directory

This directory contains token-optimized, highly concise project rules (`rules/*.md`) designed to govern AI Coding Agents (Google Antigravity, Claude Code, Cursor, etc.) and human developers.

All rules enforce **RFC 2119 directives** (`MUST`, `MUST NOT`, `NEVER`, `ALWAYS`) with explicit negative anti-hallucination constraints to prevent common LLM pitfalls.

---

## 1. Rules Catalog Index

| Rule File | Identifier | Core Focus |
| :--- | :--- | :--- |
| [**clean-code-and-principles.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/clean-code-and-principles.md) | `clean-code-and-principles` | SOLID, DRY, KISS, YAGNI, and anti-hallucination quality rules. |
| [**context-and-token-optimization.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/context-and-token-optimization.md) | `context-and-token-optimization` | Context budgeting, file line bounds, deterministic local script offloading. |
| [**conventional-commits.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/conventional-commits.md) | `conventional-commits` | Branch safety, protected branches, Conventional Commits 1.0.0. |
| [**deployment-restrictions.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/deployment-restrictions.md) | `deployment-restrictions` | Protected deployment CLI commands, pre-deploy quality gates. |
| [**documentation-and-diagrams.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/documentation-and-diagrams.md) | `documentation-and-diagrams` | Signature sync, non-obvious "why" comments, clean Mermaid syntax. |
| [**loop-engineering-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/loop-engineering-workflow.md) | `loop-engineering-workflow` | 9-stage engineering execution cycle (/spec to /ship) with dynamic orchestrator sizing and subagent delegation. |
| [**pull-requests.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/pull-requests.md) | `pull-requests` | PR size limit (<200 lines), mandatory agent self-audit checklist. |
| [**secure-coding-and-secrets.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/secure-coding-and-secrets.md) | `secure-coding-and-secrets` | Credential exclusions, OWASP Top 10 injection & auth rules. |
| [**skills-and-mcp-awareness.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/skills-and-mcp-awareness.md) | `skills-and-mcp-awareness` | Mandatory skill/MCP tool prioritization over custom scripts. |
| [**tdd-best-practices.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/tdd-best-practices.md) | `tdd-best-practices` | TDD Red-Green-Refactor, AAA pattern, anti-tampering rules. |
| [**testing-after-changes.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/testing-after-changes.md) | `testing-after-changes` | Empirical runtime verification, zero victory without `exit code 0`. |

---

## 2. Integration & Activation Policies

- **Google Antigravity**: Rules load automatically from workspace `.agents/rules/` or referenced via `@rules/<name>.md`. All rules preserve YAML frontmatter (`trigger: model_decision`).
- **Cursor**: Concatenate or select rules in Cursor Settings: `cat rules/*.md > .cursorrules`.
- **Claude Code**: Add rule paths or contents into `.claudecodesettings` under `customInstructions`.

---

## 3. Example Prompts That Trigger Each Rule

Rules apply passively (`trigger: model_decision`) — you don't invoke them directly, but the ordinary tasks below are exactly what makes each one kick in:

- "Refactor this class — it's grown pretty large." → `clean-code-and-principles` (SOLID/DRY/KISS checks apply)
- "Summarize this 2000-line log file." → `context-and-token-optimization` (should offload to a script instead of reading it all)
- "Commit and push this fix." → `conventional-commits` (format + branch safety enforced)
- "Deploy this service to production." → `deployment-restrictions` (pre-deploy gates required first)
- "Add a new API endpoint." → `documentation-and-diagrams` (docstrings/README/diagrams must stay in sync)
- "Build this feature — it touches three independent modules." → `loop-engineering-workflow` (cycle scaled to the task size)
- "Open a pull request for this branch." → `pull-requests` (size limit + self-audit checklist)
- "Add a login form that stores user credentials." → `secure-coding-and-secrets` (OWASP + secrets rules apply)
- "Query this data — is there a skill or MCP server for that already?" → `skills-and-mcp-awareness`
- "Implement the new pricing calculation." → `tdd-best-practices` (Red-Green-Refactor expected)
- "This bug is fixed now." → `testing-after-changes` (must show a passing test run before declaring it done)
