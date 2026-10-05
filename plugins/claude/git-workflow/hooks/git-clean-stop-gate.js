#!/usr/bin/env node
/**
 * git-workflow Stop gate for Claude Code.
 * Ensures the repository is not left with unresolved merge conflicts or an incomplete merge/rebase.
 * If conflicts or in-progress operations exist, blocks stopping (console.error + exit code 2).
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

const cwd = payload.cwd || (payload.workspacePaths && payload.workspacePaths[0]) || process.cwd();

// Verify git repository
let gitDir = '';
try {
  gitDir = execSync('git rev-parse --git-dir', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
} catch (e) {
  process.exit(0); // Not a git repo
}

const resolvedGitDir = path.isAbsolute(gitDir) ? gitDir : path.join(cwd, gitDir);

// 1. Check for in-progress merge, rebase, cherry-pick, or revert
const inProgressOps = [];
if (fs.existsSync(path.join(resolvedGitDir, 'MERGE_HEAD'))) {
  inProgressOps.push('Unfinished merge in progress (MERGE_HEAD present). Complete or abort with `git merge --abort`.');
}
if (
  fs.existsSync(path.join(resolvedGitDir, 'rebase-merge')) ||
  fs.existsSync(path.join(resolvedGitDir, 'rebase-apply')) ||
  fs.existsSync(path.join(resolvedGitDir, 'REBASE_HEAD'))
) {
  inProgressOps.push('Unfinished rebase in progress. Complete or abort with `git rebase --abort`.');
}
if (fs.existsSync(path.join(resolvedGitDir, 'CHERRY_PICK_HEAD'))) {
  inProgressOps.push('Unfinished cherry-pick in progress. Complete or abort with `git cherry-pick --abort`.');
}
if (fs.existsSync(path.join(resolvedGitDir, 'REVERT_HEAD'))) {
  inProgressOps.push('Unfinished revert in progress. Complete or abort with `git revert --abort`.');
}

// 2. Check for merge conflict markers in porcelain status
let unmergedFiles = [];
try {
  const statusOut = execSync('git status --porcelain', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  const lines = statusOut.split('\n');
  const conflictCodes = new Set(['UU', 'AA', 'UD', 'DU', 'DD', 'AU', 'UA']);

  for (const line of lines) {
    if (!line) continue;
    const code = line.slice(0, 2);
    if (conflictCodes.has(code) || code.includes('U')) {
      unmergedFiles.push(line.trim());
    }
  }
} catch (e) {
  // Ignored
}

// 3. Check for conflict markers in diff
let conflictMarkersFound = false;
try {
  const diffCheck = execSync('git diff --check', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  if (/conflict marker/i.test(diffCheck)) {
    conflictMarkersFound = true;
  }
} catch (e) {
  if (e.stdout && /conflict marker/i.test(e.stdout.toString())) {
    conflictMarkersFound = true;
  }
}

if (inProgressOps.length > 0 || unmergedFiles.length > 0 || conflictMarkersFound) {
  let errorMsg = '[GIT CLEANLINESS GATE VIOLATION]: Cannot finish session with unresolved git conflicts or operations:\n';

  if (inProgressOps.length > 0) {
    errorMsg += `\nIncomplete Git Operations:\n  - ${inProgressOps.join('\n  - ')}\n`;
  }
  if (unmergedFiles.length > 0) {
    errorMsg += `\nUnmerged Conflict Files:\n  - ${unmergedFiles.join('\n  - ')}\n`;
  }
  if (conflictMarkersFound) {
    errorMsg += `\nConflict markers (<<<<<<<, =======, >>>>>>>) detected in repository diff. Resolve all markers before finishing.\n`;
  }

  console.error(errorMsg);
  process.exit(2);
}

process.exit(0);
