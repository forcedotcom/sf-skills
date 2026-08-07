#!/usr/bin/env node
// Decode the base64 `report` field from an ApexGuru SFAP Scan SUCCEEDED body
// and summarize violations grouped by rule. This is the ONLY sanctioned way to
// read the report — never inline base64/jq/Read against the raw result file.
//
// Usage:
//   node decode-report.js <raw-result.json> [--group rule|severity|file]
//                                           [--rule RULE] [--severity S]
//                                           [--file NAME] [--top N] [--full]
//                                           [--present]
//
// Default: prints a single-line JSON summary to stdout:
//   { analysisMode, attribution, violationCount, filesScanned, severityCounts,
//     groups:[{key,count,severityCounts,sample:[...]}], topViolations:[...],
//     truncated }
// With --full, `groups[].items` holds every violation in that group.
//
// With --present: renders ready-to-show markdown directly (severity legend,
// one "### Issue N" card per violation with message/code/fix/resource, a
// collapsed "CPU Hotspots" table for the ExpensiveMethods rule, and a closing
// "## Summary" table listing every violation) instead of dumping raw JSON.
// Implies --full (no silent caps in a response meant to be presented as complete).

const fs = require("fs");

function fail(msg) {
  console.error(msg);
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length < 1) fail("Usage: node decode-report.js <raw-result.json> [options]");

const rawPath = args[0];
const opts = { group: "rule", top: 10, full: false, rule: null, severity: null, file: null, present: false };
for (let i = 1; i < args.length; i++) {
  const a = args[i];
  if (a === "--group") opts.group = args[++i];
  else if (a === "--top") opts.top = parseInt(args[++i], 10) || 10;
  else if (a === "--full") opts.full = true;
  else if (a === "--present") { opts.present = true; opts.full = true; }
  else if (a === "--rule") opts.rule = args[++i];
  else if (a === "--severity") opts.severity = String(args[++i]);
  else if (a === "--file") opts.file = args[++i];
}

let raw;
try {
  raw = JSON.parse(fs.readFileSync(rawPath, "utf8"));
} catch (e) {
  fail(`Could not read/parse raw result file: ${e.message}`);
}

if (raw.status && raw.status !== "SUCCEEDED") {
  fail(`Scan status is ${raw.status}, not SUCCEEDED — nothing to decode. Message: ${raw.message || "(none)"}`);
}

// --- decode the base64 report into a violations array ---
let violations = [];
if (raw.report) {
  let decoded;
  try {
    decoded = Buffer.from(raw.report, "base64").toString("utf8");
  } catch (e) {
    fail(`report field is not valid base64: ${e.message}`);
  }
  let parsed;
  try {
    parsed = JSON.parse(decoded);
  } catch (e) {
    fail(`decoded report is not valid JSON: ${e.message}`);
  }
  // API contract: report is a JSON array of violations. Tolerate a wrapper obj.
  violations = Array.isArray(parsed) ? parsed : parsed.violations || [];
}

// --- normalize each violation to a stable shape (tolerate field-name drift) ---
function loc(v) {
  const l = v.location || (Array.isArray(v.locations) && v.locations[0]) || {};
  return {
    file: basename(l.file || v.file || "unknown"),
    line: l.line || l.startLine || v.line || 0,
    comment: l.comment || "",
  };
}
function basename(p) {
  return String(p).split(/[\\/]/).pop();
}
// The API's real field for fix code is `suggestions: [{message, location}]` —
// each suggestion's `message` IS the replacement code. Older/hypothetical
// shapes (fixes/suggestedFixes/suggestedFix) are tolerated as a fallback.
function fixesOf(v) {
  if (Array.isArray(v.suggestions) && v.suggestions.length) {
    return v.suggestions.map((s) => (typeof s === "string" ? s : s.message)).filter(Boolean);
  }
  const f = v.fixes || v.suggestedFixes || (v.suggestedFix ? [v.suggestedFix] : []);
  return (Array.isArray(f) ? f : [f]).filter(Boolean);
}
// `locations[].comment` holds "ClassName.methodName" — split for a display name.
function methodOf(comment) {
  if (!comment) return "";
  const parts = comment.split(".");
  return parts.length > 1 ? parts.slice(1).join(".") : comment;
}
// The API sometimes prefixes each line of `original_code` with "Line N:" —
// strip that so the snippet reads as plain Apex inside a code block.
function stripLinePrefixes(code) {
  return code.replace(/^Line \d+:\s?/gm, "").replace(/\n+$/, "");
}
function norm(v) {
  const { file, line, comment } = loc(v);
  const metadata = v.metadata || {};
  return {
    rule: v.rule || v.ruleName || v.type || "UNKNOWN",
    message: v.message || v.description || "",
    severity: String(v.severity ?? v.sev ?? ""),
    file,
    line,
    method: methodOf(comment),
    originalCode: metadata.original_code ? stripLinePrefixes(metadata.original_code) : "",
    cpuTimePercentage: typeof metadata.cpu_time_percentage === "number" ? metadata.cpu_time_percentage : null,
    fixes: fixesOf(v),
    resources: v.resources || v.helpDocs || v.help || [],
  };
}
const allItems = violations.map(norm);
let items = allItems;

