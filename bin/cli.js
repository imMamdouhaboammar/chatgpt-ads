#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';
import { existsSync, readdirSync, readFileSync } from 'node:fs';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const ROOT = resolve(__dirname, '..');

const args = process.argv.slice(2);
const command = args[0] || '--help';

function printHelp() {
  console.log(`
ChatGPT Ads - Universal Multi-Agent AI Skill & Operating Pack (v0.4.0)
Authored by Mamdouh Aboammar (https://github.com/imMamdouhaboammar/chatgpt-ads)

Usage:
  chatgpt-ads <command> [arguments]

Commands:
  list-skills          List all 12 specialized advertising skills
  query <question>     Query the sourced research knowledge brain
  validate             Validate package structure and integrity
  doctor               Inspect system capabilities and safe I/O backend
  install              Install skills into local agent harnesses (Claude, Codex, Gemini)
  --help, -h           Show this help information
  --version, -v        Show version information
`);
}

switch (command) {
  case '--help':
  case '-h':
  case 'help':
    printHelp();
    break;

  case '--version':
  case '-v':
  case 'version':
    console.log('chatgpt-ads-brain v0.4.0');
    break;

  case 'list-skills': {
    const skillsDir = resolve(ROOT, 'skills');
    const skills = readdirSync(skillsDir, { withFileTypes: true })
      .filter(d => d.isDirectory() && existsSync(resolve(skillsDir, d.name, 'SKILL.md')))
      .map(d => {
        const content = readFileSync(resolve(skillsDir, d.name, 'SKILL.md'), 'utf-8');
        const descMatch = content.match(/description:\s*([^\r\n]+)/);
        return {
          name: d.name,
          desc: descMatch ? descMatch[1].trim() : 'Specialized advertising skill'
        };
      });
    console.log('\nAvailable ChatGPT Ads Skills (' + skills.length + ' registered):');
    skills.forEach(s => {
      console.log(`  - ${s.name.padEnd(25)} : ${s.desc}`);
    });
    console.log('\nOrchestrator: skills/chatgpt-ads/SKILL.md');
    break;
  }

  case 'query': {
    const q = args.slice(1).join(' ');
    if (!q) {
      console.error('Error: Please provide a search query.');
      process.exit(1);
    }
    const res = spawnSync('python3', [resolve(ROOT, 'scripts/query_brain.py'), q], {
      cwd: ROOT,
      stdio: 'inherit'
    });
    process.exit(res.status ?? 0);
    break;
  }

  case 'validate': {
    const res = spawnSync('python3', [resolve(ROOT, 'scripts/validate_pack.py')], {
      cwd: ROOT,
      stdio: 'inherit'
    });
    process.exit(res.status ?? 0);
    break;
  }

  case 'doctor': {
    const res = spawnSync('python3', [resolve(ROOT, 'scripts/doctor.py')], {
      cwd: ROOT,
      stdio: 'inherit'
    });
    process.exit(res.status ?? 0);
    break;
  }

  case 'install': {
    const res = spawnSync('bash', [resolve(ROOT, 'install.sh')], {
      cwd: ROOT,
      stdio: 'inherit'
    });
    process.exit(res.status ?? 0);
    break;
  }

  default:
    console.error('Unknown command: ' + command);
    printHelp();
    process.exit(1);
}
