#!/usr/bin/env node
/**
 * Senior Data Engineer Quality Gate (Stop Hook)
 * Inspects Dataform projects, dbt models, or pipeline code before allowing session completion.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

function finishAllow() {
  console.log(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}

function finishBlock(reason) {
  console.log(JSON.stringify({ decision: 'continue', reason }));
  process.exit(0);
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

if (payload.terminationReason !== 'model_stop') finishAllow();

const workspaceRoot =
  payload.workspacePaths?.[0] ||
  payload.cwd ||
  process.cwd();

// 1. Dataform project check
const isDataform =
  fs.existsSync(path.join(workspaceRoot, 'dataform.json')) ||
  fs.existsSync(path.join(workspaceRoot, 'workflow_settings.yaml'));

if (isDataform) {
  try {
    execSync('which dataform', { stdio: 'ignore' });
    try {
      execSync('dataform compile', { cwd: workspaceRoot, stdio: 'pipe', timeout: 60000 });
    } catch (compileErr) {
      const out = (compileErr.stdout?.toString() || '') + (compileErr.stderr?.toString() || '');
      finishBlock(
        `[DATA QUALITY GATE VIOLATION]: 'dataform compile' failed.\n` +
        `Fix compilation errors or missing dependencies in .sqlx models before concluding.\n\nOutput:\n${out.slice(0, 3000)}`
      );
    }
  } catch (e) {
    // dataform cli not in PATH, skip
  }
}

// 2. Python-based ETL check (if tests directory exists)
const hasPyTests =
  (fs.existsSync(path.join(workspaceRoot, 'tests')) || fs.existsSync(path.join(workspaceRoot, 'test'))) &&
  (fs.existsSync(path.join(workspaceRoot, 'requirements.txt')) || fs.existsSync(path.join(workspaceRoot, 'pyproject.toml')));

if (hasPyTests) {
  try {
    execSync('which pytest', { stdio: 'ignore' });
    try {
      execSync('pytest -q', { cwd: workspaceRoot, stdio: 'pipe', timeout: 90000 });
    } catch (pytestErr) {
      const out = (pytestErr.stdout?.toString() || '') + (pytestErr.stderr?.toString() || '');
      finishBlock(
        `[DATA QUALITY GATE VIOLATION]: Pipeline tests failed.\n` +
        `Ensure all ETL data validation tests pass cleanly.\n\nOutput:\n${out.slice(0, 3000)}`
      );
    }
  } catch (e) {
    // pytest not in PATH
  }
}

finishAllow();
