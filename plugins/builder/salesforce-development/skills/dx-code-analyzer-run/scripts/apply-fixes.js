#!/usr/bin/env node
// Apply engine-provided auto-fixes to source files
// Usage: node apply-fixes.js <path-to-results.json>
// WARNING: This modifies files in place. Ensure you have backups or are using version control.

const fs = require("fs");
const path = require("path");

if (process.argv.length < 3) {
  console.error("Usage: node apply-fixes.js <results-file.json>");
  process.exit(1);
}

const filePath = process.argv[2];
const data = JSON.parse(fs.readFileSync(filePath, "utf8"));
const runDir = data.runDir || "";

// Group fixes by file
const fileFixesMap = new Map();
data.violations.forEach(v => {
  if (v.fixes && v.fixes.length > 0) {
    v.fixes.forEach(fix => {
      const loc = fix.location;
      let filePath = loc.file;
      if (runDir && filePath.startsWith(runDir)) filePath = filePath.substring(runDir.length + 1);

      if (!fileFixesMap.has(filePath)) fileFixesMap.set(filePath, []);
      fileFixesMap.get(filePath).push({
        startLine: loc.startLine,
        startColumn: loc.startColumn,
        endLine: loc.endLine,
        endColumn: loc.endColumn,
        fixedCode: fix.fixedCode,
        rule: v.rule
      });
    });
  }
});

// Sort fixes by line/column (descending) to apply bottom-up
// This ensures earlier fixes don't shift line numbers for later ones
fileFixesMap.forEach((fixes, file) => {
  fixes.sort((a, b) => {
    if (b.startLine !== a.startLine) return b.startLine - a.startLine;
    return b.startColumn - a.startColumn;
  });
});

// Apply fixes to each file
let filesModified = 0;
let fixesApplied = 0;
let fixesSkipped = 0;

fileFixesMap.forEach((fixes, filePath) => {
  try {
    const content = fs.readFileSync(filePath, "utf8");
    const lines = content.split("\n");

    fixes.forEach(fix => {
      const startIdx = fix.startLine - 1;
      const endIdx = fix.endLine - 1;
      if (startIdx < 0 || endIdx >= lines.length || startIdx > endIdx) {
        fixesSkipped++;
        return;
      }

      // Handle multi-line replacements: splice out old lines, insert new content
      const firstLine = lines[startIdx];
      const lastLine = lines[endIdx];
      const before = firstLine.substring(0, fix.startColumn - 1);
      const after = lastLine.substring(fix.endColumn - 1);
      const replacement = before + fix.fixedCode + after;

      // Remove the spanned lines and insert the replacement
      lines.splice(startIdx, endIdx - startIdx + 1, replacement);
      fixesApplied++;
    });

    fs.writeFileSync(filePath, lines.join("\n"), "utf8");
    filesModified++;
  } catch (err) {
    console.error("Error fixing " + filePath + ": " + err.message);
  }
});

console.log(JSON.stringify({ success: true, filesModified, fixesApplied, fixesSkipped, totalFixableFiles: fileFixesMap.size }));
