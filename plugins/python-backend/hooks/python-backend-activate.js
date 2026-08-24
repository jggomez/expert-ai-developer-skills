#!/usr/bin/env node
const fs = require('fs');
const path = require('path');

const isCopilot = Boolean(process.env.COPILOT_PLUGIN_DATA);
const isCodex = !isCopilot && Boolean(process.env.PLUGIN_DATA);
const isClaudeCode = !isCopilot && !isCodex && Boolean(process.env.CLAUDE_PLUGIN_ROOT);

// Resolve directories
const pluginRoot = path.join(__dirname, '..');
const rulesPath = path.join(pluginRoot, 'rules', 'python-backend-rules.md');

// Read the rules file
let fullContext = '';
try {
  if (fs.existsSync(rulesPath)) {
    fullContext = fs.readFileSync(rulesPath, 'utf8');
  }
} catch (e) {
  // Silent fail
}

// Write hook output in the shape each host expects.
if (isCopilot) {
  process.stdout.write(JSON.stringify(
    fullContext ? { additionalContext: fullContext } : {}
  ));
} else if (isCodex) {
  const output = { systemMessage: 'PYTHON_BACKEND_ACTIVE' };
  if (fullContext) {
    output.hookSpecificOutput = {
      hookEventName: 'SessionStart',
      additionalContext: fullContext,
    };
  }
  process.stdout.write(JSON.stringify(output));
} else if (isClaudeCode) {
  process.stdout.write(JSON.stringify(
    fullContext
      ? { hookSpecificOutput: { hookEventName: 'SessionStart', additionalContext: fullContext } }
      : {}
  ));
} else {
  // Antigravity/Gemini or an unrecognized host: plain-text context injection.
  process.stdout.write(fullContext);
}
process.exit(0);
