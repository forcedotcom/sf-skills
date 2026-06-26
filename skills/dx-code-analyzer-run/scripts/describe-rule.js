#!/usr/bin/env node
// Version: v1.1 | SHA256: placeholder
// Get detailed description and documentation for a Code Analyzer rule
// Usage: node describe-rule.js <rule-name> [--engine <engine>]
//
// This script runs `sf code-analyzer rules --view detail` with a targeted
// selector and parses the output to extract rule details including description,
// severity, tags, and documentation resources.
//
// The CLI output format is:
//   === 1. RuleName
//       severity:    2 (High)
//       engine:      pmd
//       tags:        Recommended, Security, Apex
//       resource:    https://...
//       description: Some description text

const { execSync } = require("child_process");

function printUsage() {
  console.error(`Usage: node describe-rule.js <rule-name> [--engine <engine>]

Arguments:
  <rule-name>          The rule name to look up (case-insensitive partial match)

Options:
  --engine <engine>    Narrow lookup to a specific engine (pmd, eslint, cpd, etc.)

Examples:
  node describe-rule.js ApexCRUDViolation
  node describe-rule.js ApexCRUDViolation --engine pmd
  node describe-rule.js no-var --engine eslint
  node describe-rule.js OperationWithLimitsInLoop`);
  process.exit(1);
}

// Parse CLI arguments
const args = process.argv.slice(2);
if (args.length < 1 || args[0] === "--help" || args[0] === "-h") {
  printUsage();
}

const ruleName = args[0];
let engine = null;

for (let i = 1; i < args.length; i++) {
  if (args[i] === "--engine" && args[i + 1]) {
    engine = args[++i].toLowerCase();
  }
}

// Build the rule selector for the lookup
const selector = engine ? `${engine}:${ruleName}` : ruleName;

// Run `sf code-analyzer rules` with --view detail to get full rule info
let rawOutput;
try {
  const cmd = `sf code-analyzer rules --rule-selector "${selector}" --view detail 2>&1`;
  rawOutput = execSync(cmd, {
    encoding: "utf8",
    timeout: 60000,
    maxBuffer: 2 * 1024 * 1024,
  });
} catch (err) {
  // execSync throws on non-zero exit, but we still want the output
  rawOutput = err.stdout || err.stderr || (err.output && err.output.join("")) || "";
  if (!rawOutput) {
    console.log(JSON.stringify({
      status: "error",
      message: `Failed to run sf code-analyzer rules: ${err.message}`,
    }));
    process.exit(0);
  }
}

// Parse the detail view output
// Format: === N. RuleName\n    key: value\n    key: value\n
const rules = parseDetailOutput(rawOutput);

if (rules.length === 0) {
  // Try grep fallback for partial/substring match
  const grepResult = tryGrepFallback(ruleName, engine);
  if (grepResult) {
    console.log(JSON.stringify(grepResult));
    process.exit(0);
  }

  // Try fuzzy match as final fallback (catches typos like "Violtion" → "Violation")
  const fuzzyResult = tryFuzzyFallback(ruleName, engine);
  if (fuzzyResult) {
    console.log(JSON.stringify(fuzzyResult));
    process.exit(0);
  }

  console.log(JSON.stringify({
    status: "not_found",
    message: `Rule "${ruleName}" not found${engine ? ` in engine "${engine}"` : ""}. Verify the rule name with: sf code-analyzer rules --rule-selector ${engine || "all"} 2>&1 | grep -i "${ruleName}"`,
  }));
  process.exit(0);
}

// Find exact match (case-insensitive)
const exactMatch = rules.find(
  (r) => r.name.toLowerCase() === ruleName.toLowerCase()
);

if (exactMatch) {
  console.log(JSON.stringify({
    status: "success",
    rule: exactMatch,
  }));
} else if (rules.length === 1) {
  // Single result, use it
  console.log(JSON.stringify({
    status: "success",
    rule: rules[0],
  }));
} else {
  // Multiple matches
  console.log(JSON.stringify({
    status: "multiple_matches",
    message: `Found ${rules.length} rules matching "${ruleName}":`,
    candidates: rules.map((r) => ({
      name: r.name,
      engine: r.engine,
      severity: r.severity,
      tags: r.tags.join(", "),
    })),
  }));
}

/**
 * Parse the `sf code-analyzer rules --view detail` output format.
 *
 * Expected format:
 *   === 1. RuleName
 *       severity:    2 (High)
 *       engine:      pmd
 *       tags:        Recommended, Security, Apex
 *       resource:    https://pmd.github.io/...
 *       description: Validates that CRUD permissions...
 */
function parseDetailOutput(output) {
  const rules = [];
  const lines = output.split("\n");

  let currentRule = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Match rule header: === N. RuleName (must have a number prefix)
    // Skip "=== Summary" which is the footer section
    const headerMatch = line.match(/^===\s+(\d+)\.\s+(.+)$/);
    if (headerMatch) {
      if (currentRule && currentRule.name) {
        rules.push(currentRule);
      }
      currentRule = {
        name: headerMatch[2].trim(),
        engine: "unknown",
        severity: "unknown",
        tags: [],
        description: "",
        resources: [],
      };
      continue;
    }

    // Skip lines if no current rule context
    if (!currentRule) continue;

    // Match key-value pairs (indented with spaces):
    //     severity:    3 (Moderate)
    //     engine:      eslint
    //     tags:        Recommended, BestPractices, JavaScript
    //     resource:    https://...
    //     description: Some text here
    const kvMatch = line.match(/^\s{2,}(\w+):\s+(.+)$/);
    if (kvMatch) {
      const key = kvMatch[1].toLowerCase();
      const value = kvMatch[2].trim();

      switch (key) {
        case "severity":
          currentRule.severity = value;
          break;
        case "engine":
          currentRule.engine = value;
          break;
        case "tags":
          currentRule.tags = value.split(",").map((t) => t.trim()).filter(Boolean);
          break;
        case "resource":
          currentRule.resources.push(value);
          break;
        case "description":
          currentRule.description = value;
          // Description may continue on next lines (indented further)
          while (
            i + 1 < lines.length &&
            lines[i + 1].match(/^\s{14,}/) &&
            !lines[i + 1].match(/^\s{2,}\w+:/)
          ) {
            i++;
            currentRule.description += " " + lines[i].trim();
          }
          break;
      }
    }
  }

  // Push the last rule
  if (currentRule && currentRule.name) {
    rules.push(currentRule);
  }

  return rules;
}

