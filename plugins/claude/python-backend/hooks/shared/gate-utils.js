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
 *   `workspacePaths[0]` resolved to its git root; Stop only verifies on `model_stop`.
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
const { execFileSync } = require('child_process');

const MAX_BLOCKS = 3;
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
 * Directory the checks run in. Claude Code sends `cwd`. Antigravity sends `workspacePaths`, which
 * may point at a subfolder: resolve it to the git root so PLAN.md, tests and .git are found.
 * (Antigravity runs hooks with the plugin root as cwd, so process.cwd() is only a last resort.)
 */
function workspaceOf(payload) {
  if (payload.cwd) return payload.cwd;
  const ws = Array.isArray(payload.workspacePaths) ? payload.workspacePaths[0] : null;
  if (!ws) return process.cwd();
  try {
    return git(ws, ['rev-parse', '--show-toplevel']).trim() || ws;
  } catch (err) {
    return ws;
  }
}

/** Antigravity also fires Stop on errors and step limits; only a normal model stop is verified. */
function isFinalStop(payload) {
  if (detectHost(payload) !== 'antigravity') return true;
  return !payload.terminationReason || payload.terminationReason === 'model_stop';
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
 */
function createStopGate({ gateId, payload, maxBlocks = MAX_BLOCKS }) {
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
      fingerprint = fingerprintOf(cwd, files);
    } catch (err) {
      files = null;
      fingerprint = null;
    }
  }

  let lockHeld = false;

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
      if (!continuing && gate.blocks) writeGateState({ blocks: 0 });

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
      return isContinuing(gate) && (gate.blocks || 0) >= maxBlocks;
    },

    markPass() {
      writeGateState({ green: fingerprint, greenAt: Date.now(), red: null, redAt: null, blocks: 0 });
      releaseLock();
    },

    /** Releases the lock without recording a result (e.g. the check was skipped for time). */
    abandon() {
      releaseLock();
    },

    /** Records the failure and returns the reason decorated with the retry counter. */
    markFail(reason) {
      const { gate } = readGateState();
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

module.exports = {
  MAX_BLOCKS,
  SMALL_EDIT_MAX_LINES,
  readStdinJson,
  detectHost,
  hostOf,
  workspaceOf,
  isFinalStop,
  isCodePath,
  changedCodeFiles,
  createStopGate,
  exitBlock,
  exitAllow,
  retryLimitNotice,
  createBudget,
  readFileHead,
  isSmallEdit,
  isAgent,
};
