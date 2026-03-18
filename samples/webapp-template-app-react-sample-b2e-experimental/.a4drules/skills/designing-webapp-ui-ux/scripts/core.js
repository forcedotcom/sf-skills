#!/usr/bin/env node

import fs from 'fs';
import path from 'path';

const DATA_DIR = path.join(import.meta.dirname, '..', 'data');
const MAX_RESULTS = 3;

const CSV_CONFIG = {
  style: {
    file: 'styles.csv',
    searchCols: ['Style Category', 'Keywords', 'Best For', 'Type', 'AI Prompt Keywords'],
    outputCols: ['Style Category', 'Type', 'Keywords', 'Primary Colors', 'Effects & Animation', 'Best For', 'Performance', 'Accessibility', 'Framework Compatibility', 'Complexity', 'AI Prompt Keywords', 'CSS/Technical Keywords', 'Implementation Checklist', 'Design System Variables']
  },
  color: {
    file: 'colors.csv',
    searchCols: ['Product Type', 'Notes'],
    outputCols: ['Product Type', 'Primary (Hex)', 'Secondary (Hex)', 'CTA (Hex)', 'Background (Hex)', 'Text (Hex)', 'Notes']
  },
  chart: {
    file: 'charts.csv',
    searchCols: ['Data Type', 'Keywords', 'Best Chart Type', 'Accessibility Notes'],
    outputCols: ['Data Type', 'Keywords', 'Best Chart Type', 'Secondary Options', 'Color Guidance', 'Accessibility Notes', 'Library Recommendation', 'Interactive Level']
  },
  landing: {
    file: 'landing.csv',
    searchCols: ['Pattern Name', 'Keywords', 'Conversion Optimization', 'Section Order'],
    outputCols: ['Pattern Name', 'Keywords', 'Section Order', 'Primary CTA Placement', 'Color Strategy', 'Conversion Optimization']
  },
  product: {
    file: 'products.csv',
    searchCols: ['Product Type', 'Keywords', 'Primary Style Recommendation', 'Key Considerations'],
    outputCols: ['Product Type', 'Keywords', 'Primary Style Recommendation', 'Secondary Styles', 'Landing Page Pattern', 'Dashboard Style (if applicable)', 'Color Palette Focus']
  },
  ux: {
    file: 'ux-guidelines.csv',
    searchCols: ['Category', 'Issue', 'Description', 'Platform'],
    outputCols: ['Category', 'Issue', 'Platform', 'Description', 'Do', "Don't", 'Code Example Good', 'Code Example Bad', 'Severity']
  },
  typography: {
    file: 'typography.csv',
    searchCols: ['Font Pairing Name', 'Category', 'Mood/Style Keywords', 'Best For', 'Heading Font', 'Body Font'],
    outputCols: ['Font Pairing Name', 'Category', 'Heading Font', 'Body Font', 'Mood/Style Keywords', 'Best For', 'Google Fonts URL', 'CSS Import', 'Tailwind Config', 'Notes']
  },
  icons: {
    file: 'icons.csv',
    searchCols: ['Category', 'Icon Name', 'Keywords', 'Best For'],
    outputCols: ['Category', 'Icon Name', 'Keywords', 'Library', 'Import Code', 'Usage', 'Best For', 'Style']
  },
  react: {
    file: 'react-performance.csv',
    searchCols: ['Category', 'Issue', 'Keywords', 'Description'],
    outputCols: ['Category', 'Issue', 'Platform', 'Description', 'Do', "Don't", 'Code Example Good', 'Code Example Bad', 'Severity']
  },
  web: {
    file: 'web-interface.csv',
    searchCols: ['Category', 'Issue', 'Keywords', 'Description'],
    outputCols: ['Category', 'Issue', 'Platform', 'Description', 'Do', "Don't", 'Code Example Good', 'Code Example Bad', 'Severity']
  }
};

const STACK_CONFIG = {
  'html-tailwind': { file: 'stacks/html-tailwind.csv' },
  react: { file: 'stacks/react.csv' },
  shadcn: { file: 'stacks/shadcn.csv' }
};

const STACK_COLS = {
  searchCols: ['Category', 'Guideline', 'Description', 'Do', "Don't"],
  outputCols: ['Category', 'Guideline', 'Description', 'Do', "Don't", 'Code Good', 'Code Bad', 'Severity', 'Docs URL']
};

const AVAILABLE_STACKS = Object.keys(STACK_CONFIG);

// ============ CSV PARSER ============

