#!/usr/bin/env node
/**
 * Context Guard Gate (PreToolUse)
 * Prevents agents from accidentally reading massive files (>500KB) without slice pagination,
 * protecting the context window and token budget.
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
const filePath = toolArgs.AbsolutePath || toolArgs.file_path || '';

if (toolName === 'view_file' && filePath && fs.existsSync(filePath)) {
  try {
    const stats = fs.statSync(filePath);
    const maxBytes = 500 * 1024; // 500 KB

    // If file is larger than 500KB and no line slice is provided
    if (stats.size > maxBytes && !toolArgs.StartLine && !toolArgs.EndLine) {
      deny(
        `[CONTEXT GUARD BLOCKED]: File "${filePath}" is ${Math.round(stats.size / 1024)} KB.\n` +
        `Reading massive files without line boundaries consumes excessive context tokens.\n` +
        `Use 'grep_search' to locate the specific section or provide 'StartLine' and 'EndLine' with view_file.`
      );
    }
  } catch (e) {
    // Stat failed, allow
  }
}

allow();
