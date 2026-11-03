#!/usr/bin/env node
/**
 * senior-dev E2E Evidence Gate for Claude Code (SubagentStop).
 *
 * Problem: a browser-testing agent can narrate a test run it never executed.
 * Prompts cannot prevent that; this hook verifies instead of trusting.
 *
 * When `e2e-blackbox-tester` finishes, its own transcript (tool results are written by the
 * harness, not by the model) must prove any execution verdict:
 *   - PASSED / REJECTED require EITHER
 *       (a) Playwright MCP: >= 1 successful `browser_navigate` AND >= 1 successful
 *           `browser_take_screenshot`; every screenshot saved to an absolute `.png` path
 *           must exist on disk with a real PNG signature, OR
 *       (b) scripted Playwright: a successful Bash command running `playwright` AND
 *           >= 1 real PNG under a `docs/<feature-name>/evidence/` directory written during the run.
 *   - BLOCKED / SKIPPED (honest negative verdicts) always pass.
 *   - No verdict at all is blocked.
 * Exit 2 sends the reason back to the subagent so it keeps working. After MAX_BLOCKS blocks
 * the subagent may finish, and the user sees an UNVERIFIED notice instead of a fake PASSED.
 */
const crypto = require('crypto');
const fs = require('fs');
const os = require('os');
const path = require('path');

const AGENT = 'e2e-blackbox-tester';
const MAX_BLOCKS = 3;
const PNG_SIGNATURE = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);
const MIN_PNG_BYTES = 100;
const VERDICT_RE = /\b(PASSED|REJECTED|BLOCKED|SKIPPED)\b/;

function readPayload() {
  try {
    const raw = require('tty').isatty(0) ? '' : fs.readFileSync(0, 'utf-8'); // process.stdin would make the pipe non-blocking (EAGAIN)
    return raw.trim() ? JSON.parse(raw) : {};
  } catch (err) {
    return {};
  }
}

function allow(notice) {
  if (notice) process.stdout.write(JSON.stringify({ systemMessage: notice }));
  process.exit(0);
}

const payload = readPayload();
const agentType = String(payload.agent_type || '');
if (agentType.slice(agentType.lastIndexOf(':') + 1) !== AGENT) allow();

const cwd = payload.cwd || process.cwd();
const counterFile = path.join(
  os.tmpdir(),
  `claude-e2e-gate-${crypto.createHash('sha1').update(String(payload.agent_id || cwd)).digest('hex').slice(0, 16)}.json`
);

function readBlocks() {
  try {
    return JSON.parse(fs.readFileSync(counterFile, 'utf8')).blocks || 0;
  } catch (err) {
    return 0;
  }
}

function writeBlocks(blocks) {
  try {
    fs.writeFileSync(counterFile, JSON.stringify({ blocks }));
  } catch (err) {
    process.stderr.write(`[e2e-evidence-gate] could not persist retry counter: ${err.message}\n`);
  }
}

function block(problems) {
  const blocks = (payload.stop_hook_active === true ? readBlocks() : 0) + 1;
  writeBlocks(blocks);
  process.stderr.write(
    `[E2E EVIDENCE GATE - UNPROVEN VERDICT] (block ${blocks}/${MAX_BLOCKS})\n` +
    problems.map((p) => `- ${p}`).join('\n') +
    `\n\nDo not describe a browser run you did not perform. Either drive the real browser now ` +
    `(Playwright MCP: browser_navigate -> browser_snapshot -> interactions -> browser_take_screenshot ` +
    `with an absolute filename under docs/<feature-name>/evidence/), or end with ` +
    `"Verdict: BLOCKED - <exact error>" / "Verdict: SKIPPED - <reason>".\n`
  );
  process.exit(2);
}

if (payload.stop_hook_active === true && readBlocks() >= MAX_BLOCKS) {
  writeBlocks(0);
  allow(
    `[E2E evidence gate] e2e-blackbox-tester still claims a verdict without browser evidence after ` +
    `${MAX_BLOCKS} attempts. Treat its result as UNVERIFIED (equivalent to BLOCKED).`
  );
}

