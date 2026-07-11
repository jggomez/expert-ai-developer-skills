#!/usr/bin/env node
const fs = require('fs');
const path = require('path');
const os = require('os');

const isCopilot = Boolean(process.env.COPILOT_PLUGIN_DATA);
const isCodex = !isCopilot && Boolean(process.env.PLUGIN_DATA);

// Resolve directories
const pluginRoot = path.join(__dirname, '..');
const rulesPath = path.join(pluginRoot, 'rules', 'python-backend-rules.md');

// 1. Read the rules file
let outputRules = '';
try {
  if (fs.existsSync(rulesPath)) {
    outputRules = fs.readFileSync(rulesPath, 'utf8');
  }
} catch (e) {
  // Silent fail
}

// 2. Perform MCP Verification Checks
let mcpWarning = '';
try {
  const mcpConfigPath = path.join(os.homedir(), '.gemini', 'config', 'mcp_config.json');
  if (fs.existsSync(mcpConfigPath)) {
    const mcpConfig = JSON.parse(fs.readFileSync(mcpConfigPath, 'utf8'));
    const servers = mcpConfig.mcpServers || {};

    const missingMcps = [];
    if (!servers['cloudrun'] || servers['cloudrun'].disabled) missingMcps.push('cloudrun (Google Cloud Run)');
    if (!servers['firebase-mcp-server'] || servers['firebase-mcp-server'].disabled) missingMcps.push('firebase-mcp-server (Firestore & Firebase)');

    if (missingMcps.length > 0) {
      mcpWarning = `\n\n> [!WARNING]\n> The following MCP servers are recommended for Python Backend development but are currently missing or disabled in your global mcp_config.json:\n` +
        missingMcps.map(mcp => `> - **${mcp}**`).join('\n') +
        `\n> Proactively advise the user on how to enable them or configure credentials for GCP and Firebase.`;
    }
  }
} catch (e) {
  // Silent fail
}

// Combine rules and warnings
const fullContext = outputRules + mcpWarning;

// 3. Write Hook Output based on Environment
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
} else {
  process.stdout.write(fullContext);
}
process.exit(0);
