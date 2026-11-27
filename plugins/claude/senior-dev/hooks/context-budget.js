#!/usr/bin/env node
/**
 * Context budget (Claude Code, UserPromptSubmit): never blocks a prompt.
 *
 * Every prompt of a session carries its whole history. Measured usage showed a handful of
 * 1,000+ call sessions holding most of the spend, each prompt starting at 200k+ tokens of context.
 * This hook reads the session's last recorded usage from the transcript and, the first time the
 * context passes each level, tells the user (systemMessage) and the agent (additionalContext) to
 * save the work with context-capture and continue in a new session.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const g = require('./shared/gate-utils');

/** Levels in tokens, lowest first; each is announced once per session. */
const LEVELS = [
  {
    tokens: 200000,
    advice: 'Finish the current task, run the context-capture skill (context/memory/), and continue the next task ' +
      'in a new session: every prompt here re-reads the whole history.',
  },
  {
    tokens: 300000,
    advice: 'Stop adding work to this session now: run context-capture and tell the user to open a new session. ' +
      'Close to the context limit, answers get slower, costlier and lose earlier details.',
  },
];
const TAIL_BYTES = 4 * 1024 * 1024;

/** Context of the last assistant turn: input + cache read + cache write tokens, or null. */
function lastContextTokens(transcriptPath) {
  if (!transcriptPath || !fs.existsSync(transcriptPath)) return null;
  const size = fs.statSync(transcriptPath).size;
  const start = Math.max(0, size - TAIL_BYTES);
  const fd = fs.openSync(transcriptPath, 'r');
  let text;
  try {
    const buffer = Buffer.alloc(size - start);
    fs.readSync(fd, buffer, 0, buffer.length, start);
    text = buffer.toString('utf8');
  } finally {
    fs.closeSync(fd);
  }
  const lines = text.split('\n');
  for (let i = lines.length - 1; i >= 0; i -= 1) {
    const line = lines[i];
    if (!line.includes('"usage"')) continue;
    let entry;
    try {
      entry = JSON.parse(line);
    } catch (err) {
      continue; // the first line of the tail may be cut in half
    }
    const usage = entry && entry.message && entry.message.usage;
    if (!usage) continue;
    return (usage.input_tokens || 0) + (usage.cache_read_input_tokens || 0) + (usage.cache_creation_input_tokens || 0);
  }
  return null;
}

function stateFileFor(sessionId) {
  const key = crypto.createHash('sha1').update(String(sessionId)).digest('hex').slice(0, 16);
  return path.join(os.tmpdir(), `claude-context-budget-${key}.json`);
}

function announcedLevel(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8')).announced || 0;
  } catch (err) {
    return 0;
  }
}

function main() {
  const payload = g.readStdinJson();
  const tokens = lastContextTokens(payload.transcript_path);
  if (tokens === null || !payload.session_id) return;
  const reached = LEVELS.filter((level) => tokens >= level.tokens);
  if (reached.length === 0) return;
  const level = reached[reached.length - 1];
  const file = stateFileFor(payload.session_id);
  if (announcedLevel(file) >= level.tokens) return;
  try {
    fs.writeFileSync(file, JSON.stringify({ announced: level.tokens, at: new Date().toISOString() }));
  } catch (err) {
    process.stderr.write(`[context-budget] could not save ${file}: ${err.message}\n`);
  }
  const size = `${Math.round(tokens / 1000)}k`;
  process.stdout.write(JSON.stringify({
    systemMessage: `[context budget] This session carries ${size} tokens of context into every prompt. ` +
      'Save context and start a new session for the next task.',
    hookSpecificOutput: {
      hookEventName: 'UserPromptSubmit',
      additionalContext: `[context budget] The session context is ${size} tokens. ${level.advice}`,
    },
  }));
}

try {
  main();
} catch (err) {
  // A budget notice must never stop the user's prompt.
  process.stderr.write(`[context-budget] skipped: ${err.message}\n`);
}
process.exit(0);
