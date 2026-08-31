#!/usr/bin/env node
/**
 * senior-dev-flutter PreToolUse gate. Blocks two things on a protected branch
 * (main / master / develop), where they should go through CI or a dedicated
 * branch + ADR instead:
 *   - building store artifacts:  flutter build appbundle | ipa | aab
 *   - major dependency bumps:    (flutter|dart) pub upgrade --major-versions
 * Everything else is allowed. Non-blocking on a non-git or non-Flutter repo.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);
const PROTECTED = new Set(['main', 'master', 'develop']);

let raw = '';
try {
  raw = fs.readFileSync(0, 'utf-8');
} catch (e) {
  process.exit(0);
}
if (!raw.trim()) process.exit(0);

let payload;
try {
  payload = JSON.parse(raw);
} catch (e) {
  process.exit(0);
}

// Normalize Claude Code (tool_name/tool_input/cwd) and Antigravity
// (toolCall.name/toolCall.args) payload shapes.
const toolName = payload.tool_name || (payload.toolCall && payload.toolCall.name) || '';
const toolInput = payload.tool_input || (payload.toolCall && payload.toolCall.args) || {};
const command = toolInput.command || toolInput.CommandLine || '';
const cwd =
  payload.cwd ||
  toolInput.Cwd ||
  (payload.workspacePaths && payload.workspacePaths[0]) ||
  process.cwd();

const isShellTool = toolName === 'Bash' || toolName === 'run_command';
if (!isShellTool || !command) process.exit(0);

// Only care about Flutter/Dart repos.
if (!fs.existsSync(path.join(cwd, 'pubspec.yaml'))) process.exit(0);

let branch = '';
try {
  branch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
} catch (e) {
  process.exit(0); // not a git repo / detached
}
if (!PROTECTED.has(branch)) process.exit(0);

const storeBuild = /\bflutter\s+build\s+(appbundle|aab|ipa)\b/i;
const majorBump = /\b(flutter|dart)\s+pub\s+upgrade\b.*--major-versions\b/i;

let reason = null;
if (storeBuild.test(command)) {
  reason =
    `Blocked on "${branch}": store artifacts (flutter build appbundle/ipa) should be ` +
    `built by CI from a release branch, not locally on a protected branch — see the ` +
    `flutter-release-engineering skill. Use "flutter build apk/web" for local checks, ` +
    `or switch to a release branch.`;
} else if (majorBump.test(command)) {
  reason =
    `Blocked on "${branch}": a major dependency bump needs a dedicated branch and an ` +
    `ADR (flutter-upgrade-migration skill: one axis at a time, pin pubspec.lock first). ` +
    `Create a chore/ branch and run it there.`;
}

if (!reason) process.exit(0);

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
