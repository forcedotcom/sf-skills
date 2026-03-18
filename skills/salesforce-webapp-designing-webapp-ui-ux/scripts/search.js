#!/usr/bin/env node

import { CSV_CONFIG, AVAILABLE_STACKS, MAX_RESULTS, search, searchStack } from './core.js';
import { generateDesignSystem } from './design_system.js';

// ============ ARG PARSER ============

function parseArgs(argv) {
  const args = { query: null, maxResults: MAX_RESULTS, format: 'ascii' };
  let i = 2;
  while (i < argv.length) {
    const a = argv[i];
    if (a === '--domain' || a === '-d') { args.domain = argv[++i]; }
    else if (a === '--stack' || a === '-s') { args.stack = argv[++i]; }
    else if (a === '--max-results' || a === '-n') { args.maxResults = parseInt(argv[++i], 10); }
    else if (a === '--json') { args.json = true; }
    else if (a === '--design-system' || a === '-ds') { args.designSystem = true; }
    else if (a === '--project-name' || a === '-p') { args.projectName = argv[++i]; }
    else if (a === '--format' || a === '-f') { args.format = argv[++i]; }
    else if (a === '--persist') { args.persist = true; }
    else if (a === '--page') { args.page = argv[++i]; }
    else if (a === '--output-dir' || a === '-o') { args.outputDir = argv[++i]; }
    else if (!a.startsWith('-') && !args.query) { args.query = a; }
    i++;
  }
  return args;
}

// ============ FORMATTER ============

function formatOutput(result) {
  if (result.error) return `Error: ${result.error}`;

  const lines = [];
  if (result.stack) {
    lines.push('## UI Pro Max Stack Guidelines');
    lines.push(`**Stack:** ${result.stack} | **Query:** ${result.query}`);
  } else {
    lines.push('## UI Pro Max Search Results');
    lines.push(`**Domain:** ${result.domain} | **Query:** ${result.query}`);
  }
  lines.push(`**Source:** ${result.file} | **Found:** ${result.count} results\n`);

  (result.results || []).forEach((row, i) => {
    lines.push(`### Result ${i + 1}`);
    for (const [key, value] of Object.entries(row)) {
      const v = String(value);
      lines.push(`- **${key}:** ${v.length > 300 ? v.slice(0, 300) + '...' : v}`);
    }
    lines.push('');
  });

  return lines.join('\n');
}

// ============ MAIN ============

const args = parseArgs(process.argv);

if (!args.query) {
  console.error('Usage: node search.js "<query>" [--domain <d>] [--stack <s>] [--design-system] [-p "Name"]');
  console.error(`Domains: ${Object.keys(CSV_CONFIG).join(', ')}`);
  console.error(`Stacks: ${AVAILABLE_STACKS.join(', ')}`);
  process.exit(1);
}

if (args.designSystem) {
  const result = generateDesignSystem(
    args.query,
    args.projectName,
    args.format,
    !!args.persist,
    args.page || null,
    args.outputDir || null
  );
  console.log(result);

  if (args.persist) {
    const slug = args.projectName ? args.projectName.toLowerCase().replace(/\s+/g, '-') : 'default';
    console.log('\n' + '='.repeat(60));
    console.log(`✅ Design system persisted to design-system/${slug}/`);
    console.log(`   📄 design-system/${slug}/MASTER.md (Global Source of Truth)`);
    if (args.page) {
      const pageSlug = args.page.toLowerCase().replace(/\s+/g, '-');
      console.log(`   📄 design-system/${slug}/pages/${pageSlug}.md (Page Overrides)`);
    }
    console.log('');
    console.log(`📖 Usage: When building a page, check design-system/${slug}/pages/[page].md first.`);
    console.log(`   If exists, its rules override MASTER.md. Otherwise, use MASTER.md.`);
    console.log('='.repeat(60));
  }
} else if (args.stack) {
  const result = searchStack(args.query, args.stack, args.maxResults);
  console.log(args.json ? JSON.stringify(result, null, 2) : formatOutput(result));
} else {
  const result = search(args.query, args.domain, args.maxResults);
  console.log(args.json ? JSON.stringify(result, null, 2) : formatOutput(result));
}
