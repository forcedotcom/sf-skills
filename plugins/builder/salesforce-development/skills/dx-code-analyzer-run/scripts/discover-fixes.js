#!/usr/bin/env node
// Version: v1.0 | SHA256: 19ec035f7132dc162b54a931cfdd882aa473ad80aa21a8a4be1f1127d75168e5
// Discover which violations have engine-provided auto-fixes
// Usage: node discover-fixes.js <path-to-results.json>

const fs = require("fs");

if (process.argv.length < 3) {
  console.error("Usage: node discover-fixes.js <results-file.json>");
  process.exit(1);
}

const filePath = process.argv[2];
const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
const runDir = data.runDir || "";

const fixesByRule = {};
let totalFixable = 0;

data.violations.forEach(v => {
  if (v.fixes && v.fixes.length > 0) {
    totalFixable++;
    const rule = v.rule;
    if (!fixesByRule[rule]) fixesByRule[rule] = { engine: v.engine, count: 0, severity: v.severity };
    fixesByRule[rule].count++;
  }
});

const topRules = Object.entries(fixesByRule)
  .sort((a, b) => b[1].count - a[1].count)
  .slice(0, 10)
  .map(([rule, info]) => ({ rule, ...info }));

console.log(JSON.stringify({ totalFixable, totalViolations: data.violations.length, topRules }));