// --- optional filters ---
if (opts.rule) items = items.filter((v) => v.rule === opts.rule);
if (opts.severity) items = items.filter((v) => v.severity === opts.severity);
if (opts.file) items = items.filter((v) => v.file === opts.file || v.file.includes(opts.file));

// --- aggregates ---
const severityCounts = {};
for (const v of items) severityCounts[v.severity || "?"] = (severityCounts[v.severity || "?"] || 0) + 1;

function keyOf(v) {
  return opts.group === "severity" ? (v.severity || "?") : opts.group === "file" ? v.file : v.rule;
}
const byKey = new Map();
for (const v of items) {
  const k = keyOf(v);
  if (!byKey.has(k)) byKey.set(k, []);
  byKey.get(k).push(v);
}
const groups = [...byKey.entries()]
  .map(([key, arr]) => {
    const sc = {};
    for (const v of arr) sc[v.severity || "?"] = (sc[v.severity || "?"] || 0) + 1;
    const g = { key, count: arr.length, severityCounts: sc, sample: arr.slice(0, 3) };
    if (opts.full) g.items = arr;
    return g;
  })
  .sort((a, b) => b.count - a.count);

// Top violations by severity (numeric asc = most severe first when sev is 1..5).
const topViolations = items
  .slice()
  .sort((a, b) => (parseInt(a.severity, 10) || 99) - (parseInt(b.severity, 10) || 99) || a.rule.localeCompare(b.rule))
  .slice(0, opts.top);

// full = enriched with runtime metrics; static = source-only. Onboarded orgs with
// no runtime data for this code yet come back full but static-equivalent (no
// cpu_time_percentage), so only call it "Production insights" when metrics exist.
// Compute this from the FULL (unfiltered) violation list — attribution is a
// property of the whole scan, so a --rule/--severity/--file drill-down must not
// flip an enriched scan to "Static only" just because the selected subset has
// no cpu_time_percentage.
const analysisMode = raw.analysisMode || "static";
const hasRuntimeMetrics = allItems.some((v) => v.cpuTimePercentage != null);
const attribution = analysisMode === "full" && hasRuntimeMetrics ? "Production insights" : "Static only";

const summary = {
  scanId: raw.scanId || null,
  analysisMode,
  attribution,
  violationCount: items.length,
  filesScanned: raw.filesScanned ?? null,
  serverViolationBreakdown: raw.violationBreakdown || null,
  severityCounts,
  groupedBy: opts.group,
  groups: opts.full ? groups : groups.slice(0, opts.top),
  topViolations,
  truncated: !opts.full && groups.length > opts.top,
};

if (!opts.present) {
  console.log(JSON.stringify(summary));
  process.exit(0);
}

// --- --present: render ready-to-read markdown (icons, per-issue detail, ---
// --- summary table) instead of leaving table-building up to the reader. ---

// ApexGuru severities run 1 (critical) .. 5 (info); map to icon + label.
const SEVERITY_MAP = {
  1: { icon: "\u{1F534}", label: "Critical" }, // red
  2: { icon: "\u{1F7E0}", label: "Major" }, // orange
  3: { icon: "\u{1F7E0}", label: "Major" }, // orange
  4: { icon: "\u{1F7E1}", label: "Minor" }, // yellow
  5: { icon: "\u{1F7E1}", label: "Minor" }, // yellow
};
function sevInfo(sev) {
  return SEVERITY_MAP[parseInt(sev, 10)] || { icon: "⚪", label: `Severity ${sev}` };
}

