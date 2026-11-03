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
const cwd = g.workspaceOf(payload);

const gate = g.createStopGate({ gateId: 'anti-lazy', payload });
if (gate.retryLimitReached()) {
  g.exitAllow(g.retryLimitNotice('anti-lazy'));
}
if (gate.begin()) {
  process.exit(0);
}

// Verify git repository
try {
  execSync('git rev-parse --is-inside-work-tree', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
} catch (e) {
  gate.markPass();
  process.exit(0); // Not a git repo
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

if (!diff.trim()) {
  gate.markPass();
  process.exit(0);
}

// Lazy stub patterns
const LAZY_PATTERNS = [
  { name: 'TODO implement later', regex: /\bTODO:\s*(?:implement\s+later|finish\s+later|add\s+later)\b/i },
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

  g.exitBlock(gate.markFail(reason)); // Claude Code stop failure contract
}

gate.markPass();
process.exit(0);
