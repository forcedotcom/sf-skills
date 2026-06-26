#!/usr/bin/env node
// Version: v1.0 | SHA256: placeholder
// List Code Analyzer rules matching a selector and return structured JSON
// Usage: node list-rules.js <selector> [options]
//
// This script runs `sf code-analyzer rules --rule-selector <selector>` and
// parses the table output into structured JSON for presentation.
//
// The CLI table format is:
//   #   Name                   Engine   Severity       Tags
//   1   @lwc/lwc/no-inner-html eslint   2 (High)       Recommended, LWC, Security
//
// Output: JSON with {status, totalRules, rules: [{name, engine, severity, severityNum, tags}], engines, summary}

const { execSync } = require("child_process");

function printUsage() {
  console.error(`Usage: node list-rules.js <selector> [options]

Arguments:
  <selector>           Rule selector (same syntax as --rule-selector)
                       Examples: "Security", "pmd", "eslint:Recommended",
                       "(pmd,eslint):Security:(1,2)", "Apex", "JavaScript"

Options:
  --engine <name>      Filter results to a specific engine after listing
  --severity <n>       Filter results to specific severity (1-5, comma-separated)
  --top <n>            Return at most N rules (default: 100)
  --count-only         Return only counts by engine/severity/category (no rule list)

Valid selector tokens:
  Engines: eslint, regex, retire-js, flow, pmd, cpd, sfge
  Severities: Critical/1, High/2, Moderate/3, Low/4, Info/5
  Categories: Security, Performance, BestPractices, CodeStyle, Design, ErrorProne, Documentation
  Languages: Apex, JavaScript, TypeScript, HTML, CSS, Visualforce, XML
  Tags: Recommended, Custom, All, DevPreview, LWC, Fixable

Examples:
  node list-rules.js "Security"
  node list-rules.js "pmd:Security"
  node list-rules.js "eslint:Recommended"
  node list-rules.js "(pmd,eslint):Security:(1,2)"
  node list-rules.js "Apex"
  node list-rules.js "JavaScript:BestPractices"
  node list-rules.js "Recommended" --count-only
  node list-rules.js "all" --engine pmd --severity 1,2 --top 10`);
  process.exit(1);
}

// Parse CLI arguments
const args = process.argv.slice(2);
if (args.length < 1 || args[0] === "--help" || args[0] === "-h") {
  printUsage();
}

const selector = args[0];
const options = {
  engine: null,
  severity: null,
  top: 100,
  countOnly: false,
};

for (let i = 1; i < args.length; i++) {
  switch (args[i]) {
    case "--engine":
      options.engine = (args[++i] || "").toLowerCase();
      break;
    case "--severity":
      options.severity = (args[++i] || "")
        .split(",")
        .map((s) => parseInt(s.trim(), 10))
        .filter((n) => n >= 1 && n <= 5);
      break;
    case "--top":
      options.top = parseInt(args[++i] || "25", 10);
      break;
    case "--count-only":
      options.countOnly = true;
      break;
    default:
      console.error(`Unknown option: ${args[i]}`);
      printUsage();
  }
}

// Validate selector tokens before running CLI
const validationError = validateSelector(selector);
if (validationError) {
  console.log(JSON.stringify({
    status: "invalid_selector",
    message: validationError,
    hint: "Valid tokens: engines (pmd, eslint, cpd, retire-js, regex, flow, sfge), severities (1-5 or Critical/High/Moderate/Low/Info), categories (Security, Performance, BestPractices, CodeStyle, Design, ErrorProne, Documentation), languages (Apex, JavaScript, TypeScript, HTML, CSS, Visualforce, XML), tags (Recommended, Custom, All, DevPreview, LWC, Fixable)",
  }));
  process.exit(0);
}

// Run `sf code-analyzer rules`
let rawOutput;
try {
  const cmd = `sf code-analyzer rules --rule-selector "${selector}" 2>&1`;
  rawOutput = execSync(cmd, {
    encoding: "utf8",
    timeout: 60000,
    maxBuffer: 2 * 1024 * 1024,
  });
} catch (err) {
  rawOutput = err.stdout || err.stderr || (err.output && err.output.join("")) || "";
  if (!rawOutput) {
    console.log(JSON.stringify({
      status: "error",
      message: `Failed to run sf code-analyzer rules: ${err.message}`,
    }));
    process.exit(0);
  }
}

// Parse the table output
const rules = parseTableOutput(rawOutput);

