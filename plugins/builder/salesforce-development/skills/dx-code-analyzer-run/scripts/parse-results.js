#!/usr/bin/env node
// Version: v1.0 | SHA256: 077933925fea8efb4bcfd2c2fd59d4589a0b31ae34d5c1ac68c2080c8af7d74d
// Parse Code Analyzer JSON results and extract summary data
// Usage: node parse-results.js <path-to-results.json>

const fs = require("fs");

if (process.argv.length < 3) {
  console.error("Usage: node parse-results.js <results-file.json>");
  process.exit(1);
}

const filePath = process.argv[2];
const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
const c = data.violationCounts;
const runDir = data.runDir || "";

// Summary counts
const summary = {
  total: c.total, sev1: c.sev1, sev2: c.sev2, sev3: c.sev3, sev4: c.sev4, sev5: c.sev5,
  topViolations: [],
  topRules: [],
  topFiles: []
};

// Top 10 violations sorted by severity
const sorted = data.violations.slice().sort((a, b) => a.severity - b.severity || a.rule.localeCompare(b.rule));
sorted.slice(0, 10).forEach(v => {
  const loc = v.locations && v.locations[0] || {};
  let file = loc.file || "unknown";
  if (runDir && file.startsWith(runDir)) file = file.substring(runDir.length + 1);
  file = file.split("/").pop();
  summary.topViolations.push({ rule: v.rule, engine: v.engine, sev: v.severity, file: file, line: loc.startLine || 0 });
});

// Top 10 rules by frequency
const ruleCounts = {};
const ruleEngines = {};
data.violations.forEach(v => {
  ruleCounts[v.rule] = (ruleCounts[v.rule] || 0) + 1;
  if (!ruleEngines[v.rule]) ruleEngines[v.rule] = v.engine;
});
Object.entries(ruleCounts).sort((a, b) => b[1] - a[1]).slice(0, 10).forEach(([rule, count]) => {
  summary.topRules.push({ rule, engine: ruleEngines[rule], count });
});

// Top 5 files by violation count
const fileCounts = {};
data.violations.forEach(v => {
  const loc = v.locations && v.locations[0] || {};
  let file = loc.file || "unknown";
  if (runDir && file.startsWith(runDir)) file = file.substring(runDir.length + 1);
  fileCounts[file] = (fileCounts[file] || 0) + 1;
});
Object.entries(fileCounts).sort((a, b) => b[1] - a[1]).slice(0, 5).forEach(([file, count]) => {
  summary.topFiles.push({ file, count });
});

console.log(JSON.stringify(summary));
