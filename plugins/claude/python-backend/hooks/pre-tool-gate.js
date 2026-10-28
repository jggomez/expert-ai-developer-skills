#!/usr/bin/env node
/**
 * python-backend PreToolUse gate for Claude Code.
 * 1. "Plan First" for Python code: If Write or Edit targets a .py file (app/, src/, tests/, or root),
 *    enforces that an active PLAN.md exists in the workspace.
 * 2. Deployment Guardrail: Prompts for explicit confirmation before running deployment commands.
 * 3. Gitflow Branch Safety: Denies committing or pushing directly to main/develop branches.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PROTECTED_BRANCHES = new Set(['main', 'master', 'develop', 'dev']);

function allow() {
  process.exit(0);
}

function ask(reason) {
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'ask',
      permissionDecisionReason: reason,
    },
  }));
  process.exit(0);
}

function deny(reason) {
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  }));
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

const toolName = payload.tool_name || '';
const toolInput = payload.tool_input || {};
const cwd = payload.cwd || (payload.workspacePaths && payload.workspacePaths[0]) || process.cwd();

// --- 1. Plan-First Enforcement for Write | Edit on Python files ---
const isFileModTool = /^(write_to_file|replace_file_content|Write|Edit)$/i.test(toolName);
if (isFileModTool) {
  const targetFile = toolInput.file_path || toolInput.path || toolInput.TargetFile || '';
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

  if (!isDoc && targetFile.endsWith('.py')) {
    let branch = '';
    try {
      branch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    } catch (e) {
      branch = '';
    }

    if (PROTECTED_BRANCHES.has(branch)) {
      deny(
        `[GIT BRANCH GOVERNANCE]: Prohibited from modifying Python source code (${basename}) directly on protected branch "${branch}".\n` +
        `You MUST create and switch to a dedicated feature branch first:\n` +
        `  Bash: git checkout -b feat/<descriptive-slug>\n` +
        `Always work on isolated branches with Conventional naming.`
      );
    }

    const possiblePlanPaths = [
      path.join(cwd, 'PLAN.md'),
      path.join(cwd, 'docs', 'PLAN.md'),
      path.join(cwd, '.agents', 'PLAN.md'),
      path.join(cwd, '.claude', 'PLAN.md')
    ];
    const hasPlan = possiblePlanPaths.some(p => fs.existsSync(p));

    if (!hasPlan) {
      deny(
        `[PLAN-FIRST VIOLATION]: Cannot modify Python code in "${targetFile}" without an active "PLAN.md".\n` +
        `Per Python Backend Architecture standards, you must create and structure a "PLAN.md" ` +
        `defining architecture, data schemas, API contracts, and subagent assignments before writing or modifying code.`
      );
    }
  }
}

// --- 2. Deployment Guardrail (Bash commands) ---
const commandLine = toolInput.command || '';
if (toolName === 'Bash' && commandLine) {
  const deployRegex = /\b(deploy|apply\s+-f|firebase\s+deploy|gcloud\s+run\s+deploy)\b/i;
  if (deployRegex.test(commandLine)) {
    ask(`Deployment command detected: "${commandLine}". Deployment operations require explicit user approval.`);
  }

  // --- 3. Gitflow Branch Safety Gate ---
  const gitWriteRegex = /\b(git\s+commit|git\s+push|git\s+add|git\s+merge)\b/i;
  if (gitWriteRegex.test(commandLine)) {
    try {
      const activeBranch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
      if (PROTECTED_BRANCHES.has(activeBranch)) {
        deny(`Gitflow Safety Blocked: directly running git add/commit/push/merge on "${activeBranch}" is prohibited. Use a feature/ or bugfix/ branch and merge via Pull Request.`);
      }
    } catch (e) {
      // Not a git repository or detached HEAD — proceed
    }
  }
}

// --- 4. MCP Tools Guardrail (Cloud Run & Firebase writes) ---
if (toolName.startsWith('mcp__cloudrun__') && /^deploy_/.test(toolName.replace('mcp__cloudrun__', ''))) {
  ask(`Cloud Run deployment via MCP detected: "${toolName}". Deployment operations require explicit user approval.`);
}

const firestoreWriteRegex = /(add|update|delete|set|create_database)/i;
if (toolName.startsWith('mcp__firebase-mcp-server__') && firestoreWriteRegex.test(toolName.replace('mcp__firebase-mcp-server__', ''))) {
  ask(`Firestore mutation via MCP detected: "${toolName}". Data modification operations require explicit user approval.`);
}

// Default: allow tool execution
allow();
