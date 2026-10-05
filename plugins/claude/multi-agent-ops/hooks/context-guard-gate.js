#!/usr/bin/env node
/**
 * multi-agent-ops PreToolUse hook for Claude Code (Context Guard).
 * Protects agent context by intercepting Read tool calls on oversized or binary files:
 * 1. Blocks reading files > 500KB without pagination (offset / limit).
 * 2. Blocks reading large lockfiles / minified assets (> 200KB) without pagination.
 * 3. Blocks reading raw binary files.
 */
const fs = require('fs');
const path = require('path');

function allow() {
  process.exit(0);
}

function deny(reason) {
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  }));
  process.exit(0);
}

let inputData = '';
try {
  if (!process.stdin.isTTY) {
    inputData = fs.readFileSync(0, 'utf-8');
  }
} catch (e) {
  allow();
}

if (!inputData.trim()) allow();

let payload;
try {
  payload = JSON.parse(inputData);
} catch (e) {
  allow();
}

const toolName = payload.tool_name || '';
const toolInput = payload.tool_input || {};
const cwd = payload.cwd || (payload.workspacePaths && payload.workspacePaths[0]) || process.cwd();

if (toolName !== 'Read') {
  allow();
}

const targetFile = toolInput.file_path || toolInput.path || '';
if (!targetFile) {
  allow();
}

const resolvedPath = path.isAbsolute(targetFile) ? targetFile : path.join(cwd, targetFile);
if (!fs.existsSync(resolvedPath)) {
  allow(); // Let Read handle missing file error
}

let stats;
try {
  stats = fs.statSync(resolvedPath);
} catch (e) {
  allow();
}

if (stats.isDirectory()) {
  allow();
}

const sizeBytes = stats.size;
const sizeKb = Math.round(sizeBytes / 1024);
const filename = path.basename(targetFile).toLowerCase();
const ext = path.extname(targetFile).toLowerCase();

const hasPagination =
  (toolInput.offset !== undefined && toolInput.offset !== null) ||
  (toolInput.limit !== undefined && toolInput.limit !== null);

// 1. Binary files check
const BINARY_EXTENSIONS = new Set([
  '.png', '.jpg', '.jpeg', '.gif', '.ico', '.pdf', '.zip', '.tar', '.gz',
  '.exe', '.bin', '.dylib', '.so', '.dll', '.a', '.pyc', '.class', '.jar'
]);

if (BINARY_EXTENSIONS.has(ext)) {
  deny(
    `[CONTEXT GUARD VIOLATION]: File "${filename}" appears to be a binary file. ` +
    `Reading raw binary contents into agent context is prohibited. Use specialized inspection tools or Bash.`
  );
}

// 2. Lockfiles and minified files (> 200KB)
const LOCKFILES = new Set([
  'package-lock.json', 'pnpm-lock.yaml', 'yarn.lock', 'cargo.lock',
  'poetry.lock', 'composer.lock', 'pipfile.lock', 'pubspec.lock'
]);

const isLockOrBundle =
  LOCKFILES.has(filename) ||
  filename.endsWith('.min.js') ||
  filename.endsWith('.min.css') ||
  filename.endsWith('.map');

if (isLockOrBundle && sizeBytes > 200 * 1024 && !hasPagination) {
  deny(
    `[CONTEXT GUARD VIOLATION]: "${filename}" (${sizeKb}KB) is a large generated artifact or lockfile. ` +
    `Reading it without pagination will flood the conversation context. ` +
    `Please supply "offset" and "limit" parameters with Read, or use "Grep" to search for specific dependencies or keys.`
  );
}

// 3. General 500KB threshold
if (sizeBytes > 500 * 1024 && !hasPagination) {
  deny(
    `[CONTEXT GUARD VIOLATION]: "${filename}" (${sizeKb}KB) exceeds the 500KB safe context threshold. ` +
    `Reading large files in a single pass floods the agent context window and degrades reasoning quality. ` +
    `Please supply "offset" and "limit" parameters with Read to paginate the file, or use "Grep" / "Glob" to target specific sections.`
  );
}

allow();
