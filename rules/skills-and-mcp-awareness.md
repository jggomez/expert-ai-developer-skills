---
trigger: model_decision
description: Rules for discovering, registering, and integrating local skills and Model Context Protocol (MCP) servers.
---

# Rule: Skills Catalog & MCP Tool Awareness

**Identifier**: `skills-and-mcp-awareness`

## 1. Core Tooling Directive

**MUST** prioritize existing filesystem Skills and Model Context Protocol (MCP) servers over generating custom ad-hoc scripts or raw shell commands.

## 2. Discovery & Execution Protocol

1. **Scan Catalog**: **MUST** inspect the available skills list before starting non-trivial tasks.
2. **Load Instructions**: **MUST** view `SKILL.md` via `view_file` before executing skill-related work.
3. **Use Utility Scripts**: **MUST** execute helper scripts within skill packages (`skills/<name>/scripts/`).
4. **Preserve Standards**: **MUST NOT** overwrite skill instructions without explicit user approval.

## 3. Mandatory Substitutions (Anti-Reinvention)

| Task Domain | Mandatory Tool / Skill |
| :--- | :--- |
| **Database Queries** | **MUST** call a configured MCP server (e.g. `firebase-mcp-server`) instead of writing raw DB clients, when one is registered for the project. |
| **Cloud Infrastructure**| **MUST** leverage `cloudrun` MCP tools for Cloud Run service management, when registered. |
| **Security Audits** | **MUST** execute utilities from `skills/security-audit/`. |
| **Git / Commits** | **MUST** adhere to `skills/commit-expert/` conventional commit rules. |

Check `plugins/*/mcp_config.json` for which MCP servers are actually registered before assuming one is available.