if (rules.length === 0) {
  console.log(JSON.stringify({
    status: "no_rules_found",
    message: `No rules matched selector "${selector}". Check the selector syntax or try a broader query.`,
    hint: "Use tokens like: Security, pmd, eslint:Recommended, (1,2), Apex",
  }));
  process.exit(0);
}

// Apply post-filters
let filtered = rules;
if (options.engine) {
  filtered = filtered.filter((r) => r.engine.toLowerCase() === options.engine);
}
if (options.severity) {
  filtered = filtered.filter((r) => options.severity.includes(r.severityNum));
}

// Compute summary stats
const engineCounts = {};
const severityCounts = {};
const categoryCounts = {};
filtered.forEach((r) => {
  engineCounts[r.engine] = (engineCounts[r.engine] || 0) + 1;
  const sevKey = `${r.severityNum} (${severityName(r.severityNum)})`;
  severityCounts[sevKey] = (severityCounts[sevKey] || 0) + 1;
  (r.tags || []).forEach((tag) => {
    const t = tag.trim();
    if (["Security", "Performance", "BestPractices", "CodeStyle", "Design", "ErrorProne", "Documentation"].includes(t)) {
      categoryCounts[t] = (categoryCounts[t] || 0) + 1;
    }
  });
});

// Build result
const result = {
  status: "success",
  selector,
  totalRules: filtered.length,
  summary: {
    byEngine: engineCounts,
    bySeverity: severityCounts,
    byCategory: categoryCounts,
  },
};

if (!options.countOnly) {
  result.rules = filtered.slice(0, options.top).map((r) => ({
    name: r.name,
    engine: r.engine,
    severity: r.severity,
    severityNum: r.severityNum,
    tags: r.tags,
  }));
  if (filtered.length > options.top) {
    result.truncated = true;
    result.showing = options.top;
  }
}

console.log(JSON.stringify(result));

// --- Helper Functions ---

function parseTableOutput(output) {
  const rules = [];
  const lines = output.split("\n");

  for (const line of lines) {
    // Match table rows: starts with spaces + number
    // Format: "  1   ruleName   engine   severity   tags"
    const match = line.match(/^\s+(\d+)\s{2,}(\S+)\s{2,}(\S+)\s{2,}(\d+\s*\([^)]+\))\s{2,}(.+)$/);
    if (match) {
      const severityStr = match[4].trim();
      const sevNumMatch = severityStr.match(/^(\d)/);
      rules.push({
        name: match[2].trim(),
        engine: match[3].trim(),
        severity: severityStr,
        severityNum: sevNumMatch ? parseInt(sevNumMatch[1], 10) : 0,
        tags: match[5].trim().split(",").map((t) => t.trim()).filter(Boolean),
      });
    }
  }

  return rules;
}

function validateSelector(selector) {
  if (!selector || !selector.trim()) {
    return "Selector cannot be empty.";
  }

  const VALID_TOKENS = new Set([
    // Engines
    "eslint", "regex", "retire-js", "flow", "pmd", "cpd", "sfge",
    // Severity names
    "critical", "high", "moderate", "low", "info",
    // Severity numbers
    "1", "2", "3", "4", "5",
    // General tags
    "recommended", "custom", "all",
    // Categories
    "bestpractices", "codestyle", "design", "documentation", "errorprone", "security", "performance",
    // Languages
    "apex", "css", "html", "javascript", "typescript", "visualforce", "xml",
    // Engine-specific
    "devpreview", "lwc", "fixable",
  ]);

  // Split by : (AND), then handle () groups (OR)
  const groups = selector.split(":").map((s) => s.trim()).filter(Boolean);
  const invalid = [];

  for (const group of groups) {
    let tokens;
    if (group.startsWith("(") && group.endsWith(")")) {
      // OR group: (token1,token2)
      tokens = group.slice(1, -1).split(",").map((t) => t.trim()).filter(Boolean);
    } else {
      tokens = [group];
    }

    for (const token of tokens) {
      if (!VALID_TOKENS.has(token.toLowerCase())) {
        invalid.push(token);
      }
    }
  }

  if (invalid.length > 0) {
    return `Invalid selector token(s): ${invalid.join(", ")}. Did you misspell a token?`;
  }
  return null;
}

function severityName(num) {
  const names = { 1: "Critical", 2: "High", 3: "Moderate", 4: "Low", 5: "Info" };
  return names[num] || "Unknown";
}
