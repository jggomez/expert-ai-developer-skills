#!/usr/bin/env node
const { execSync } = require('child_process');
const fs = require('fs');
const path = require('path');

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

const terminationReason = payload.terminationReason || '';
const workspaceRoot = payload.workspacePaths?.[0] || process.cwd();

// Only check quality gates on standard model stops
if (terminationReason === 'model_stop') {
  const testScriptPath = path.join(workspaceRoot, 'test-driven-development', 'scripts', 'verify_tests.py');
  
  if (fs.existsSync(testScriptPath)) {
    try {
      // Run the test suite gate
      execSync(`python3 "${testScriptPath}"`, { cwd: workspaceRoot, stdio: 'pipe' });
    } catch (error) {
      const testOutput = error.stdout ? error.stdout.toString() : (error.message || '');
      
      // Stop the termination, forcing the agent to stay and fix the failing tests
      console.log(JSON.stringify({
        decision: 'continue',
        reason: `Quality Gate Violation: You are trying to complete the task, but some tests are failing or have not run successfully. You must fix the code or the tests before you can complete the request.\n\nTest Output:\n${testOutput}`
      }));
      process.exit(0);
    }
  }
}

// Default: allow the agent to stop
console.log(JSON.stringify({ decision: 'allow' }));
process.exit(0);
