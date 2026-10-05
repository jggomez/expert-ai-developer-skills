#!/usr/bin/env node
/**
 * sql-query-optimizer PreToolUse gate for Claude Code.
 * 1. Blocks destructive DDL/DML in Bash: DROP, TRUNCATE, ALTER TABLE ... DROP.
 * 2. Mandates --dry_run for all "bq query" commands executed via Bash.
 */
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
  const fs = require('fs');
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

// --- Intercept Bash Commands ---
if (toolName === 'Bash') {
  const command = toolInput.command || '';

  // 1. Destructive DDL/DML Checks
  const dropRegex = /\bDROP\s+(TABLE|VIEW|SCHEMA|DATABASE|INDEX)\b/i;
  const truncateRegex = /\bTRUNCATE\s+(TABLE\s+)?[\w`."]+/i;
  const alterDropRegex = /\bALTER\s+TABLE\s+.*\bDROP\b/i;

  if (dropRegex.test(command)) {
    deny(`[SQL SAFETY GATE VIOLATION]: Destructive DROP statement blocked: "${command}". Schema/table drops are prohibited.`);
  }

  if (truncateRegex.test(command)) {
    deny(`[SQL SAFETY GATE VIOLATION]: Destructive TRUNCATE statement blocked: "${command}".`);
  }

  if (alterDropRegex.test(command)) {
    deny(`[SQL SAFETY GATE VIOLATION]: Destructive ALTER TABLE ... DROP statement blocked: "${command}".`);
  }

  // 2. bq query must use --dry_run
  const bqQueryRegex = /\bbq\s+query\b/i;
  if (bqQueryRegex.test(command)) {
    const hasDryRun = /(?:^|\s)--dry[-_]?run\b/i.test(command);
    if (!hasDryRun) {
      deny(`[SQL SAFETY GATE VIOLATION]: "bq query" command requires "--dry_run" flag. Query optimization must inspect query plans and billed bytes safely without executing mutations.`);
    }
  }
}

allow();
