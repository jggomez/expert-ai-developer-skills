'use strict';
/**
 * Shared helpers for plugin hooks, for both Claude Code and Google Antigravity.
 *
 * CANONICAL SOURCE: scripts/hook-lib/gate-utils.js
 * Copied verbatim into plugins/{claude,antigravity}/<plugin>/hooks/shared/ by scripts/sync_agents.py.
 * Never edit the copies; tests/unit/test_{claude,antigravity}_gate_utils.py fail on drift.
 *
 * Host contract (detected from the stdin payload by readStdinJson):
 * - Claude Code: block = stderr + exit 2; turn retries flagged by `stop_hook_active`.
 * - Antigravity (antigravity.google/docs/hooks): always exit 0 with JSON on stdout
 *   (`{"decision":"continue","reason"}` keeps a Stop going; non-zero exits are ignored);
 *   no retry flag, so a turn is keyed by conversationId + lastUserInput; the workspace is
 *   `workspacePaths[0]` resolved to its git root; Stop only verifies a normal finish.
 *
 * 1. Stop-gate state (createStopGate):
 *    - Bounded retries: a gate blocks at most MAX_BLOCKS consecutive times inside one user
 *      turn, then lets the turn end with a notice instead of looping forever.
 *    - Change detection: verification is skipped when no code file changed, or when the
 *      exact same code state already passed this gate (fingerprint = HEAD + changed code
 *      file contents).
 *    - Cross-plugin de-duplication: gates sharing a `gateId` (e.g. two plugins both running
 *      pytest) serialise through a lock file; the second one reuses the first one's result.
 * 2. Plan-first relaxation (isSmallEdit): small, surgical `Edit` calls (Tier 1 fixes)
 *    do not require a PLAN.md.
 * 3. Role detection (isAgent): reads Claude Code's `agent_type` hook field.
 */
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync, execSync } = require('child_process');

const MAX_BLOCKS = 3;
const FINAL_STOP_REASONS = new Set(['NO_TOOL_CALL', 'model_stop']);
const SMALL_EDIT_MAX_LINES = 10;
const LOCK_STALE_MS = 10 * 60 * 1000;
const LOCK_POLL_MS = 250;

const NON_CODE_EXTENSIONS = new Set([
  '.md', '.mdx', '.txt', '.rst', '.adoc',
  '.png', '.jpg', '.jpeg', '.gif', '.webp', '.svg', '.pdf', '.ico',
  '.log', '.lock',
]);
const NON_CODE_DIRS = ['docs/', 'doc/', 'context/', '.claude/', '.agents/', 'evidence/', '.github/ISSUE_TEMPLATE/'];

/**
 * Reads the whole hook payload from stdin (fd 0).
 * Never touch `process.stdin` here: creating that stream switches a pipe to non-blocking
 * mode, and readFileSync(0) then throws EAGAIN whenever the payload has not arrived yet.
 * EAGAIN is still retried in case the parent hands over a non-blocking pipe.
 */
function readStdinRaw(timeoutMs = 10000) {
  if (require('tty').isatty(0)) return '';
  const chunks = [];
  const buf = Buffer.alloc(65536);
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    let n;
    try {
      n = fs.readSync(0, buf, 0, buf.length, null);
    } catch (err) {
      if (err.code === 'EAGAIN' && Date.now() < deadline) {
        sleep(10);
        continue;
      }
      if (err.code === 'EOF') break;
      throw err;
    }
    if (n === 0) break;
    chunks.push(Buffer.from(buf.subarray(0, n)));
  }
  return Buffer.concat(chunks).toString('utf-8');
}

let host = 'claude';

/** 'antigravity' for Antigravity payloads (conversationId / workspacePaths / toolCall), else 'claude'. */
function detectHost(payload) {
  if (!payload || payload.hook_event_name) return 'claude';
  return payload.conversationId || Array.isArray(payload.workspacePaths) || payload.toolCall ? 'antigravity' : 'claude';
}

function hostOf() {
  return host;
}

function readStdinJson() {
  let raw = '';
  try {
    raw = readStdinRaw();
  } catch (err) {
    process.stderr.write(`[gate-utils] could not read hook payload from stdin: ${err.message}\n`);
    return {};
  }
  if (!raw.trim()) return {};
  try {
    const parsed = JSON.parse(raw);
    const payload = parsed && typeof parsed === 'object' ? parsed : {};
    host = detectHost(payload);
    return payload;
  } catch (err) {
    return {};
  }
}

