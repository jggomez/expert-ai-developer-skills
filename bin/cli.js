#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const os = require('os');

// Terminal ANSI colors
const colors = {
  reset: '\x1b[0m',
  bright: '\x1b[1m',
  green: '\x1b[32m',
  blue: '\x1b[34m',
  cyan: '\x1b[36m',
  yellow: '\x1b[33m',
  red: '\x1b[31m',
  gray: '\x1b[90m'
};

// Root of the package
const pkgRoot = path.join(__dirname, '..');
const skillsDir = path.join(pkgRoot, 'skills');
const pluginDir = path.join(pkgRoot, 'plugins', 'python-backend');

// Helper to print styled messages
function log(msg) { console.log(msg); }
function success(msg) { log(`${colors.green}✔ ${msg}${colors.reset}`); }
function info(msg) { log(`${colors.blue}ℹ ${msg}${colors.reset}`); }
function warn(msg) { log(`${colors.yellow}⚠ ${msg}${colors.reset}`); }
function error(msg) { log(`${colors.red}✘ ${msg}${colors.reset}`); }
function title(msg) { log(`\n${colors.bright}${colors.cyan}=== ${msg} ===${colors.reset}\n`); }

// Print CLI banner
function printHeader() {
  log(`${colors.bright}${colors.blue}  ___                       _      _   ___ `);
  log(` | __|_ __ _ __  ___ _ _ __| |_   /_\\ |_ _|`);
  log(` | _||\\ \\ /| '_ \\/ -_) '_|  _| |_/ _ \\ | | `);
  log(` |___|/_\\_\\| .__/\\___|_|  \\__|(_)_/ \\_\\___|`);
  log(`           |_|  ${colors.reset}${colors.gray}expert-ai-developer-skills CLI v1.0.0${colors.reset}\n`);
}

// Print help usage
function printHelp() {
  printHeader();
  log(`${colors.bright}Usage:${colors.reset}`);
  log(`  npx expert-ai-developer-skills <command> [options]`);
  log(`  npx skills <command> [options]\n`);
  
  log(`${colors.bright}Commands:${colors.reset}`);
  log(`  ${colors.green}list${colors.reset}                  List all available skills in this catalog`);
  log(`  ${colors.green}add <skill-name>${colors.reset}      Add one or more skills to your project or global system`);
  log(`                        (e.g., 'add python-expert', 'add python-expert commit-expert', 'add all')`);
  log(`  ${colors.green}plugin install${colors.reset}        Install the unified python-backend quality-gate plugin\n`);
  
  log(`${colors.bright}Options:${colors.reset}`);
  log(`  ${colors.cyan}-g, --global${colors.reset}          Install target globally to ~/.gemini/config/ instead of local .agents/`);
  log(`  ${colors.cyan}-h, --help${colors.reset}            Show this help information\n`);
  
  log(`${colors.bright}Examples:${colors.reset}`);
  log(`  npx expert-ai-developer-skills add python-expert`);
  log(`  npx expert-ai-developer-skills add all --global`);
  log(`  npx expert-ai-developer-skills plugin install\n`);
}

