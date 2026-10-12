#!/usr/bin/env node
/**
 * Python Backend PreToolUse gate.
 * 1. Plan-First Gate: Requires PLAN.md before creating or editing Python backend code (*.py).
 * 2. Deployment Guardrail: Requires explicit user approval for deployment commands.
 * 3. MCP Guardrail: Requires explicit user approval for Cloud Run deploy or Firestore mutations.
 * 4. Gitflow Safety: Blocks commits directly on main or develop.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);

function allow() {
  if (!isClaudeCode) {
    console.log(JSON.stringify({ decision: 'allow' }));
  }
  process.exit(0);
}

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

let inputData = '';
try {
  inputData = fs.readFileSync(0, 'utf-8');
} catch (e) {
  allow();
}
if (!inputData.trim()) allow();

let payload;
try {
  payload = JSON.parse(inputData);
} catch (e) {
  allow();
}

const toolCall = payload.toolCall || {};
const toolName = toolCall.name || payload.tool_name || '';
const toolInput = toolCall.args || payload.tool_input || {};
const commandLine = toolInput.command || toolInput.CommandLine || '';
const cwd = payload.cwd || toolInput.Cwd || payload.workspacePaths?.[0] || process.cwd();

// 1. GATE: Plan-First before creating/modifying Python code
const isFileModTool = /^(write_to_file|replace_file_content|Write|Edit)$/i.test(toolName);
if (isFileModTool) {
  const targetFile = toolInput.TargetFile || toolInput.file_path || toolInput.path || '';
  const basename = path.basename(targetFile);
  const ext = path.extname(targetFile).toLowerCase();

  const isDoc =
    /^PLAN(\.[\w-]+)?\.md$/i.test(basename) ||
    targetFile.includes('/docs/') ||
    targetFile.includes('/context/memory/') ||
    targetFile.includes('/context/') ||
    targetFile.includes('/.agents/') ||
    ext === '.md' ||
    ext === '.txt';

  if (!isDoc && ext === '.py') {
    const hasPlan =
      fs.existsSync(path.join(cwd, 'PLAN.md')) ||
      fs.existsSync(path.join(cwd, 'docs', 'PLAN.md'));

    if (!hasPlan) {
      deny(
        `[PYTHON BACKEND GRAPH GATE - PLAN FIRST]: No "PLAN.md" found in "${cwd}".\n` +
        `You MUST create a "PLAN.md" defining API routes, schemas, and migrations before writing Python backend code.`
      );
    }
  }
}

// 2. GATE: Deployment Guardrail
const isShellTool = toolName === 'Bash' || toolName === 'run_command';
const deployRegex = /\b(deploy|apply\s+-f|firebase\s+deploy|gcloud\s+run\s+deploy)\b/i;
if (isShellTool && deployRegex.test(commandLine)) {
  ask(`Deployment command detected: "${commandLine}". Deployment operations require explicit user approval.`);
}

// 3. GATE: MCP Guardrail
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

// 4. GATE: Gitflow Branch Safety Gate
const gitWriteRegex = /\b(git\s+commit|git\s+push|git\s+add|git\s+merge)\b/i;
if (isShellTool && gitWriteRegex.test(commandLine)) {
  try {
    const activeBranch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8' }).trim();
    if (activeBranch === 'main' || activeBranch === 'develop') {
      deny(`Gitflow Safety Blocked: directly running git add/commit/push/merge on "${activeBranch}" is prohibited. Use a feature/ or bugfix/ branch and merge via Pull Request.`);
    }
  } catch (e) {
    // Not a git repository
  }
}

allow();
