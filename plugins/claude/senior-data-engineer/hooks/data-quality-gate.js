#!/usr/bin/env node
/**
 * senior-data-engineer Stop gate for Claude Code.
 * Runs compile validation for Dataform (dataform compile) or dbt (dbt compile).
 * If compilation fails, logs to console.error and exits with code 2. Exit 0 for success.
 * Skips when no code changed / the same state already compiled, and gives up after
 * 3 blocks per turn (see hooks/shared/gate-utils.js).
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const g = require(path.join(__dirname, 'shared', 'gate-utils.js'));

const payload = g.readStdinJson();
if (!g.isFinalStop(payload)) g.exitAllow();
const cwd = g.workspaceOf(payload);

const notices = [];
// The host kills the hook at its hooks.json timeout (180 s): share that budget across checks.
const budget = g.createBudget(180000);

function commandExists(cmd) {
  try {
    execSync(`command -v ${cmd}`, { stdio: 'ignore', shell: '/bin/sh' });
    return true;
  } catch (e) {
    return false;
  }
}

/** Runs one cached, bounded check; blocks the stop on failure. */
function runCheck(gateId, command, maxMs, message) {
  const gate = g.createStopGate({ gateId, payload });
  if (gate.retryLimitReached()) {
    notices.push(g.retryLimitNotice(gateId));
    return;
  }
  if (gate.begin()) return;
  const timeout = budget.timeout(maxMs);
  if (timeout < 10000) {
    gate.abandon();
    notices.push(`[data quality gate] skipped '${gateId}': hook time budget exhausted`);
    return;
  }
  try {
    execSync(command, { cwd, stdio: 'pipe', timeout });
    gate.markPass();
  } catch (error) {
    const out =
      (error.stdout ? error.stdout.toString() : '') +
      (error.stderr ? error.stderr.toString() : '') || error.message;
    g.exitBlock(gate.markFail(`${message}\n\n${out.slice(0, 4000)}`));
  }
}

// 1. Dataform compile check
const isDataform =
  fs.existsSync(path.join(cwd, 'dataform.json')) ||
  fs.existsSync(path.join(cwd, 'workflow_settings.yaml'));
if (isDataform && commandExists('dataform')) {
  runCheck('dataform-compile', 'dataform compile', 60000,
    '[DATAFORM COMPILATION FAILED]: "dataform compile" failed with errors. ' +
    'Fix broken SQLX models, dependencies, or assertions before finishing.');
}

// 2. dbt compile check
const isDbt =
  fs.existsSync(path.join(cwd, 'dbt_project.yml')) ||
  fs.existsSync(path.join(cwd, 'dbt_project.yaml'));
if (isDbt && commandExists('dbt')) {
  runCheck('dbt-compile', 'dbt compile', 60000,
    '[DBT COMPILATION FAILED]: "dbt compile" failed with errors. ' +
    'Fix model syntax, Jinja expressions, or ref() dependencies before finishing.');
}

// 3. Python pipeline tests (gate id shared with senior-dev / python-backend: runs once per code state)
const hasPyTests =
  (fs.existsSync(path.join(cwd, 'tests')) || fs.existsSync(path.join(cwd, 'test'))) &&
  (fs.existsSync(path.join(cwd, 'requirements.txt')) || fs.existsSync(path.join(cwd, 'pyproject.toml')));
if (hasPyTests && commandExists('pytest')) {
  runCheck('python-tests', 'pytest -q', 90000,
    '[DATA QUALITY GATE VIOLATION]: Pipeline tests failed. Ensure all ETL data validation tests pass.');
}

g.exitAllow(notices.join('\n'));
