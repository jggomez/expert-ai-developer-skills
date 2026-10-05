#!/usr/bin/env node
/**
 * senior-dev-flutter Stop gate for Claude Code.
 * When the session ends in a Flutter/Dart repo and `dart` is on PATH,
 * runs `dart analyze`. If it fails, the agent is blocked from stopping
 * (console.error and exit code 2).
 * No-op on non-Flutter repo or when `dart` is unavailable.
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

const pubspec = path.join(cwd, 'pubspec.yaml');
if (!fs.existsSync(pubspec)) {
  process.exit(0);
}

let dartOk = true;
try {
  execSync('dart --version', { stdio: 'ignore' });
} catch (e) {
  dartOk = false;
}
if (!dartOk) {
  process.exit(0);
}

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

  console.error(reason);
  process.exit(2); // Claude Code stop failure contract: console.error and exit 2
}

process.exit(0);
