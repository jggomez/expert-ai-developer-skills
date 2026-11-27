#!/usr/bin/env node
/**
 * Red-test brake (Claude Code, PostToolUse + PostToolUseFailure on Bash): never blocks a tool call.
 *
 * Measured runs showed implementers re-running failing tests five or more times, each attempt
 * costlier than the last (flutter-implementer: 13.5 test runs and 4.7 failures per run). This hook
 * counts consecutive failed test commands per agent (the main session counts as one agent) and,
 * from the third, tells the agent to stop, report the failing test and what blocks it. A passing
 * test run resets the count.
 *
 * Per the hooks reference, a Bash call that exits non-zero fires PostToolUseFailure, whose `error`
 * starts with `Exit code N`; inside a subagent the payload carries `agent_id` and `agent_type`.
 */
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');
const g = require('./shared/gate-utils');

const LIMIT = 3;
// A test runner at the start of the command or after `&&`, `;`, `|` or `cd dir &&`.
const TEST_COMMAND = new RegExp(
  '(?:^|&&|;|\\|\\|?)\\s*(?:[A-Z_]+=\\S+\\s+)*' +
  '(?:(?:uv|poetry|pipenv|pdm|hatch)\\s+run\\s+)?(?:python3?\\s+-m\\s+)?(?:npx\\s+|pnpm\\s+(?:exec\\s+)?|yarn\\s+)?' +
  '(?:pytest|flutter\\s+test|dart\\s+test|go\\s+test|cargo\\s+test|vitest|jest|mocha|' +
  'npm\\s+(?:run\\s+)?test|pnpm\\s+(?:run\\s+)?test|yarn\\s+(?:run\\s+)?test|gradle\\w*\\s+test|\\./gradlew\\s+test|' +
  'mvn\\s+test|swift\\s+test|xcodebuild\\s+test|bun\\s+test|deno\\s+test|tox|nox)\\b',
);

function isTestCommand(command) {
  return typeof command === 'string' && TEST_COMMAND.test(command.trim());
}

function stateFile(payload) {
  const key = crypto.createHash('sha1').update(`${payload.session_id || ''}\0${payload.agent_id || 'main'}`)
    .digest('hex').slice(0, 16);
  return path.join(os.tmpdir(), `claude-red-test-brake-${key}.json`);
}

function readCount(file) {
  try {
    return JSON.parse(fs.readFileSync(file, 'utf8')).failures || 0;
  } catch (err) {
    return 0;
  }
}

function writeCount(file, failures) {
  try {
    fs.writeFileSync(file, JSON.stringify({ failures, at: new Date().toISOString() }));
  } catch (err) {
    process.stderr.write(`[red-test-brake] could not save ${file}: ${err.message}\n`);
  }
}

function failed(payload) {
  if (payload.hook_event_name !== 'PostToolUseFailure' || payload.is_interrupt === true) return false;
  const match = /^Exit code (\d+)/.exec(String(payload.error || ''));
  return !match || match[1] !== '0';
}

function main() {
  const payload = g.readStdinJson();
  if (payload.tool_name !== 'Bash' || !payload.tool_input || !isTestCommand(payload.tool_input.command)) return;
  if (payload.hook_event_name === 'PostToolUseFailure' && payload.is_interrupt === true) return;
  const file = stateFile(payload);
  if (!failed(payload)) {
    if (payload.hook_event_name === 'PostToolUse') writeCount(file, 0);
    return;
  }
  const failures = readCount(file) + 1;
  writeCount(file, failures);
  if (failures < LIMIT) return;
  process.stdout.write(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PostToolUseFailure',
      additionalContext: `[red-test brake] ${failures} test runs in a row failed. Stop changing code to make them ` +
        'pass. Report the failing test, the error, what you tried and what blocks you (missing setup, unclear spec, ' +
        'a bug outside your files), and hand back. Do not weaken or delete assertions.',
    },
  }));
}

try {
  main();
} catch (err) {
  // The brake is advice: it must never turn a tool call into an error.
  process.stderr.write(`[red-test-brake] skipped: ${err.message}\n`);
}
process.exit(0);
