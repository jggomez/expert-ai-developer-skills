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

// Normalize across Claude Code (tool_name/tool_input/cwd) and the legacy
// Antigravity/Gemini shape (toolCall.name/toolCall.args) some hosts still send.
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
process.exit(0);
