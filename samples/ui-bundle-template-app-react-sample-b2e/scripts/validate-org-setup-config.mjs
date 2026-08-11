/**
 * Build / CI gate: validate this package's org-setup.config.json against the
 * shared schema (W-23043729, spec §5.2).
 *
 * Ships inside the SFDX project template, so a generated app can self-check its
 * org-setup.config.json in its own CI:
 *   npm run validate:org-setup-config
 *
 * Uses the SAME validateConfig + schema as org-setup.mjs runtime, so build-time
 * and runtime checks can never drift. A missing config file is OK (not every
 * project ships one); a present-but-invalid config fails the gate.
 */

import { existsSync, readFileSync } from 'node:fs';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

import { validateConfig } from './org-setup-config-schema.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const configPath = resolve(__dirname, 'org-setup.config.json');

if (!existsSync(configPath)) {
  console.log('✓ org-setup.config.json: not present (nothing to validate)');
  process.exit(0);
}

const result = validateConfig(readFileSync(configPath, 'utf8'), configPath);
if (result.ok) {
  console.log('✓ org-setup.config.json');
  process.exit(0);
}

console.error('❌ org-setup.config.json is invalid:');
for (const err of result.errors) {
  console.error(`   - ${err}`);
}
process.exit(1);
