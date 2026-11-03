#!/usr/bin/env node
/**
 * Senior Developer Universal Quality Gate (Stop hook, Claude Code and Antigravity)
 * Polyglot verification hook:
 * When Claude Code finishes a turn / attempts to stop:
 * Inspects the project environment and executes relevant test suites or linters.
 * If tests/linters fail, keeps the agent working and feeds the output back (gate-utils exitBlock).
 *
 * Cost controls (hooks/shared/gate-utils.js):
 * - A suite is skipped when no code file changed, or when the same code state already passed it.
 * - Suites share gate ids with the language plugins ('python-tests', 'dart-analyze'), so when
 *   both plugins are installed the suite runs once per code state.
 * - Each suite blocks at most 3 times per user turn (`stop_hook_active`), then lets the turn end
 *   with a notice instead of looping.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const g = require(path.join(__dirname, 'shared', 'gate-utils.js'));

const payload = g.readStdinJson();
if (!g.isFinalStop(payload)) g.exitAllow();
const workspaceRoot = g.workspaceOf(payload);
const exists = (rel) => fs.existsSync(path.join(workspaceRoot, rel));

// Helper to check if a command exists in PATH
function commandExists(cmd) {
  try {
    execSync(`command -v ${cmd}`, { stdio: 'ignore', shell: '/bin/sh' });
    return true;
  } catch (e) {
    return false;
  }
}

function npmTestDefined() {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(workspaceRoot, 'package.json'), 'utf8'));
    const test = (pkg.scripts || {}).test;
    return Boolean(test) && !test.includes('no test specified');
  } catch (e) {
    // Invalid package.json: nothing reliable to run
    return false;
  }
}

const isPythonRepo = ['pyproject.toml', 'pytest.ini', 'setup.cfg', 'requirements.txt'].some(exists);

// Ordered verification suites. `applies` is evaluated lazily so absent toolchains cost nothing.
const SUITES = [
  {
    // 1. Custom Repository Verification Script (Highest Priority)
    gateId: 'verify-sh',
    applies: () => exists(path.join('scripts', 'verify.sh')),
    command: `bash "${path.join(workspaceRoot, 'scripts', 'verify.sh')}"`,
    message: `[UNIVERSAL QUALITY GATE VIOLATION]: Repository verification script 'scripts/verify.sh' failed.\nFix all issues before finishing.`,
  },
  {
    // 2. Flutter / Dart
    gateId: 'dart-analyze',
    applies: () => exists('pubspec.yaml') && commandExists('dart'),
    command: 'dart analyze',
    message: `[UNIVERSAL QUALITY GATE VIOLATION]: 'dart analyze' detected errors or warnings.\nFix all static analysis findings before completing the task.`,
  },
  {
    // 3. Node.js / TypeScript / JavaScript (npm test if defined and not the default placeholder)
    gateId: 'node-tests',
    applies: () => exists('package.json') && commandExists('npm') && npmTestDefined(),
    command: 'npm test',
    message: `[UNIVERSAL QUALITY GATE VIOLATION]: 'npm test' failed.\nFix failing tests before finishing.`,
  },
  {
    // 4. Python
    gateId: 'python-tests',
    applies: () => isPythonRepo && (exists('tests') || exists('test')) && commandExists('pytest'),
    command: 'pytest -q',
    message: `[UNIVERSAL QUALITY GATE VIOLATION]: 'pytest' test suite failed.\nEnsure all unit and integration tests pass with exit code 0 before completing the task.`,
  },
  {
    // 5. Rust
    gateId: 'rust-tests',
    applies: () => exists('Cargo.toml') && commandExists('cargo'),
    command: 'cargo test --quiet',
    message: `[UNIVERSAL QUALITY GATE VIOLATION]: 'cargo test' failed.\nEnsure Rust tests pass before finishing.`,
  },
  {
    // 6. Go
    gateId: 'go-tests',
    applies: () => exists('go.mod') && commandExists('go'),
    command: 'go test ./...',
    message: `[UNIVERSAL QUALITY GATE VIOLATION]: 'go test ./...' failed.\nEnsure Go packages pass all tests before finishing.`,
  },
];

// The host kills the hook at its hooks.json timeout (180 s): share that budget across suites.
const budget = g.createBudget(180000);
const notices = [];
for (const suite of SUITES) {
  if (!suite.applies()) continue;

  const gate = g.createStopGate({ gateId: suite.gateId, payload });
  if (gate.retryLimitReached()) {
    notices.push(g.retryLimitNotice(suite.gateId));
    continue;
  }
  if (gate.begin()) continue; // no code change, already green, or verified by a parallel gate

  const timeout = budget.timeout(120000);
  if (timeout < 10000) {
    gate.abandon(); // release the lock without recording a result
    notices.push(`[universal quality gate] skipped '${suite.gateId}': hook time budget exhausted`);
    continue;
  }
  try {
    execSync(suite.command, { cwd: workspaceRoot, stdio: 'pipe', timeout });
    gate.markPass();
  } catch (error) {
    const out = (error.stdout?.toString() || '') + (error.stderr?.toString() || '') || error.message || '';
    g.exitBlock(gate.markFail(`${suite.message}\n\nOutput:\n${out.slice(0, 3000)}`));
  }
}

g.exitAllow(notices.join('\n'));
