#!/usr/bin/env node
/**
 * shared-context: on session start, if a context/ directory with prior sessions
 * exists, tell the agent to ask the user whether to load it (via the
 * context-restore skill) before doing other work. Never loads anything itself.
 *
 * Claude Code: wired to SessionStart. Antigravity: wired to PreInvocation
 * (no SessionStart event there), debounced so it prompts about once per
 * working session, not per turn.
 */
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const { execFileSync } = require('child_process');

const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);
const PROMPT_TTL_MS = 4 * 60 * 60 * 1000; // re-prompt at most every 4h per repo

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

  const listScript = path.join(
    __dirname, '..', 'skills', 'context-restore', 'scripts', 'context_list.py'
  );
  if (!fs.existsSync(listScript)) return exitQuiet();

  let info;
  try {
    const out = execFileSync('python3', [listScript, '--json'], {
      cwd,
      encoding: 'utf-8',
      stdio: ['ignore', 'pipe', 'ignore'],
    });
    info = JSON.parse(out);
  } catch (e) {
    return exitQuiet();
  }
  if (!info || !info.exists || !info.count) return exitQuiet();

  // Debounce via a machine-local marker in the temp dir.
  const key = crypto.createHash('sha1').update(path.resolve(cwd)).digest('hex').slice(0, 16);
  const marker = path.join(os.tmpdir(), `shared-context-start-${key}.json`);
  try {
    const prev = JSON.parse(fs.readFileSync(marker, 'utf-8'));
    if (prev && Date.now() - prev.at < PROMPT_TTL_MS) return exitQuiet();
  } catch (e) {
    /* no marker yet */
  }
  try {
    fs.writeFileSync(marker, JSON.stringify({ at: Date.now() }));
  } catch (e) {
    /* best effort */
  }

  const latest = info.sessions[0] || {};
  const extras = [
    info.preferences ? 'preferences.md' : null,
    info.architecture ? 'architecture.md' : null,
  ].filter(Boolean);

  const message =
    `Shared AI context is available at \`context/\` — ${info.count} prior ` +
    `session(s)${extras.length ? ` plus ${extras.join(' + ')}` : ''}. ` +
    `Latest: ${latest.date || '?'} \`${latest.session || '?'}\` ` +
    `[${latest.host || '?'}/${latest.agent || '?'}, ${latest.status || '?'}]` +
    (latest.task ? ` — "${latest.task}"` : '') + '.\n' +
    `Before doing other work, follow the \`context-restore\` skill: summarize ` +
    `what's there and ASK the user which set to load (Full / Light / Just list ` +
    `/ Skip). Do not load any context without the user's explicit OK.`;

  emit(message);
}

function emit(text) {
  if (isClaudeCode) {
    process.stdout.write(JSON.stringify({
      hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext: text },
    }));
  } else {
    // Antigravity / other: plain-text context injection.
    process.stdout.write(text);
  }
  process.exit(0);
}

function exitQuiet() {
  if (isClaudeCode) process.stdout.write('{}');
  process.exit(0);
}

main();