function parseCsvLine(line) {
  const fields = [];
  let current = '';
  let inQuotes = false;
  for (let i = 0; i < line.length; i++) {
    const ch = line[i];
    if (ch === '"') {
      if (inQuotes && i + 1 < line.length && line[i + 1] === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (ch === ',' && !inQuotes) {
      fields.push(current);
      current = '';
    } else {
      current += ch;
    }
  }
  fields.push(current);
  return fields;
}

function loadCsv(filepath) {
  if (!fs.existsSync(filepath)) return [];
  const content = fs.readFileSync(filepath, 'utf-8');
  const lines = content.split('\n').filter(l => l.trim());
  if (lines.length === 0) return [];
  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map(line => {
    const values = parseCsvLine(line);
    const row = {};
    headers.forEach((h, i) => { row[h] = values[i] || ''; });
    return row;
  });
}

// ============ BM25 ============

class BM25 {
  constructor(k1 = 1.5, b = 0.75) {
    this.k1 = k1;
    this.b = b;
    this.corpus = [];
    this.docLengths = [];
    this.avgdl = 0;
    this.idf = {};
    this.docFreqs = {};
    this.N = 0;
  }

  tokenize(text) {
    return String(text).toLowerCase().replace(/[^\w\s]/g, ' ').split(/\s+/).filter(w => w.length > 2);
  }

  fit(documents) {
    this.corpus = documents.map(d => this.tokenize(d));
    this.N = this.corpus.length;
    if (this.N === 0) return;
    this.docLengths = this.corpus.map(d => d.length);
    this.avgdl = this.docLengths.reduce((a, b) => a + b, 0) / this.N;

    for (const doc of this.corpus) {
      const seen = new Set();
      for (const word of doc) {
        if (!seen.has(word)) {
          this.docFreqs[word] = (this.docFreqs[word] || 0) + 1;
          seen.add(word);
        }
      }
    }

    for (const [word, freq] of Object.entries(this.docFreqs)) {
      this.idf[word] = Math.log((this.N - freq + 0.5) / (freq + 0.5) + 1);
    }
  }

  score(query) {
    const tokens = this.tokenize(query);
    const scores = [];

    for (let idx = 0; idx < this.corpus.length; idx++) {
      const doc = this.corpus[idx];
      const docLen = this.docLengths[idx];
      const tf = {};
      for (const w of doc) tf[w] = (tf[w] || 0) + 1;

      let s = 0;
      for (const t of tokens) {
        if (this.idf[t] !== undefined) {
          const freq = tf[t] || 0;
          s += this.idf[t] * (freq * (this.k1 + 1)) / (freq + this.k1 * (1 - this.b + this.b * docLen / this.avgdl));
        }
      }
      scores.push([idx, s]);
    }

    return scores.sort((a, b) => b[1] - a[1]);
  }
}

// ============ SEARCH FUNCTIONS ============

function searchCsv(filepath, searchCols, outputCols, query, maxResults) {
  const data = loadCsv(filepath);
  if (data.length === 0) return [];

  const documents = data.map(row => searchCols.map(col => String(row[col] || '')).join(' '));
  const bm25 = new BM25();
  bm25.fit(documents);
  const ranked = bm25.score(query);

  const results = [];
  for (const [idx, score] of ranked.slice(0, maxResults)) {
    if (score > 0) {
      const row = data[idx];
      const entry = {};
      for (const col of outputCols) {
        if (row[col] !== undefined) entry[col] = row[col];
      }
      results.push(entry);
    }
  }
  return results;
}

function detectDomain(query) {
  const q = query.toLowerCase();
  const map = {
    color: ['color', 'palette', 'hex', '#', 'rgb'],
    chart: ['chart', 'graph', 'visualization', 'trend', 'bar', 'pie', 'scatter', 'heatmap', 'funnel'],
    landing: ['landing', 'page', 'cta', 'conversion', 'hero', 'testimonial', 'pricing', 'section'],
    product: ['saas', 'ecommerce', 'e-commerce', 'fintech', 'healthcare', 'gaming', 'portfolio', 'crypto', 'dashboard'],
    style: ['style', 'design', 'ui', 'minimalism', 'glassmorphism', 'neumorphism', 'brutalism', 'dark mode', 'flat', 'aurora', 'prompt', 'css', 'implementation', 'variable', 'checklist', 'tailwind'],
    ux: ['ux', 'usability', 'accessibility', 'wcag', 'touch', 'scroll', 'animation', 'keyboard', 'navigation', 'mobile'],
    typography: ['font', 'typography', 'heading', 'serif', 'sans'],
    icons: ['icon', 'icons', 'lucide', 'heroicons', 'symbol', 'glyph', 'pictogram', 'svg icon'],
    react: ['react', 'suspense', 'memo', 'usecallback', 'useeffect', 'rerender', 'bundle', 'waterfall', 'barrel', 'dynamic import', 'rsc', 'server component'],
    web: ['aria', 'focus', 'outline', 'semantic', 'virtualize', 'autocomplete', 'form', 'input type', 'preconnect']
  };

  let best = 'style';
  let bestScore = 0;
  for (const [domain, keywords] of Object.entries(map)) {
    const score = keywords.filter(kw => q.includes(kw)).length;
    if (score > bestScore) { best = domain; bestScore = score; }
  }
  return bestScore > 0 ? best : 'style';
}

function search(query, domain, maxResults = MAX_RESULTS) {
  if (!domain) domain = detectDomain(query);
  const config = CSV_CONFIG[domain] || CSV_CONFIG.style;
  const filepath = path.join(DATA_DIR, config.file);

  if (!fs.existsSync(filepath)) {
    return { error: `File not found: ${filepath}`, domain };
  }

  const results = searchCsv(filepath, config.searchCols, config.outputCols, query, maxResults);
  return { domain, query, file: config.file, count: results.length, results };
}

function searchStack(query, stack, maxResults = MAX_RESULTS) {
  if (!STACK_CONFIG[stack]) {
    return { error: `Unknown stack: ${stack}. Available: ${AVAILABLE_STACKS.join(', ')}` };
  }

  const filepath = path.join(DATA_DIR, STACK_CONFIG[stack].file);
  if (!fs.existsSync(filepath)) {
    return { error: `Stack file not found: ${filepath}`, stack };
  }

  const results = searchCsv(filepath, STACK_COLS.searchCols, STACK_COLS.outputCols, query, maxResults);
  return { domain: 'stack', stack, query, file: STACK_CONFIG[stack].file, count: results.length, results };
}

export { CSV_CONFIG, STACK_CONFIG, AVAILABLE_STACKS, MAX_RESULTS, DATA_DIR, loadCsv, parseCsvLine, search, searchStack };
