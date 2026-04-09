#!/usr/bin/env node

/**
 * SLDS Quality Analyzer
 *
 * Analyzes CSS and HTML files for SLDS quality issues beyond what the linter catches.
 *
 * Usage: node analyze-quality.cjs <component-path> [--hooks-index <path>]
 *
 * Output: JSON with findings categorized by severity
 */

const fs = require('fs');
const path = require('path');

function resolveHooksIndexPath(args) {
  const idx = args.indexOf('--hooks-index');
  if (idx !== -1 && idx + 1 < args.length) {
    return path.resolve(args[idx + 1]);
  }
  return null;
}

let HOOKS_INDEX_PATH = null;

// Severity levels
const CRITICAL = 'critical';
const WARNING = 'warning';
const INFO = 'info';

// Detection patterns
// NOTE: Checks that the SLDS linter already handles are excluded here to avoid
// double-counting. The linter covers: slds/class-override (L001),
// slds/lwc-token-to-slds-hook (L002), slds/no-hardcoded-values (L003).
// This script focuses on what the linter does NOT catch.
const PATTERNS = {
  // CSS patterns (linter-complementary only)
  css: {
    missingFallback: {
      pattern: /var\(--slds-g-[^,)]+\)/g,
      severity: CRITICAL,
      id: 'T002',
      message: 'SLDS hook without fallback value',
      recommendation: 'Add fallback: var(--slds-g-color-surface-1, #fff)'
    },
    important: {
      pattern: /!important/g,
      severity: WARNING,
      id: 'Q001',
      message: '!important declaration found',
      recommendation: 'Remove !important, use proper specificity'
    },
    magicPixels: {
      pattern: /\b(?:margin(?:-[a-z-]+)?|padding(?:-[a-z-]+)?|gap|row-gap|column-gap)\s*:\s*(\d+)px\b(?![^;]*var\()/g,
      severity: WARNING,
      id: 'T021',
      message: 'Magic pixel value not using spacing hook',
      recommendation: 'Use var(--slds-g-spacing-*) or utility class'
    },
    highZindex: {
      pattern: /z-index\s*:\s*(\d{3,})/g,
      severity: WARNING,
      id: 'Q021',
      message: 'High z-index value',
      recommendation: 'Use defined z-index scale'
    },
    outlineNone: {
      pattern: /outline\s*:\s*none/g,
      severity: WARNING,
      id: 'A021',
      message: 'Focus outline removed without alternative',
      recommendation: 'Provide alternative focus indicator'
    }
  },
  // JS patterns (inline styles and dynamic class manipulation)
  js: {
    inlineStyleJS: {
      pattern: /\.style\.\w+\s*=/g,
      severity: WARNING,
      id: 'Q025',
      message: 'Inline style manipulation in JavaScript',
      recommendation: 'Use CSS classes instead of direct style property assignment'
    },
    classListManipulation: {
      pattern: /\.classList\.(add|remove|toggle)\(\s*['"]slds-/g,
      severity: WARNING,
      id: 'Q012',
      message: 'Dynamic SLDS class manipulation in JavaScript',
      recommendation: 'Prefer declarative class bindings; avoid manipulating slds-* classes directly'
    }
  },
  // HTML patterns
  html: {
    inlineStyle: {
      pattern: /style\s*=\s*["'][^"']+["']/gi,
      severity: WARNING,
      id: 'Q002',
      message: 'Inline style attribute',
      recommendation: 'Move styles to CSS file'
    },
    lightningInputNoLabel: {
      pattern: /<lightning-input(?![^>]*\blabel\b)[^>]*>/gi,
      severity: CRITICAL,
      id: 'A001',
      message: 'Lightning input without label attribute',
      recommendation: 'Add label attribute to lightning-input'
    },
    iconNoAlt: {
      pattern: /<lightning-icon(?![^>]*alternative-text)[^>]*>/gi,
      severity: CRITICAL,
      id: 'A004',
      message: 'Icon without alternative-text',
      recommendation: 'Add alternative-text (or empty string for decorative)'
    },
    imgNoAlt: {
      pattern: /<img(?![^>]*\balt\b)[^>]*>/gi,
      severity: CRITICAL,
      id: 'A005',
      message: 'Image without alt attribute',
      recommendation: 'Add alt attribute'
    },
    positiveTabindex: {
      pattern: /tabindex\s*=\s*["']([1-9]\d*)["']/gi,
      severity: WARNING,
      id: 'A020',
      message: 'Positive tabindex value',
      recommendation: 'Use tabindex="0" or "-1" only'
    },
    clickableDiv: {
      pattern: /<div[^>]*onclick[^>]*>/gi,
      severity: WARNING,
      id: 'A022',
      message: 'Div with click handler instead of button',
      recommendation: 'Use <button> or <lightning-button> for interactive elements'
    },
    nativeInput: {
      pattern: /<input\s/gi,
      severity: WARNING,
      id: 'C001',
      message: 'Native input element',
      recommendation: 'Consider <lightning-input> for built-in labeling and validation'
    },
    nativeButton: {
      pattern: /<button\s(?![^>]*class\s*=\s*["'][^"']*slds-button)/gi,
      severity: WARNING,
      id: 'C002',
      message: 'Native button element',
      recommendation: 'Consider <lightning-button> for SLDS styling consistency (suppressed if slds-button class present)'
    },
    nativeSelect: {
      pattern: /<select\s/gi,
      severity: WARNING,
      id: 'C004',
      message: 'Native select element',
      recommendation: 'Consider <lightning-combobox> for consistency'
    }
  }
};

/**
 * Find all files with given extensions in directory
 */
function findFiles(dir, extensions) {
  const files = [];

  function walk(currentDir) {
    try {
      const items = fs.readdirSync(currentDir);
      for (const item of items) {
        const fullPath = path.join(currentDir, item);
        const stat = fs.statSync(fullPath);

        if (stat.isDirectory() && !item.startsWith('.') && item !== 'node_modules') {
          walk(fullPath);
        } else if (stat.isFile()) {
          const ext = path.extname(item).toLowerCase();
          if (extensions.includes(ext)) {
            files.push(fullPath);
          }
        }
      }
    } catch (err) {
      // Skip directories we can't read
    }
  }

  walk(dir);
  return files;
}

/**
 * Analyze a single file
 */
function analyzeFile(filePath, patterns) {
  const findings = [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');

  for (const [name, config] of Object.entries(patterns)) {
    const regex = new RegExp(config.pattern.source, config.pattern.flags);
    let match;

    while ((match = regex.exec(content)) !== null) {
      // Find line number
      const beforeMatch = content.substring(0, match.index);
      const lineNumber = beforeMatch.split('\n').length;
      const lineContent = lines[lineNumber - 1] || '';

      findings.push({
        id: config.id,
        severity: config.severity,
        file: filePath,
        line: lineNumber,
        column: match.index - beforeMatch.lastIndexOf('\n'),
        match: match[0].substring(0, 50),
        message: config.message,
        recommendation: config.recommendation,
        context: lineContent.trim().substring(0, 80)
      });
    }
  }

  return findings;
}

/**
 * Analyze heading hierarchy in HTML
 */
function analyzeHeadings(filePath) {
  const findings = [];
  const content = fs.readFileSync(filePath, 'utf-8');
  const headingRegex = /<h([1-6])[^>]*>/gi;
  const headings = [];
  let match;

  while ((match = headingRegex.exec(content)) !== null) {
    headings.push({
      level: parseInt(match[1]),
      index: match.index
    });
  }

  // Check for skipped levels
  for (let i = 1; i < headings.length; i++) {
    const prev = headings[i - 1].level;
    const curr = headings[i].level;

    if (curr > prev + 1) {
      const beforeMatch = content.substring(0, headings[i].index);
      const lineNumber = beforeMatch.split('\n').length;

      findings.push({
        id: 'A010',
        severity: WARNING,
        file: filePath,
        line: lineNumber,
        message: `Skipped heading level: h${prev} to h${curr}`,
        recommendation: `Use h${prev + 1} instead of h${curr}`
      });
    }
  }

  return findings;
}

/**
 * Load valid hook tokens from hooks-index.json
 */
let _validHooks = null;
function loadValidHooks() {
  if (_validHooks) return _validHooks;
  if (!HOOKS_INDEX_PATH) return null;
  try {
    const data = JSON.parse(fs.readFileSync(HOOKS_INDEX_PATH, 'utf-8'));
    _validHooks = new Set(data.hooks.map(h => h.token));
  } catch {
    console.error(`WARNING: Could not load hooks-index.json at ${HOOKS_INDEX_PATH}`);
    console.error('Invented-hook detection (T051) will be skipped.');
    _validHooks = null;
  }
  return _validHooks;
}

/**
 * Check for invented hooks (T051) — hooks referenced in CSS that don't exist in metadata
 */
function analyzeInventedHooks(filePath) {
  const findings = [];
  const validHooks = loadValidHooks();
  if (!validHooks) return findings; // skip if metadata unavailable

  const content = fs.readFileSync(filePath, 'utf-8');
  const lines = content.split('\n');
  const hookRef = /var\((--slds-g-[^,)]+)/g;
  let match;

  while ((match = hookRef.exec(content)) !== null) {
    const hookName = match[1].trim();
    if (!validHooks.has(hookName)) {
      const beforeMatch = content.substring(0, match.index);
      const lineNumber = beforeMatch.split('\n').length;
      const lineContent = lines[lineNumber - 1] || '';

      findings.push({
        id: 'T051',
        severity: CRITICAL,
        file: filePath,
        line: lineNumber,
        match: hookName,
        message: `Invented hook — "${hookName}" does not exist in hooks-index.json`,
        recommendation: 'Verify the hook exists via: node scripts/search-hooks.cjs --prefix "' + hookName + '"',
        context: lineContent.trim().substring(0, 80)
      });
    }
  }

  return findings;
}

/**
 * Check for hook pairing issues
 */
function analyzeHookPairing(filePath) {
  const findings = [];
  const content = fs.readFileSync(filePath, 'utf-8');

  // Find all background hooks
  const bgHookRegex = /--slds-g-color-(surface|accent|success|warning|error|info)(?:-container)?-\d/g;
  const textHookRegex = /--slds-g-color-on-(surface|accent|success|warning|error|info)(?:-container)?-\d/g;

  const bgHooks = content.match(bgHookRegex) || [];
  const textHooks = content.match(textHookRegex) || [];

  // Extract families
  const bgFamilies = new Set(bgHooks.map(h => {
    const match = h.match(/--slds-g-color-(\w+(?:-container)?)-\d/);
    return match ? match[1] : null;
  }).filter(Boolean));

  const textFamilies = new Set(textHooks.map(h => {
    const match = h.match(/--slds-g-color-on-(\w+(?:-container)?)-\d/);
    return match ? match[1] : null;
  }).filter(Boolean));

  // Check for mismatches
  for (const bgFamily of bgFamilies) {
    const expectedTextFamily = bgFamily.replace('-container', '');
    if (!textFamilies.has(expectedTextFamily) && !textFamilies.has(bgFamily)) {
      findings.push({
        id: 'T010',
        severity: WARNING,
        file: filePath,
        message: `Background hook family '${bgFamily}' may lack matching text hook`,
        recommendation: `Pair with --slds-g-color-on-${expectedTextFamily}-*`
      });
    }
  }

  return findings;
}

/**
 * Calculate scores from findings
 */
function calculateScores(findings) {
  const weights = {
    [CRITICAL]: 10,
    [WARNING]: 3,
    [INFO]: 1
  };

  // NOTE: Linter findings (L001, L002, L003) come from the SLDS linter output,
  // not from this script. They should be merged in by the calling agent.
  // This script only produces findings for the other categories.
  const categories = {
    theming: { issues: 0, ids: ['T002', 'T010', 'T011', 'T021', 'T051'] },
    accessibility: { issues: 0, ids: ['A001', 'A004', 'A005', 'A010', 'A020', 'A021', 'A022'] },
    codeQuality: { issues: 0, ids: ['Q001', 'Q002', 'Q012', 'Q021', 'Q025'] },
    componentUsage: { issues: 0, ids: ['C001', 'C002', 'C004'] }
  };

  // Count weighted issues per category
  for (const finding of findings) {
    const weight = weights[finding.severity];
    for (const [category, config] of Object.entries(categories)) {
      if (config.ids.includes(finding.id)) {
        config.issues += weight;
        break;
      }
    }
  }

  // Calculate scores
  const scores = {};
  for (const [category, config] of Object.entries(categories)) {
    scores[category] = Math.max(0, 100 - config.issues);
  }

  return scores;
}

/**
 * Get grade from score
 */
function getGrade(score) {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 70) return 'C';
  if (score >= 60) return 'D';
  return 'F';
}

/**
 * Main analysis function
 */
function analyze(componentPath) {
  const resolvedPath = path.resolve(componentPath);

  if (!fs.existsSync(resolvedPath)) {
    console.error(`Error: Path does not exist: ${resolvedPath}`);
    process.exit(1);
  }

  const findings = [];

  // Find and analyze CSS files
  const cssFiles = findFiles(resolvedPath, ['.css']);
  for (const file of cssFiles) {
    findings.push(...analyzeFile(file, PATTERNS.css));
    findings.push(...analyzeHookPairing(file));
    findings.push(...analyzeInventedHooks(file));
  }

  // Find and analyze HTML files
  const htmlFiles = findFiles(resolvedPath, ['.html']);
  for (const file of htmlFiles) {
    findings.push(...analyzeFile(file, PATTERNS.html));
    findings.push(...analyzeHeadings(file));
  }

  // Find and analyze JS files
  const jsFiles = findFiles(resolvedPath, ['.js']);
  for (const file of jsFiles) {
    findings.push(...analyzeFile(file, PATTERNS.js));
  }

  // Calculate scores
  const scores = calculateScores(findings);

  // Organize findings by severity
  const organized = {
    critical: findings.filter(f => f.severity === CRITICAL),
    warning: findings.filter(f => f.severity === WARNING),
    info: findings.filter(f => f.severity === INFO)
  };

  // Calculate total lines for complexity classification
  let totalLines = 0;
  for (const file of [...cssFiles, ...htmlFiles, ...jsFiles]) {
    totalLines += fs.readFileSync(file, 'utf-8').split('\n').length;
  }
  const totalFiles = cssFiles.length + htmlFiles.length + jsFiles.length;
  let complexity = 'small';
  if (totalFiles >= 7 || totalLines >= 500) complexity = 'large';
  else if (totalFiles >= 3 || totalLines >= 100) complexity = 'medium';

  // Build result
  const result = {
    component: path.basename(resolvedPath),
    path: resolvedPath,
    timestamp: new Date().toISOString(),
    complexity: {
      classification: complexity,
      totalFiles,
      totalLines
    },
    note: "These are automated category scores only. Combine them with SLDS linter results and the required Step 3 manual review gate in SKILL.md before making a final ship recommendation.",
    scores: {
      theming: { score: scores.theming, grade: getGrade(scores.theming) },
      accessibility: { score: scores.accessibility, grade: getGrade(scores.accessibility) },
      codeQuality: { score: scores.codeQuality, grade: getGrade(scores.codeQuality) },
      componentUsage: { score: scores.componentUsage, grade: getGrade(scores.componentUsage) }
    },
    findings: organized,
    summary: {
      filesAnalyzed: totalFiles,
      cssFiles: cssFiles.length,
      htmlFiles: htmlFiles.length,
      jsFiles: jsFiles.length,
      totalLines,
      critical: organized.critical.length,
      warnings: organized.warning.length,
      info: organized.info.length
    }
  };

  return result;
}

// CLI entry point
if (require.main === module) {
  const args = process.argv.slice(2);
  const positionalArgs = args.filter((a, i) => !a.startsWith('--') && (i === 0 || !args[i - 1].startsWith('--')));

  if (positionalArgs.length === 0) {
    console.log('SLDS Quality Analyzer');
    console.log('Usage: node analyze-quality.cjs <component-path> [--hooks-index <path>]');
    console.log('');
    console.log('Options:');
    console.log('  --hooks-index <path>  Path to hooks-index.json (optional; enables T051 invented-hook detection)');
    console.log('');
    console.log('Output: JSON analysis of SLDS quality issues');
    process.exit(0);
  }

  HOOKS_INDEX_PATH = resolveHooksIndexPath(args);
  const result = analyze(positionalArgs[0]);
  console.log(JSON.stringify(result, null, 2));
}

module.exports = { analyze, PATTERNS };
