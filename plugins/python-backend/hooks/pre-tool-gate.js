#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');

// Read input payload from stdin
let inputData = '';
try {
  inputData = fs.readFileSync(0, 'utf-8');
} catch (e) {
  process.exit(0);
}

if (!inputData.trim()) {
  process.exit(0);
}

let payload;
try {
  payload = JSON.parse(inputData);
} catch (e) {
  process.exit(0);
}

// Claude Code sets CLAUDE_PLUGIN_ROOT when running plugin hooks; Antigravity
// does not, so anything else falls back to Antigravity's real PreToolUse
// contract: a top-level {"decision": "allow"|"deny"|"ask", "reason": ...}
// (verified against antigravity.google/docs/hooks — this is NOT the same
// shape as Claude Code's hookSpecificOutput.permissionDecision).
const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);

function ask(reason) {
  if (isClaudeCode) {
    console.log(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'ask',
        permissionDecisionReason: reason,
      },
    }));
  } else {
    console.log(JSON.stringify({ decision: 'ask', reason }));
  }
  process.exit(0);
}

function deny(reason) {
  if (isClaudeCode) {
    console.log(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: reason,
      },
    }));
  } else {
    console.log(JSON.stringify({ decision: 'deny', reason }));
  }
  process.exit(0);
}

// Normalize across Claude Code (tool_name/tool_input/cwd) and Antigravity
// (toolCall.name/toolCall.args) payload shapes.
const toolName = payload.tool_name || payload.toolCall?.name || '';
const toolInput = payload.tool_input || payload.toolCall?.args || {};
const commandLine = toolInput.command || toolInput.CommandLine || '';
const cwd = payload.cwd || toolInput.Cwd || payload.workspacePaths?.[0] || process.cwd();

const isShellTool = toolName === 'Bash' || toolName === 'run_command';

// 1. Deployment Guardrail (never deploy without explicit user approval)
const deployRegex = /\b(deploy|apply\s+-f|firebase\s+deploy|gcloud\s+run\s+deploy)\b/i;
if (isShellTool && deployRegex.test(commandLine)) {
  ask(`Deployment command detected: "${commandLine}". Deployment operations require explicit user approval.`);
}

// 2. MCP Tools Guardrail (Cloud Run & Firebase writes)
// Claude Code names MCP tools "mcp__<server>__<tool>"; Antigravity uses a
// dedicated call_mcp_tool wrapper with ServerName/ToolName fields.
let mcpServer = '';
let mcpTool = '';
if (toolName.startsWith('mcp__')) {
  const parts = toolName.split('__');
  mcpServer = parts[1] || '';
  mcpTool = parts.slice(2).join('__');
} else if (toolName === 'call_mcp_tool') {
  mcpServer = toolInput.ServerName || '';
  mcpTool = toolInput.ToolName || '';
}

if (mcpServer === 'cloudrun' && /^deploy_/.test(mcpTool)) {
  ask(`Cloud Run deployment via MCP detected: "${mcpTool}". Deployment operations require explicit user approval.`);
}

const firestoreWriteRegex = /(add|update|delete|set|create_database)/i;
if (mcpServer === 'firebase-mcp-server' && firestoreWriteRegex.test(mcpTool)) {
  ask(`Firestore mutation via MCP detected: "${mcpTool}". Data modification operations require explicit user approval.`);
}

// 3. Gitflow Branch Safety Gate (never commit/push directly on main or develop)
const gitWriteRegex = /\b(git\s+commit|git\s+push|git\s+add|git\s+merge)\b/i;
if (isShellTool && gitWriteRegex.test(commandLine)) {
  try {
    const activeBranch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8' }).trim();
    if (activeBranch === 'main' || activeBranch === 'develop') {
      deny(`Gitflow Safety Blocked: directly running git add/commit/push/merge on "${activeBranch}" is prohibited. Use a feature/ or bugfix/ branch and merge via Pull Request.`);
    }
  } catch (e) {
    // Not a git repository, or the command failed — let it proceed.
  }
}

// Default: allow tool execution
process.exit(0);
