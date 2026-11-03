#!/usr/bin/env node
/**
 * senior-dev-flutter Stop gate for Claude Code.
 * When the session ends in a Flutter/Dart repo and `dart` is on PATH,
 * runs `dart analyze`. If it fails, the agent is blocked from stopping
 * (console.error and exit code 2).
 * No-op on non-Flutter repo or when `dart` is unavailable.
 * Skips when no code changed / the same code state already passed, shares the
 * 'dart-analyze' gate with senior-dev's universal gate (runs once), and gives up
 * after 3 blocks per turn (see hooks/shared/gate-utils.js).
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');
const g = require(path.join(__dirname, 'shared', 'gate-utils.js'));

const payload = g.readStdinJson();
if (!g.isFinalStop(payload)) g.exitAllow();
const cwd = g.workspaceOf(payload);

const pubspec = path.join(cwd, 'pubspec.yaml');
if (!fs.existsSync(pubspec)) {
  g.exitAllow();
}

let dartOk = true;
try {
  execSync('dart --version', { stdio: 'ignore' });
} catch (e) {
  dartOk = false;
}
if (!dartOk) {
  g.exitAllow();
}

const gate = g.createStopGate({ gateId: 'dart-analyze', payload });
if (gate.retryLimitReached()) {
  g.exitAllow(g.retryLimitNotice('dart-analyze'));
}
if (gate.begin()) {
  g.exitAllow();
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

  g.exitBlock(gate.markFail(reason)); // host-aware block (hooks/shared/gate-utils.js)
}

gate.markPass();
g.exitAllow();
