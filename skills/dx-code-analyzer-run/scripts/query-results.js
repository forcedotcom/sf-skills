#!/usr/bin/env node
// Version: v1.0 | SHA256: placeholder
// Query and filter Code Analyzer results JSON with rich filtering capabilities
// Usage: node query-results.js <results-file.json> [options]
//
// Options:
//   --engine <name>        Filter by engine (pmd, eslint, cpd, retire-js, etc.)
//   --severity <n>         Filter by severity (1-5, comma-separated for multiple)
//   --category <tag>       Filter by category/tag (Security, Performance, etc.)
//   --rule <name>          Filter by exact rule name (case-insensitive)
//   --file <substring>     Filter by file path substring
//   --top <n>              Return top N results (default: 10)
//   --sort <field>         Sort by: severity, rule, engine, file (default: severity)
//   --sort-dir <dir>       Sort direction: asc, desc (default: asc)
//   --summary              Show only summary counts (no individual violations)

const fs = require("fs");
const path = require("path");

function printUsage() {
  console.error(`Usage: node query-results.js <results-file.json> [options]

Options:
  --engine <name>        Filter by engine (pmd, eslint, cpd, retire-js, etc.)
  --severity <n>         Filter by severity (1-5, comma-separated for multiple: 1,2)
  --category <tag>       Filter by category/tag (Security, Performance, BestPractices, etc.)
  --rule <name>          Filter by exact rule name (case-insensitive)
  --file <substring>     Filter by file path substring (case-insensitive)
  --top <n>              Return top N results (default: 10)
  --sort <field>         Sort by: severity, rule, engine, file (default: severity)
  --sort-dir <dir>       Sort direction: asc, desc (default: asc)
  --summary              Show only summary counts (no individual violations)

Examples:
  node query-results.js results.json --engine pmd --severity 1,2
  node query-results.js results.json --category Security --top 20
  node query-results.js results.json --file AccountService.cls
  node query-results.js results.json --rule ApexCRUDViolation
  node query-results.js results.json --summary`);
  process.exit(1);
}

// Parse CLI arguments
const args = process.argv.slice(2);
if (args.length < 1 || args[0] === "--help" || args[0] === "-h") {
  printUsage();
}

const filePath = args[0];
const options = {
  engine: null,
  severity: null,
  category: null,
  rule: null,
  file: null,
  top: 10,
  sort: "severity",
  sortDir: "asc",
  summary: false,
};

// Parse named options
for (let i = 1; i < args.length; i++) {
  const arg = args[i];
  switch (arg) {
    case "--engine":
      options.engine = (args[++i] || "").toLowerCase();
      break;
    case "--severity":
      options.severity = (args[++i] || "")
        .split(",")
        .map((s) => parseInt(s.trim(), 10))
        .filter((n) => n >= 1 && n <= 5);
      break;
    case "--category":
      options.category = (args[++i] || "").toLowerCase();
      break;
    case "--rule":
      options.rule = (args[++i] || "").toLowerCase();
      break;
    case "--file":
      options.file = (args[++i] || "").toLowerCase();
      break;
    case "--top":
      options.top = parseInt(args[++i] || "10", 10);
      break;
    case "--sort":
      options.sort = args[++i] || "severity";
      break;
    case "--sort-dir":
      options.sortDir = args[++i] || "asc";
      break;
    case "--summary":
      options.summary = true;
      break;
    default:
      console.error(`Unknown option: ${arg}`);
      printUsage();
  }
}

// Read and parse results file
let data;
try {
  data = JSON.parse(fs.readFileSync(filePath, "utf8"));
} catch (err) {
  console.error(`Error reading results file: ${err.message}`);
  process.exit(1);
}

const runDir = data.runDir || "";
const violations = data.violations || [];

// Apply filters
let filtered = violations.filter((v) => {
  if (options.engine && v.engine.toLowerCase() !== options.engine) return false;
  if (options.severity && !options.severity.includes(v.severity)) return false;
  if (options.category) {
    const tags = (v.tags || []).map((t) => t.toLowerCase());
    if (!tags.includes(options.category)) return false;
  }
  if (options.rule && v.rule.toLowerCase() !== options.rule) return false;
  if (options.file) {
    const loc = v.locations && v.locations[v.primaryLocationIndex || 0];
    const fileLower = ((loc && loc.file) || "").toLowerCase();
    if (!fileLower.includes(options.file)) return false;
  }
  return true;
});

// Sort
const sortMul = options.sortDir === "desc" ? -1 : 1;
filtered.sort((a, b) => {
  let cmp = 0;
  switch (options.sort) {
    case "severity":
      cmp = a.severity - b.severity;
      break;
    case "rule":
      cmp = a.rule.localeCompare(b.rule);
      break;
    case "engine":
      cmp = a.engine.localeCompare(b.engine);
      break;
    case "file": {
      const aLoc = a.locations && a.locations[a.primaryLocationIndex || 0];
      const bLoc = b.locations && b.locations[b.primaryLocationIndex || 0];
      const aFile = (aLoc && aLoc.file) || "";
      const bFile = (bLoc && bLoc.file) || "";
      cmp = aFile.localeCompare(bFile);
      break;
    }
  }
  if (cmp !== 0) return cmp * sortMul;
  // Secondary sort: severity ascending
  return (a.severity - b.severity) * sortMul;
});

// Build output
const totalMatches = filtered.length;
const limited = filtered.slice(0, options.top);

// Compute severity breakdown of matches
const sevCounts = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
filtered.forEach((v) => {
  if (sevCounts[v.severity] !== undefined) sevCounts[v.severity]++;
});

// Compute rule frequency for matches
const ruleCounts = {};
const ruleEngines = {};
filtered.forEach((v) => {
  ruleCounts[v.rule] = (ruleCounts[v.rule] || 0) + 1;
  if (!ruleEngines[v.rule]) ruleEngines[v.rule] = v.engine;
});
const topRules = Object.entries(ruleCounts)
  .sort((a, b) => b[1] - a[1])
  .slice(0, options.top)
  .map(([rule, count]) => ({ rule, engine: ruleEngines[rule], count }));

// Compute file frequency for matches
const fileCounts = {};
filtered.forEach((v) => {
  const loc = v.locations && v.locations[v.primaryLocationIndex || 0];
  let file = (loc && loc.file) || "unknown";
  if (runDir && file.startsWith(runDir)) file = file.substring(runDir.length + 1);
  fileCounts[file] = (fileCounts[file] || 0) + 1;
});
const topFiles = Object.entries(fileCounts)
  .sort((a, b) => b[1] - a[1])
  .slice(0, options.top)
  .map(([file, count]) => ({ file, count }));

// Build result object
const result = {
  query: {
    engine: options.engine,
    severity: options.severity,
    category: options.category,
    rule: options.rule,
    file: options.file,
    top: options.top,
    sort: options.sort,
    sortDir: options.sortDir,
  },
  totalViolations: violations.length,
  totalMatches,
  severityCounts: sevCounts,
  topRules,
  topFiles,
};

if (!options.summary) {
  result.violations = limited.map((v) => {
    const loc = v.locations && v.locations[v.primaryLocationIndex || 0];
    let file = (loc && loc.file) || "unknown";
    if (runDir && file.startsWith(runDir)) file = file.substring(runDir.length + 1);
    return {
      rule: v.rule,
      engine: v.engine,
      severity: v.severity,
      message: v.message,
      file: file,
      startLine: (loc && loc.startLine) || 0,
      tags: v.tags || [],
    };
  });
}

console.log(JSON.stringify(result));
