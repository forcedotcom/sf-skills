#!/usr/bin/env node

import fs from 'fs';
import path from 'path';
import { search, loadCsv, DATA_DIR } from './core.js';

const REASONING_FILE = 'ui-reasoning.csv';

const SEARCH_CONFIG = {
  product: { maxResults: 1 },
  style: { maxResults: 3 },
  color: { maxResults: 2 },
  landing: { maxResults: 2 },
  typography: { maxResults: 2 }
};

// ============ DESIGN SYSTEM GENERATOR ============

function loadReasoning() {
  try {
    const filepath = path.join(DATA_DIR, REASONING_FILE);
    return loadCsv(filepath);
  } catch (err) {
    console.error('Warning: could not load reasoning file:', err?.message || err);
    return [];
  }
}

function multiDomainSearch(query, stylePriority) {
  const results = {};
  for (const [domain, config] of Object.entries(SEARCH_CONFIG)) {
    try {
      if (domain === 'style' && stylePriority && stylePriority.length > 0) {
        const priorityQuery = stylePriority.slice(0, 2).join(' ');
        results[domain] = search(`${query} ${priorityQuery}`, domain, config.maxResults);
      } else {
        results[domain] = search(query, domain, config.maxResults);
      }
    } catch (err) {
      console.error(`Warning: search failed for domain "${domain}":`, err?.message || err);
      results[domain] = { results: [] };
    }
  }
  return results;
}

