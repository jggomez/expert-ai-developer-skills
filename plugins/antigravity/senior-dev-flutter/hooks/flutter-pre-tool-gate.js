#!/usr/bin/env node
/**
 * senior-dev-flutter PreToolUse gate.
 * 1. Plan-First Gate: Requires PLAN.md before writing or editing Dart code.
 * 2. Orchestrator Boundary: Prohibits the main orchestrator from writing .dart code directly.
 * 3. Branch Safety: Blocks store builds / major dependency bumps on protected branches.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PROTECTED = new Set(['main', 'master', 'develop']);

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

const toolCall = payload.toolCall || {};
const toolName = toolCall.name || payload.tool_name || '';
const toolArgs = toolCall.args || payload.tool_input || {};
const command = toolArgs.CommandLine || toolArgs.command || '';
const targetFile = toolArgs.TargetFile || toolArgs.file_path || toolArgs.path || '';
const cwd =
  payload.workspacePaths?.[0] ||
  payload.cwd ||
  toolArgs.Cwd ||
  process.cwd();

// Only care if workspace is a Flutter/Dart repo
if (!fs.existsSync(path.join(cwd, 'pubspec.yaml'))) allow();

// 1. GATE: File Modification (write_to_file / replace_file_content)
const isFileModTool = /^(write_to_file|replace_file_content)$/i.test(toolName);
if (isFileModTool && targetFile) {
  const basename = path.basename(targetFile);
  const ext = path.extname(targetFile).toLowerCase();

  // Allow docs and plans
  const isDoc =
    /^PLAN(\.[\w-]+)?\.md$/i.test(basename) ||
    targetFile.includes('/doc/adr/') ||
    targetFile.includes('/docs/') ||
    ext === '.md' ||
    ext === '.txt';

  if (!isDoc && ext === '.dart') {
    // Check Plan First
    const hasPlan =
      fs.existsSync(path.join(cwd, 'PLAN.md')) ||
      fs.existsSync(path.join(cwd, 'doc', 'PLAN.md'));

    if (!hasPlan) {
      deny(
        `[FLUTTER GRAPH GATE - PLAN FIRST]: No "PLAN.md" found in "${cwd}".\n` +
        `You MUST create a "PLAN.md" defining target platforms, state management, and tasks before modifying Dart code.`
      );
    }

    // Check Orchestrator Boundary
    const transcriptPath = payload.transcriptPath;
    if (transcriptPath && fs.existsSync(transcriptPath)) {
      try {
        const firstLine = fs.readFileSync(transcriptPath, 'utf8').trim().split('\n')[0] || '';
        if (firstLine.includes('<USER_REQUEST>')) {
          deny(
            `[FLUTTER GRAPH INVARIANT VIOLATION]: As the Flutter Feature Orchestrator, you are STRICTLY FORBIDDEN ` +
            `from editing Dart files (${basename}) directly.\n` +
            `You MUST delegate implementation to the 'flutter-implementer' subagent using invoke_subagent.`
          );
        }
      } catch (err) {
        // fail open if transcript unreadable
      }
    }
  }
}

// 2. GATE: Shell Commands (run_command)
const isShellTool = toolName === 'run_command' || toolName === 'Bash';
if (isShellTool && command) {
  let branch = '';
  try {
    branch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  } catch (e) {
    allow(); // not a git repo / detached
  }

  if (PROTECTED.has(branch)) {
    const storeBuild = /\bflutter\s+build\s+(appbundle|aab|ipa)\b/i;
    const majorBump = /\b(flutter|dart)\s+pub\s+upgrade\b.*--major-versions\b/i;

    if (storeBuild.test(command)) {
      deny(
        `Blocked on "${branch}": store artifacts (flutter build appbundle/ipa) should be ` +
        `built by CI from a release branch, not locally on a protected branch — see the ` +
        `flutter-release-engineering skill.`
      );
    } else if (majorBump.test(command)) {
      deny(
        `Blocked on "${branch}": a major dependency bump needs a dedicated branch and an ` +
        `ADR. Create a chore/ branch and run it there.`
      );
    }
  }
}

allow();
