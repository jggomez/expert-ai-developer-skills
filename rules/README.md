# AI Developer Rules Directory

Welcome to the **Developer Rules Catalog**. This directory contains generic, highly optimized project rules (`.rules`) designed to govern AI Coding Agents (such as Antigravity/AGY, Claude Code, Cursor, Copilot, etc.) and human developers.

Unlike **Skills** (which are actionable tools and procedural instructions), **Rules** are behavioral constraints, compliance gates, and architectural guidelines that must be adhered to at all times during the development lifecycle.

---

## 1. Directory Structure & Sitemap

These rules are modularized by concern. You can use them individually or compile them into your agent's configuration:

* [**README.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/README.md): This index and configuration guide.
* [**testing-after-changes.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/testing-after-changes.md): Enforcement rule requiring thorough testing after code generation, feature additions, or modifications.
* [**conventional-commits.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/conventional-commits.md): Rules for structured, semantic commit messages and automatic branch safety guidelines.
* [**clean-code-and-principles.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/clean-code-and-principles.md): Comprehensive guidelines for SOLID, DRY, and KISS principles, preventing technical debt and code smells.
* [**deployment-restrictions.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/deployment-restrictions.md): Production protection rules preventing unauthorized or accidental builds and deployments.
* [**skills-and-mcp-awareness.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/skills-and-mcp-awareness.md): Rules governing the discovery, registration, and active integration of local Skills and MCP servers.
* [**secure-coding-and-secrets.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/secure-coding-and-secrets.md): Rules for credentials protection, preventing leaked secrets, and adhering to OWASP security standards.
* [**context-and-token-optimization.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/context-and-token-optimization.md): Rule for minimizing prompt token bloat, managing session context efficiently, and working modularly.
* [**documentation-and-diagrams.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/documentation-and-diagrams.md): Rule for maintaining code comments, docstrings, README files, and Mermaid architecture diagrams.
* [**pull-requests.md**](file:///Users/jggomez/Documents/jggomez/code/skills-programming-ai/rules/pull-requests.md): Rule governing Pull Request quality, line-change guidelines, and agent self-review checklists.

---

## 2. How to Integrate Rules into AI Agents

You can import these rules into various AI development tools to shape the agent's behavior automatically.

### A. Cursor (`.cursorrules` or Cursor Settings)
To load these rules in **Cursor**, you can copy the contents of the relevant rules directly into a root-level `.cursorrules` file, or select them from Cursor's Settings under *Project Rules*. 
For example, to combine all rules, you can run a script or concatenate them:
```bash
cat rules/*.md > .cursorrules
```

### B. Claude Code (`.claudecodesettings` or Custom System Prompts)
To load these rules in **Claude Code**, add them as custom instructions. You can append the rule contents to the `customInstructions` field in your `.claudecodesettings` file:
```json
{
  "customInstructions": "Please adhere to the rules specified under the rules/ directory: 1. Always run tests after code changes (see rules/testing-after-changes.md). 2. Format commits semantically (see rules/conventional-commits.md)..."
}
```

### C. Google Antigravity & AGY Plugins
In **Antigravity (AGY)**, rules can be linked to Editor Execution Hooks (such as `PreToolUse` or `Stop`). For example, you can configure your plugin's `rules/` directory to inject these constraints into the model system prompt automatically on every session start.

---

## 3. Customizing the Rules

Each rule file is written in clear, concise Markdown. We recommend customizing the specific paths, commands, and language conventions inside each file to match your project's technology stack (e.g., swapping `pytest` for `jest`, or customizing deployment CLI commands).
