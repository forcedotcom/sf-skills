#!/usr/bin/env node

/**
 * Search SLDS blueprint metadata.
 *
 * Usage:
 *   node search-blueprints.js --search "dialog"
 *   node search-blueprints.js --category "Overlay"
 *   node search-blueprints.js --name "modals"
 *   node search-blueprints.js                      # list all blueprints
 */

const fs = require('fs');
const path = require('path');

const BLUEPRINTS_DIR = path.join(__dirname, '..', 'metadata', 'blueprints', 'components');

function loadBlueprints() {
  const blueprints = [];
  if (!fs.existsSync(BLUEPRINTS_DIR)) {
    console.error(`Blueprints directory not found: ${BLUEPRINTS_DIR}`);
    process.exit(1);
  }

  const files = fs.readdirSync(BLUEPRINTS_DIR).filter(f => f.endsWith('.yaml'));
  for (const file of files) {
    const content = fs.readFileSync(path.join(BLUEPRINTS_DIR, file), 'utf8');
    const nameMatch = content.match(/^name:\s*"?([^"\n]+)"?/m);
    const descMatch = content.match(/^description:\s*"?([^"\n]+)"?/m);
    const catMatch = content.match(/^category:\s*"?([^"\n]+)"?/m);
    const rootMatch = content.match(/root:\s*"?([^"\n]+)"?/m);

    blueprints.push({
      file: file.replace('.yaml', ''),
      name: nameMatch ? nameMatch[1].trim() : file.replace('.yaml', ''),
      description: descMatch ? descMatch[1].trim() : '',
      category: catMatch ? catMatch[1].trim() : 'Unknown',
      rootClass: rootMatch ? rootMatch[1].trim() : '',
    });
  }

  return blueprints.sort((a, b) => a.name.localeCompare(b.name));
}

function run() {
  const args = process.argv.slice(2);
  const flags = {};
  for (let i = 0; i < args.length; i += 2) {
    if (args[i].startsWith('--')) {
      flags[args[i].slice(2)] = args[i + 1] || '';
    }
  }

  const blueprints = loadBlueprints();

  if (flags.name) {
    const needle = flags.name.toLowerCase();
    const bp = blueprints.find(b =>
      b.file.toLowerCase() === needle || b.name.toLowerCase() === needle
    );
    if (!bp) {
      console.log(`Blueprint "${flags.name}" not found.`);
      console.log(`\nAvailable: ${blueprints.map(b => b.file).join(', ')}`);
      return;
    }
    console.log(`\n=== ${bp.name} ===`);
    console.log(`Category: ${bp.category}`);
    console.log(`Root class: ${bp.rootClass}`);
    console.log(`Description: ${bp.description}`);
    console.log(`\nFull YAML: metadata/blueprints/components/${bp.file}.yaml`);
    console.log('\nRead the full YAML file for classes, modifiers, states, accessibility, and example HTML.');
    return;
  }

  let results = blueprints;

  if (flags.category) {
    const cat = flags.category.toLowerCase();
    results = results.filter(b => b.category.toLowerCase() === cat);
  }

  if (flags.search) {
    const term = flags.search.toLowerCase();
    results = results.filter(b =>
      b.name.toLowerCase().includes(term) ||
      b.description.toLowerCase().includes(term) ||
      b.file.toLowerCase().includes(term)
    );
  }

  if (results.length === 0) {
    console.log('No blueprints found matching your criteria.');
    const categories = [...new Set(blueprints.map(b => b.category))].sort();
    console.log(`\nAvailable categories: ${categories.join(', ')}`);
    return;
  }

  console.log(`\nFound ${results.length} blueprint(s):\n`);

  const byCategory = {};
  for (const bp of results) {
    if (!byCategory[bp.category]) byCategory[bp.category] = [];
    byCategory[bp.category].push(bp);
  }

  for (const [cat, bps] of Object.entries(byCategory).sort()) {
    console.log(`── ${cat} ──`);
    for (const bp of bps) {
      console.log(`  ${bp.name.padEnd(30)} ${bp.rootClass.padEnd(25)} ${bp.description.slice(0, 60)}`);
    }
    console.log();
  }

  console.log('Use --name "<blueprint>" to get full details.');
}

run();