// Human-friendly rule names mapping (for violation.rule field)
const RULE_DISPLAY_NAMES = {
  // Single-file scan rules (API_SUPPORTED_AP_TYPES)
  "SoqlWithoutAWhereClauseOrLimitStatement": "SOQL Without WHERE Clause or LIMIT Statement",
  "SoqlWithUnusedFields": "SOQL With Unused Fields",
  "SoqlWithWildcardFilter": "SOQL With Wildcard Filter",
  "SchemaGetGlobalDescribeNotEfficient": "Inefficient Schema.getGlobalDescribe() Usage",
  "SoqlInALoop": "SOQL in Loop",
  "SoqlInALoopOneHop": "SOQL in One-Hop Loop",
  "DmlInALoop": "DML in Loop",
  "SortingInApex": "Sorting in Apex",
  "BusyLoopDelay": "Busy Loop Delay",
  "CopyingListOrSetElementsUsingAForLoop": "Copying List/Set Elements Using a For Loop",
  "SObjectMapInAForLoop": "SObject Map Lookup in a Loop",
  "SoqlWithNegativeExpressions": "SOQL With Negative Expressions",
  "SoqlWithApexFilter": "SOQL With Apex Filter",
  "ExpensiveMethods": "Expensive Methods",
  "UsingTheTestMethodKeyword": "Using the testMethod Keyword",
  "WritingFillerStatements": "Writing Filler Statements",
  // Project-scope scan rules (API_SCAN_PROJECT_AP_TYPES)
  "UnusedMethods": "Unused Methods",
  "LimitsGetHeapsizeMethods": "Limits.getHeapSize() in Loop",
  "ExpensiveStringComparison": "Expensive String Comparison",
  "ExpensiveDebugStatements": "Expensive Debug Statements",
  // Fallback-style entries (no explicit ANTI_PATTERN_RULE_NAMES mapping)
  "Soql Aggregation": "SOQL Aggregation",
  "Redundant Soql": "Redundant SOQL",
};

// Mapping for violationBreakdown keys (SCREAMING_SNAKE_CASE internal IDs)
const BREAKDOWN_DISPLAY_NAMES = {
  "SOQL_NO_WHERE_LIMIT": "SOQL Without WHERE Clause or LIMIT Statement",
  "SOQL_UNUSED_FIELDS": "SOQL With Unused Fields",
  "SOQL_WILDCARD": "SOQL With Wildcard Filter",
  "GGD": "Inefficient Schema.getGlobalDescribe() Usage",
  "SOQL_IN_LOOP": "SOQL in Loop",
  "SOQL_IN_LOOP_1HOP": "SOQL in One-Hop Loop",
  "DML_IN_LOOP": "DML in Loop",
  "SOQL_SORT_IN_APEX": "Sorting in Apex",
  "BUSY_DELAY_LOOP": "Busy Loop Delay",
  "COPY_LIST_ELEMENTS_LOOP": "Copying List/Set Elements Using a For Loop",
  "CREATE_MAP_WITH_LOOP": "SObject Map Lookup in a Loop",
  "SOQL_NEGATIVE_EXPR": "SOQL With Negative Expressions",
  "SOQL_FILTER_IN_APEX": "SOQL With Apex Filter",
  "EXPENSIVE_METHODS": "Expensive Methods",
  "DEPRECATED_TEST_METHOD_KEYWORD": "Using the testMethod Keyword",
  "CODE_COVERAGE_INFLATION": "Writing Filler Statements",
  "OBSOLETE_CLASSES_METHODS": "Unused Methods",
  "EXPENSIVE_LIMIT_METHODS": "Limits.getHeapSize() in Loop",
  "EXPENSIVE_STRING_COMPARE": "Expensive String Comparison",
  "EXPENSIVE_DEBUG_STMT": "Expensive Debug Statements",
  "SOQL_AGGREGATION": "SOQL Aggregation",
  "REDUNDANT_SOQL": "Redundant SOQL",
};
function displayRuleName(rule) {
  return RULE_DISPLAY_NAMES[rule] || rule;
}

// Three ApexGuru states, distinguished per the SFAP contract (hasRuntimeMetrics
// and attribution computed above):
//   analysisMode: static             → org is NOT onboarded to ApexGuru
//   analysisMode: full + runtime data → onboarded; runtime metrics applied
//   analysisMode: full + NO runtime   → onboarded, but no runtime data for this
//                                       code yet (result is static-equivalent)
const isFull = summary.analysisMode === "full";
const isEnriched = isFull && hasRuntimeMetrics;
const isOnboardedNoData = isFull && !hasRuntimeMetrics;

const violationWord = summary.violationCount === 1 ? "violation" : "violations";
// attribution already reflects runtime presence ("Production insights" only when enriched).
let out = `# ApexGuru Scan Results — ${summary.attribution}\n\n`;
out += `Found **${summary.violationCount} performance ${violationWord}** across ${summary.filesScanned ?? "?"} file(s). `;
if (isEnriched) {
  out += "Findings enriched with production runtime metrics.\n";
} else if (isOnboardedNoData) {
  out += "No runtime metrics were found for this class yet. Generate an ApexGuru report in Scale Center to see runtime insights.\n";
} else {
  out += "ApexGuru static analysis is active. To see how this code performs in your production org, generate a runtime report in Scale Center.\n";
}
out += "\n";

out += "## Severity Legend\n\n";
out += "- \u{1F534} Critical — blocks deployment and causes test failures\n";
out += "- \u{1F7E0} Major — reduces reliability without blocking deployment\n";
out += "- \u{1F7E1} Minor — deviates from quality standards\n";
if (isEnriched) out += "- \u{1F4A1} Severity adjusted based on production performance.\n";
out += "\n";

