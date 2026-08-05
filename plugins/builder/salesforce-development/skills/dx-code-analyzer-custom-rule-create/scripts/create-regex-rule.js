#!/usr/bin/env node
// Creates a regex custom rule in code-analyzer.yml
// Usage: node create-regex-rule.js --name <name> --regex <pattern> --description <desc> [options]

const fs = require("fs");
const path = require("path");

function printUsage() {
  console.error(`Usage: node create-regex-rule.js --name <name> --regex <pattern> --description <desc> [options]

Required:
  --name <name>              Rule name (PascalCase, no spaces)
  --regex <pattern>          Regex in /pattern/flags format
  --description <desc>       What the rule checks

Optional:
  --violation-message <msg>  Message shown on violation
  --severity <1-5>           Severity level (default: 3)
  --tags <tag1,tag2>         Comma-separated tags (default: Recommended,Custom)
  --file-extensions <exts>   Comma-separated extensions (e.g., .cls,.trigger)
  --regex-ignore <pattern>   Negative pattern to exclude matches
  --config-file <path>       Path to code-analyzer.yml (default: ./code-analyzer.yml)

Examples:
  node create-regex-rule.js --name NoHardcodedIds --regex "/[0-9a-zA-Z]{18}/g" --description "Detects hardcoded IDs" --severity 2 --file-extensions ".cls,.trigger"
  node create-regex-rule.js --name NoTodos --regex "/TODO|FIXME/gi" --description "Flags TODO comments" --severity 4`);
  process.exit(1);
}

// Parse arguments
const args = process.argv.slice(2);
if (args.length < 1 || args[0] === "--help" || args[0] === "-h") {
  printUsage();
}

const options = {
  name: null,
  regex: null,
  description: null,
  violationMessage: null,
  severity: 3,
  tags: ["Recommended", "Custom"],
  fileExtensions: null,
  regexIgnore: null,
  configFile: "./code-analyzer.yml",
};

for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case "--name": options.name = args[++i]; break;
    case "--regex": options.regex = args[++i]; break;
    case "--description": options.description = args[++i]; break;
    case "--violation-message": options.violationMessage = args[++i]; break;
    case "--severity": options.severity = parseInt(args[++i], 10); break;
    case "--tags": options.tags = args[++i].split(",").map(t => t.trim()); break;
    case "--file-extensions": options.fileExtensions = args[++i].split(",").map(e => e.trim()); break;
    case "--regex-ignore": options.regexIgnore = args[++i]; break;
    case "--config-file": options.configFile = args[++i]; break;
    default:
      console.error(`Unknown option: ${args[i]}`);
      printUsage();
  }
}

// Validate required fields
if (!options.name) { console.error("Error: --name is required"); process.exit(1); }
if (!options.regex) { console.error("Error: --regex is required"); process.exit(1); }
if (!options.description) { console.error("Error: --description is required"); process.exit(1); }

// Validate rule name
const RULE_NAME_PATTERN = /^[A-Za-z@][A-Za-z_0-9@\-/]*$/;
if (!RULE_NAME_PATTERN.test(options.name)) {
  console.error(`Error: Invalid rule name "${options.name}". Must match: ${RULE_NAME_PATTERN}`);
  process.exit(1);
}

// Validate regex format — must be /pattern/flags with no surrounding whitespace
// and the flags portion must contain only valid JavaScript regex flag characters.
options.regex = options.regex.trim();
if (!options.regex.startsWith("/") || options.regex.lastIndexOf("/") <= 0) {
  console.error(`Error: Regex must be in /pattern/flags format. Got: "${options.regex}"`);
  process.exit(1);
}
const lastSlash = options.regex.lastIndexOf("/");
const flags = options.regex.slice(lastSlash + 1);
if (!flags) {
  console.error(`Error: Regex must include flags after the closing /. Use /pattern/g at minimum. Got: "${options.regex}"`);
  process.exit(1);
}
// Strict flags validation — only valid JS regex flag chars allowed, no spaces, no junk.
if (!/^[gimsuy]+$/.test(flags)) {
  console.error(`Error: Invalid regex flags "${flags}". Allowed: g, i, m, s, u, y (no spaces, no other characters). Got: "${options.regex}"`);
  process.exit(1);
}
// Code Analyzer regex rules require the global flag.
if (!flags.includes("g")) {
  console.error(`Error: Regex must include the global flag 'g'. Got flags: "${flags}"`);
  process.exit(1);
}

// Validate severity
if (options.severity < 1 || options.severity > 5) {
  console.error("Error: Severity must be 1-5");
  process.exit(1);
}