function git(cwd, args) {
  // --no-optional-locks: never take .git/index.lock (parallel hooks, user's own git commands).
  return execFileSync('git', ['--no-optional-locks', ...args], { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] });
}

/**
 * Directory the checks run in: the git root of the host's workspace. Claude Code sends `cwd`,
 * which follows the shell (a `cd apps/x` in a Bash call would otherwise make the Stop gate pick
 * up that subfolder's pyproject.toml); Antigravity sends `workspacePaths`, which may point at a
 * subfolder. Both resolve to the git root so PLAN.md, tests and .git are found and the gate runs
 * the same checks no matter where the agent last stood. Outside git the path is used as is.
 * (Antigravity runs hooks with the plugin root as cwd, so process.cwd() is only a last resort.)
 */
function workspaceOf(payload) {
  const ws = payload.cwd || (Array.isArray(payload.workspacePaths) ? payload.workspacePaths[0] : null);
  if (!ws) return process.cwd();
  try {
    return git(ws, ['rev-parse', '--show-toplevel']).trim() || ws;
  } catch (err) {
    return ws;
  }
}

/** True when `cmd` resolves on PATH. */
function commandExists(cmd) {
  try {
    if (process.platform === 'win32') execFileSync('where', [cmd], { stdio: 'ignore' });
    else execSync(`command -v ${cmd}`, { stdio: 'ignore', shell: '/bin/sh' });
    return true;
  } catch (err) {
    return false;
  }
}

/**
 * The command that runs pytest inside the project's own environment, or null when none exists.
 * A global `pytest` from PATH cannot import the project's dependencies, so it fails every module:
 * `uv run` (uv.lock), the project's virtualenv, `poetry run` (poetry.lock), and PATH only last.
 */
function pytestCommand(root) {
  const has = (rel) => fs.existsSync(path.join(root, rel));
  if (has('uv.lock') && commandExists('uv')) return 'uv run pytest -q';
  for (const venv of ['.venv', 'venv']) {
    const bin = path.join(root, venv, process.platform === 'win32' ? 'Scripts' : 'bin',
      process.platform === 'win32' ? 'pytest.exe' : 'pytest');
    if (fs.existsSync(bin)) return `"${bin}" -q`;
  }
  if (has('poetry.lock') && commandExists('poetry')) return 'poetry run pytest -q';
  if (commandExists('pytest')) return 'pytest -q';
  return null;
}

/**
 * Where a plan-first gate accepts the plan, relative to a checkout root. The orchestrator keeps a
 * feature's plan with its other artifacts in `docs/<feature-name>/PLAN.md` (see plansIn); these
 * root locations stay accepted for projects that still carry a root PLAN.md.
 */
const PLAN_LOCATIONS = ['PLAN.md', path.join('docs', 'PLAN.md'), path.join('doc', 'PLAN.md'), path.join('.agents', 'PLAN.md'), path.join('.claude', 'PLAN.md')];

/** Every plan under `root`: `docs/<feature-name>/PLAN.md` first, then the legacy root locations. */
function plansIn(root) {
  const found = [];
  try {
    for (const entry of fs.readdirSync(path.join(root, 'docs'), { withFileTypes: true }).sort((a, b) => a.name.localeCompare(b.name))) {
      if (!entry.isDirectory()) continue;
      const candidate = path.join(root, 'docs', entry.name, 'PLAN.md');
      if (fs.existsSync(candidate)) found.push(candidate);
    }
  } catch (err) {
    // no docs/ folder
  }
  for (const rel of PLAN_LOCATIONS) {
    const candidate = path.join(root, rel);
    if (fs.existsSync(candidate)) found.push(candidate);
  }
  return found;
}

/**
 * Path of the active PLAN.md for `dir`, or null. Looks in `dir`, then in the main checkout when
 * `dir` is a linked git worktree: PLAN.md is usually untracked, so a parallel implementer's fresh
 * worktree does not contain it even though the orchestrator wrote it.
 */
