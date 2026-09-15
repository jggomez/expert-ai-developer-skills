#!/usr/bin/env node
/**
 * senior-dev-flutter Stop gate. When the session ends in a Flutter/Dart repo
 * and `dart` is on PATH, runs `dart analyze` (fast). If it fails, the agent is
 * not allowed to finish until it's clean. `flutter test` is NOT run here (too
 * slow for a Stop hook) — the reason text reminds the agent to run it.
 * No-op on a non-Flutter repo or when `dart` is unavailable.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);

let raw = '';
try {
  raw = fs.readFileSync(0, 'utf-8');
} catch (e) {
  finishAllow();
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

const pubspec = path.join(cwd, 'pubspec.yaml');
if (!fs.existsSync(pubspec)) finishAllow();

let dartOk = true;
try {
  execSync('dart --version', { stdio: 'ignore' });
} catch (e) {
  dartOk = false;
}
if (!dartOk) finishAllow();

try {
  execSync('dart analyze', { cwd, stdio: 'pipe', timeout: 120000 });
} catch (error) {
  const out =
    (error.stdout ? error.stdout.toString() : '') +
    (error.stderr ? error.stderr.toString() : '');
  const reason =
    'Flutter quality gate: `dart analyze` is not clean. Fix the analyzer ' +
    'findings (use the dart-run-static-analysis skill) before finishing. Also ' +
    'run `flutter test` — this hook does not.\n\n' +
    out.slice(0, 4000);

  if (isClaudeCode) {
    console.error(reason);
    process.exit(2); // blocks the stop, feeds stderr back
  } else {
    console.log(JSON.stringify({ decision: 'continue', reason }));
    process.exit(0);
  }
}

finishAllow();

function finishAllow() {
  if (!isClaudeCode) console.log(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}
