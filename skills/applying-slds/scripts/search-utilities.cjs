#!/usr/bin/env node

/**
 * Search SLDS utility classes metadata.
 *
 * Usage:
 *   node search-utilities.js --category "all"         # list all categories
 *   node search-utilities.js --category "grid"         # browse category
 *   node search-utilities.js --search "slds-m-bottom"  # search by class name
 *   node search-utilities.js --pattern "slds-p-*"      # wildcard pattern
 */

const fs = require('fs');
const path = require('path');

const INDEX_PATH = path.join(__dirname, '..', 'metadata', 'utilities-index.json');
const GUIDANCE_DIR = path.join(__dirname, '..', 'guidance', 'utilities');

function loadUtilities() {
  if (!fs.existsSync(INDEX_PATH)) {
    console.error(`Utilities index not found: ${INDEX_PATH}`);
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(INDEX_PATH, 'utf8'));
  return {
    utilities: data.utilities || [],
    categories: data.categories || {},
    total: data.total_utilities || 0,
  };
}

function formatUtility(u) {
  const parts = [`  ${u.class}`];
  if (u.category) parts.push(`    category: ${u.category}`);
  if (u.description) parts.push(`    description: ${u.description}`);
  if (u.css) {
    const rules = Object.entries(u.css).map(([prop, val]) => `${prop}: ${val}`).join('; ');
    parts.push(`    css: ${rules}`);
  }
  if (u.css_rules && u.css_rules.length) {
    parts.push(`    css: ${u.css_rules.join('; ')}`);
  }
  return parts.join('\n');
}

function run() {
  const args = process.argv.slice(2);
  const flags = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i].startsWith('--') && i + 1 < args.length) {
      flags[args[i].slice(2)] = args[i + 1]; i++;
    }
  }

  const { utilities, categories, total } = loadUtilities();

  if (Object.keys(flags).length === 0) {
    console.log(`\nSLDS Utility Classes: ${total} total across ${Object.keys(categories).length} categories\n`);
    console.log('Usage:');
    console.log('  --category "all"        List all categories with counts');
    console.log('  --category "grid"       Show utilities in a specific category');
    console.log('  --search "slds-m-"      Search by class name or description');
    console.log('  --pattern "slds-p-*"    Wildcard pattern match');
    return;
  }

  if (flags.category) {
    if (flags.category === 'all') {
      console.log(`\nAll utility categories (${Object.keys(categories).length}):\n`);
      for (const [cat, count] of Object.entries(categories).sort()) {
        const guidePath = path.join(GUIDANCE_DIR, `${cat}.md`);
        const hasGuide = fs.existsSync(guidePath) ? ' (has guidance)' : '';
        console.log(`  ${cat.padEnd(20)} ${String(count).padStart(4)} classes${hasGuide}`);
      }
      console.log(`\nTotal: ${total} utility classes`);
      console.log('\nUse --category "<name>" to browse a specific category.');
      return;
    }

    const catKey = flags.category.toLowerCase().replace(/\s+/g, '-');
    const catUtilities = utilities.filter(u => {
      const uCat = (u.category_key || u.category || '').toLowerCase().replace(/\s+/g, '-');
      return uCat === catKey;
    });

    if (catUtilities.length === 0) {
      console.log(`Category "${flags.category}" not found or empty.`);
      console.log(`Available: ${Object.keys(categories).join(', ')}`);
      return;
    }

    console.log(`\n── ${flags.category} (${catUtilities.length} classes) ──\n`);
    for (const u of catUtilities.slice(0, 30)) {
      console.log(formatUtility(u));
      console.log();
    }
    if (catUtilities.length > 30) {
      console.log(`... and ${catUtilities.length - 30} more. Use --search to narrow.`);
    }

    const guidePath = path.join(GUIDANCE_DIR, `${catKey}.md`);
    if (fs.existsSync(guidePath)) {
      console.log(`\nDetailed guidance: guidance/utilities/${catKey}.md`);
    }
    return;
  }

  if (flags.pattern) {
    const regex = new RegExp('^' + flags.pattern.toLowerCase().replace(/\*/g, '.*') + '$');
    const matches = utilities.filter(u => regex.test((u.class || '').toLowerCase()));

    if (matches.length === 0) {
      console.log(`No utilities matching pattern "${flags.pattern}".`);
      return;
    }

    console.log(`\nFound ${matches.length} utility(ies) matching "${flags.pattern}":\n`);
    for (const u of matches.slice(0, 50)) {
      console.log(formatUtility(u));
      console.log();
    }
    if (matches.length > 50) {
      console.log(`... and ${matches.length - 50} more.`);
    }
    return;
  }

  if (flags.search) {
    const term = flags.search.toLowerCase();

    const exact = utilities.find(u => (u.class || '').toLowerCase() === term);
    if (exact) {
      console.log(`\nExact match:\n`);
      console.log(formatUtility(exact));
      return;
    }

    const matches = utilities.filter(u =>
      (u.class || '').toLowerCase().includes(term) ||
      (u.description || '').toLowerCase().includes(term)
    );

    if (matches.length === 0) {
      console.log(`No utilities found for "${flags.search}".`);
      console.log('Use --category "all" to browse available categories.');
      return;
    }

    console.log(`\nFound ${matches.length} utility(ies) for "${flags.search}":\n`);
    for (const u of matches.slice(0, 30)) {
      console.log(formatUtility(u));
      console.log();
    }
    if (matches.length > 30) {
      console.log(`... and ${matches.length - 30} more.`);
    }
    return;
  }
}

run();