function findPlan(dir) {
  if (!dir) return null;
  const roots = [dir];
  try {
    const common = git(dir, ['rev-parse', '--path-format=absolute', '--git-common-dir']).trim();
    if (common && path.basename(common) === '.git') roots.push(path.dirname(common));
  } catch (err) {
    // Not a git repository (or git unavailable): only `dir` itself is checked.
  }
  for (const root of roots) {
    const plans = plansIn(root);
    if (plans.length) return plans[0];
  }
  return null;
}

/**
 * Antigravity also fires Stop on errors, cancellations and step limits; only a normal finish is
 * verified. Live `agy` runs send `NO_TOOL_CALL` when the model finishes.
 * `fullyIdle: false` means background tasks (e.g. parallel subagents) are still running, so the
 * tree may hold other workers' half-finished edits: verify once everything is idle.
 */
function isFinalStop(payload) {
  if (detectHost(payload) !== 'antigravity') return true;
  if (payload.fullyIdle === false) return false;
  return !payload.terminationReason || FINAL_STOP_REASONS.has(payload.terminationReason);
}

function resolveGitDir(cwd) {
  try {
    const dir = git(cwd, ['rev-parse', '--git-dir']).trim();
    return path.isAbsolute(dir) ? dir : path.join(cwd, dir);
  } catch (err) {
    return null;
  }
}

function isCodePath(relPath) {
  const normalized = relPath.replace(/\\/g, '/');
  if (NON_CODE_DIRS.some((dir) => normalized.startsWith(dir) || normalized.includes(`/${dir}`))) return false;
  return !NON_CODE_EXTENSIONS.has(path.extname(normalized).toLowerCase());
}

/** Paths (relative to the repo root) of changed or untracked code files. */
function changedCodeFiles(cwd) {
  const out = git(cwd, ['status', '--porcelain', '-uall', '-z']);
  const entries = out.split('\0').filter(Boolean);
  const files = [];
  for (let i = 0; i < entries.length; i += 1) {
    const entry = entries[i];
    const status = entry.slice(0, 2);
    const file = entry.slice(3);
    if (status.startsWith('R') || status.startsWith('C')) i += 1; // skip rename/copy source
    if (isCodePath(file)) files.push(file);
  }
  return files.sort();
}

function fingerprintOf(cwd, files) {
  const hash = crypto.createHash('sha1');
  let head = 'no-head';
  try {
    head = git(cwd, ['rev-parse', 'HEAD']).trim();
  } catch (err) {
    head = 'no-head';
  }
  hash.update(head);
  const root = git(cwd, ['rev-parse', '--show-toplevel']).trim();
  for (const file of files) {
    hash.update(`\0${file}\0`);
    try {
      hash.update(fs.readFileSync(path.join(root, file)));
    } catch (err) {
      hash.update('<deleted>');
    }
  }
  return hash.digest('hex');
}

function sleep(ms) {
  Atomics.wait(new Int32Array(new SharedArrayBuffer(4)), 0, 0, ms);
}

function loadJson(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8'));
  } catch (err) {
    return {};
  }
}

function saveJson(file, data) {
  try {
    const tmp = `${file}.${process.pid}.tmp`;
    fs.writeFileSync(tmp, JSON.stringify(data, null, 2));
    fs.renameSync(tmp, file);
  } catch (err) {
    process.stderr.write(`[gate-utils] could not persist gate state to ${file}: ${err.message}\n`);
  }
}

/**
 * @param {object} opts
 * @param {string} opts.gateId   Shared id for identical verifications across plugins (e.g. 'python-tests').
 * @param {object} opts.payload  Parsed hook stdin.
 * @param {number} [opts.maxBlocks]
 * @param {(file: string) => boolean} [opts.fileFilter]  Keeps only the changed code files this gate
 *   cares about (e.g. UI files): the fingerprint, the "no code changes" skip and isRepeat() then
 *   ignore every other change.
 */
