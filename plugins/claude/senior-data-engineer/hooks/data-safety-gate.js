#!/usr/bin/env node
/**
 * senior-data-engineer PreToolUse gate for Claude Code.
 * 1. Bash Safety Gate: Blocks destructive operations:
 *    - DDL/DML: DROP TABLE/SCHEMA/DATABASE, TRUNCATE, DELETE FROM without WHERE
 *    - Cloud CLI: bq rm -f, gcloud storage rm -r, gsutil rm -r
 * 2. Plan-First Gate: Requires PLAN.md before writing or editing .sql, .sqlx, or ETL scripts.
 */
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

const PROTECTED_BRANCHES = new Set(['main', 'master', 'develop', 'dev']);

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

let payload;
try {
  payload = JSON.parse(raw);
} catch (e) {
  allow();
}

const toolName = payload.tool_name || '';
const toolInput = payload.tool_input || {};
const cwd = payload.cwd || (payload.workspacePaths && payload.workspacePaths[0]) || process.cwd();

// --- 1. Intercept Bash: Block Destructive SQL & Cloud Storage Operations ---
if (toolName === 'Bash') {
  const command = toolInput.command || '';

  // Destructive DDL / DML
  const dropRegex = /\bDROP\s+(TABLE|SCHEMA|DATABASE|VIEW)\b/i;
  const truncateRegex = /\bTRUNCATE\s+(TABLE\s+)?[\w`."]+/i;
  const deleteNoWhereRegex = /\bDELETE\s+FROM\s+[\w`."]+(?!\s+WHERE\b)/i;

  if (dropRegex.test(command)) {
    deny(`[DATA SAFETY GATE VIOLATION]: Destructive DROP statement blocked: "${command}". Schema and table dropping is prohibited without explicit administrative approval.`);
  }

  if (truncateRegex.test(command)) {
    deny(`[DATA SAFETY GATE VIOLATION]: Destructive TRUNCATE statement blocked: "${command}". Truncation leads to irreversible data loss.`);
  }

  if (/\bDELETE\s+FROM\b/i.test(command) && !/\bWHERE\b/i.test(command)) {
    deny(`[DATA SAFETY GATE VIOLATION]: Unbounded DELETE FROM statement without a WHERE clause blocked: "${command}".`);
  }

  // Destructive CLI commands
  const bqRmRegex = /\bbq\s+rm\b.*(?:-f|--force)/i;
  const gcloudStorageRmRegex = /\bgcloud\s+(?:storage\s+rm|alpha\s+storage\s+rm)\b.*-r/i;
  const gsutilRmRegex = /\bgsutil\s+rm\b.*-r/i;

  if (bqRmRegex.test(command)) {
    deny(`[DATA SAFETY GATE VIOLATION]: Destructive BigQuery dataset/table deletion blocked: "${command}".`);
  }

  if (gcloudStorageRmRegex.test(command) || gsutilRmRegex.test(command)) {
    deny(`[DATA SAFETY GATE VIOLATION]: Recursive Cloud Storage bucket/object deletion blocked: "${command}".`);
  }
}

// --- 2. Intercept Write | Edit: Enforce Plan-First for SQL, SQLX, and ETL scripts ---
if (toolName === 'Write' || toolName === 'Edit') {
  const targetFile = toolInput.file_path || toolInput.path || '';
  const ext = path.extname(targetFile).toLowerCase();
  const basename = path.basename(targetFile);

  const isDocOrPlan =
    /^PLAN(\.[\w-]+)?\.md$/i.test(basename) ||
    /^ADR-[\w-]+\.md$/i.test(basename) ||
    ext === '.md';

  if (!isDocOrPlan) {
    const isSql = ext === '.sql' || ext === '.sqlx';
    const isEtl = ext === '.py' && (
      targetFile.includes('/dags/') ||
      targetFile.includes('/pipelines/') ||
      targetFile.includes('/etl/') ||
      targetFile.includes('/dataform/') ||
      targetFile.includes('/jobs/')
    );

    if (isSql || isEtl) {
      let branch = '';
      try {
        branch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8', stdio: ['ignore', 'pipe', 'ignore'] }).trim();
      } catch (e) {
        branch = '';
      }

      if (PROTECTED_BRANCHES.has(branch)) {
        deny(
          `[GIT BRANCH GOVERNANCE]: Prohibited from modifying data pipeline code (${basename}) directly on protected branch "${branch}".\n` +
          `You MUST create and switch to a dedicated feature branch first:\n` +
          `  Bash: git checkout -b feat/<descriptive-slug>\n` +
          `Always work on isolated branches with Conventional naming.`
        );
      }

      const possiblePlanPaths = [
        path.join(cwd, 'PLAN.md'),
        path.join(cwd, 'docs', 'PLAN.md'),
        path.join(cwd, '.agents', 'PLAN.md'),
        path.join(cwd, '.claude', 'PLAN.md')
      ];
      const hasPlan = possiblePlanPaths.some(p => fs.existsSync(p));

      if (!hasPlan) {
        deny(
          `[PLAN-FIRST VIOLATION]: Cannot write or modify data transformation code in "${targetFile}" without an active "PLAN.md".\n` +
          `Per Senior Data Engineer standards, you must author and structure a "PLAN.md" ` +
          `defining the Lakehouse architecture, partition/clustering keys, SCD modeling, and pipeline stages before implementing.`
        );
      }
    }
  }
}

allow();
