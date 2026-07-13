# Rule: Skills Catalog & Model Context Protocol (MCP) Awareness

**Identifier**: `skills-and-mcp-awareness`  
**Purpose**: Force active discovery, usage, and preservation of local Skills and MCP servers in all agent tasks, preventing redundant code generation and leveraging deterministic system tools.

---

## 1. Core Mandate

**AI agents must always prioritize using existing filesystem-based Skills and active Model Context Protocol (MCP) servers over generating custom ad-hoc code or executing raw shell commands.**

If a task requires database queries, deployment checks, linting, git commits, or security auditing, the agent must check if a specialized Skill or MCP tool exists to handle that process.

---

## 2. Skills Usage Workflow

Whenever a new task is received, follow this discovery protocol:

1. **Scan the Skills Catalog**: List the contents of the `skills/` directory. Read the `README.md` or the `SKILL.md` of any skill that appears relevant to your objective.
2. **Import or Reference Instructions**: If a skill matches the concern (e.g. `test-driven-development`, `security-audit`, `commit-expert`), the agent must follow its step-by-step guides and execute its pre-configured utility scripts.
3. **Keep Filesystem-Based Skills Intact**: Do not overwrite or modify existing skills without explicit instruction. Enhance or update them strictly under the rules of the Open Agent Skills Standard (`agentskills.io`).

---

## 3. MCP Tool Awareness & Prioritization

The workspace contains specialized, lazy-loaded MCP servers. Agents must leverage their tools to perform operations securely and efficiently:

### Active Servers & Capabilities:
* **`bigquery`**: Use for database exploration, table schemas, and running read-only SQL queries instead of writing raw database connection scripts.
* **`chrome-devtools`**: Use for executing UI screenshots, audits, network tracking, and client-side testing.
* **`cloudrun`**: Use for projects and service listings, Cloud Run deployments, log inspection, and configuration reviews.
* **`firebase-mcp-server`**: Use for Firestore operations (queries, updates), auth checks, functions logs, hosting, and remote configs.

---

## 4. Anti-Pattern Prevention (Rules of Substitution)

To avoid token bloat and project clutter, adhere to these substitutions:

| Instead of writing custom logic for... | Use this standard tool... |
| :--- | :--- |
| **Running security audits / scanning secrets** | Run the script in `skills/security-audit/` or execute its scanning utilities. |
| **Drafting branch names or commit messages** | Check `skills/commit-expert/` and use conventional commits formatting. |
| **Querying Firestore databases** | Call the `firestore_query_collection` tool from `firebase-mcp-server`. |
| **Interacting with Google Cloud resources** | Use the `cloudrun` or `bigquery` MCP servers. |
| **Writing custom AST parsers / linter runners** | Use `skills/build-and-ci-gates/` or `skills/code-smells-expert/`. |

---

## 5. Checklist for Session Start

On every user prompt, check:
- [ ] What skills are registered in the `skills/` directory?
- [ ] Are any MCP tools available that can execute database, cloud, or browser actions for this task?
- [ ] Am I writing redundant python scripts or bash commands when a tool/skill already provides this capability?
