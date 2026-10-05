#!/usr/bin/env node
/**
 * Git Workflow Clean State Gate (Stop Hook)
 * Ensures no unresolved merge conflicts or corrupted git states exist before task termination.
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

// Only check git repos
if (!fs.existsSync(path.join(workspaceRoot, '.git'))) {
  finishAllow();
}

try {
  const statusOutput = execSync('git status --porcelain', {
    cwd: workspaceRoot,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
    timeout: 10000
  });

  // Check for unresolved merge conflicts (UU, AA, DD, etc.)
  const hasConflicts = /^([UAD]{2})\s+/m.test(statusOutput);
  if (hasConflicts) {
    finishBlock(
      `[GIT WORKFLOW GATE VIOLATION]: Unresolved merge conflicts detected in repository.\n` +
      `You cannot complete the task while files contain unresolved conflict markers ('<<<<<<< HEAD').`
    );
  }
} catch (e) {
  // git error or not in git repo
}

finishAllow();
