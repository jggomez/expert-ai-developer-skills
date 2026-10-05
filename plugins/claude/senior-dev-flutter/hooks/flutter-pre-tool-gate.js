#!/usr/bin/env node
/**
 * senior-dev-flutter PreToolUse gate for Claude Code.
 * 1. "Plan First" for Dart code: If Write or Edit targets a .dart file (in lib/ or test/),
 *    enforces that an active PLAN.md exists in the workspace.
 * 2. Protected branch protection for Bash: On main/master/develop in a Flutter repo:
 *    - blocks building store artifacts: flutter build appbundle | ipa | aab
 *    - blocks major dependency bumps: (flutter|dart) pub upgrade --major-versions
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PROTECTED = new Set(['main', 'master', 'develop']);

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

let raw = '';
try {
  raw = fs.readFileSync(0, 'utf-8');
} catch (e) {
  allow();
}
if (!raw.trim()) allow();

let payload;
try {
  payload = JSON.parse(raw);
} catch (e) {
  allow();
}

const toolName = payload.tool_name || '';
const toolInput = payload.tool_input || {};
const cwd = payload.cwd || (payload.workspacePaths && payload.workspacePaths[0]) || process.cwd();

// --- 1. Intercept Write | Edit for Dart files (Plan-First Rule) ---
if (toolName === 'Write' || toolName === 'Edit') {
  const targetFile = toolInput.file_path || toolInput.path || '';
  const isDartFile = targetFile.endsWith('.dart');
  const isLibOrTest = /(?:^|[\\/])(lib|test)[\\/].*\.dart$/i.test(targetFile) || isDartFile;

  if (isDartFile && isLibOrTest) {
    const possiblePlanPaths = [
      path.join(cwd, 'PLAN.md'),
      path.join(cwd, 'docs', 'PLAN.md'),
      path.join(cwd, '.agents', 'PLAN.md'),
      path.join(cwd, '.claude', 'PLAN.md')
    ];
    const hasPlan = possiblePlanPaths.some(p => fs.existsSync(p));

    if (!hasPlan) {
      deny(
        `[PLAN-FIRST VIOLATION]: Cannot modify Dart code in "${targetFile}" without an active "PLAN.md".\n` +
        `Per Senior Flutter Orchestration standards, you must create and structure a "PLAN.md" ` +
        `defining architecture, state management strategy, and subagent assignments before writing or modifying code.`
      );
    }
  }
}

// --- 2. Intercept Bash commands (Protected Branch Safety) ---
if (toolName === 'Bash') {
  const command = toolInput.command || '';
  if (command && fs.existsSync(path.join(cwd, 'pubspec.yaml'))) {
    let branch = '';
    try {
      branch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
    } catch (e) {
      branch = '';
    }

    if (PROTECTED.has(branch)) {
      const storeBuild = /\bflutter\s+build\s+(appbundle|aab|ipa)\b/i;
      const majorBump = /\b(flutter|dart)\s+pub\s+upgrade\b.*--major-versions\b/i;

      if (storeBuild.test(command)) {
        deny(
          `Blocked on "${branch}": store artifacts (flutter build appbundle/ipa) should be ` +
          `built by CI from a release branch, not locally on a protected branch — see the ` +
          `flutter-release-engineering skill. Use "flutter build apk/web" for local checks, ` +
          `or switch to a release branch.`
        );
      } else if (majorBump.test(command)) {
        deny(
          `Blocked on "${branch}": a major dependency bump needs a dedicated branch and an ` +
          `ADR (flutter-upgrade-migration skill: one axis at a time, pin pubspec.lock first). ` +
          `Create a chore/ branch and run it there.`
        );
      }
    }
  }
}

allow();
