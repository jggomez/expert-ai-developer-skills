#!/usr/bin/env node
/**
 * shared-context: periodic checkpoint nudge. Counts tool calls and elapsed time
 * per repo (state in the OS temp dir, never committed). When the threshold from
 * context/.contextrc.json is crossed (default 25 tool calls or 10 minutes), it
 * asks the agent to checkpoint via the context-capture skill. Always
 * non-blocking — it never denies a tool call.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);
const DEFAULTS = { everyNToolCalls: 25, everyMinutes: 10 };
const NUDGE_DEBOUNCE_MS = 3 * 60 * 1000;

function readPayload() {
  try {
    const raw = fs.readFileSync(0, 'utf-8');
    return raw.trim() ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
}

function loadThresholds(contextDir) {
  try {
    const cfg = JSON.parse(fs.readFileSync(path.join(contextDir, '.contextrc.json'), 'utf-8'));
    return Object.assign({}, DEFAULTS, cfg.autosave || {});
  } catch (e) {
    return Object.assign({}, DEFAULTS);
  }
}

function main() {
  const payload = readPayload();
  const cwd =
    payload.cwd ||
    (payload.workspacePaths && payload.workspacePaths[0]) ||
    process.cwd();
  const contextDir = path.join(cwd, 'context');

  // Only nudge once a context/ store exists — starting one is a deliberate act.
  if (!fs.existsSync(contextDir)) return done();

  const th = loadThresholds(contextDir);
  const key = crypto.createHash('sha1').update(path.resolve(cwd)).digest('hex').slice(0, 16);
  const stateFile = path.join(os.tmpdir(), `shared-context-state-${key}.json`);

  let state = { calls: 0, lastCheckpoint: Date.now(), lastNudge: 0 };
  try {
    state = Object.assign(state, JSON.parse(fs.readFileSync(stateFile, 'utf-8')));
  } catch (e) {
    /* fresh */
  }
  state.calls += 1;

  const now = Date.now();
  const dueByCalls = state.calls >= th.everyNToolCalls;
  const dueByTime = now - state.lastCheckpoint >= th.everyMinutes * 60 * 1000;
  const debounced = now - state.lastNudge < NUDGE_DEBOUNCE_MS;

  let message = null;
  if ((dueByCalls || dueByTime) && !debounced) {
    const why = dueByCalls ? `${state.calls} tool calls` :
      `${Math.round((now - state.lastCheckpoint) / 60000)} min`;
    message =
      `shared-context checkpoint due (${why}). If meaningful work has happened, ` +
      `use the context-capture skill to update this session's summary.md / ` +
      `decisions.md, then run context_snapshot.py --session <id>. Keep working ` +
      `otherwise — this is only a reminder.`;
    // Optimistic reset: assume the agent will checkpoint shortly.
    state.calls = 0;
    state.lastCheckpoint = now;
    state.lastNudge = now;
  }

  try {
    fs.writeFileSync(stateFile, JSON.stringify(state));
  } catch (e) {
    /* best effort */
  }

  if (message) return done(message);
  return done();
}

function done(text) {
  if (isClaudeCode) {
    process.stdout.write(JSON.stringify(
      text
        ? { hookSpecificOutput: { hookEventName: 'PostToolUse', additionalContext: text } }
        : {}
    ));
  } else if (text) {
    process.stdout.write(JSON.stringify({ decision: 'allow', reason: text }));
  } else {
    process.stdout.write(JSON.stringify({ decision: 'allow' }));
  }
  process.exit(0);
}

main();