function createStopGate({ gateId, payload, maxBlocks = MAX_BLOCKS, fileFilter = null }) {
  const cwd = workspaceOf(payload);
  const gitDir = resolveGitDir(cwd);
  const stateDir = gitDir || os.tmpdir();
  const scope = gitDir ? 'repo' : crypto.createHash('sha1').update(cwd).digest('hex').slice(0, 12);
  const stateFile = path.join(stateDir, `claude-stop-gates-${scope}.json`);
  const lockFile = path.join(stateDir, `claude-stop-gate-${gateId}-${scope}.lock`);
  // Claude Code flags retries inside a turn; Antigravity has no flag, so the turn is keyed by
  // conversation + latest user message (a new message resets the block counter).
  const turnKey = detectHost(payload) === 'antigravity'
    ? crypto.createHash('sha1').update(`${payload.conversationId || ''}\0${payload.lastUserInput || ''}`).digest('hex')
    : null;
  const isContinuing = (gate) => (turnKey ? gate.turn === turnKey : payload.stop_hook_active === true);
  const startedAt = Date.now();

  let files = null;
  let fingerprint = null;
  if (gitDir) {
    try {
      files = changedCodeFiles(cwd);
      if (typeof fileFilter === 'function') files = files.filter(fileFilter);
      fingerprint = fingerprintOf(cwd, files);
    } catch (err) {
      files = null;
      fingerprint = null;
    }
  }

  let lockHeld = false;
  let repeat = false;

  function readGateState() {
    const state = loadJson(stateFile);
    return { state, gate: state[gateId] || {} };
  }

  function writeGateState(update) {
    const { state, gate } = readGateState();
    state[gateId] = Object.assign({}, gate, update, { updatedAt: new Date().toISOString() });
    saveJson(stateFile, state);
  }

  function releaseLock() {
    if (!lockHeld) return;
    try {
      fs.unlinkSync(lockFile);
    } catch (err) {
      process.stderr.write(`[gate-utils] could not release lock ${lockFile}: ${err.message}\n`);
    }
    lockHeld = false;
  }

  function acquireLockOrWait() {
    const deadline = Date.now() + LOCK_STALE_MS;
    while (Date.now() < deadline) {
      try {
        fs.writeFileSync(lockFile, String(process.pid), { flag: 'wx' });
        lockHeld = true;
        return true;
      } catch (err) {
        if (err.code !== 'EEXIST') return true; // cannot lock (read-only dir) -> just run
        try {
          if (Date.now() - fs.statSync(lockFile).mtimeMs > LOCK_STALE_MS) fs.unlinkSync(lockFile);
        } catch (statErr) {
          // lock vanished between calls; retry immediately
        }
        sleep(LOCK_POLL_MS);
      }
    }
    return true;
  }

  return {
    cwd,
    gateId,
    changedFiles: files,

    /**
     * Returns a reason string when verification should be skipped, otherwise null.
     * When it returns null the gate holds its lock: call markPass() or markFail() next.
     */
    begin() {
      const { gate } = readGateState();
      const continuing = isContinuing(gate);
      const blocks = continuing ? gate.blocks || 0 : 0;
      // `seen` is the state at the previous Stop: a new turn that left these files untouched
      // (a plain answer, or edits elsewhere) is a repeat of a state already reported.
      repeat = !continuing && Boolean(fingerprint) && gate.seen === fingerprint;
      const update = {};
      if (fingerprint && gate.seen !== fingerprint) update.seen = fingerprint;
      if (!continuing && gate.blocks) update.blocks = 0;
      if (Object.keys(update).length) writeGateState(update);

      if (continuing && blocks >= maxBlocks) {
        return `retry-limit (${blocks}/${maxBlocks} blocks this turn)`;
      }
      if (fingerprint) {
        if (gate.green === fingerprint) return 'unchanged since last green run';
        if (!gate.green && files && files.length === 0) {
          writeGateState({ green: fingerprint });
          return 'no code changes';
        }
      }

      acquireLockOrWait();
      // Another plugin may have verified this exact state while we waited for the lock.
      const after = readGateState().gate;
      // A result recorded while we waited comes from a gate that ran in parallel on the same
      // Stop event: reuse it even when no fingerprint is available (git error, non-git dir).
      const finishedWhileWaiting = (at) => (at || 0) >= startedAt;
      if ((fingerprint && after.green === fingerprint) || (finishedWhileWaiting(after.greenAt) && !after.red)) {
        releaseLock();
        return 'verified by a parallel gate';
      }
      if (finishedWhileWaiting(after.redAt) && (!fingerprint || [fingerprint, 'unknown'].includes(after.red))) {
        releaseLock();
        return 'already reported by a parallel gate';
      }
      return null;
    },

    retryLimitReached() {
      const { gate } = readGateState();
      const reached = isContinuing(gate) && (gate.blocks || 0) >= maxBlocks;
      // The turn ends here: remember the state it leaves behind so the next turn can tell
      // whether it touched these files at all.
      if (reached && fingerprint && gate.seen !== fingerprint) writeGateState({ seen: fingerprint });
      return reached;
    },

    /**
     * True (after begin()) when this is a new turn and the gate's files are exactly as the
     * previous turn left them: the check may run, but blocking again would only repeat a
     * verdict the agent already received.
     */
    isRepeat() {
      return repeat;
    },

    markPass() {
      writeGateState({ green: fingerprint, greenAt: Date.now(), red: null, redAt: null, blocks: 0 });
      releaseLock();
    },

    /** Releases the lock without recording a result (e.g. the check was skipped for time). */
    abandon() {
      releaseLock();
    },

    /**
     * Records the failure and returns the reason decorated with the retry counter.
     * `blocking: false` records the red state without spending one of the turn's blocks
     * (the caller reports it as a notice instead of stopping the agent).
     */
    markFail(reason, { blocking = true } = {}) {
      const { gate } = readGateState();
      if (!blocking) {
        writeGateState({ red: fingerprint || 'unknown', redAt: Date.now(), greenAt: null });
        releaseLock();
        return reason;
      }
      const blocks = (isContinuing(gate) ? gate.blocks || 0 : 0) + 1;
      writeGateState({ red: fingerprint || 'unknown', redAt: Date.now(), greenAt: null, blocks, turn: turnKey });
      releaseLock();
      return `${reason}\n\n[stop gate ${gateId}: block ${blocks}/${maxBlocks} this turn]`;
    },
  };
}

