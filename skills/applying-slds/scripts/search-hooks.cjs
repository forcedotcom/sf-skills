#!/usr/bin/env node

/**
 * Search SLDS styling hooks metadata.
 *
 * Usage:
 *   node search-hooks.js --prefix "--slds-g-color-accent-"
 *   node search-hooks.js --category "color"
 *   node search-hooks.js --property "background-color"
 *   node search-hooks.js --value "#0176d3"
 *   node search-hooks.js --search "accent"
 *   node search-hooks.js                            # show category summary
 */

const fs = require('fs');
const path = require('path');

const INDEX_PATH = path.join(__dirname, '..', 'metadata', 'hooks-index.json');

function loadHooks() {
  if (!fs.existsSync(INDEX_PATH)) {
    console.error(`Hooks index not found: ${INDEX_PATH}`);
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(INDEX_PATH, 'utf8'));
  return { hooks: data.hooks || [], categories: data.categories || {} };
}

function normalizeValue(v) {
  return (v || '').toLowerCase().replace(/\s+/g, '');
}

function matchesValue(hook, searchValue) {
  const needle = normalizeValue(searchValue);

  const check = (v) => {
    if (!v) return false;
    const n = normalizeValue(v);
    return n === needle || n.includes(needle);
  };

  if (hook.value && check(hook.value)) return true;
  if (hook.value_dark && check(hook.value_dark)) return true;
  if (hook.rawValues) {
    if (check(hook.rawValues.slds) || check(hook.rawValues.cosmos)) return true;
  }
  if (hook.values) {
    if (check(hook.values.slds) || check(hook.values.cosmos)) return true;
  }
  return false;
}

function matchesProperty(hook, targetProps) {
  const appliesTo = hook.properties?.['applies-to'] || hook.properties || [];
  if (!Array.isArray(appliesTo) || appliesTo.length === 0) return false;
  const targets = targetProps.map(p => p.toLowerCase());
  return targets.some(t => appliesTo.some(hp => hp.toLowerCase().includes(t) || t.includes(hp.toLowerCase())));
}

function formatHook(hook) {
  const parts = [`  ${hook.token}`];
  if (hook.category) parts.push(`    category: ${hook.category}`);
  if (hook.value) parts.push(`    value: ${hook.value}`);
  if (hook.value_dark) parts.push(`    value_dark: ${hook.value_dark}`);
  if (hook.rawValues?.slds) parts.push(`    value(slds): ${hook.rawValues.slds}`);
  if (hook.rawValues?.cosmos) parts.push(`    value(cosmos): ${hook.rawValues.cosmos}`);
  const props = hook.properties?.['applies-to'] || [];
  if (props.length) parts.push(`    applies-to: ${props.join(', ')}`);
  return parts.join('\n');
}

function run() {
  const args = process.argv.slice(2);
  const flags = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--') && i + 1 < args.length) {
      flags[args[i].slice(2)] = args[i + 1];
      i++;
    }
  }

  const { hooks, categories } = loadHooks();

  if (Object.keys(flags).length === 0) {
    console.log(`\nSLDS Styling Hooks: ${hooks.length} total\n`);
    console.log('Categories:');
    for (const [cat, count] of Object.entries(categories).sort()) {
      console.log(`  ${cat.padEnd(15)} ${count} hooks`);
    }
    console.log('\nUsage:');
    console.log('  --prefix   Match by token prefix (e.g., "--slds-g-color-accent-")');
    console.log('  --category Filter by category (e.g., "color", "spacing", "font")');
    console.log('  --property Filter by CSS property (e.g., "background-color")');
    console.log('  --value    Find hook by CSS value (e.g., "#0176d3")');
    console.log('  --search   Search token names (e.g., "accent")');
    return;
  }

  let results = hooks;

  if (flags.prefix) {
    const prefix = flags.prefix.toLowerCase();
    results = results.filter(h => h.token.toLowerCase().startsWith(prefix));
  }

  if (flags.search) {
    const term = flags.search.toLowerCase();
    results = results.filter(h => h.token.toLowerCase().includes(term));
  }

  if (flags.category) {
    const cat = flags.category.toLowerCase();
    results = results.filter(h => (h.category || '').toLowerCase() === cat);
  }

  if (flags.property) {
    results = results.filter(h => matchesProperty(h, [flags.property]));
  }

  if (flags.value) {
    results = results.filter(h => matchesValue(h, flags.value));
  }

  if (results.length === 0) {
    console.log('No hooks found matching your criteria.');
    return;
  }

  console.log(`\nFound ${results.length} hook(s):\n`);
  for (const hook of results.slice(0, 50)) {
    console.log(formatHook(hook));
    console.log();
  }
  if (results.length > 50) {
    console.log(`... and ${results.length - 50} more. Narrow your search.`);
  }
}

run();
