#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');

// Read input payload from stdin
let inputData = '';
try {
  inputData = fs.readFileSync(0, 'utf-8');
} catch (e) {
  console.log(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}

if (!inputData.trim()) {
  console.log(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}

let payload;
try {
  payload = JSON.parse(inputData);
} catch (e) {
  console.log(JSON.stringify({ decision: 'allow' }));
  process.exit(0);
}

const toolCall = payload.toolCall || {};
const toolName = toolCall.name || '';
const toolArgs = toolCall.args || {};
const commandLine = toolArgs.CommandLine || '';
const cwd = toolArgs.Cwd || payload.workspacePaths?.[0] || process.cwd();

// 1. Deployment Guardrail (never deploy without permission)
const deployRegex = /\b(deploy|apply\s+-f|firebase\s+deploy|gcloud\s+run\s+deploy)\b/i;
if (toolName === 'run_command' && deployRegex.test(commandLine)) {
  console.log(JSON.stringify({
    decision: 'force_ask',
    reason: `Deployment command detected: "${commandLine}". Deployment operations require explicit user validation and approval.`
  }));
  process.exit(0);
}

// 2. MCP Tools Guardrail (Cloud Run & Firebase writes)
if (toolName === 'call_mcp_tool') {
  const mcpServer = toolArgs.ServerName || '';
  const mcpTool = toolArgs.ToolName || '';
  
  // Block Cloud Run deployments via MCP without permission
  if (mcpServer === 'cloudrun' && mcpTool.startsWith('deploy_')) {
    console.log(JSON.stringify({
      decision: 'force_ask',
      reason: `Cloud Run deployment via MCP detected: "${mcpTool}". Deployment operations require explicit user validation and approval.`
    }));
    process.exit(0);
  }
  
  // Guard Firestore writes / deletions via MCP
  const firestoreWriteRegex = /(add|update|delete|set|create_database)/i;
  if (mcpServer === 'firebase-mcp-server' && firestoreWriteRegex.test(mcpTool)) {
    console.log(JSON.stringify({
      decision: 'force_ask',
      reason: `Firestore mutation via MCP detected: "${mcpTool}". Data modification operations require explicit user validation and approval.`
    }));
    process.exit(0);
  }
}

// 3. Gitflow Branch Safety Gate (never use develop or main for features)
const gitWriteRegex = /\b(git\s+commit|git\s+push|git\s+add|git\s+merge)\b/i;
if (toolName === 'run_command' && gitWriteRegex.test(commandLine)) {
  try {
    // Check active branch in the workspace directory
    const activeBranch = execSync('git symbolic-ref --short HEAD', { cwd, encoding: 'utf8' }).trim();
    if (activeBranch === 'main' || activeBranch === 'develop') {
      console.log(JSON.stringify({
        decision: 'deny',
        reason: `Gitflow Safety Blocked: Directly committing, adding, or pushing code on the "${activeBranch}" branch is prohibited. Features and modifications must be developed on a dedicated feature/ or bugfix/ branch, and merged via Pull Requests.`
      }));
      process.exit(0);
    }
  } catch (e) {
    // If not a git repository or command fails, let it proceed
  }
}

// Default: allow tool execution
console.log(JSON.stringify({ decision: 'allow' }));
process.exit(0);
