#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

// Read input payload from stdin
let inputData = '';
try {
  inputData = fs.readFileSync(0, 'utf-8');
} catch (e) {
  process.exit(0);
}

let payload = {};
if (inputData.trim()) {
  try {
    payload = JSON.parse(inputData);
  } catch (e) {
    payload = {};
  }
}

// Normalize across Claude Code (cwd) and the legacy Antigravity/Gemini shape
// (workspacePaths) some hosts still send.
const workspaceRoot = payload.cwd || payload.workspacePaths?.[0] || process.cwd();

// The TDD skill lives under skills/test-driven-development in this repo's
// layout, wherever the plugin is installed.
const testScriptPath = path.join(workspaceRoot, 'skills', 'test-driven-development', 'scripts', 'verify_tests.py');

if (fs.existsSync(testScriptPath)) {
  try {
    execSync(`python3 "${testScriptPath}"`, { cwd: workspaceRoot, stdio: 'pipe' });
  } catch (error) {
    const testOutput = error.stdout ? error.stdout.toString() : (error.message || '');

    // Exit code 2 blocks the stop and feeds stderr back as the reason.
    console.error(
      `Quality Gate Violation: you are trying to finish, but some tests are failing or did not run successfully. Fix the code or the tests before completing the request.\n\nTest Output:\n${testOutput}`
    );
    process.exit(2);
  }
}

// Default: allow the agent to stop
process.exit(0);
