#!/usr/bin/env node
/**
 * shared-context: on session stop, if a context/ store exists and this session
 * did work, remind the agent to flush a final record (summary + decisions),
 * roll decisions up, and compress old sessions. Non-blocking on both hosts —
 * it nudges, it never prevents the agent from stopping.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);

function readPayload() {
  try {
    const raw = fs.readFileSync(0, 'utf-8');
    return raw.trim() ? JSON.parse(raw) : {};
  } catch (e) {
    return {};
  }
}

function main() {
  const payload = readPayload();
  const cwd =
    payload.cwd ||
    (payload.workspacePaths && payload.workspacePaths[0]) ||
    process.cwd();
  const contextDir = path.join(cwd, 'context');
  if (!fs.existsSync(contextDir)) return allow();

  // Did this session touch a tool at all? (state file is written by the
  // post-tool-autosave hook). If not, nothing to flush.
  const key = crypto.createHash('sha1').update(path.resolve(cwd)).digest('hex').slice(0, 16);
  const stateFile = path.join(os.tmpdir(), `shared-context-state-${key}.json`);
  let hadActivity = false;
  try {
    const st = JSON.parse(fs.readFileSync(stateFile, 'utf-8'));
    hadActivity = (st.calls || 0) > 0 || Boolean(st.lastNudge);
  } catch (e) {
    hadActivity = false;
  }
  if (!hadActivity) return allow();

  const message =
    'Session ending. If meaningful work happened, flush the shared context ' +
    'before stopping (context-capture skill):\n' +
    '  1. update summary.md + decisions.md for this session\n' +
    '  2. python3 ./skills/context-capture/scripts/context_snapshot.py --session <id> --status done\n' +
    '  3. python3 ./skills/context-capture/scripts/context_rollup.py\n' +
    '  4. python3 ./skills/context-capture/scripts/context_pack.py --auto';

  // Clear activity so a follow-up stop doesn't nag again.
  try {
    fs.writeFileSync(stateFile, JSON.stringify({ calls: 0, lastCheckpoint: Date.now(), lastNudge: 0 }));
  } catch (e) {
    /* best effort */
  }

  if (isClaudeCode) {
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: { hookEventName: 'Stop', additionalContext: message },
    }));
  } else {
    process.stdout.write(JSON.stringify({ decision: 'allow', reason: message }));
  }
  process.exit(0);
}

function allow() {
  if (isClaudeCode) process.stdout.write('{}');
  else process.stdout.write(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}

main();
