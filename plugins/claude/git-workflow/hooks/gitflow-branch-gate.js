#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');

const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);

function allow() {
  if (!isClaudeCode) {
    console.log(JSON.stringify({ decision: 'allow' }));
  }
  process.exit(0);
}

// Read input payload from stdin
let inputData = '';
try {
  inputData = fs.readFileSync(0, 'utf-8');
} catch (e) {
  allow();
}

if (!inputData.trim()) {
  allow();
}

let payload;
try {
  payload = JSON.parse(inputData);
} catch (e) {
  allow();
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
    // Antigravity's PreToolUse contract (verified against
    // antigravity.google/docs/hooks): a top-level {"decision": ...}.
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

// Gitflow Branch Safety Gate (never commit/push directly on main or develop)
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
allow();
