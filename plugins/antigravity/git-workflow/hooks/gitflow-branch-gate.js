#!/usr/bin/env node
/**
 * Gitflow Branch & Commit Safety Gate (PreToolUse)
 * 1. Blocks direct git add/commit/push/merge on protected branches (main, master, develop).
 * 2. Enforces Conventional Commits format on git commit messages.
 */
const { execSync } = require('child_process');
const fs = require('fs');

const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);

function allow() {
  if (!isClaudeCode) {
    console.log(JSON.stringify({ decision: 'allow' }));
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
const commandLine = toolInput.CommandLine || toolInput.command || '';
const cwd = payload.workspacePaths?.[0] || payload.cwd || toolInput.Cwd || process.cwd();

const isShellTool = toolName === 'run_command' || toolName === 'Bash';
if (!isShellTool || !commandLine) allow();

// 1. GATE: Gitflow Branch Safety Gate (never commit/push directly on main or develop)
const gitWriteRegex = /\b(git\s+commit|git\s+push|git\s+add|git\s+merge)\b/i;
if (gitWriteRegex.test(commandLine)) {
  try {
    const activeBranch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    if (activeBranch === 'main' || activeBranch === 'master' || activeBranch === 'develop') {
      deny(
        `Gitflow Safety Blocked: directly running git add/commit/push/merge on "${activeBranch}" is prohibited. Use a feature/ or bugfix/ branch and merge via Pull Request.`
      );
    }
  } catch (e) {
    // Not a git repository
  }
}

// 2. GATE: Conventional Commits Validation
const commitMsgMatch = commandLine.match(/\bgit\s+commit\b.*-m\s+["']([^"']+)["']/i);
if (commitMsgMatch) {
  const commitMsg = commitMsgMatch[1].trim();
  const conventionalRegex = /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\([a-zA-Z0-9_\-\.\/]+\))?!?: .+/;

  if (!conventionalRegex.test(commitMsg)) {
    deny(
      `[CONVENTIONAL COMMITS VIOLATION]: Commit message "${commitMsg}" does not follow Conventional Commits.\n` +
      `Format must be '<type>(<scope>): <subject>'.\n` +
      `Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.\n` +
      `Example: git commit -m "feat(auth): implement token refresh flow"`
    );
  }
}

allow();
