# AI Developer Rules Directory

This directory contains token-optimized, highly concise project rules (`rules/*.md`) designed to govern AI Coding Agents (Google Antigravity, Claude Code, Cursor, etc.) and human developers.

All rules enforce **RFC 2119 directives** (`MUST`, `MUST NOT`, `NEVER`, `ALWAYS`) with explicit negative anti-hallucination constraints to prevent common LLM pitfalls.

---

## 1. Rules Catalog Index

| Rule File | Identifier | Core Focus |
| :--- | :--- | :--- |
| [**clean-code-and-principles.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/clean-code-and-principles.md) | `clean-code-and-principles` | SOLID, DRY, KISS, YAGNI, and anti-hallucination quality rules. |
| [**context-and-token-optimization.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/context-and-token-optimization.md) | `context-and-token-optimization` | Context budgeting, file line bounds, deterministic RTK script offloading. |
| [**conventional-commits.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/conventional-commits.md) | `conventional-commits` | Branch safety, protected branches, Conventional Commits 1.0.0. |
| [**deployment-restrictions.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/deployment-restrictions.md) | `deployment-restrictions` | Protected deployment CLI commands, pre-deploy quality gates. |
| [**documentation-and-diagrams.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/documentation-and-diagrams.md) | `documentation-and-diagrams` | Signature sync, non-obvious "why" comments, clean Mermaid syntax. |
| [**loop-engineering-workflow.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/loop-engineering-workflow.md) | `loop-engineering-workflow` | Mandatory 7-stage cycle, subagent delegation, manager quality gates. |
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