/**
 * Keeps the agent working and feeds `reason` back to the model.
 * Claude Code: stderr + exit 2. Antigravity: {"decision":"continue"} on stdout, exit 0.
 */
function exitBlock(reason) {
  if (host === 'antigravity') {
    process.stdout.write(JSON.stringify({ decision: 'continue', reason }));
    process.exit(0);
  }
  process.stderr.write(`${reason}\n`);
  process.exit(2);
}

/**
 * Lets the agent stop / the tool run. Claude Code shows `notice` to the user as a systemMessage;
 * Antigravity has no user notice for an allowed Stop, so it goes to the hook log (stderr).
 */
function exitAllow(notice) {
  if (host === 'antigravity') {
    if (notice) process.stderr.write(`${notice}\n`);
    process.stdout.write(JSON.stringify({ decision: 'allow' }));
    process.exit(0);
  }
  if (notice) process.stdout.write(JSON.stringify({ systemMessage: notice }));
  process.exit(0);
}

/**
 * Wall-clock budget for a hook that runs several checks: the host kills a hook at its
 * hooks.json `timeout`, so each check gets min(its own limit, what is left).
 * @param {number} totalMs  The hook's hooks.json timeout, in ms.
 */
function createBudget(totalMs, reserveMs = 5000) {
  const deadline = Date.now() + totalMs - reserveMs;
  return {
    remaining: () => Math.max(0, deadline - Date.now()),
    timeout: (maxMs) => Math.max(0, Math.min(maxMs, deadline - Date.now())),
  };
}

/** First `maxBytes` of a file as UTF-8 ('' when unreadable): never load a whole transcript. */
function readFileHead(file, maxBytes = 4096) {
  let fd = null;
  try {
    fd = fs.openSync(file, 'r');
    const buf = Buffer.alloc(maxBytes);
    const n = fs.readSync(fd, buf, 0, maxBytes, 0);
    return buf.subarray(0, n).toString('utf8');
  } catch (err) {
    return '';
  } finally {
    if (fd !== null) fs.closeSync(fd);
  }
}

/** Notice shown when a gate gives up after MAX_BLOCKS consecutive blocks. */
function retryLimitNotice(gateId, maxBlocks = MAX_BLOCKS) {
  return `[stop gate ${gateId}] still failing after ${maxBlocks} fix attempts this turn; ` +
    'letting the turn end. Review the failures above before continuing.';
}