function findReasoningRule(reasoningData, category) {
  const catLower = category.toLowerCase();

  for (const rule of reasoningData) {
    if ((rule.UI_Category || '').toLowerCase() === catLower) return rule;
  }
  for (const rule of reasoningData) {
    const uiCat = (rule.UI_Category || '').toLowerCase();
    if (uiCat.includes(catLower) || catLower.includes(uiCat)) return rule;
  }
  for (const rule of reasoningData) {
    const uiCat = (rule.UI_Category || '').toLowerCase();
    const keywords = uiCat.replace(/\//g, ' ').replace(/-/g, ' ').split(/\s+/);
    if (keywords.some(kw => catLower.includes(kw))) return rule;
  }
  return {};
}

function applyReasoning(reasoningData, category) {
  const rule = findReasoningRule(reasoningData, category);

  if (!rule || Object.keys(rule).length === 0) {
    return {
      pattern: 'Hero + Features + CTA',
      stylePriority: ['Minimalism', 'Flat Design'],
      colorMood: 'Professional',
      typographyMood: 'Clean',
      keyEffects: 'Subtle hover transitions',
      antiPatterns: '',
      decisionRules: {},
      severity: 'MEDIUM'
    };
  }

  let decisionRules = {};
  try {
    decisionRules = JSON.parse(rule.Decision_Rules || '{}');
  } catch {
    // invalid JSON, keep empty object
  }

  return {
    pattern: rule.Recommended_Pattern || '',
    stylePriority: (rule.Style_Priority || '').split('+').map(s => s.trim()),
    colorMood: rule.Color_Mood || '',
    typographyMood: rule.Typography_Mood || '',
    keyEffects: rule.Key_Effects || '',
    antiPatterns: rule.Anti_Patterns || '',
    decisionRules,
    severity: rule.Severity || 'MEDIUM'
  };
}

function selectBestMatch(results, priorityKeywords) {
  try {
    if (!results || results.length === 0) return {};
    if (!priorityKeywords || priorityKeywords.length === 0) return results[0];

    for (const priority of priorityKeywords) {
      const pLower = priority.toLowerCase().trim();
      for (const result of results) {
        const name = (result['Style Category'] || '').toLowerCase();
        if (pLower.includes(name) || name.includes(pLower)) return result;
      }
    }

    const scored = results.map(result => {
      const str = JSON.stringify(result).toLowerCase();
      let score = 0;
      for (const kw of priorityKeywords) {
        const k = kw.toLowerCase().trim();
        if ((result['Style Category'] || '').toLowerCase().includes(k)) score += 10;
        else if ((result.Keywords || '').toLowerCase().includes(k)) score += 3;
        else if (str.includes(k)) score += 1;
      }
      return { score, result };
    });

    scored.sort((a, b) => b.score - a.score);
    return scored[0] && scored[0].score > 0 ? scored[0].result : results[0];
  } catch (err) {
    console.error('Warning: selectBestMatch failed:', err?.message || err);
    return results?.[0] ?? {};
  }
}

function getDefaultDesignSystem(query, projectName) {
  return {
    project_name: projectName || (typeof query === 'string' ? query.toUpperCase() : 'PROJECT'),
    category: 'General',
    pattern: { name: 'Hero + Features + CTA', sections: 'Hero > Features > CTA', cta_placement: 'Above fold', color_strategy: '', conversion: '' },
    style: { name: 'Minimalism', type: 'General', effects: '', keywords: '', best_for: '', performance: '', accessibility: '' },
    colors: { primary: '#2563EB', secondary: '#3B82F6', cta: '#F97316', background: '#F8FAFC', text: '#1E293B', notes: '' },
    typography: { heading: 'Inter', body: 'Inter', mood: 'Clean', best_for: '', google_fonts_url: '', css_import: '' },
    key_effects: 'Subtle hover transitions',
    anti_patterns: '',
    decision_rules: {},
    severity: 'MEDIUM'
  };
}

function generate(query, projectName) {
  try {
    const reasoningData = loadReasoning();

    let productResult = { results: [] };
    try {
      productResult = search(query, 'product', 1);
    } catch (err) {
      console.error('Warning: product search failed:', err?.message || err);
    }
    const productResults = productResult.results || [];
    let category = 'General';
    if (productResults.length > 0) category = productResults[0]['Product Type'] || 'General';

    const reasoning = applyReasoning(reasoningData, category);
    const stylePriority = reasoning.stylePriority || [];

    const searchResults = multiDomainSearch(query, stylePriority);
    searchResults.product = productResult;

    const styleResults = (searchResults.style || {}).results || [];
    const colorResults = (searchResults.color || {}).results || [];
    const typographyResults = (searchResults.typography || {}).results || [];
    const landingResults = (searchResults.landing || {}).results || [];

    const bestStyle = selectBestMatch(styleResults, reasoning.stylePriority);
    const bestColor = colorResults[0] || {};
    const bestTypography = typographyResults[0] || {};
    const bestLanding = landingResults[0] || {};

    const styleEffects = bestStyle['Effects & Animation'] || '';
    const reasoningEffects = reasoning.keyEffects || '';

    return {
      project_name: projectName || (typeof query === 'string' ? query.toUpperCase() : 'PROJECT'),
      category,
      pattern: {
        name: bestLanding['Pattern Name'] || reasoning.pattern || 'Hero + Features + CTA',
        sections: bestLanding['Section Order'] || 'Hero > Features > CTA',
        cta_placement: bestLanding['Primary CTA Placement'] || 'Above fold',
        color_strategy: bestLanding['Color Strategy'] || '',
        conversion: bestLanding['Conversion Optimization'] || ''
      },
      style: {
        name: bestStyle['Style Category'] || 'Minimalism',
        type: bestStyle.Type || 'General',
        effects: styleEffects,
        keywords: bestStyle.Keywords || '',
        best_for: bestStyle['Best For'] || '',
        performance: bestStyle.Performance || '',
        accessibility: bestStyle.Accessibility || ''
      },
      colors: {
        primary: bestColor['Primary (Hex)'] || '#2563EB',
        secondary: bestColor['Secondary (Hex)'] || '#3B82F6',
        cta: bestColor['CTA (Hex)'] || '#F97316',
        background: bestColor['Background (Hex)'] || '#F8FAFC',
        text: bestColor['Text (Hex)'] || '#1E293B',
        notes: bestColor.Notes || ''
      },
      typography: {
        heading: bestTypography['Heading Font'] || 'Inter',
        body: bestTypography['Body Font'] || 'Inter',
        mood: bestTypography['Mood/Style Keywords'] || reasoning.typographyMood || '',
        best_for: bestTypography['Best For'] || '',
        google_fonts_url: bestTypography['Google Fonts URL'] || '',
        css_import: bestTypography['CSS Import'] || ''
      },
      key_effects: styleEffects || reasoningEffects,
      anti_patterns: reasoning.antiPatterns || '',
      decision_rules: reasoning.decisionRules || {},
      severity: reasoning.severity || 'MEDIUM'
    };
  } catch (err) {
    console.error('Error generating design system:', err?.message || err);
    return getDefaultDesignSystem(query, projectName);
  }
}

// ============ OUTPUT FORMATTERS ============

const BOX_WIDTH = 90;

function wrapText(text, prefix, width) {
  if (!text) return [];
  const words = text.split(/\s+/);
  const lines = [];
  let cur = prefix;
  for (const word of words) {
    if (cur.length + word.length + 1 <= width - 2) {
      cur += (cur !== prefix ? ' ' : '') + word;
    } else {
      if (cur !== prefix) lines.push(cur);
      cur = prefix + word;
    }
  }
  if (cur !== prefix) lines.push(cur);
  return lines;
}

function formatAsciiBox(ds) {
  try {
    if (!ds || typeof ds !== 'object') return 'Error: invalid design system object';
  const project = ds.project_name || 'PROJECT';
  const pattern = ds.pattern || {};
  const style = ds.style || {};
  const colors = ds.colors || {};
  const typo = ds.typography || {};
  const effects = ds.key_effects || '';
  const antiPatterns = ds.anti_patterns || '';

  const sections = (pattern.sections || '').split('>').map(s => s.trim()).filter(Boolean);
  const w = BOX_WIDTH - 1;
  const pad = s => s.padEnd(BOX_WIDTH) + '|';
  const blank = () => pad('|' + ' '.repeat(BOX_WIDTH));
  const lines = [];

  lines.push('+' + '-'.repeat(w) + '+');
  lines.push(pad(`|  TARGET: ${project} - RECOMMENDED DESIGN SYSTEM`));
  lines.push('+' + '-'.repeat(w) + '+');
  lines.push(blank());

  lines.push(pad(`|  PATTERN: ${pattern.name || ''}`));
  if (pattern.conversion) lines.push(pad(`|     Conversion: ${pattern.conversion}`));
  if (pattern.cta_placement) lines.push(pad(`|     CTA: ${pattern.cta_placement}`));
  lines.push(pad('|     Sections:'));
  sections.forEach((s, i) => lines.push(pad(`|       ${i + 1}. ${s}`)));
  lines.push(blank());

  lines.push(pad(`|  STYLE: ${style.name || ''}`));
  if (style.keywords) wrapText(`Keywords: ${style.keywords}`, '|     ', BOX_WIDTH).forEach(l => lines.push(pad(l)));
  if (style.best_for) wrapText(`Best For: ${style.best_for}`, '|     ', BOX_WIDTH).forEach(l => lines.push(pad(l)));
  if (style.performance || style.accessibility) {
    lines.push(pad(`|     Performance: ${style.performance || ''} | Accessibility: ${style.accessibility || ''}`));
  }
  lines.push(blank());

  lines.push(pad('|  COLORS:'));
  lines.push(pad(`|     Primary:    ${colors.primary || ''}`));
  lines.push(pad(`|     Secondary:  ${colors.secondary || ''}`));
  lines.push(pad(`|     CTA:        ${colors.cta || ''}`));
  lines.push(pad(`|     Background: ${colors.background || ''}`));
  lines.push(pad(`|     Text:       ${colors.text || ''}`));
  if (colors.notes) wrapText(`Notes: ${colors.notes}`, '|     ', BOX_WIDTH).forEach(l => lines.push(pad(l)));
  lines.push(blank());

  lines.push(pad(`|  TYPOGRAPHY: ${typo.heading || ''} / ${typo.body || ''}`));
  if (typo.mood) wrapText(`Mood: ${typo.mood}`, '|     ', BOX_WIDTH).forEach(l => lines.push(pad(l)));
  if (typo.best_for) wrapText(`Best For: ${typo.best_for}`, '|     ', BOX_WIDTH).forEach(l => lines.push(pad(l)));
  if (typo.google_fonts_url) lines.push(pad(`|     Google Fonts: ${typo.google_fonts_url}`));
  if (typo.css_import) lines.push(pad(`|     CSS Import: ${typo.css_import.slice(0, 70)}...`));
  lines.push(blank());

  if (effects) {
    lines.push(pad('|  KEY EFFECTS:'));
    wrapText(effects, '|     ', BOX_WIDTH).forEach(l => lines.push(pad(l)));
    lines.push(blank());
  }

  if (antiPatterns) {
    lines.push(pad('|  AVOID (Anti-patterns):'));
    wrapText(antiPatterns, '|     ', BOX_WIDTH).forEach(l => lines.push(pad(l)));
    lines.push(blank());
  }

  lines.push(pad('|  PRE-DELIVERY CHECKLIST:'));
  [
    '[ ] No emojis as icons (use SVG: Heroicons/Lucide)',
    '[ ] cursor-pointer on all clickable elements',
    '[ ] Hover states with smooth transitions (150-300ms)',
    '[ ] Light mode: text contrast 4.5:1 minimum',
    '[ ] Focus states visible for keyboard nav',
    '[ ] prefers-reduced-motion respected',
    '[ ] Responsive: 375px, 768px, 1024px, 1440px'
  ].forEach(item => lines.push(pad(`|     ${item}`)));
  lines.push(blank());

  lines.push('+' + '-'.repeat(w) + '+');
  return lines.join('\n');
  } catch (err) {
    console.error('Error formatting ASCII box:', err?.message || err);
    return `Error: could not format design system (${err?.message || err})`;
  }
}

function formatMarkdown(ds) {
  try {
    if (!ds || typeof ds !== 'object') return 'Error: invalid design system object';
  const project = ds.project_name || 'PROJECT';
  const pattern = ds.pattern || {};
  const style = ds.style || {};
  const colors = ds.colors || {};
  const typo = ds.typography || {};
  const effects = ds.key_effects || '';
  const antiPatterns = ds.anti_patterns || '';

  const L = [];
  L.push(`## Design System: ${project}`, '');

  L.push('### Pattern');
  L.push(`- **Name:** ${pattern.name || ''}`);
  if (pattern.conversion) L.push(`- **Conversion Focus:** ${pattern.conversion}`);
  if (pattern.cta_placement) L.push(`- **CTA Placement:** ${pattern.cta_placement}`);
  if (pattern.color_strategy) L.push(`- **Color Strategy:** ${pattern.color_strategy}`);
  L.push(`- **Sections:** ${pattern.sections || ''}`, '');

  L.push('### Style');
  L.push(`- **Name:** ${style.name || ''}`);
  if (style.keywords) L.push(`- **Keywords:** ${style.keywords}`);
  if (style.best_for) L.push(`- **Best For:** ${style.best_for}`);
  if (style.performance || style.accessibility) {
    L.push(`- **Performance:** ${style.performance || ''} | **Accessibility:** ${style.accessibility || ''}`);
  }
  L.push('');

  L.push('### Colors');
  L.push('| Role | Hex |', '|------|-----|');
  L.push(`| Primary | ${colors.primary || ''} |`);
  L.push(`| Secondary | ${colors.secondary || ''} |`);
  L.push(`| CTA | ${colors.cta || ''} |`);
  L.push(`| Background | ${colors.background || ''} |`);
  L.push(`| Text | ${colors.text || ''} |`);
  if (colors.notes) L.push(`\n*Notes: ${colors.notes}*`);
  L.push('');

  L.push('### Typography');
  L.push(`- **Heading:** ${typo.heading || ''}`);
  L.push(`- **Body:** ${typo.body || ''}`);
  if (typo.mood) L.push(`- **Mood:** ${typo.mood}`);
  if (typo.best_for) L.push(`- **Best For:** ${typo.best_for}`);
  if (typo.google_fonts_url) L.push(`- **Google Fonts:** ${typo.google_fonts_url}`);
  if (typo.css_import) L.push('- **CSS Import:**', '```css', typo.css_import, '```');
  L.push('');

  if (effects) L.push('### Key Effects', effects, '');
  if (antiPatterns) L.push('### Avoid (Anti-patterns)', `- ${antiPatterns.replace(/ \+ /g, '\n- ')}`, '');

  L.push('### Pre-Delivery Checklist');
  L.push('- [ ] No emojis as icons (use SVG: Heroicons/Lucide)');
  L.push('- [ ] cursor-pointer on all clickable elements');
  L.push('- [ ] Hover states with smooth transitions (150-300ms)');
  L.push('- [ ] Light mode: text contrast 4.5:1 minimum');
  L.push('- [ ] Focus states visible for keyboard nav');
  L.push('- [ ] prefers-reduced-motion respected');
  L.push('- [ ] Responsive: 375px, 768px, 1024px, 1440px', '');

  return L.join('\n');
  } catch (err) {
    console.error('Error formatting markdown:', err?.message || err);
    return `Error: could not format design system (${err?.message || err})`;
  }
}

// ============ PERSISTENCE ============

function timestamp() {
  const d = new Date();
  const pad = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function formatMasterMd(ds) {
  try {
    if (!ds || typeof ds !== 'object') return '# Error: invalid design system object';
  const project = ds.project_name || 'PROJECT';
  const pattern = ds.pattern || {};
  const style = ds.style || {};
  const colors = ds.colors || {};
  const typo = ds.typography || {};
  const effects = ds.key_effects || '';
  const antiPatterns = ds.anti_patterns || '';
  const ts = timestamp();

  const L = [];

  L.push('# Design System Master File');
  L.push('');
  L.push('> **LOGIC:** When building a specific page, first check `design-system/pages/[page-name].md`.');
  L.push('> If that file exists, its rules **override** this Master file.');
  L.push('> If not, strictly follow the rules below.');
  L.push('', '---', '');
  L.push(`**Project:** ${project}`);
  L.push(`**Generated:** ${ts}`);
  L.push(`**Category:** ${ds.category || 'General'}`);
  L.push('', '---', '');

  // Global Rules
  L.push('## Global Rules', '');

  L.push('### Color Palette', '');
  L.push('| Role | Hex | CSS Variable |');
  L.push('|------|-----|--------------|');
  L.push(`| Primary | \`${colors.primary || '#2563EB'}\` | \`--color-primary\` |`);
  L.push(`| Secondary | \`${colors.secondary || '#3B82F6'}\` | \`--color-secondary\` |`);
  L.push(`| CTA/Accent | \`${colors.cta || '#F97316'}\` | \`--color-cta\` |`);
  L.push(`| Background | \`${colors.background || '#F8FAFC'}\` | \`--color-background\` |`);
  L.push(`| Text | \`${colors.text || '#1E293B'}\` | \`--color-text\` |`);
  L.push('');
  if (colors.notes) L.push(`**Color Notes:** ${colors.notes}`, '');

  L.push('### Typography', '');
  L.push(`- **Heading Font:** ${typo.heading || 'Inter'}`);
  L.push(`- **Body Font:** ${typo.body || 'Inter'}`);
  if (typo.mood) L.push(`- **Mood:** ${typo.mood}`);
  if (typo.google_fonts_url) L.push(`- **Google Fonts:** [${typo.heading || ''} + ${typo.body || ''}](${typo.google_fonts_url})`);
  L.push('');
  if (typo.css_import) L.push('**CSS Import:**', '```css', typo.css_import, '```', '');

  L.push('### Spacing Variables', '');
  L.push('| Token | Value | Usage |');
  L.push('|-------|-------|-------|');
  L.push('| `--space-xs` | `4px` / `0.25rem` | Tight gaps |');
  L.push('| `--space-sm` | `8px` / `0.5rem` | Icon gaps, inline spacing |');
  L.push('| `--space-md` | `16px` / `1rem` | Standard padding |');
  L.push('| `--space-lg` | `24px` / `1.5rem` | Section padding |');
  L.push('| `--space-xl` | `32px` / `2rem` | Large gaps |');
  L.push('| `--space-2xl` | `48px` / `3rem` | Section margins |');
  L.push('| `--space-3xl` | `64px` / `4rem` | Hero padding |');
  L.push('');

  L.push('### Shadow Depths', '');
  L.push('| Level | Value | Usage |');
  L.push('|-------|-------|-------|');
  L.push('| `--shadow-sm` | `0 1px 2px rgba(0,0,0,0.05)` | Subtle lift |');
  L.push('| `--shadow-md` | `0 4px 6px rgba(0,0,0,0.1)` | Cards, buttons |');
  L.push('| `--shadow-lg` | `0 10px 15px rgba(0,0,0,0.1)` | Modals, dropdowns |');
  L.push('| `--shadow-xl` | `0 20px 25px rgba(0,0,0,0.15)` | Hero images, featured cards |');
  L.push('');

  // Component Specs
  L.push('---', '', '## Component Specs', '');

  L.push('### Buttons', '');
  L.push('```css');
  L.push('/* Primary Button */');
  L.push('.btn-primary {');
  L.push(`  background: ${colors.cta || '#F97316'};`);
  L.push('  color: white;');
  L.push('  padding: 12px 24px;');
  L.push('  border-radius: 8px;');
  L.push('  font-weight: 600;');
  L.push('  transition: all 200ms ease;');
  L.push('  cursor: pointer;');
  L.push('}');
  L.push('');
  L.push('.btn-primary:hover {');
  L.push('  opacity: 0.9;');
  L.push('  transform: translateY(-1px);');
  L.push('}');
  L.push('');
  L.push('/* Secondary Button */');
  L.push('.btn-secondary {');
  L.push('  background: transparent;');
  L.push(`  color: ${colors.primary || '#2563EB'};`);
  L.push(`  border: 2px solid ${colors.primary || '#2563EB'};`);
  L.push('  padding: 12px 24px;');
  L.push('  border-radius: 8px;');
  L.push('  font-weight: 600;');
  L.push('  transition: all 200ms ease;');
  L.push('  cursor: pointer;');
  L.push('}');
  L.push('```', '');

  L.push('### Cards', '');
  L.push('```css');
  L.push('.card {');
  L.push(`  background: ${colors.background || '#FFFFFF'};`);
  L.push('  border-radius: 12px;');
  L.push('  padding: 24px;');
  L.push('  box-shadow: var(--shadow-md);');
  L.push('  transition: all 200ms ease;');
  L.push('  cursor: pointer;');
  L.push('}');
  L.push('');
  L.push('.card:hover {');
  L.push('  box-shadow: var(--shadow-lg);');
  L.push('  transform: translateY(-2px);');
  L.push('}');
  L.push('```', '');

  L.push('### Inputs', '');
  L.push('```css');
  L.push('.input {');
  L.push('  padding: 12px 16px;');
  L.push('  border: 1px solid #E2E8F0;');
  L.push('  border-radius: 8px;');
  L.push('  font-size: 16px;');
  L.push('  transition: border-color 200ms ease;');
  L.push('}');
  L.push('');
  L.push('.input:focus {');
  L.push(`  border-color: ${colors.primary || '#2563EB'};`);
  L.push('  outline: none;');
  L.push(`  box-shadow: 0 0 0 3px ${colors.primary || '#2563EB'}20;`);
  L.push('}');
  L.push('```', '');

  L.push('### Modals', '');
  L.push('```css');
  L.push('.modal-overlay {');
  L.push('  background: rgba(0, 0, 0, 0.5);');
  L.push('  backdrop-filter: blur(4px);');
  L.push('}');
  L.push('');
  L.push('.modal {');
  L.push('  background: white;');
  L.push('  border-radius: 16px;');
  L.push('  padding: 32px;');
  L.push('  box-shadow: var(--shadow-xl);');
  L.push('  max-width: 500px;');
  L.push('  width: 90%;');
  L.push('}');
  L.push('```', '');

  // Style Guidelines
  L.push('---', '', '## Style Guidelines', '');
  L.push(`**Style:** ${style.name || 'Minimalism'}`, '');
  if (style.keywords) L.push(`**Keywords:** ${style.keywords}`, '');
  if (style.best_for) L.push(`**Best For:** ${style.best_for}`, '');
  if (effects) L.push(`**Key Effects:** ${effects}`, '');

  L.push('### Page Pattern', '');
  L.push(`**Pattern Name:** ${pattern.name || ''}`, '');
  if (pattern.conversion) L.push(`- **Conversion Strategy:** ${pattern.conversion}`);
  if (pattern.cta_placement) L.push(`- **CTA Placement:** ${pattern.cta_placement}`);
  L.push(`- **Section Order:** ${pattern.sections || ''}`, '');

  // Anti-Patterns
  L.push('---', '', '## Anti-Patterns (Do NOT Use)', '');
  if (antiPatterns) {
    for (const a of antiPatterns.split('+').map(s => s.trim()).filter(Boolean)) {
      L.push(`- ❌ ${a}`);
    }
  }
  L.push('');
  L.push('### Additional Forbidden Patterns', '');
  L.push('- ❌ **Emojis as icons** — Use SVG icons (Heroicons, Lucide, Simple Icons)');
  L.push('- ❌ **Missing cursor:pointer** — All clickable elements must have cursor:pointer');
  L.push('- ❌ **Layout-shifting hovers** — Avoid scale transforms that shift layout');
  L.push('- ❌ **Low contrast text** — Maintain 4.5:1 minimum contrast ratio');
  L.push('- ❌ **Instant state changes** — Always use transitions (150-300ms)');
  L.push('- ❌ **Invisible focus states** — Focus states must be visible for a11y');
  L.push('');

  // Pre-Delivery Checklist
  L.push('---', '', '## Pre-Delivery Checklist', '');
  L.push('Before delivering any UI code, verify:', '');
  L.push('- [ ] No emojis used as icons (use SVG instead)');
  L.push('- [ ] All icons from consistent icon set (Heroicons/Lucide)');
  L.push('- [ ] `cursor-pointer` on all clickable elements');
  L.push('- [ ] Hover states with smooth transitions (150-300ms)');
  L.push('- [ ] Light mode: text contrast 4.5:1 minimum');
  L.push('- [ ] Focus states visible for keyboard navigation');
  L.push('- [ ] `prefers-reduced-motion` respected');
  L.push('- [ ] Responsive: 375px, 768px, 1024px, 1440px');
  L.push('- [ ] No content hidden behind fixed navbars');
  L.push('- [ ] No horizontal scroll on mobile', '');

  return L.join('\n');
  } catch (err) {
    console.error('Error formatting MASTER.md:', err?.message || err);
    return `# Error: could not format design system (${err?.message || err})`;
  }
}

// ============ PAGE OVERRIDES ============

function detectPageType(context, styleResults) {
  const ctx = context.toLowerCase();
  const patterns = [
    [['dashboard', 'admin', 'analytics', 'data', 'metrics', 'stats', 'monitor', 'overview'], 'Dashboard / Data View'],
    [['checkout', 'payment', 'cart', 'purchase', 'order', 'billing'], 'Checkout / Payment'],
    [['settings', 'profile', 'account', 'preferences', 'config'], 'Settings / Profile'],
    [['landing', 'marketing', 'homepage', 'hero', 'home', 'promo'], 'Landing / Marketing'],
    [['login', 'signin', 'signup', 'register', 'auth', 'password'], 'Authentication'],
    [['pricing', 'plans', 'subscription', 'tiers', 'packages'], 'Pricing / Plans'],
    [['blog', 'article', 'post', 'news', 'content', 'story'], 'Blog / Article'],
    [['product', 'item', 'detail', 'pdp', 'shop', 'store'], 'Product Detail'],
    [['search', 'results', 'browse', 'filter', 'catalog', 'list'], 'Search Results'],
    [['empty', '404', 'error', 'not found', 'zero'], 'Empty State']
  ];

  for (const [keywords, pageType] of patterns) {
    if (keywords.some(kw => ctx.includes(kw))) return pageType;
  }

  if (styleResults && styleResults.length > 0) {
    const bestFor = (styleResults[0]['Best For'] || '').toLowerCase();
    if (bestFor.includes('dashboard') || bestFor.includes('data')) return 'Dashboard / Data View';
    if (bestFor.includes('landing') || bestFor.includes('marketing')) return 'Landing / Marketing';
  }

  return 'General';
}

function generateIntelligentOverrides(pageName, pageQuery, _designSystem) {
  try {
  const pageLower = (pageName || '').toLowerCase();
  const queryLower = (pageQuery || '').toLowerCase();
  const combined = `${pageLower} ${queryLower}`;

  let styleSearch = { results: [] };
  let uxSearch = { results: [] };
  let landingSearch = { results: [] };
  try {
    styleSearch = search(combined, 'style', 1);
  } catch (err) {
    console.error('Warning: style search failed in page overrides:', err?.message || err);
  }
  try {
    uxSearch = search(combined, 'ux', 3);
  } catch (err) {
    console.error('Warning: ux search failed in page overrides:', err?.message || err);
  }
  try {
    landingSearch = search(combined, 'landing', 1);
  } catch (err) {
    console.error('Warning: landing search failed in page overrides:', err?.message || err);
  }

  const styleResults = styleSearch.results || [];
  const uxResults = uxSearch.results || [];
  const landingResults = landingSearch.results || [];

  const pageType = detectPageType(combined, styleResults);

  const layout = {};
  const spacing = {};
  const typography = {};
  const colors = {};
  const components = [];
  const uniqueComponents = [];
  const recommendations = [];

  if (styleResults.length > 0) {
    const s = styleResults[0];
    const keywords = (s.Keywords || '').toLowerCase();
    const effects = s['Effects & Animation'] || '';

    if (['data', 'dense', 'dashboard', 'grid'].some(kw => keywords.includes(kw))) {
      layout['Max Width'] = '1400px or full-width';
      layout['Grid'] = '12-column grid for data flexibility';
      spacing['Content Density'] = 'High — optimize for information display';
    } else if (['minimal', 'simple', 'clean', 'single'].some(kw => keywords.includes(kw))) {
      layout['Max Width'] = '800px (narrow, focused)';
      layout['Layout'] = 'Single column, centered';
      spacing['Content Density'] = 'Low — focus on clarity';
    } else {
      layout['Max Width'] = '1200px (standard)';
      layout['Layout'] = 'Full-width sections, centered content';
    }

    if (effects) recommendations.push(`Effects: ${effects}`);
  }

  for (const ux of uxResults) {
    const cat = ux.Category || '';
    const doText = ux.Do || '';
    const dontText = ux["Don't"] || '';
    if (doText) recommendations.push(`${cat}: ${doText}`);
    if (dontText) components.push(`Avoid: ${dontText}`);
  }

  if (landingResults.length > 0) {
    const l = landingResults[0];
    if (l['Section Order']) layout['Sections'] = l['Section Order'];
    if (l['Primary CTA Placement']) recommendations.push(`CTA Placement: ${l['Primary CTA Placement']}`);
    if (l['Color Strategy']) colors['Strategy'] = l['Color Strategy'];
  }

  if (Object.keys(layout).length === 0) {
    layout['Max Width'] = '1200px';
    layout['Layout'] = 'Responsive grid';
  }

  if (recommendations.length === 0) {
    recommendations.push('Refer to MASTER.md for all design rules', 'Add specific overrides as needed for this page');
  }

  return { page_type: pageType, layout, spacing, typography, colors, components, unique_components: uniqueComponents, recommendations };
  } catch (err) {
    console.error('Error generating page overrides:', err?.message || err);
    return {
      page_type: 'General',
      layout: { 'Max Width': '1200px', Layout: 'Responsive grid' },
      spacing: {},
      typography: {},
      colors: {},
      components: [],
      unique_components: [],
      recommendations: ['Refer to MASTER.md for all design rules']
    };
  }
}

function formatPageOverrideMd(designSystem, pageName, pageQuery) {
  try {
    if (!designSystem || typeof designSystem !== 'object') return '# Error: invalid design system';
  const project = designSystem.project_name || 'PROJECT';
  const ts = timestamp();
  const pageTitle = (pageName || 'Page').replace(/[-_]/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
  const overrides = generateIntelligentOverrides(pageName, pageQuery, designSystem);

  const L = [];

  L.push(`# ${pageTitle} Page Overrides`, '');
  L.push(`> **PROJECT:** ${project}`);
  L.push(`> **Generated:** ${ts}`);
  L.push(`> **Page Type:** ${overrides.page_type || 'General'}`, '');
  L.push('> ⚠️ **IMPORTANT:** Rules in this file **override** the Master file (`design-system/MASTER.md`).');
  L.push('> Only deviations from the Master are documented here. For all other rules, refer to the Master.');
  L.push('', '---', '');

  L.push('## Page-Specific Rules', '');

  const section = (title, obj, fallback) => {
    L.push(`### ${title}`, '');
    const entries = Object.entries(obj || {});
    if (entries.length > 0) {
      for (const [k, v] of entries) L.push(`- **${k}:** ${v}`);
    } else {
      L.push(`- ${fallback}`);
    }
    L.push('');
  };

  section('Layout Overrides', overrides.layout, 'No overrides — use Master layout');
  section('Spacing Overrides', overrides.spacing, 'No overrides — use Master spacing');
  section('Typography Overrides', overrides.typography, 'No overrides — use Master typography');
  section('Color Overrides', overrides.colors, 'No overrides — use Master colors');

  L.push('### Component Overrides', '');
  if (overrides.components && overrides.components.length > 0) {
    for (const c of overrides.components) L.push(`- ${c}`);
  } else {
    L.push('- No overrides — use Master component specs');
  }
  L.push('');

  L.push('---', '', '## Page-Specific Components', '');
  if (overrides.unique_components && overrides.unique_components.length > 0) {
    for (const c of overrides.unique_components) L.push(`- ${c}`);
  } else {
    L.push('- No unique components for this page');
  }
  L.push('');

  L.push('---', '', '## Recommendations', '');
  if (overrides.recommendations && overrides.recommendations.length > 0) {
    for (const r of overrides.recommendations) L.push(`- ${r}`);
  }
  L.push('');

  return L.join('\n');
  } catch (err) {
    console.error('Error formatting page override:', err?.message || err);
    return `# Error: could not format page override (${err?.message || err})`;
  }
}

function persistDesignSystem(designSystem, page, outputDir, pageQuery) {
  try {
    if (!designSystem || typeof designSystem !== 'object') {
      return { status: 'error', error: 'Invalid design system object' };
    }
    const baseDir = outputDir || process.cwd();
    const project = designSystem.project_name || 'default';
    const projectSlug = String(project).toLowerCase().replace(/\s+/g, '-');

    const dsDir = path.join(baseDir, 'design-system', projectSlug);
    const pagesDir = path.join(dsDir, 'pages');
    const createdFiles = [];

    fs.mkdirSync(pagesDir, { recursive: true });

    const masterFile = path.join(dsDir, 'MASTER.md');
    fs.writeFileSync(masterFile, formatMasterMd(designSystem), 'utf-8');
    createdFiles.push(masterFile);

    if (page) {
      const pageFile = path.join(pagesDir, `${String(page).toLowerCase().replace(/\s+/g, '-')}.md`);
      fs.writeFileSync(pageFile, formatPageOverrideMd(designSystem, page, pageQuery), 'utf-8');
      createdFiles.push(pageFile);
    }

    return { status: 'success', design_system_dir: dsDir, created_files: createdFiles };
  } catch (err) {
    console.error('Error persisting design system:', err?.message || err);
    return { status: 'error', error: err?.message || String(err) };
  }
}

// ============ MAIN ENTRY POINT ============

function generateDesignSystem(query, projectName, outputFormat = 'ascii', persist = false, page = null, outputDir = null) {
  try {
    const ds = generate(query, projectName);

    if (persist) {
      const persistResult = persistDesignSystem(ds, page, outputDir, query);
      if (persistResult.status === 'error') {
        console.error('Persist warning:', persistResult.error);
      }
    }

    return outputFormat === 'markdown' ? formatMarkdown(ds) : formatAsciiBox(ds);
  } catch (err) {
    console.error('Error in generateDesignSystem:', err?.message || err);
    const fallback = getDefaultDesignSystem(query, projectName);
    return outputFormat === 'markdown' ? formatMarkdown(fallback) : formatAsciiBox(fallback);
  }
}

export { generateDesignSystem, persistDesignSystem };
