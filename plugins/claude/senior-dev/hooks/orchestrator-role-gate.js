#!/usr/bin/env node
/**
 * Senior Developer Orchestrator Role Gate for Claude Code (PreToolUse)
 * Enforces Graph Engineering constraints:
 * 1. "Plan First": An up-to-date PLAN.md must exist in the workspace before source code is modified.
 * 2. "Orchestrator Role Boundary": Blocks direct code edits when the running agent (`agent_type`) is an orchestrator.
 * Small surgical Edits (<= 10 lines) are exempt from Plan First (Tier 1 fast-track).
 */
const fs = require('fs');
const path = require('path');
const g = require(path.join(__dirname, 'shared', 'gate-utils.js'));

function allow() {
  process.exit(0);
}

function deny(reason) {
  console.log(JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: reason,
    },
  }));
  process.exit(0);
}

let raw = '';
try {
  raw = fs.readFileSync(0, 'utf-8');
} catch (e) {
  allow();
}
if (!raw.trim()) allow();

let payload = {};
try {
  payload = JSON.parse(raw);
} catch (e) {
  allow();
}

// Extract tool and arguments (Claude Code schema: tool_name, tool_input, cwd)
const toolName = payload.tool_name || '';
const toolInput = payload.tool_input || {};
const targetFile = toolInput.file_path || toolInput.path || '';
const workspaceRoot = payload.cwd || (payload.workspacePaths && payload.workspacePaths[0]) || process.cwd();

// Only inspect file-writing tools: Write, Edit
const isFileModTool = /^(Write|Edit)$/i.test(toolName);
if (!isFileModTool || !targetFile) {
  allow();
}

const basename = path.basename(targetFile);
const ext = path.extname(targetFile).toLowerCase();

// Allowed planning, documentation, and LLM Wiki memory artifacts:
// PLAN.md, ADR-*.md, *.md, docs/*, .agents/*, context/memory/*, .claude/*, *.txt
const isDocOrPlan =
  /^PLAN(\.[\w-]+)?\.md$/i.test(basename) ||
  /^ADR-[\w-]+\.md$/i.test(basename) ||
  targetFile.includes('/docs/') ||
  targetFile.includes('/.agents/') ||
  targetFile.includes('/context/memory/') ||
  targetFile.includes('/context/') ||
  targetFile.includes('/.claude/') ||
  ext === '.md' ||
  ext === '.txt';

if (isDocOrPlan) {
  allow();
}

// 0. GATE 0: "Protected Branch Safety" Rule
// Verify that the active branch is NOT main, master, or develop before any application code is created/edited
try {
  const { execSync } = require('child_process');
  const activeBranch = execSync('git symbolic-ref --short HEAD', { cwd: workspaceRoot, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
  if (['main', 'master', 'develop', 'dev'].includes(activeBranch)) {
    deny(
      `[GRAPH GATE ERROR - PROTECTED BRANCH]: Active git branch is "${activeBranch}".\n` +
      `Per Senior Dev policy, modifying application source code directly on base/protected branches is strictly prohibited.\n` +
      `You MUST create and switch to a dedicated feature branch ('git checkout -b feat/<slug>') before modifying code.`
    );
  }
} catch (e) {
  // Not a git repository or git command unavailable
}

// 1. GATE 1: "Plan First" Rule
// Verify that a PLAN.md exists in the workspace before any implementation file is created/edited
// Tier 1 fast-track: surgical Edits (<= 10 lines each side) do not need a PLAN.md.
    const hasPlan = g.findPlan(workspaceRoot) !== null || g.isSmallEdit(toolName, toolInput);

if (!hasPlan) {
  deny(
    `[GRAPH GATE ERROR - PLAN FIRST]: No "PLAN.md" was found in "${workspaceRoot}".\n` +
    `Per the Senior Dev Loop Engineering lifecycle in Claude Code, you MUST create and structure a "PLAN.md" ` +
    `defining the tasks and subagent assignments before writing or editing application code.`
  );
}

// 2. GATE 2: "Orchestrator Role Boundary" Rule
// Claude Code puts the running agent's name in `agent_type` (main thread started with
// `claude --agent <plugin>:<name>`, or inside a subagent). Orchestrators coordinate; workers write code.
const ORCHESTRATORS = ['senior-dev-orchestrator', 'flutter-feature-orchestrator', 'python-backend-orchestrator'];
if (g.isAgent(payload, ORCHESTRATORS)) {
  deny(
    `[GRAPH INVARIANT VIOLATION - ORCHESTRATOR CODE PROHIBITION]:\n` +
    `As the "${payload.agent_type}" orchestrator, you are STRICTLY FORBIDDEN from modifying application source code (${basename}) directly.\n` +
    `You MUST delegate to a worker subagent (e.g. 'code-implementer') via Agent to write or modify code.`
  );
}

// Default: allow execution once Plan First gate is satisfied
allow();
