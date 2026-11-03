#!/usr/bin/env node
/**
 * docs-and-quality Stop gate for Claude Code.
 * Enforces production-grade code completeness by checking git diff for lazy LLM stubs:
 * - "TODO: implement later"
 * - "// ... rest of code" / "# ... rest of code"
 * - "pass # placeholder"
 * - "/* unimplemented *\/" / "// unimplemented"
 * If lazy stubs are detected in code files, blocks stopping (console.error + exit code 2).
 * Gives up after 3 blocks per turn and skips unchanged code states (hooks/shared/gate-utils.js).
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const g = require(path.join(__dirname, 'shared', 'gate-utils.js'));

const payload = g.readStdinJson();
if (!g.isFinalStop(payload)) g.exitAllow();
const cwd = g.workspaceOf(payload);

const gate = g.createStopGate({ gateId: 'anti-lazy', payload });
if (gate.retryLimitReached()) {
  g.exitAllow(g.retryLimitNotice('anti-lazy'));
}
if (gate.begin()) {
  g.exitAllow();
}

// Verify git repository
try {
  execSync('git rev-parse --is-inside-work-tree', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
} catch (e) {
  gate.markPass();
  g.exitAllow(); // Not a git repo
}

let diff = '';
try {
  diff = execSync('git diff HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
} catch (e) {
  try {
    diff =
      execSync('git diff', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }) + '\n' +
      execSync('git diff --cached', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
  } catch (err) {
    diff = '';
  }
}

// Untracked files never appear in `git diff HEAD`: scan their content as added lines.
try {
  const untracked = execSync('git ls-files --others --exclude-standard -z', {
    cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'],
  }).split('\0').filter(Boolean);
  for (const file of untracked.slice(0, 200)) {
    const full = path.join(cwd, file);
    try {
      if (fs.statSync(full).size > 512 * 1024) continue; // generated or binary blobs
      const content = fs.readFileSync(full, 'utf8');
      diff += `\ndiff --git a/${file} b/${file}\n` + content.split('\n').map((l) => `+${l}`).join('\n');
    } catch (err) {
      // unreadable or vanished file: nothing to scan
    }
  }
} catch (e) {
  // git ls-files failed: the tracked diff is still scanned
}

if (!diff.trim()) {
  gate.markPass();
  g.exitAllow();
}

// Lazy stub patterns
const LAZY_PATTERNS = [
  { name: 'TODO implement later', regex: /\bTODO:\s*(?:implement\s+later|finish\s+later|add\s+later|to\s+be\s+implemented)\b/i },
  { name: 'your code here placeholder', regex: /(?:\/\/|#)\s*(?:your\s+code\s+here|implement\s+here)\b/i },
  { name: 'UnimplementedError stub', regex: /\bthrow\s+UnimplementedError\(\s*\)/ },
  { name: 'rest of code placeholder', regex: /(?:\/\/|#|\/\*)\s*\.\.\.\s*rest of (?:the )?code/i },
  { name: 'pass placeholder', regex: /\bpass\s*#\s*(?:placeholder|todo|implement|later)\b/i },
  { name: 'unimplemented stub', regex: /(?:\/\*|\/\/|#)\s*unimplemented\b/i },
];

const lines = diff.split('\n');
let currentFile = '';
const violations = [];

// Extensions to skip (documentation and non-code files)
const DOC_EXTENSIONS = new Set(['.md', '.txt', '.rst', '.json', '.yaml', '.yml']);

for (const line of lines) {
  if (line.startsWith('diff --git a/')) {
    const parts = line.split(' ');
    currentFile = parts[parts.length - 1].replace(/^b\//, '');
    continue;
  }

  // Only inspect newly added lines (starting with + but not +++)
  if (line.startsWith('+') && !line.startsWith('+++')) {
    const ext = path.extname(currentFile).toLowerCase();
    if (DOC_EXTENSIONS.has(ext)) {
      continue;
    }

    const addedContent = line.slice(1);
    for (const pattern of LAZY_PATTERNS) {
      if (pattern.regex.test(addedContent)) {
        violations.push({
          file: currentFile,
          line: addedContent.trim(),
          pattern: pattern.name,
        });
        break;
      }
    }
  }
}

if (violations.length > 0) {
  const reason =
    `[ANTI-LAZY CODE GATE VIOLATION]: Detected ${violations.length} lazy placeholder stub(s) in code changes:\n` +
    violations.map(v => `  - ${v.file}: "${v.line}" (matched: ${v.pattern})`).join('\n') +
    `\n\nPer Karpathy Guidelines and quality standards, LLM shortcut stubs are prohibited. ` +
    `Provide complete, robust, production-grade implementations for all methods before finishing.`;

  g.exitBlock(gate.markFail(reason)); // host-aware block (hooks/shared/gate-utils.js)
}

gate.markPass();
g.exitAllow();
