#!/usr/bin/env node
/**
 * Anti-Lazy Code Quality Gate (Stop Hook)
 * Scans modified lines in the workspace for lazy AI placeholders before allowing session termination.
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

// Only scan if git repository exists
if (!fs.existsSync(path.join(workspaceRoot, '.git'))) {
  finishAllow();
}

try {
  // Get git diff of unstaged and staged changes
  const diffOutput = execSync('git diff -U0 HEAD', {
    cwd: workspaceRoot,
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'ignore'],
    timeout: 15000
  });

  const lazyPatterns = [
    /^\+.*TODO:\s*(implement\s+later|add\s+later|to\s+be\s+implemented|placeholder)/i,
    /^\+.*pass\s+#\s*(placeholder|to\s*do|implement)/i,
    /^\+.*\/\/\s*(your\s+code\s+here|implement\s+here)/i,
    /^\+.*\.\.\.\s*#\s*your\s+code\s+here/i,
    /^\+.*throw\s+UnimplementedError\(\)/i
  ];

  const lines = diffOutput.split('\n');
  const violations = [];

  for (const line of lines) {
    for (const pattern of lazyPatterns) {
      if (pattern.test(line)) {
        violations.push(line.slice(1).trim());
        break;
      }
    }
  }

  if (violations.length > 0) {
    finishBlock(
      `[ANTI-LAZY CODE GATE VIOLATION]: Detected incomplete implementation / lazy placeholders:\n` +
      violations.slice(0, 5).map(v => `  - "${v}"`).join('\n') +
      `\nPer the Karpathy quality guidelines, all code must be fully implemented and verified. Remove placeholders and finish the implementation.`
    );
  }
} catch (e) {
  // Git diff failed or clean
}

finishAllow();
