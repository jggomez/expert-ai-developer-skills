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
const cwd = g.workspaceOf(payload);

const notices = [];

// 1. Dataform compile check
const isDataform =
  fs.existsSync(path.join(cwd, 'dataform.json')) ||
  fs.existsSync(path.join(cwd, 'workflow_settings.yaml'));

if (isDataform) {
  const gate = g.createStopGate({ gateId: 'dataform-compile', payload });
  if (gate.retryLimitReached()) {
    notices.push(g.retryLimitNotice('dataform-compile'));
  } else if (!gate.begin()) {
    try {
      execSync('dataform compile', { cwd, stdio: 'pipe', timeout: 45000 });
      gate.markPass();
    } catch (error) {
      const out =
        (error.stdout ? error.stdout.toString() : '') +
        (error.stderr ? error.stderr.toString() : '') || error.message;
      g.exitBlock(gate.markFail(
        `[DATAFORM COMPILATION FAILED]: "dataform compile" failed with errors. ` +
        `Fix broken SQLX models, dependencies, or assertions before finishing.\n\n${out.slice(0, 4000)}`
      ));
    }
  }
}

// 2. dbt compile check
const isDbt =
  fs.existsSync(path.join(cwd, 'dbt_project.yml')) ||
  fs.existsSync(path.join(cwd, 'dbt_project.yaml'));

if (isDbt) {
  const gate = g.createStopGate({ gateId: 'dbt-compile', payload });
  if (gate.retryLimitReached()) {
    notices.push(g.retryLimitNotice('dbt-compile'));
  } else if (!gate.begin()) {
    try {
      execSync('dbt compile', { cwd, stdio: 'pipe', timeout: 45000 });
      gate.markPass();
    } catch (error) {
      const out =
        (error.stdout ? error.stdout.toString() : '') +
        (error.stderr ? error.stderr.toString() : '') || error.message;
      g.exitBlock(gate.markFail(
        `[DBT COMPILATION FAILED]: "dbt compile" failed with errors. ` +
        `Fix model syntax, Jinja expressions, or ref() dependencies before finishing.\n\n${out.slice(0, 4000)}`
      ));
    }
  }
}

g.exitAllow(notices.join('\n'));
