#!/usr/bin/env node
/**
 * Senior Developer Orchestrator Role Gate for Claude Code (PreToolUse)
 * Enforces Graph Engineering constraints:
 * 1. "Plan First": An up-to-date PLAN.md must exist in the workspace before source code is modified.
 * 2. "Orchestrator Role Boundary": Blocks direct code edits on protected source paths when no plan exists.
 */
const fs = require('fs');
const path = require('path');

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

// Allowed planning and documentation artifacts:
// PLAN.md, ADR-*.md, *.md, docs/*, .agents/*, .claude/*, *.txt
const isDocOrPlan =
  /^PLAN(\.[\w-]+)?\.md$/i.test(basename) ||
  /^ADR-[\w-]+\.md$/i.test(basename) ||
  targetFile.includes('/docs/') ||
  targetFile.includes('/.agents/') ||
  targetFile.includes('/.claude/') ||
  ext === '.md' ||
  ext === '.txt';

if (isDocOrPlan) {
  allow();
}

// 1. GATE 1: "Plan First" Rule
// Verify that a PLAN.md exists in the workspace before any implementation file is created/edited
const possiblePlanPaths = [
  path.join(workspaceRoot, 'PLAN.md'),
  path.join(workspaceRoot, 'docs', 'PLAN.md'),
  path.join(workspaceRoot, '.agents', 'PLAN.md')
];
const hasPlan = possiblePlanPaths.some(p => fs.existsSync(p));

if (!hasPlan) {
  deny(
    `[GRAPH GATE ERROR - PLAN FIRST]: No "PLAN.md" was found in "${workspaceRoot}".\n` +
    `Per the Senior Dev Loop Engineering lifecycle in Claude Code, you MUST create and structure a "PLAN.md" ` +
    `defining the tasks and subagent assignments before writing or editing application code.`
  );
}

// Default: allow execution once Plan First gate is satisfied
allow();
