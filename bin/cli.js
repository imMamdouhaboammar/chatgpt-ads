#!/usr/bin/env node
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);

// Installation remains a shell compatibility surface. Every product and
// maintenance command delegates to the canonical Python CLI.
const command = args[0] || '--help';
const child = command === 'install'
  ? spawnSync('bash', [resolve(ROOT, 'install.sh'), ...args.slice(1)], { cwd: ROOT, stdio: 'inherit' })
  : spawnSync('python3', ['-m', 'chatgpt_ads_brain', ...args], { cwd: ROOT, stdio: 'inherit' });

if (child.error) {
  console.error('Unable to start ChatGPT Ads CLI.');
  process.exit(1);
}
process.exit(child.status ?? 1);
