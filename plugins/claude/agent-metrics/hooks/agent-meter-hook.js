#!/usr/bin/env node
/**
 * agent-metrics: thin, host-neutral wrapper around the standalone `agent-meter` CLI.
 *
 * Usage (from hooks.json):  node agent-meter-hook.js --host <claude-code|antigravity> --event <event>
 *
 * Runs `agent-meter hook --host <h> --event <e>` with the host's hook payload piped to its
 * stdin. All ingestion, privacy filtering (allowlisted payload keys) and notification logic
 * lives in the CLI; this file only locates it, forwards the payload and guarantees the host
 * contract (ADR-001 §3.10, PRD US-12):
 *   - always exits 0 (never blocks or fails the host), on every path;
 *   - stdout: nothing for Claude Code, exactly `{}\n` for Antigravity (it requires a JSON
 *     object, and `{}` allows the stop); the CLI's own stdout is discarded;
 *   - enforces its own timeout (AGENT_METER_HOOK_TIMEOUT_MS, default 8000, clamped to
 *     100..9000) below the 10 s host timeout and kills a hung CLI;
 *   - when `agent-meter` is not installed, prints one install hint line to stderr only.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawn } = require('child_process');

const EVENTS_BY_HOST = Object.freeze({
  'claude-code': Object.freeze(['session-end', 'task-end']),
  antigravity: Object.freeze(['task-end']),
});
const CLI_NAME = 'agent-meter';
const DOCS_URL = 'https://github.com/jggomez/expert-ai-developer-skills/blob/main/docs/agent-metrics/README.md';
const DEFAULT_TIMEOUT_MS = 8000;
const MIN_TIMEOUT_MS = 100;
const MAX_TIMEOUT_MS = 9000;
const FLUSH_GRACE_MS = 500;
const IGNORABLE_PIPE_ERRORS = new Set(['EPIPE', 'ERR_STREAM_DESTROYED', 'ECONNRESET']);

/** Parses exactly `--host <h> --event <e>` (either order); returns null when invalid. */
function parseArgs(argv) {
  if (argv.length !== 4) return null;
  const options = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i];
    if ((key !== '--host' && key !== '--event') || key.slice(2) in options) return null;
    options[key.slice(2)] = argv[i + 1];
  }
  const events = Object.prototype.hasOwnProperty.call(EVENTS_BY_HOST, options.host)
    ? EVENTS_BY_HOST[options.host]
    : null;
  if (!events || !events.includes(options.event)) return null;
  return { host: options.host, event: options.event };
}

/** The host is known from argv even when the rest is invalid, so stdout stays valid for it. */
function hostFromArgv(argv) {
  const index = argv.indexOf('--host');
  return index >= 0 ? argv[index + 1] : undefined;
}

function timeoutMs(raw) {
  const value = Number.parseInt(raw, 10);
  if (!Number.isFinite(value)) return DEFAULT_TIMEOUT_MS;
  return Math.min(MAX_TIMEOUT_MS, Math.max(MIN_TIMEOUT_MS, value));
}

function isExecutableFile(candidate) {
  try {
    if (!fs.statSync(candidate).isFile()) return false;
    if (process.platform !== 'win32') {
      fs.accessSync(candidate, fs.constants.X_OK);
    }
    return true;
  } catch (error) {
    return false; // missing or not executable: try the next candidate
  }
}

/** PATH first, then ~/.local/bin (default bin dir of `uv tool install` and `pipx`). */
function findCli(env) {
  const dirs = (env.PATH || env.Path || '').split(path.delimiter).filter(Boolean);
  dirs.push(path.join(os.homedir(), '.local', 'bin'));
  if (process.platform === 'win32' && env.APPDATA) {
    dirs.push(path.join(env.APPDATA, 'Python', 'Scripts'));
  }
  const names = process.platform === 'win32' || env.PATHEXT
    ? ['agent-meter.exe', 'agent-meter.cmd', CLI_NAME]
    : [CLI_NAME, 'agent-meter.exe', 'agent-meter.cmd'];
  for (const dir of dirs) {
    for (const name of names) {
      const candidate = path.join(dir, name);
      if (isExecutableFile(candidate)) return candidate;
    }
  }
  return null;
}

function warn(message) {
  process.stderr.write(`${message}\n`);
}

/**
 * The error class or code only (ADR 3.13.3): error messages can embed file paths, so they are
 * never printed.
 */
function describe(error) {
  if (error && typeof error.code === 'string' && error.code) return error.code;
  if (error && typeof error.name === 'string' && error.name) return error.name;
  return 'Error';
}

function createFinisher(host) {
  let finished = false;
  return function finish() {
    if (finished) return;
    finished = true;
    process.stdin.unpipe();
    process.stdin.destroy();
    // Backstop: exit even if the host never drains stdout (the write callback would not fire).
    setTimeout(() => process.exit(0), FLUSH_GRACE_MS).unref();
    const output = host === 'antigravity' ? '{}\n' : '';
    process.stdout.write(output, () => process.exit(0));
  };
}

function main() {
  const argv = process.argv.slice(2);
  const finish = createFinisher(hostFromArgv(argv));

  process.on('uncaughtException', (error) => {
    warn(`agent-meter hook wrapper: unexpected error (${describe(error)})`);
    finish();
  });
  process.stdout.on('error', (error) => {
    // The host closed our stdout (e.g. it gave up on the hook): nobody is left to read output.
    warn(`agent-meter hook wrapper: stdout closed by host (${describe(error)})`);
    process.exit(0);
  });

  const args = parseArgs(argv);
  if (!args) {
    warn('agent-meter hook wrapper: invalid arguments; expected --host <claude-code|antigravity> --event <event>');
    finish();
    return;
  }

  const cli = findCli(process.env);
  if (!cli) {
    warn(`agent-meter not installed: see ${DOCS_URL}`);
    finish();
    return;
  }

  const limitMs = timeoutMs(process.env.AGENT_METER_HOOK_TIMEOUT_MS);
  const child = spawn(cli, ['hook', '--host', args.host, '--event', args.event], {
    stdio: ['pipe', 'ignore', 'inherit'],
    shell: false,
    windowsHide: true,
  });

  const timer = setTimeout(() => {
    warn(`agent-meter hook timed out after ${limitMs} ms`);
    child.kill('SIGKILL');
    finish();
  }, limitMs);

  const done = () => {
    clearTimeout(timer);
    finish();
  };

  child.on('error', (error) => {
    warn(`agent-meter hook wrapper: could not run ${CLI_NAME} (${describe(error)})`);
    done();
  });
  child.on('exit', done);

  child.stdin.on('error', (error) => {
    // The CLI may exit before reading the whole payload; that is not an error for the host.
    if (!IGNORABLE_PIPE_ERRORS.has(error.code)) {
      warn(`agent-meter hook wrapper: stdin forwarding failed (${describe(error)})`);
    }
  });
  process.stdin.on('error', (error) => {
    warn(`agent-meter hook wrapper: could not read hook payload (${describe(error)})`);
    child.stdin.end();
  });
  process.stdin.pipe(child.stdin);
}

main();
