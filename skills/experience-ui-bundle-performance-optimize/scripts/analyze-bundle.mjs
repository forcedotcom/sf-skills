#!/usr/bin/env node
/**
 * UI Bundle build-output analyzer.
 *
 * Reads a Vite dist/ directory and reports every JS/CSS asset against the
 * skill's size budgets, flagging what to split first.
 *
 * Usage: node analyze-bundle.mjs <path-to-dist> [--json]
 *
 * Exit code: 0 when all budgets pass, 1 when any budget is exceeded,
 * 2 on usage/IO errors — so it can gate CI.
 */

import fs from 'node:fs';
import path from 'node:path';

const BUDGETS = {
  entryChunkKb: 300, // index-*.js
  anyChunkKb: 500,
  routeChunkKb: 100, // lazy page chunks
  cssTotalKb: 150,
};

const args = process.argv.slice(2);
const asJson = args.includes('--json');
const distDir = args.find((a) => !a.startsWith('--'));

if (!distDir) {
  console.error('Usage: node analyze-bundle.mjs <path-to-dist> [--json]');
  process.exit(2);
}

const assetsDir = path.join(distDir, 'assets');
if (!fs.existsSync(assetsDir)) {
  console.error(`No assets directory at ${assetsDir} — run the app's \`npm run build\` first.`);
  process.exit(2);
}

const kb = (bytes) => Math.round((bytes / 1024) * 100) / 100;

const assets = fs
  .readdirSync(assetsDir)
  .filter((f) => f.endsWith('.js') || f.endsWith('.css'))
  .map((f) => {
    const size = fs.statSync(path.join(assetsDir, f)).size;
    const isJs = f.endsWith('.js');
    const isEntry = isJs && /^index-/.test(f);
    // Vite names lazy chunks after their source module (e.g. PropertySearch-<hash>.js)
    const isRoute = isJs && !isEntry && /^[A-Z]/.test(f);
    return { file: f, sizeKb: kb(size), type: isJs ? 'js' : 'css', isEntry, isRoute };
  })
  .sort((a, b) => b.sizeKb - a.sizeKb);

const findings = [];

for (const a of assets.filter((x) => x.type === 'js')) {
  if (a.isEntry && a.sizeKb > BUDGETS.entryChunkKb) {
    findings.push({
      severity: 'error',
      file: a.file,
      sizeKb: a.sizeKb,
      budgetKb: BUDGETS.entryChunkKb,
      message: 'Entry chunk over budget — apply route-level code splitting (SKILL.md §2), then vendor chunking (§3).',
    });
  } else if (a.sizeKb > BUDGETS.anyChunkKb) {
    findings.push({
      severity: 'error',
      file: a.file,
      sizeKb: a.sizeKb,
      budgetKb: BUDGETS.anyChunkKb,
      message: 'Chunk over budget — split its largest dependency into its own manualChunks entry (§3). Check for substring matches absorbing extra packages.',
    });
  } else if (a.isRoute && a.sizeKb > BUDGETS.routeChunkKb) {
    findings.push({
      severity: 'warning',
      file: a.file,
      sizeKb: a.sizeKb,
      budgetKb: BUDGETS.routeChunkKb,
      message: 'Route chunk is heavy — lazy-load this page\'s heavy dependencies or move shared code up.',
    });
  }
}

const cssTotal = kb(assets.filter((a) => a.type === 'css').reduce((s, a) => s + a.sizeKb * 1024, 0));
if (cssTotal > BUDGETS.cssTotalKb) {
  findings.push({
    severity: 'warning',
    file: '(all css)',
    sizeKb: cssTotal,
    budgetKb: BUDGETS.cssTotalKb,
    message: 'CSS total over budget — check Tailwind content globs for over-broad patterns.',
  });
}

const hasVendorSplit = assets.some((a) => /^(react|router|vendor|charts|radix|icons)-/.test(a.file));
const errors = findings.filter((f) => f.severity === 'error');

const result = {
  distDir,
  budgets: BUDGETS,
  vendorChunksDetected: hasVendorSplit,
  assets,
  findings,
  pass: errors.length === 0,
};

if (asJson) {
  console.log(JSON.stringify(result, null, 2));
} else {
  console.log(`Assets in ${assetsDir} (largest first):\n`);
  for (const a of assets) {
    const flag = findings.find((f) => f.file === a.file);
    const mark = flag ? (flag.severity === 'error' ? '✗' : '⚠') : '✓';
    console.log(`  ${mark} ${a.sizeKb.toString().padStart(9)} kB  ${a.file}`);
  }
  console.log(`\nVendor chunks detected: ${hasVendorSplit ? 'yes' : 'no (see SKILL.md §3)'}`);
  if (findings.length) {
    console.log(`\n${findings.length} finding(s):`);
    for (const f of findings) console.log(`  [${f.severity}] ${f.file} (${f.sizeKb} kB > ${f.budgetKb} kB): ${f.message}`);
  } else {
    console.log('\nAll budgets pass.');
  }
}

process.exit(result.pass ? 0 : 1);
