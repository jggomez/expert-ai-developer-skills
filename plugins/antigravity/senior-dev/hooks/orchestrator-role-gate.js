#!/usr/bin/env node
/**
 * Senior Developer Orchestrator Role Gate (PreToolUse)
 * Enforces Graph Engineering constraints:
 * 1. "Plan First": An up-to-date PLAN.md must exist in the workspace before source code is modified.
 * 2. "Orchestrator Role Boundary": The main orchestrator agent is strictly forbidden from directly
 *    writing or modifying application code. It must delegate to `code-implementer`.
 */
const fs = require('fs');
const path = require('path');

function allow() {
  const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);
  if (!isClaudeCode) {
    console.log(JSON.stringify({ decision: 'allow' }));
  }
  process.exit(0);
}

function deny(reason) {
  const isClaudeCode = Boolean(process.env.CLAUDE_PLUGIN_ROOT);
  if (isClaudeCode) {
    console.log(JSON.stringify({
      hookSpecificOutput: {
        hookEventName: 'PreToolUse',
        permissionDecision: 'deny',
        permissionDecisionReason: reason,
      },
    }));
  } else {
    console.log(JSON.stringify({ decision: 'deny', reason }));
  }
  process.exit(0);
}

let raw = '';
try {
  raw = fs.readFileSync(0, 'utf-8');
} catch (e) {
  allow();
}
if (!raw.trim()) allow();

let payload;
try {
  payload = JSON.parse(raw);
} catch (e) {
  allow();
}

// Extract tool and arguments
const toolCall = payload.toolCall || {};
const toolName = toolCall.name || payload.tool_name || '';
const toolArgs = toolCall.args || payload.tool_input || {};
const targetFile = toolArgs.TargetFile || toolArgs.file_path || toolArgs.path || '';
const workspaceRoot =
  payload.workspacePaths?.[0] ||
  payload.cwd ||
  toolArgs.Cwd ||
  process.cwd();

// Only inspect file-writing tools: write_to_file, replace_file_content, Write, Edit
const isFileModTool = /^(write_to_file|replace_file_content|Write|Edit)$/i.test(toolName);
if (!isFileModTool || !targetFile) {
  allow();
}

const basename = path.basename(targetFile);
const ext = path.extname(targetFile).toLowerCase();

// Allowed planning, documentation, and LLM Wiki memory artifacts:
// PLAN.md, ADR-*.md, *.md, docs/*, .agents/*, context/memory/*, .gemini/*, *.txt
const isDocOrPlan =
  /^PLAN(\.[\w-]+)?\.md$/i.test(basename) ||
  /^ADR-[\w-]+\.md$/i.test(basename) ||
  targetFile.includes('/docs/') ||
  targetFile.includes('/.agents/') ||
  targetFile.includes('/context/memory/') ||
  targetFile.includes('/context/') ||
  targetFile.includes('/.gemini/') ||
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
const possiblePlanPaths = [
  path.join(workspaceRoot, 'PLAN.md'),
  path.join(workspaceRoot, 'docs', 'PLAN.md'),
  path.join(workspaceRoot, '.agents', 'PLAN.md')
];
const hasPlan = possiblePlanPaths.some(p => fs.existsSync(p));

if (!hasPlan) {
  deny(
    `[GRAPH GATE ERROR - PLAN FIRST]: No "PLAN.md" was found in "${workspaceRoot}".\n` +
    `Per the Loop Engineering lifecycle, you MUST create and structure a "PLAN.md" ` +
    `defining the tasks and subagent assignments before writing or editing application code.`
  );
}

// 2. GATE 2: "Orchestrator Role Boundary" Rule
// Determine if the current session is the main Orchestrator (not a subagent).
// In Antigravity/Claude Code transcripts, the main orchestrator conversation starts with the user request.
const transcriptPath = payload.transcriptPath;
if (transcriptPath && fs.existsSync(transcriptPath)) {
  try {
    const content = fs.readFileSync(transcriptPath, 'utf8');
    const firstLine = content.trim().split('\n')[0] || '';
    
    // Subagents are given specialized prompts and do not have '<USER_REQUEST>' as the original user prompt
    const isMainSession = firstLine.includes('<USER_REQUEST>');
    
    if (isMainSession) {
      deny(
        `[GRAPH INVARIANT VIOLATION - ORCHESTRATOR CODE PROHIBITION]:\n` +
        `As the Senior Developer Orchestrator, you are STRICTLY FORBIDDEN from modifying application source code (${basename}) directly.\n` +
        `You MUST invoke the 'code-implementer' subagent via invoke_subagent to write or modify code.`
      );
    }
  } catch (err) {
    // If transcript cannot be read, fail open to avoid halting the toolchain
  }
}

allow();
