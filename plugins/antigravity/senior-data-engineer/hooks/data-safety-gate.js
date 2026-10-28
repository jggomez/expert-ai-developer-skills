#!/usr/bin/env node
/**
 * Senior Data Engineer Safety Gate (PreToolUse)
 * 1. Plan-First Gate: Requires PLAN.md before creating or editing pipeline models (.sqlx, .py, .sql).
 * 2. Destructive Command Guard: Blocks destructive BigQuery, Cloud Storage, or Dataform commands.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PROTECTED_BRANCHES = new Set(['main', 'master', 'develop', 'dev']);

function allow() {
  console.log(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}

function deny(reason) {
  console.log(JSON.stringify({ decision: 'deny', reason }));
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

const toolCall = payload.toolCall || {};
const toolName = toolCall.name || payload.tool_name || '';
const toolArgs = toolCall.args || payload.tool_input || {};
const command = toolArgs.CommandLine || toolArgs.command || '';
const targetFile = toolArgs.TargetFile || toolArgs.file_path || toolArgs.path || '';
const cwd = payload.workspacePaths?.[0] || payload.cwd || toolArgs.Cwd || process.cwd();

// 1. GATE: Destructive Commands via run_command
if (toolName === 'run_command' && command) {
  const destructiveCliRegex = /\b(bq\s+rm(\s+-[a-zA-Z]*f|\s+-[a-zA-Z]*r)|\bgsutil\s+rm\s+-[a-zA-Z]*r|\bgcloud\s+storage\s+rm\s+--recursive)\b/i;
  const destructiveSqlRegex = /\b(DROP\s+TABLE|DROP\s+SCHEMA|DROP\s+DATABASE|TRUNCATE\s+TABLE|DELETE\s+FROM\s+[^\s]+\s+WHERE\s+1\s*=\s*1)\b/i;

  if (destructiveCliRegex.test(command) || destructiveSqlRegex.test(command)) {
    deny(
      `[DATA SAFETY GATE VIOLATION]: Destructive data operation blocked: "${command}".\n` +
      `Dropping tables, truncating datasets, or recursively deleting buckets requires explicit user approval.`
    );
  }
}

// 2. GATE: Destructive MCP Operations
if (toolName === 'call_mcp_tool') {
  const mcpTool = toolArgs.ToolName || '';
  if (/^(delete_table|delete_instance|delete_database)$/i.test(mcpTool)) {
    deny(
      `[DATA SAFETY GATE VIOLATION]: Destructive MCP call blocked: "${mcpTool}".\n` +
      `Deleting cloud data assets via MCP is restricted without user authorization.`
    );
  }
}

// 3. GATE: Plan-First before creating/modifying pipeline files
const isFileModTool = /^(write_to_file|replace_file_content)$/i.test(toolName);
if (isFileModTool && targetFile) {
  const basename = path.basename(targetFile);
  const ext = path.extname(targetFile).toLowerCase();

  const isDoc =
    /^PLAN(\.[\w-]+)?\.md$/i.test(basename) ||
    targetFile.includes('/docs/') ||
    ext === '.md' ||
    ext === '.txt';

  const isPipelineCode =
    ext === '.sqlx' ||
    ext === '.sql' ||
    ext === '.py' ||
    basename === 'workflow_settings.yaml';

  if (!isDoc && isPipelineCode) {
    try {
      const branch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
      if (PROTECTED_BRANCHES.has(branch)) {
        deny(
          `[GIT BRANCH GOVERNANCE]: Prohibited from modifying data pipeline code (${basename}) directly on protected branch "${branch}".\n` +
          `You MUST create and switch to a dedicated feature branch first:\n` +
          `  run_command: git checkout -b feat/<descriptive-slug>\n` +
          `Always work on isolated branches with Conventional naming.`
        );
      }
    } catch (e) {
      // Not a git repository or detached HEAD
    }

    const hasPlan =
      fs.existsSync(path.join(cwd, 'PLAN.md')) ||
      fs.existsSync(path.join(cwd, 'docs', 'PLAN.md'));

    if (!hasPlan) {
      deny(
        `[DATA GRAPH GATE - PLAN FIRST]: No "PLAN.md" found in "${cwd}".\n` +
        `You MUST create a "PLAN.md" defining data sources, SLAs, and Bronze/Silver/Gold schema contracts before writing pipeline code.`
      );
    }
  }
}

allow();
