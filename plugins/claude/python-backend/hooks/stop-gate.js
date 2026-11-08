#!/usr/bin/env node
/**
 * python-backend Stop gate for Claude Code.
 * Checks if a test suite exists (tests/ directory, pytest.ini, test_*.py files, or verify_tests.py).
 * Runs pytest or python3 -m unittest discover.
 * If tests fail, logs error to console.error and exits with code 2. Exit 0 for success.
 * Skips when no code changed / the same code state already passed, shares the
 * 'python-tests' gate with senior-dev's universal gate (runs once), and gives up
 * after 3 blocks per turn (see hooks/shared/gate-utils.js).
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const g = require(path.join(__dirname, 'shared', 'gate-utils.js'));

const payload = g.readStdinJson();
if (!g.isFinalStop(payload)) g.exitAllow();
const workspaceRoot = g.workspaceOf(payload);

// 1. Check for verify_tests.py in skills layout
const verifyScript = path.join(workspaceRoot, 'skills', 'test-driven-development', 'scripts', 'verify_tests.py');
const hasVerifyScript = fs.existsSync(verifyScript);

// 2. Check for common Python test indicators
const hasTestsDir = fs.existsSync(path.join(workspaceRoot, 'tests')) || fs.existsSync(path.join(workspaceRoot, 'test'));
const hasPytestConfig = fs.existsSync(path.join(workspaceRoot, 'pytest.ini')) || fs.existsSync(path.join(workspaceRoot, 'setup.cfg'));

let hasTestFiles = false;
if (!hasTestsDir && !hasPytestConfig) {
  try {
    const files = fs.readdirSync(workspaceRoot);
    hasTestFiles = files.some(f => /^test_.*\.py$/.test(f) || /_test\.py$/.test(f));
  } catch (e) {
    hasTestFiles = false;
  }
}

const testsExist = hasVerifyScript || hasTestsDir || hasPytestConfig || hasTestFiles;
if (!testsExist) {
  g.exitAllow();
}

const gate = g.createStopGate({ gateId: 'python-tests', payload });
if (gate.retryLimitReached()) {
  g.exitAllow(g.retryLimitNotice('python-tests'));
}
if (gate.begin()) {
  g.exitAllow();
}

// 3. Execute tests
let testCommand = '';
if (hasVerifyScript) {
  testCommand = `python3 "${verifyScript}"`;
} else {
  // pytest from the project's own environment (uv / .venv / poetry) before a global one from PATH:
  // a global pytest cannot import the project's dependencies and fails every module.
  const pytestCommand = g.pytestCommand(workspaceRoot);
  if (pytestCommand) {
    testCommand = pytestCommand;
  } else if (hasTestsDir) {
    testCommand = 'python3 -m unittest discover -s tests';
  } else {
    testCommand = 'python3 -m unittest discover';
  }
}

try {
  execSync(testCommand, { cwd: workspaceRoot, stdio: 'pipe', timeout: 150000 });
} catch (error) {
  const testOutput =
    (error.stdout ? error.stdout.toString() : '') +
    (error.stderr ? error.stderr.toString() : '') || error.message || '';
  const reason =
    `[PYTHON QUALITY GATE FAILURE]: Test suite failed under "${testCommand}". ` +
    `Fix the failing tests or application code before completing your turn.\n\n` +
    `Test Output:\n${testOutput.slice(0, 4000)}`;

  g.exitBlock(gate.markFail(reason)); // host-aware block (hooks/shared/gate-utils.js)
}

gate.markPass();
g.exitAllow();
