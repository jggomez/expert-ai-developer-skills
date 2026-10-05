#!/usr/bin/env node
/**
 * gitflow-branch-gate PreToolUse hook for Claude Code.
 * 1. Gitflow Branch Safety: Denies running git add/commit/push/merge directly on main or develop.
 * 2. Conventional Commits: Validates that git commit -m messages follow Conventional Commits format.
 */
const { execSync } = require('child_process');
const fs = require('fs');

function allow() {
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
const commandLine = toolInput.command || '';
const cwd = payload.cwd || (payload.workspacePaths && payload.workspacePaths[0]) || process.cwd();

if (toolName !== 'Bash' || !commandLine) {
  allow();
}

// --- 1. Conventional Commits Validation ---
const isCommitCommand = /\bgit\s+commit\b/i.test(commandLine);
if (isCommitCommand) {
  // Extract commit message
  let commitMessage = null;
  const quotedMatch = /(?:-m\s+|--message=|-m["']|--message\s+)["']([^"']+)["']/.exec(commandLine);
  if (quotedMatch) {
    commitMessage = quotedMatch[1];
  } else {
    const unquotedMatch = /(?:-m|--message)\s+([^-\s][^\s]*)/.exec(commandLine);
    if (unquotedMatch) {
      commitMessage = unquotedMatch[1];
    }
  }

  if (commitMessage) {
    const conventionalCommitRegex =
      /^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(?:\([a-zA-Z0-9_\-\./ ]+\))?!?: .+/;

    if (!conventionalCommitRegex.test(commitMessage.trim())) {
      deny(
        `[CONVENTIONAL COMMIT VIOLATION]: Commit message "${commitMessage}" does not follow Conventional Commits specification.\n` +
        `Expected format: "<type>(<optional scope>): <description>"\n` +
        `Allowed types: feat, fix, docs, style, refactor, perf, test, build, ci, chore, revert.\n` +
        `Examples:\n` +
        `  - feat(auth): implement oauth2 token refresh\n` +
        `  - fix(cart): prevent duplicate checkout submission\n` +
        `  - test(user): add unit tests for password hashing`
      );
    }
  }
}

// --- 2. Gitflow Branch Safety Gate ---
const gitWriteRegex = /\b(git\s+commit|git\s+push|git\s+add|git\s+merge)\b/i;
if (gitWriteRegex.test(commandLine)) {
  try {
    const activeBranch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    if (activeBranch === 'main' || activeBranch === 'develop') {
      deny(
        `[GITFLOW SAFETY VIOLATION]: Directly executing git add/commit/push/merge on "${activeBranch}" is prohibited.\n` +
        `Per Gitflow workflow rules, create a dedicated feature/ or bugfix/ branch and merge via Pull Request.`
      );
    }
  } catch (e) {
    // Not a git repository or detached HEAD — proceed
  }
}

allow();