/** True when the hook fires inside one of the named orchestrator agents (main thread via --agent or subagent). */
function isAgent(payload, names) {
  const type = String((payload && payload.agent_type) || '');
  if (!type) return false;
  const bare = type.includes(':') ? type.slice(type.lastIndexOf(':') + 1) : type;
  return names.includes(bare);
}

/**
 * True for a surgical edit of an existing file (both sides <= maxLines lines in total):
 * Claude Code `Edit` (no replace_all), Antigravity `replace_file_content` (no AllowMultiple)
 * and `multi_replace_file_content` (all chunks together). Whole-file writes never qualify.
 */
function isSmallEdit(toolName, toolInput, maxLines = SMALL_EDIT_MAX_LINES) {
  if (!toolInput) return false;
  const lines = (s) => (typeof s === 'string' ? s.split('\n').length : Infinity);
  const name = toolName || '';
  if (/^Edit$/i.test(name)) {
    if (toolInput.replace_all) return false;
    return lines(toolInput.old_string) <= maxLines && lines(toolInput.new_string) <= maxLines;
  }
  if (name === 'replace_file_content') {
    if (toolInput.AllowMultiple) return false;
    return lines(toolInput.TargetContent) <= maxLines && lines(toolInput.ReplacementContent) <= maxLines;
  }
  if (name === 'multi_replace_file_content') {
    const chunks = toolInput.ReplacementChunks;
    if (!Array.isArray(chunks) || chunks.length === 0) return false;
    const total = (key) => chunks.reduce((sum, chunk) => sum + lines(chunk && chunk[key]), 0);
    return total('TargetContent') <= maxLines && total('ReplacementContent') <= maxLines;
  }
  return false;
}

/** Production code the fake-data check reads (UI, mobile Dart and backends alike). */
const FAKE_DATA_FILE = /\.(ts|tsx|js|jsx|mjs|vue|svelte|html|dart|py|go|kt|swift|java)$/i;

/**
 * Fake-data gate shared by every Stop gate: runs check_fake_data.py when changed production code
 * (mobile Flutter and backends included) is not yet known to be clean. Returns null when it passes
 * or does not apply, `{ block }` with the reason to block, or `{ notice }` after the retry limit.
 * One gate id across plugins, so a Stop that runs several gates checks the same files once.
 */
function runFakeDataGate({ payload, script, timeoutMs = 60000 }) {
  if (!script || !fs.existsSync(script) || !commandExists('python3')) return null;
  const root = workspaceOf(payload);
  let files;
  try {
    files = changedCodeFiles(root).filter((file) => FAKE_DATA_FILE.test(file));
  } catch (err) {
    return null; // not a git repository: nothing to compare against
  }
  if (files.length === 0) return null;
  const gate = createStopGate({ gateId: 'fake-data', payload, fileFilter: (file) => FAKE_DATA_FILE.test(file) });
  if (gate.retryLimitReached()) return { notice: retryLimitNotice('fake-data') };
  if (gate.begin()) return null;
  try {
    execFileSync('python3', [script, '--repo', root], { cwd: root, stdio: 'pipe', timeout: timeoutMs });
    gate.markPass();
    return null;
  } catch (error) {
    const out = `${error.stdout ? error.stdout.toString() : ''}${error.stderr ? error.stderr.toString() : ''}` ||
      error.message || '';
    return {
      block: gate.markFail('[FAKE DATA GATE]: Production code returns invented data instead of its real source ' +
        '(API, database, Firebase). Connect the real source, or ask the user to approve a demo ' +
        '(`demo-data: approved` in the file and in docs/<feature-name>/PLAN.md).\n\nOutput:\n' + out.slice(0, 3000)),
    };
  }
}

module.exports = {
  MAX_BLOCKS,
  SMALL_EDIT_MAX_LINES,
  readStdinJson,
  detectHost,
  hostOf,
  workspaceOf,
  commandExists,
  pytestCommand,
  findPlan,
  isFinalStop,
  isCodePath,
  changedCodeFiles,
  runFakeDataGate,
  createStopGate,
  exitBlock,
  exitAllow,
  retryLimitNotice,
  createBudget,
  readFileHead,
  isSmallEdit,
  isAgent,
};