const lastMessage = String(payload.last_assistant_message || '');
const verdictMatch = lastMessage.match(VERDICT_RE);
if (!verdictMatch) {
  block(['The final message has no verdict. End with exactly one of: PASSED, REJECTED, BLOCKED, SKIPPED.']);
}
const verdict = verdictMatch[1];
if (verdict === 'BLOCKED' || verdict === 'SKIPPED') {
  writeBlocks(0);
  allow();
}

// ---- Collect tool calls and results from the subagent transcript ----
const uses = new Map(); // id -> { name, input }
const results = new Map(); // tool_use_id -> { isError }
let firstTimestamp = null;

function walk(node) {
  if (Array.isArray(node)) {
    node.forEach(walk);
    return;
  }
  if (!node || typeof node !== 'object') return;
  if (node.type === 'tool_use' && node.id) uses.set(node.id, { name: String(node.name || ''), input: node.input || {} });
  if (node.type === 'tool_result' && node.tool_use_id) results.set(node.tool_use_id, { isError: node.is_error === true });
  Object.values(node).forEach(walk);
}

const transcriptPath = payload.agent_transcript_path || payload.transcript_path;
try {
  for (const line of fs.readFileSync(transcriptPath, 'utf8').split('\n')) {
    if (!line.trim()) continue;
    try {
      const entry = JSON.parse(line);
      if (!firstTimestamp && entry.timestamp) firstTimestamp = Date.parse(entry.timestamp) || null;
      walk(entry);
    } catch (err) {
      // Skip a malformed line; the remaining evidence is still checked.
    }
  }
} catch (err) {
  block([`Could not read the subagent transcript (${transcriptPath || 'missing path'}): ${err.message}`]);
}

const succeeded = (predicate) =>
  [...uses.entries()].filter(([id, use]) => predicate(use) && results.has(id) && !results.get(id).isError);

function isRealPng(file, notBefore) {
  try {
    const stat = fs.statSync(file);
    if (!stat.isFile() || stat.size < MIN_PNG_BYTES) return false;
    if (notBefore && stat.mtimeMs < notBefore) return false;
    const fd = fs.openSync(file, 'r');
    const header = Buffer.alloc(PNG_SIGNATURE.length);
    fs.readSync(fd, header, 0, header.length, 0);
    fs.closeSync(fd);
    return header.equals(PNG_SIGNATURE);
  } catch (err) {
    return false;
  }
}

function evidencePngs(root, notBefore) {
  const found = [];
  const stack = [path.join(root, 'docs')];
  while (stack.length) {
    const dir = stack.pop();
    let entries = [];
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch (err) {
      continue;
    }
    for (const entry of entries) {
      const full = path.join(dir, entry.name);
      if (entry.isDirectory()) stack.push(full);
      else if (/\.png$/i.test(entry.name) && full.split(path.sep).includes('evidence') && isRealPng(full, notBefore)) {
        found.push(full);
      }
    }
  }
  return found;
}

const isPlaywrightMcp = (name, tool) => /playwright/i.test(name) && name.endsWith(`__${tool}`);
const navigations = succeeded((u) => isPlaywrightMcp(u.name, 'browser_navigate'));
const screenshots = succeeded((u) => isPlaywrightMcp(u.name, 'browser_take_screenshot'));
const scriptedRuns = succeeded((u) => u.name === 'Bash' && /\bplaywright\b/.test(String(u.input.command || '')));

// Route (b): scripted Playwright run with fresh PNG evidence on disk.
if (scriptedRuns.length > 0 && evidencePngs(cwd, firstTimestamp).length > 0) {
  writeBlocks(0);
  allow();
}

// Route (a): Playwright MCP.
const problems = [];
if (navigations.length === 0) {
  problems.push(`Verdict ${verdict} but no successful browser_navigate call was recorded.`);
}
if (screenshots.length === 0) {
  problems.push(`Verdict ${verdict} but no successful browser_take_screenshot call was recorded.`);
}
for (const [, shot] of screenshots) {
  const file = String(shot.input.filename || '');
  if (file && path.isAbsolute(file) && !isRealPng(file)) {
    problems.push(`Screenshot ${file} is missing on disk or is not a real PNG.`);
  }
}
if (problems.length > 0 && scriptedRuns.length > 0) {
  problems.push('A Playwright command ran via Bash, but no real PNG was written under docs/**/evidence/.');
}

if (problems.length > 0) block(problems);
writeBlocks(0);
allow();
