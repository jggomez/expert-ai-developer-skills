#!/usr/bin/env node
/**
 * Senior Developer Universal Quality Gate (Stop Hook)
 * Polyglot verification hook:
 * When the execution loop terminates (terminationReason: "model_stop"),
 * inspects the project environment and executes relevant test suites or linters.
 * If tests/linters fail (exit code != 0), blocks the agent from finishing and forces remediation.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);

function finishAllow() {
  if (!isClaudeCode) {
    console.log(JSON.stringify({ decision: 'allow' }));
  }
  process.exit(0);
}

function finishBlock(reason) {
  if (isClaudeCode) {
    console.error(reason);
    process.exit(2);
  } else {
    console.log(JSON.stringify({ decision: 'continue', reason }));
    process.exit(0);
  }
}

let raw = '';
try {
  raw = fs.readFileSync(0, 'utf-8');
} catch (e) {
  finishAllow();
}
if (!raw.trim()) finishAllow();

let payload = {};
try {
  payload = JSON.parse(raw);
} catch (e) {
  finishAllow();
}

const terminationReason = payload.terminationReason || '';
// Only enforce gate on intentional model stops
if (terminationReason !== 'model_stop') {
  finishAllow();
}

const workspaceRoot =
  payload.workspacePaths?.[0] ||
  payload.cwd ||
  process.cwd();

// Helper to check if a command exists in PATH
function commandExists(cmd) {
  try {
    execSync(`which ${cmd}`, { stdio: 'ignore' });
    return true;
  } catch (e) {
    return false;
  }
}

// 1. Custom Repository Verification Script (Highest Priority)
const customVerifyScript = path.join(workspaceRoot, 'scripts', 'verify.sh');
if (fs.existsSync(customVerifyScript)) {
  try {
    execSync(`bash "${customVerifyScript}"`, { cwd: workspaceRoot, stdio: 'pipe', timeout: 120000 });
  } catch (error) {
    const out = (error.stdout?.toString() || '') + (error.stderr?.toString() || '');
    finishBlock(
      `[UNIVERSAL QUALITY GATE VIOLATION]: Repository verification script 'scripts/verify.sh' failed.\n` +
      `You cannot complete the task until verification passes cleanly.\n\nOutput:\n${out.slice(0, 3000)}`
    );
  }
}

// 2. Flutter / Dart
const pubspec = path.join(workspaceRoot, 'pubspec.yaml');
if (fs.existsSync(pubspec) && commandExists('dart')) {
  try {
    execSync('dart analyze', { cwd: workspaceRoot, stdio: 'pipe', timeout: 120000 });
  } catch (error) {
    const out = (error.stdout?.toString() || '') + (error.stderr?.toString() || '');
    finishBlock(
      `[UNIVERSAL QUALITY GATE VIOLATION]: 'dart analyze' detected errors or warnings.\n` +
      `Fix all static analysis findings before completing the task.\n\nOutput:\n${out.slice(0, 3000)}`
    );
  }
}

// 3. Node.js / TypeScript / JavaScript
const pkgJsonPath = path.join(workspaceRoot, 'package.json');
if (fs.existsSync(pkgJsonPath) && commandExists('npm')) {
  try {
    const pkg = JSON.parse(fs.readFileSync(pkgJsonPath, 'utf8'));
    const scripts = pkg.scripts || {};
    
    // Run npm test if defined and not default placeholder
    if (scripts.test && !scripts.test.includes('no test specified')) {
      try {
        execSync('npm test', { cwd: workspaceRoot, stdio: 'pipe', timeout: 120000 });
      } catch (testErr) {
        const out = (testErr.stdout?.toString() || '') + (testErr.stderr?.toString() || '');
        finishBlock(
          `[UNIVERSAL QUALITY GATE VIOLATION]: 'npm test' failed.\n` +
          `Fix failing tests before finishing.\n\nOutput:\n${out.slice(0, 3000)}`
        );
      }
    }
  } catch (e) {
    // If package.json is invalid JSON or npm fails, don't crash
  }
}

// 4. Python
const isPythonRepo =
  fs.existsSync(path.join(workspaceRoot, 'pyproject.toml')) ||
  fs.existsSync(path.join(workspaceRoot, 'pytest.ini')) ||
  fs.existsSync(path.join(workspaceRoot, 'setup.cfg')) ||
  fs.existsSync(path.join(workspaceRoot, 'requirements.txt'));

if (isPythonRepo) {
  // If pytest is present and tests directory exists
  const hasTestsDir =
    fs.existsSync(path.join(workspaceRoot, 'tests')) ||
    fs.existsSync(path.join(workspaceRoot, 'test'));

  if (hasTestsDir && commandExists('pytest')) {
    try {
      execSync('pytest -q', { cwd: workspaceRoot, stdio: 'pipe', timeout: 120000 });
    } catch (error) {
      const out = (error.stdout?.toString() || '') + (error.stderr?.toString() || '');
      finishBlock(
        `[UNIVERSAL QUALITY GATE VIOLATION]: 'pytest' test suite failed.\n` +
        `Ensure all unit and integration tests pass with exit code 0 before completing the task.\n\nOutput:\n${out.slice(0, 3000)}`
      );
    }
  }
}

// 5. Rust
const cargoToml = path.join(workspaceRoot, 'Cargo.toml');
if (fs.existsSync(cargoToml) && commandExists('cargo')) {
  try {
    execSync('cargo test --quiet', { cwd: workspaceRoot, stdio: 'pipe', timeout: 120000 });
  } catch (error) {
    const out = (error.stdout?.toString() || '') + (error.stderr?.toString() || '');
    finishBlock(
      `[UNIVERSAL QUALITY GATE VIOLATION]: 'cargo test' failed.\n` +
      `Ensure Rust tests pass before finishing.\n\nOutput:\n${out.slice(0, 3000)}`
    );
  }
}

// 6. Go
const goMod = path.join(workspaceRoot, 'go.mod');
if (fs.existsSync(goMod) && commandExists('go')) {
  try {
    execSync('go test ./...', { cwd: workspaceRoot, stdio: 'pipe', timeout: 120000 });
  } catch (error) {
    const out = (error.stdout?.toString() || '') + (error.stderr?.toString() || '');
    finishBlock(
      `[UNIVERSAL QUALITY GATE VIOLATION]: 'go test ./...' failed.\n` +
      `Ensure Go packages pass all tests before finishing.\n\nOutput:\n${out.slice(0, 3000)}`
    );
  }
}

finishAllow();