// Copy directory recursively helper
function copyDirSync(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  const entries = fs.readdirSync(src, { withFileTypes: true });

  for (let entry of entries) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);

    if (entry.isDirectory()) {
      copyDirSync(srcPath, destPath);
    } else {
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

// List all available skills
function listSkills() {
  printHeader();
  title('Available AI Developer Skills');
  
  if (!fs.existsSync(skillsDir)) {
    error('Skills directory not found in the package root.');
    process.exit(1);
  }
  
  const entries = fs.readdirSync(skillsDir, { withFileTypes: true });
  const skills = entries.filter(e => e.isDirectory() && e.name !== 'node_modules');
  
  skills.forEach((skill, index) => {
    let desc = '';
    const skillPath = path.join(skillsDir, skill.name, 'SKILL.md');
    if (fs.existsSync(skillPath)) {
      const content = fs.readFileSync(skillPath, 'utf8');
      const descMatch = content.match(/description:\s*(.*)/i);
      if (descMatch && descMatch[1]) {
        desc = descMatch[1].trim().replace(/^['"]|['"]$/g, '');
      }
    }
    log(`  ${colors.green}${String(index + 1).padStart(2, ' ')}. ${skill.name.padEnd(30)}${colors.reset} - ${colors.gray}${desc || 'Modular agent directive'}${colors.reset}`);
  });
  log('');
}

// Add skill command
function addSkill(requestedSkills, isGlobal) {
  if (requestedSkills.length === 0) {
    error('Please specify at least one skill name, or use "all".');
    process.exit(1);
  }

  const availableEntries = fs.readdirSync(skillsDir, { withFileTypes: true });
  const allAvailableSkills = availableEntries.filter(e => e.isDirectory() && e.name !== 'node_modules').map(e => e.name);

  let targetSkills = [];
  if (requestedSkills.includes('all')) {
    targetSkills = allAvailableSkills;
  } else {
    // Validate each requested skill
    for (let req of requestedSkills) {
      if (allAvailableSkills.includes(req)) {
        targetSkills.push(req);
      } else {
        error(`Skill "${req}" does not exist in the catalog.`);
        log(`Run ${colors.cyan}npx expert-ai-developer-skills list${colors.reset} to see all available skills.`);
        process.exit(1);
      }
    }
  }

  // Determine destination root
  let destRoot;
  if (isGlobal) {
    destRoot = path.join(os.homedir(), '.gemini', 'config', 'skills');
  } else {
    destRoot = path.join(process.cwd(), '.agents', 'skills');
  }

  title(`Installing ${targetSkills.length} Skill(s) ${isGlobal ? 'Globally' : 'Locally'}`);
  info(`Destination: ${destRoot}`);

  targetSkills.forEach(skill => {
    const srcPath = path.join(skillsDir, skill);
    const destPath = path.join(destRoot, skill);

    try {
      if (fs.existsSync(destPath)) {
        warn(`Skill "${skill}" already exists at destination. Overwriting...`);
        fs.rmSync(destPath, { recursive: true, force: true });
      }
      copyDirSync(srcPath, destPath);
      success(`Successfully added skill: ${colors.bright}${skill}${colors.reset}`);
    } catch (err) {
      error(`Failed to copy skill "${skill}": ${err.message}`);
    }
  });

  log(`\n${colors.green}🎉 Done! Your Antigravity session will now load these skills.${colors.reset}\n`);
}

// Install plugin command
function installPlugin(isGlobal) {
  let destRoot;
  if (isGlobal) {
    destRoot = path.join(os.homedir(), '.gemini', 'config', 'plugins', 'python-backend');
  } else {
    destRoot = path.join(process.cwd(), '.agents', 'plugins', 'python-backend');
  }

  title(`Installing unified python-backend Plugin ${isGlobal ? 'Globally' : 'Locally'}`);
  info(`Source:      ${pluginDir}`);
  info(`Destination: ${destRoot}`);

  try {
    if (!fs.existsSync(pluginDir)) {
      error('Plugin source directory not found inside the package.');
      process.exit(1);
    }

    if (fs.existsSync(destRoot)) {
      warn('Plugin directory already exists at destination. Overwriting...');
      fs.rmSync(destRoot, { recursive: true, force: true });
    }

    copyDirSync(pluginDir, destRoot);
    success(`Successfully installed ${colors.bright}python-backend${colors.reset} plugin!`);
    log(`\n${colors.green}🎉 Done! Start a new Antigravity session to initialize quality-gates and hooks.${colors.reset}\n`);
  } catch (err) {
    error(`Failed to install plugin: ${err.message}`);
  }
}

// Main CLI logic
function main() {
  const args = process.argv.slice(2);
  
  if (args.length === 0 || args.includes('-h') || args.includes('--help')) {
    printHelp();
    process.exit(0);
  }

  const isGlobal = args.includes('-g') || args.includes('--global');
  // Filter out flags to get raw positional arguments
  const cleanArgs = args.filter(a => !['-g', '--global', '-h', '--help'].includes(a));

  const command = cleanArgs[0];

  if (command === 'list') {
    listSkills();
  } else if (command === 'add') {
    const requestedSkills = cleanArgs.slice(1);
    addSkill(requestedSkills, isGlobal);
  } else if (command === 'plugin' && cleanArgs[1] === 'install') {
    installPlugin(isGlobal);
  } else {
    error(`Unknown command: "${command}"`);
    log(`Run ${colors.cyan}npx expert-ai-developer-skills --help${colors.reset} for list of commands.`);
    process.exit(1);
  }
}

main();
