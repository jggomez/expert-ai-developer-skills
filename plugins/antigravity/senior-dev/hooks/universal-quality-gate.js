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
 *
 * UI reality gate: a changed web or Flutter web UI needs no fake data and fresh evidence that the
 * real app was opened and used (skills/compliance-verifier and skills/blackbox-tester scripts).
 * It blocks only in the turn that changed the UI (its own edits or a subagent's); a later turn
 * that leaves those files as they were gets a notice that the UI is still unverified, so a plain
 * answer is never held hostage by an earlier, already reported, unverified UI.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const g = require(path.join(__dirname, 'shared', 'gate-utils.js'));

const payload = g.readStdinJson();
if (!g.isFinalStop(payload)) g.exitAllow();
const workspaceRoot = g.workspaceOf(payload); // git root: stable even after a `cd` in the shell
const exists = (rel) => fs.existsSync(path.join(workspaceRoot, rel));
const commandExists = g.commandExists;

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

const UI_FILE = /\.(tsx|jsx|vue|svelte|html|css|scss|dart)$/i;
const TEST_FILE = /(^|\/)(tests?|__tests__|e2e|integration_test|test_driver)\/|\.(test|spec|stories)\.|_test\.dart$/;
const FAKE_DATA_CHECK = path.join(__dirname, '..', 'skills', 'compliance-verifier', 'scripts', 'check_fake_data.py');
const EVIDENCE_CHECK = path.join(__dirname, '..', 'skills', 'blackbox-tester', 'scripts', 'check_evidence.py');

/** A production UI file. Dart counts only with a web target: mobile apps are out of scope for browser runs. */
function isUiFile(file) {
  return UI_FILE.test(file) && !TEST_FILE.test(file) && (exists('web') || !/\.dart$/i.test(file));
}

/** Changed UI files (repo-relative, like every path from `git status`). */
function changedUiFiles() {
  return g.changedCodeFiles(workspaceRoot).filter(isUiFile);
}

function latestChangeSeconds(files) {
  const times = files.map((file) => {
    try {
      return fs.statSync(path.join(workspaceRoot, file)).mtimeMs;
    } catch (err) {
      return 0; // deleted file
    }
  });
  return Math.floor(Math.max(0, ...times) / 1000);
}

function uiRealityCommand() {
  const root = JSON.stringify(workspaceRoot);
  const since = latestChangeSeconds(changedUiFiles());
  return `python3 "${FAKE_DATA_CHECK}" --repo ${root} && ` +
    `python3 "${EVIDENCE_CHECK}" --latest --root ${root} --min-mtime ${since}`;
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
    // 4. Python: pytest from the project's environment (uv / .venv / poetry), never a global one
    gateId: 'python-tests',
    applies: () => isPythonRepo && (exists('tests') || exists('test')) && g.pytestCommand(workspaceRoot) !== null,
    command: () => g.pytestCommand(workspaceRoot),
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
  {
    // 7. The real UI: last, so it never asks to open an app whose tests fail
    gateId: 'ui-reality',
    applies: () => fs.existsSync(FAKE_DATA_CHECK) && fs.existsSync(EVIDENCE_CHECK) && commandExists('python3') &&
      changedUiFiles().length > 0,
    files: isUiFile, // only UI changes count as "changed" for this gate
    noticeOnRepeat: true, // a turn that left the UI untouched is told, not blocked
    command: uiRealityCommand,
    message: `[UI REALITY GATE]: This UI was not proven against real data in the running app.\n` +
      `Delegate to e2e-blackbox-tester: start the app and backend, use it, and record the run. If it cannot run, ` +
      `tell the user the UI is NOT verified, with the exact error.`,
    limitNotice: '[UI reality gate] UI NOT verified in the real app after 3 attempts: treat this task as unfinished.',
    repeatNotice: '[UI reality gate] The changed UI is still NOT verified in the real app (unchanged since it was ' +
      'last reported). Run it with e2e-blackbox-tester, or tell the user it stays unverified.',
  },
];

// The host kills the hook at its hooks.json timeout (180 s): share that budget across suites.
const budget = g.createBudget(180000);
const notices = [];
for (const suite of SUITES) {
  if (!suite.applies()) continue;

  const gate = g.createStopGate({ gateId: suite.gateId, payload, fileFilter: suite.files });
  if (gate.retryLimitReached()) {
    notices.push(suite.limitNotice || g.retryLimitNotice(suite.gateId));
    continue;
  }
  if (gate.begin()) continue; // no code change, already green, or verified by a parallel gate
  const repeat = Boolean(suite.noticeOnRepeat) && gate.isRepeat();

  const timeout = budget.timeout(120000);
  if (timeout < 10000) {
    gate.abandon(); // release the lock without recording a result
    notices.push(`[universal quality gate] skipped '${suite.gateId}': hook time budget exhausted`);
    continue;
  }
  try {
    const command = typeof suite.command === 'function' ? suite.command() : suite.command;
    execSync(command, { cwd: workspaceRoot, stdio: 'pipe', timeout });
    gate.markPass();
  } catch (error) {
    const out = (error.stdout?.toString() || '') + (error.stderr?.toString() || '') || error.message || '';
    if (repeat) {
      // Same files as when this was last reported: the agent already got the verdict (and up to
      // 3 blocks) in the turn that changed them. Record it and let this turn end with a notice.
      gate.markFail(suite.message, { blocking: false });
      notices.push(suite.repeatNotice || suite.message);
      continue;
    }
    g.exitBlock(gate.markFail(`${suite.message}\n\nOutput:\n${out.slice(0, 3000)}`));
  }
}

g.exitAllow(notices.join('\n'));
