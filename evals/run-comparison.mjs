import { existsSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const here = dirname(fileURLToPath(import.meta.url));
const root = resolve(here, '..');
if (existsSync(resolve(root, '.env'))) process.loadEnvFile(resolve(root, '.env'));
const allProviders = process.argv.includes('--all');
const required = allProviders
  ? ['OPENAI_API_KEY', 'ANTHROPIC_API_KEY', 'DEEPSEEK_API_KEY', 'EVAL_OPENAI_MODEL', 'EVAL_ANTHROPIC_MODEL', 'EVAL_DEEPSEEK_MODEL']
  : ['DEEPSEEK_API_KEY', 'EVAL_DEEPSEEK_MODEL'];
const missing = required.filter(name => !process.env[name]?.trim());
if (missing.length) {
  console.error(`Comparison not started. Configure these names in .env: ${missing.join(', ')}. No model calls made.`);
  process.exit(1);
}
if (!existsSync(resolve(root, '.cache/eval-pack.json'))) {
  console.error('Export one evidence pack first: uv run python -m evals.export_pack');
  process.exit(1);
}
const python = process.env.PROMPTFOO_PYTHON || resolve(root, process.platform === 'win32' ? '.venv/Scripts/python.exe' : '.venv/bin/python');
if (!existsSync(python)) {
  console.error('Run uv sync --extra dev or set PROMPTFOO_PYTHON to an absolute project Python path.');
  process.exit(1);
}
const cli = resolve(here, 'node_modules/promptfoo/dist/src/entrypoint.js');
const args = [cli, 'eval', '--no-cache', '--no-share', '--max-concurrency', '1', '-c', resolve(here, 'promptfooconfig.yaml'), '--output', resolve(here, 'results/comparison.json')];
if (!allProviders) args.push('--filter-providers', '^DeepSeek$');
const result = spawnSync(process.execPath, args, {
  cwd: here, stdio: 'inherit', env: { ...process.env, PROMPTFOO_PYTHON: python, PROMPTFOO_DISABLE_TELEMETRY: '1' },
});
if (result.error) console.error(result.error.message);
process.exit(result.status ?? 1);
