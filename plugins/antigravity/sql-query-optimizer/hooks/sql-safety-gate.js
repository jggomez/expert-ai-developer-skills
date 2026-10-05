#!/usr/bin/env node
/**
 * SQL Query Optimizer Safety Gate (PreToolUse)
 * 1. Blocks destructive SQL statements (DROP, TRUNCATE, ALTER TABLE DROP).
 * 2. Enforces BigQuery dry-run checks before running expensive live analytical queries.
 */
const fs = require('fs');

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

// 1. GATE: Destructive SQL Guard
const destructiveSql = /\b(DROP\s+TABLE|DROP\s+DATABASE|DROP\s+SCHEMA|TRUNCATE\s+TABLE|ALTER\s+TABLE\s+[^\s]+\s+DROP)\b/i;
if (destructiveSql.test(command)) {
  deny(
    `[SQL OPTIMIZER SAFETY VIOLATION]: Destructive statement blocked: "${command}".\n` +
    `The SQL Query Optimizer is strictly read-only and performance-focused; modifying or dropping schema objects is prohibited.`
  );
}

// 2. GATE: BigQuery Dry-Run Safety Check
if (/\bbq\s+query\b/i.test(command)) {
  const isDryRun = /--dry_run\b/i.test(command);
  const isInformational = /\b(show|ls|head)\b/i.test(command);

  // If executing bq query without --dry_run, enforce caution
  if (!isDryRun && !isInformational) {
    // If running a mutation or expensive SELECT without dry-run first
    if (/SELECT\b/i.test(command) && !/LIMIT\s+[0-9]+/i.test(command)) {
      deny(
        `[BIGQUERY COST GUARD]: Running un-limited BigQuery queries without --dry_run is blocked.\n` +
        `Always execute with 'bq query --use_legacy_sql=false --dry_run' first to verify bytes scanned before executing.`
      );
    }
  }
}

allow();