/**
 * Fallback: grep the full rule list for partial matches
 */
function tryGrepFallback(ruleName, engine) {
  try {
    const sel = engine || "Recommended";
    const cmd = `sf code-analyzer rules --rule-selector "${sel}" 2>&1 | grep -i "${ruleName}"`;
    const grepOutput = execSync(cmd, {
      encoding: "utf8",
      timeout: 60000,
      maxBuffer: 2 * 1024 * 1024,
    });

    if (!grepOutput.trim()) return null;

    // Parse table output lines
    // Format: index  name  engine  severity  tags
    const candidates = grepOutput
      .trim()
      .split("\n")
      .filter((line) => line.trim() && !line.startsWith("─") && !line.startsWith("="))
      .slice(0, 10)
      .map((line) => {
        const parts = line.trim().split(/\s{2,}/);
        // Try to identify which part is the rule name (usually index 1 after the row number)
        if (parts.length >= 4) {
          return {
            name: parts[1] || parts[0],
            engine: parts[2] || "unknown",
            severity: parts[3] || "unknown",
            tags: parts[4] || "",
          };
        }
        return { name: line.trim(), engine: "unknown", severity: "unknown", tags: "" };
      });

    if (candidates.length === 0) return null;

    return {
      status: "multiple_matches",
      message: `Rule "${ruleName}" not found as exact match. Found ${candidates.length} potential matches:`,
      candidates,
    };
  } catch (err) {
    return null;
  }
}

/**
 * Fuzzy fallback: get all rule names and find closest matches by edit distance.
 * Catches typos like "ApexCRUDVioltion" → "ApexCRUDViolation"
 */
function tryFuzzyFallback(ruleName, engine) {
  try {
    const sel = engine || "Recommended";
    const cmd = `sf code-analyzer rules --rule-selector "${sel}" 2>&1`;
    const output = execSync(cmd, {
      encoding: "utf8",
      timeout: 60000,
      maxBuffer: 2 * 1024 * 1024,
    });

    // Extract rule names from table output
    // Lines with rule data have: index  name  engine  severity  tags
    const ruleNames = [];
    const ruleInfo = {};
    output.split("\n").forEach((line) => {
      const parts = line.trim().split(/\s{2,}/);
      if (parts.length >= 4 && /^\d+$/.test(parts[0])) {
        const name = parts[1];
        ruleNames.push(name);
        ruleInfo[name] = {
          name: name,
          engine: parts[2] || "unknown",
          severity: parts[3] || "unknown",
          tags: parts[4] || "",
        };
      }
    });

    if (ruleNames.length === 0) return null;

    // Score each rule by edit distance to the query
    const queryLower = ruleName.toLowerCase();
    const scored = ruleNames
      .map((name) => ({
        name,
        distance: levenshtein(queryLower, name.toLowerCase()),
        // Also check if query is a subsequence (handles missing chars)
        containsSubseq: isSubsequence(queryLower, name.toLowerCase()),
      }))
      .filter((r) => {
        // Only include if distance is reasonable (within 30% of query length)
        const maxDistance = Math.max(3, Math.floor(ruleName.length * 0.3));
        return r.distance <= maxDistance || r.containsSubseq;
      })
      .sort((a, b) => a.distance - b.distance)
      .slice(0, 5);

    if (scored.length === 0) return null;

    const candidates = scored.map((s) => ({
      ...ruleInfo[s.name],
      distance: s.distance,
    }));

    // If the best match is very close (distance <= 2), mark as likely match
    const best = scored[0];
    if (best.distance <= 2) {
      return {
        status: "multiple_matches",
        message: `Rule "${ruleName}" not found. Did you mean "${best.name}"? (${best.distance} character${best.distance === 1 ? "" : "s"} different)`,
        candidates,
      };
    }

    return {
      status: "multiple_matches",
      message: `Rule "${ruleName}" not found. Closest matches by name similarity:`,
      candidates,
    };
  } catch (err) {
    return null;
  }
}

/**
 * Levenshtein edit distance between two strings
 */
function levenshtein(a, b) {
  const m = a.length;
  const n = b.length;
  const dp = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0));

  for (let i = 0; i <= m; i++) dp[i][0] = i;
  for (let j = 0; j <= n; j++) dp[0][j] = j;

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      if (a[i - 1] === b[j - 1]) {
        dp[i][j] = dp[i - 1][j - 1];
      } else {
        dp[i][j] = 1 + Math.min(dp[i - 1][j], dp[i][j - 1], dp[i - 1][j - 1]);
      }
    }
  }

  return dp[m][n];
}

/**
 * Check if 'query' is a subsequence of 'target' (handles missing chars)
 * e.g., "CRUDVioltion" is a subsequence of "CRUDViolation"
 */
function isSubsequence(query, target) {
  let qi = 0;
  for (let ti = 0; ti < target.length && qi < query.length; ti++) {
    if (query[qi] === target[ti]) qi++;
  }
  // Consider it a match if at least 80% of query chars appear in order
  return qi >= query.length * 0.8;
}
