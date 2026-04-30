#!/usr/bin/env node

/**
 * Search SLDS icons with synonym matching and relevance scoring.
 *
 * Usage:
 *   node search-icons.js --query "save button"
 *   node search-icons.js --query "user" --category "standard"
 *   node search-icons.js --query "delete" --limit 20
 *   node search-icons.js --list-categories
 */

const fs = require('fs');
const path = require('path');

const ICONS_PATH = path.join(__dirname, '..', 'metadata', 'icon-metadata.json');

function loadIcons() {
  if (!fs.existsSync(ICONS_PATH)) {
    console.error(`Icon metadata not found: ${ICONS_PATH}`);
    process.exit(1);
  }
  const data = JSON.parse(fs.readFileSync(ICONS_PATH, 'utf8'));
  const icons = [];
  for (const [key, icon] of Object.entries(data.icons || {})) {
    icons.push({
      symbol: key,
      displayName: icon.displayName || key,
      category: icon.category || 'unknown',
      description: icon.description || '',
      synonyms: icon.synonyms || [],
      fullName: `${icon.category}:${key}`,
    });
  }
  return icons;
}

function tokenize(query) {
  return query.toLowerCase().split(/[\s_-]+/).filter(t => t.length > 0);
}

function scoreIcon(icon, query, tokens) {
  let score = 0;
  let matchType = 'partial';
  const matchedTerms = [];
  const sym = icon.symbol.toLowerCase();
  const syns = icon.synonyms.map(s => s.toLowerCase());
  const desc = icon.description.toLowerCase();

  if (sym === query) {
    score = 100; matchType = 'exact'; matchedTerms.push(icon.symbol);
  } else if (syns.includes(query)) {
    score = 95; matchType = 'synonym'; matchedTerms.push(...icon.synonyms.filter(s => s.toLowerCase() === query));
  } else if (sym.startsWith(query)) {
    score = 85; matchType = 'partial'; matchedTerms.push(icon.symbol);
  } else if (syns.some(s => s.startsWith(query))) {
    score = 80; matchType = 'synonym'; matchedTerms.push(...icon.synonyms.filter(s => s.toLowerCase().startsWith(query)));
  }

  if (score < 80 && sym.includes(query)) {
    score = Math.max(score, 70); matchedTerms.push(icon.symbol);
  }
  const partialSyns = icon.synonyms.filter(s => s.toLowerCase().includes(query));
  if (partialSyns.length > 0) {
    score = Math.max(score, 65); matchedTerms.push(...partialSyns);
    if (matchType === 'partial' && score === 65) matchType = 'synonym';
  }
  if (desc.includes(query)) {
    score = Math.max(score, 55);
    if (matchType === 'partial' && score === 55) matchType = 'contextual';
  }

  if (tokens.length > 1) {
    let tokenScore = 0;
    let matched = 0;
    for (const token of tokens) {
      let hit = false;
      if (sym.includes(token)) { tokenScore += 30; hit = true; matchedTerms.push(icon.symbol); }
      const synHits = icon.synonyms.filter(s => s.toLowerCase().includes(token));
      if (synHits.length) { tokenScore += 25; hit = true; matchedTerms.push(...synHits); }
      if (desc.includes(token)) { tokenScore += 10; hit = true; }
      if (hit) matched++;
    }
    if (matched > 1) tokenScore *= 1.2;
    if (tokenScore > score) { score = tokenScore; matchType = matched > 0 ? 'synonym' : 'contextual'; }
  }

  return { icon, score: Math.round(score), matchType, matchedTerms: [...new Set(matchedTerms)] };
}

function usageExample(fullName, category) {
  const altText = 'TODO: describe what this icon communicates';
  switch (category) {
    case 'action':
      return `<lightning-button-icon icon-name="${fullName}" alternative-text="${altText}" title="TODO: tooltip"></lightning-button-icon>`;
    case 'utility':
      return `<lightning-icon icon-name="${fullName}" alternative-text="${altText}" size="small"></lightning-icon>`;
    case 'standard':
    case 'custom':
      return `<lightning-icon icon-name="${fullName}" alternative-text="${altText}" size="medium"></lightning-icon>`;
    case 'doctype':
      return `<lightning-icon icon-name="${fullName}" alternative-text="${altText}" size="small"></lightning-icon>`;
    default:
      return `<lightning-icon icon-name="${fullName}" alternative-text="${altText}"></lightning-icon>`;
  }
}

function run() {
  const args = process.argv.slice(2);
  const flags = {};
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--list-categories') { flags.listCategories = true; continue; }
    if (args[i].startsWith('--') && i + 1 < args.length) {
      flags[args[i].slice(2)] = args[i + 1]; i++;
    }
  }

  const icons = loadIcons();

  if (flags.listCategories) {
    const cats = {};
    for (const icon of icons) {
      cats[icon.category] = (cats[icon.category] || 0) + 1;
    }
    console.log('\nIcon categories:');
    for (const [cat, count] of Object.entries(cats).sort()) {
      console.log(`  ${cat.padEnd(12)} ${count} icons`);
    }
    return;
  }

  if (!flags.query) {
    console.log('Usage: node search-icons.js --query "search term" [--category action|utility|standard|custom|doctype] [--limit N]');
    return;
  }

  const query = flags.query.toLowerCase().trim();
  const limit = parseInt(flags.limit) || 10;
  const tokens = tokenize(query);

  let searchable = icons;
  if (flags.category) {
    const cat = flags.category.toLowerCase();
    searchable = searchable.filter(i => i.category === cat);
  }

  const results = searchable
    .map(icon => scoreIcon(icon, query, tokens))
    .filter(r => r.score > 0)
    .sort((a, b) => b.score - a.score || a.icon.symbol.localeCompare(b.icon.symbol))
    .slice(0, limit);

  if (results.length === 0) {
    console.log(`No icons found for "${flags.query}".`);
    const suggestions = icons
      .filter(i => i.symbol.startsWith(query.slice(0, 3)))
      .slice(0, 5)
      .map(i => i.symbol);
    if (suggestions.length) console.log(`Try: ${suggestions.join(', ')}`);
    return;
  }

  console.log(`\nFound ${results.length} icon(s) for "${flags.query}":\n`);
  for (const r of results) {
    const { icon, score, matchType, matchedTerms } = r;
    console.log(`  ${icon.fullName.padEnd(35)} score: ${score}  match: ${matchType}`);
    if (matchedTerms.length) console.log(`    matched: ${matchedTerms.join(', ')}`);
    console.log(`    ${icon.description.slice(0, 80)}`);
    console.log(`    LWC: ${usageExample(icon.fullName, icon.category)}`);
    console.log();
  }
}

run();
