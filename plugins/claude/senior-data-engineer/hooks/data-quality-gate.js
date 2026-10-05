#!/usr/bin/env node
/**
 * senior-data-engineer Stop gate for Claude Code.
 * Runs compile validation for Dataform (dataform compile) or dbt (dbt compile).
 * If compilation fails, logs to console.error and exits with code 2. Exit 0 for success.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

let raw = '';
try {
  if (!process.stdin.isTTY) {
    raw = fs.readFileSync(0, 'utf-8');
  }
} catch (e) {
  process.exit(0);
}

let payload = {};
if (raw.trim()) {
  try {
    payload = JSON.parse(raw);
  } catch (e) {
    payload = {};
  }
}

const cwd = payload.cwd || (payload.workspacePaths && payload.workspacePaths[0]) || process.cwd();

// 1. Dataform compile check
const isDataform =
  fs.existsSync(path.join(cwd, 'dataform.json')) ||
  fs.existsSync(path.join(cwd, 'workflow_settings.yaml'));

if (isDataform) {
  try {
    execSync('dataform compile', { cwd, stdio: 'pipe', timeout: 45000 });
  } catch (error) {
    const out =
      (error.stdout ? error.stdout.toString() : '') +
      (error.stderr ? error.stderr.toString() : '') || error.message;
    console.error(
      `[DATAFORM COMPILATION FAILED]: "dataform compile" failed with errors. ` +
      `Fix broken SQLX models, dependencies, or assertions before finishing.\n\n${out.slice(0, 4000)}`
    );
    process.exit(2);
  }
}

// 2. dbt compile check
const isDbt =
  fs.existsSync(path.join(cwd, 'dbt_project.yml')) ||
  fs.existsSync(path.join(cwd, 'dbt_project.yaml'));

if (isDbt) {
  try {
    execSync('dbt compile', { cwd, stdio: 'pipe', timeout: 45000 });
  } catch (error) {
    const out =
      (error.stdout ? error.stdout.toString() : '') +
      (error.stderr ? error.stderr.toString() : '') || error.message;
    console.error(
      `[DBT COMPILATION FAILED]: "dbt compile" failed with errors. ` +
      `Fix model syntax, Jinja expressions, or ref() dependencies before finishing.\n\n${out.slice(0, 4000)}`
    );
    process.exit(2);
  }
}

process.exit(0);