// Validate file extensions
if (options.fileExtensions) {
  for (const ext of options.fileExtensions) {
    if (!ext.startsWith(".")) {
      console.error(`Error: File extension must start with dot: "${ext}"`);
      process.exit(1);
    }
  }
}

// Safely quote a string for YAML output.
// CRITICAL: regex patterns contain backslashes (`\.`, `\d`, `\\`, etc.).
// Double-quoted YAML treats `\` as an escape introducer — `\.` is an unknown
// escape and YAML rejects the file with "unknown escape sequence". Single-quoted
// YAML treats backslash as literal, which is exactly what regex needs.
// Strategy:
//   - If value contains a backslash → ALWAYS use single quotes (escape ' as '')
//   - Else if value has no quotes → double quotes (simplest, most readable)
//   - Else → single quotes (escape ' as '')
function yamlQuote(value) {
  const hasBackslash = value.includes("\\");
  const hasSingle = value.includes("'");
  const hasDouble = value.includes('"');

  if (!hasBackslash && !hasSingle && !hasDouble) {
    return `"${value}"`;
  }

  // Single-quoted YAML: only ' needs escaping (as ''). Backslashes pass through.
  const escaped = value.replace(/'/g, "''");
  return `'${escaped}'`;
}

// Build the rule YAML block
function buildRuleYaml() {
  const indent = "      ";
  const lines = [];
  lines.push(`      ${options.name}:`);
  lines.push(`${indent}  regex: ${yamlQuote(options.regex)}`);
  lines.push(`${indent}  description: ${yamlQuote(options.description)}`);

  if (options.violationMessage) {
    lines.push(`${indent}  violation_message: ${yamlQuote(options.violationMessage)}`);
  }

  lines.push(`${indent}  severity: ${options.severity}`);

  if (options.tags && options.tags.length > 0) {
    lines.push(`${indent}  tags:`);
    options.tags.forEach(tag => lines.push(`${indent}    - "${tag}"`));
  }

  if (options.fileExtensions && options.fileExtensions.length > 0) {
    lines.push(`${indent}  file_extensions:`);
    options.fileExtensions.forEach(ext => lines.push(`${indent}    - "${ext}"`));
  }

  if (options.regexIgnore) {
    lines.push(`${indent}  regex_ignore: ${yamlQuote(options.regexIgnore)}`);
  }

  return lines.join("\n");
}

// Read or create config file
const configPath = path.resolve(options.configFile);
let configContent = "";

if (fs.existsSync(configPath)) {
  configContent = fs.readFileSync(configPath, "utf8");

  // Check if rule already exists
  if (configContent.includes(`${options.name}:`)) {
    console.error(`Error: Rule "${options.name}" already exists in ${configPath}`);
    process.exit(1);
  }
}

const ruleYaml = buildRuleYaml();

// Upsert into config
if (!configContent) {
  // Create new file
  configContent = `engines:\n  regex:\n    custom_rules:\n${ruleYaml}\n`;
} else if (configContent.includes("custom_rules:") && configContent.includes("regex:")) {
  // Add to existing custom_rules section
  const insertPoint = configContent.indexOf("custom_rules:");
  const afterCustomRules = configContent.indexOf("\n", insertPoint) + 1;
  configContent = configContent.slice(0, afterCustomRules) + ruleYaml + "\n" + configContent.slice(afterCustomRules);
} else if (configContent.includes("regex:")) {
  // Add custom_rules section under regex
  const insertPoint = configContent.indexOf("regex:");
  const afterRegex = configContent.indexOf("\n", insertPoint) + 1;
  configContent = configContent.slice(0, afterRegex) + "    custom_rules:\n" + ruleYaml + "\n" + configContent.slice(afterRegex);
} else if (configContent.includes("engines:")) {
  // Add regex section under engines
  const insertPoint = configContent.indexOf("engines:");
  const afterEngines = configContent.indexOf("\n", insertPoint) + 1;
  configContent = configContent.slice(0, afterEngines) + "  regex:\n    custom_rules:\n" + ruleYaml + "\n" + configContent.slice(afterEngines);
} else {
  // Append engines section
  configContent += "\nengines:\n  regex:\n    custom_rules:\n" + ruleYaml + "\n";
}

// Write config
fs.writeFileSync(configPath, configContent, "utf8");

console.log(JSON.stringify({
  status: "success",
  ruleName: options.name,
  engine: "regex",
  configFile: configPath,
  message: `Rule "${options.name}" created. Validate with: sf code-analyzer rules --rule-selector regex:${options.name}`
}));