if (summary.violationCount === 0) {
  out += "No performance antipatterns found.\n";
  console.log(out);
  process.exit(0);
}

const allViolations = groups.flatMap((g) => g.items || g.sample);
allViolations.sort((a, b) => (parseInt(a.severity, 10) || 99) - (parseInt(b.severity, 10) || 99));

// ExpensiveMethods is a per-method CPU-hotspot ranking, not a line-level
// antipattern — with N methods ranked it produces N near-identical cards, so
// collapse it into one ranked table instead of repeating the detail format.
const hotspots = allViolations.filter((v) => v.rule === "ExpensiveMethods");
const otherViolations = allViolations.filter((v) => v.rule !== "ExpensiveMethods");

if (hotspots.length) {
  out += `## CPU Hotspots (${hotspots.length})\n\n`;
  out += "Methods ranked by share of observed Apex CPU time (production metrics):\n\n";
  out += "| Method | % of CPU time |\n";
  out += "|--------|---------------|\n";
  hotspots
    .slice()
    .sort((a, b) => (b.cpuTimePercentage || 0) - (a.cpuTimePercentage || 0))
    .forEach((v) => {
      const pct = v.cpuTimePercentage != null ? Math.round(v.cpuTimePercentage * 10) / 10 : "?";
      out += `| \`${v.method || v.file}\` | ${pct}% |\n`;
    });
  out += "\n";
}

// Full-detail cards for the remaining (non-hotspot) violations, capped at
// 10 most critical. Both the detailed cards AND the summary table are capped.
const cardLimit = 10;
const cards = otherViolations.slice(0, cardLimit);
const remainingCount = otherViolations.length - cardLimit;

if (cards.length) {
  out += `## Issues${otherViolations.length > cardLimit ? ` (top ${cardLimit} of ${otherViolations.length}, most critical first)` : ""}\n\n`;
  cards.forEach((v, i) => {
    const sev = sevInfo(v.severity);
    const where = v.method ? ` in \`${v.method}\`` : "";
    const ruleName = displayRuleName(v.rule);
    out += `### Issue ${i + 1} — ${isEnriched ? "\u{1F4A1}" : ""}${sev.icon} ${sev.label}: ${ruleName}${where} (Line ${v.line})\n\n`;
    out += `${v.message}\n\n`;
    if (v.originalCode) {
      out += `**Current code** (\`${v.file}\`, line ${v.line}):\n\n\`\`\`apex\n${v.originalCode}\n\`\`\`\n\n`;
    }
    if (v.fixes.length) {
      out += `**Suggested fix:**\n\n\`\`\`apex\n${v.fixes[0]}\n\`\`\`\n\n`;
    }
    if (v.resources.length) {
      out += `[Learn more](${v.resources[0]})\n\n`;
    }
  });
}

// Summary table also capped at top 10 (matches the detailed cards above).
out += "## Summary\n\n";
out += "| # | Severity | Rule | Method | Line |\n";
out += "|---|----------|------|--------|------|\n";
const summaryViolations = allViolations.slice(0, cardLimit);
summaryViolations.forEach((v, i) => {
  const sev = sevInfo(v.severity);
  const lineCell = v.rule === "ExpensiveMethods" ? "-" : v.line;
  const ruleName = displayRuleName(v.rule);
  out += `| ${i + 1} | ${sev.icon} ${sev.label} | ${ruleName} | ${v.method || "-"} | ${lineCell} |\n`;
});

// Add Anti-pattern breakdown section with summary (always show the full breakdown)
if (summary.serverViolationBreakdown && Object.keys(summary.serverViolationBreakdown).length > 0) {
  out += `\n---\n\n`;
  const breakdown = summary.serverViolationBreakdown;
  const ruleTypeCount = Object.keys(breakdown).length;

  // Summary line
  out += `Detected **${summary.violationCount} anti-patterns** across **${ruleTypeCount} rule types**.\n\n`;

  // Breakdown list
  out += `**Anti-pattern breakdown:**\n\n`;
  const sortedBreakdown = Object.entries(breakdown).sort((a, b) => b[1] - a[1]);
  sortedBreakdown.forEach(([key, count]) => {
    const displayName = BREAKDOWN_DISPLAY_NAMES[key] || key.replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
    out += `- ${displayName} (${count})\n`;
  });

  // Footer message if more than 10 violations
  if (remainingCount > 0) {
    out += `\n---\n\n`;
    out += `Showing the top ${cardLimit} of ${otherViolations.length} antipatterns. `;
    out += `Type **"show all"** or ask for details to see the remaining ${remainingCount}.\n`;
  }
}

console.log(out);
