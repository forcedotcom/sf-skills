#!/usr/bin/env node
// Summarize applied fixes by severity and rule
// Usage: node summarize-fixes.js <path-to-results.json>

const fs = require("fs");

if (process.argv.length < 3) {
  console.error("Usage: node summarize-fixes.js <results-file.json>");
  process.exit(1);
}

const filePath = process.argv[2];
const data = JSON.parse(fs.readFileSync(filePath, "utf8"));

const fixesByRule = {};
const fixesBySeverity = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };

data.violations.forEach(v => {
  if (v.fixes && v.fixes.length > 0) {
    const fixCount = v.fixes.length;
    fixesByRule[v.rule] = (fixesByRule[v.rule] || 0) + fixCount;
    fixesBySeverity[v.severity] += fixCount;
  }
});

const topRules = Object.entries(fixesByRule)
  .sort((a, b) => b[1] - a[1])
  .slice(0, 10)
  .map(([rule, count]) => ({ rule, count }));

console.log(JSON.stringify({ fixesByRule: topRules, fixesBySeverity }));
console.error("SUCCESS: Summary script completed. Present results to user and offer re-scan (Step 6.7).");
