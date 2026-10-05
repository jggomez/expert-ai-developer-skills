#!/usr/bin/env node
/**
 * python-backend Stop gate for Claude Code.
 * Checks if a test suite exists (tests/ directory, pytest.ini, test_*.py files, or verify_tests.py).
 * Runs pytest or python3 -m unittest discover.
 * If tests fail, logs error to console.error and exits with code 2. Exit 0 for success.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

let inputData = '';
try {
  if (!process.stdin.isTTY) {
    inputData = fs.readFileSync(0, 'utf-8');
  }
} catch (e) {
  process.exit(0);
}

let payload = {};
if (inputData.trim()) {
  try {
    payload = JSON.parse(inputData);
  } catch (e) {
    payload = {};
  }
}

const workspaceRoot = payload.cwd || (payload.workspacePaths && payload.workspacePaths[0]) || process.cwd();

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
  process.exit(0);
}

// 3. Execute tests
let testCommand = '';
if (hasVerifyScript) {
  testCommand = `python3 "${verifyScript}"`;
} else {
  // Check if pytest is available
  let pytestAvailable = false;
  try {
    execSync('pytest --version', { stdio: 'ignore' });
    pytestAvailable = true;
  } catch (e) {
    pytestAvailable = false;
  }

  if (pytestAvailable) {
    testCommand = 'pytest';
  } else if (hasTestsDir) {
    testCommand = 'python3 -m unittest discover -s tests';
  } else {
    testCommand = 'python3 -m unittest discover';
  }
}

try {
  execSync(testCommand, { cwd: workspaceRoot, stdio: 'pipe', timeout: 60000 });
} catch (error) {
  const testOutput =
    (error.stdout ? error.stdout.toString() : '') +
    (error.stderr ? error.stderr.toString() : '') || error.message || '';
  const reason =
    `[PYTHON QUALITY GATE FAILURE]: Test suite failed under "${testCommand}". ` +
    `Fix the failing tests or application code before completing your turn.\n\n` +
    `Test Output:\n${testOutput.slice(0, 4000)}`;

  console.error(reason);
  process.exit(2); // Claude Code stop failure contract: console.error and exit 2
}

process.exit(0);
