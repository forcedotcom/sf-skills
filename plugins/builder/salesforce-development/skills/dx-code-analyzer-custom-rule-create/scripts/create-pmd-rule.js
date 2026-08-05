#!/usr/bin/env node
// Creates a PMD XPath custom rule (XML ruleset file + config reference)
// Usage: node create-pmd-rule.js --name <name> --xpath <expression> --message <msg> [options]

const fs = require("fs");
const path = require("path");

function printUsage() {
  console.error(`Usage: node create-pmd-rule.js --name <name> --xpath <expression> --message <msg> [options]

Required:
  --name <name>              Rule name (PascalCase, no spaces)
  --xpath <expression>       XPath expression to match violations
  --message <msg>            Violation message shown to users

Optional:
  --description <desc>       Detailed rule description (default: same as message)
  --language <lang>          PMD language (default: apex)
  --priority <1-5>           PMD priority (default: 3)
  --example <code>           Example violating code snippet
  --config-file <path>       Path to code-analyzer.yml (default: ./code-analyzer.yml)
  --ruleset-dir <dir>        Directory for ruleset XML (default: ./custom-rules)

Examples:
  node create-pmd-rule.js --name NoSystemDebug --xpath "//MethodCallExpression[@FullMethodName='System.debug']" --message "System.debug not allowed" --priority 3
  node create-pmd-rule.js --name SoqlInLoop --xpath "//ForEachStatement//SoqlExpression" --message "SOQL inside loop" --priority 2`);
  process.exit(1);
}

// Parse arguments
const args = process.argv.slice(2);
if (args.length < 1 || args[0] === "--help" || args[0] === "-h") {
  printUsage();
}

const options = {
  name: null,
  xpath: null,
  message: null,
  description: null,
  language: "apex",
  priority: 3,
  example: null,
  configFile: "./code-analyzer.yml",
  rulesetDir: "./custom-rules",
};

for (let i = 0; i < args.length; i++) {
  switch (args[i]) {
    case "--name": options.name = args[++i]; break;
    case "--xpath": options.xpath = args[++i]; break;
    case "--message": options.message = args[++i]; break;
    case "--description": options.description = args[++i]; break;
    case "--language": options.language = args[++i]; break;
    case "--priority": options.priority = parseInt(args[++i], 10); break;
    case "--example": options.example = args[++i]; break;
    case "--config-file": options.configFile = args[++i]; break;
    case "--ruleset-dir": options.rulesetDir = args[++i]; break;
    default:
      console.error(`Unknown option: ${args[i]}`);
      printUsage();
  }
}

// Validate required fields
if (!options.name) { console.error("Error: --name is required"); process.exit(1); }
if (!options.xpath) { console.error("Error: --xpath is required"); process.exit(1); }
if (!options.message) { console.error("Error: --message is required"); process.exit(1); }

// Validate rule name
const RULE_NAME_PATTERN = /^[A-Za-z@][A-Za-z_0-9@\-/]*$/;
if (!RULE_NAME_PATTERN.test(options.name)) {
  console.error(`Error: Invalid rule name "${options.name}". Must match: ${RULE_NAME_PATTERN}`);
  process.exit(1);
}

// Validate priority
if (options.priority < 1 || options.priority > 5) {
  console.error("Error: Priority must be 1-5");
  process.exit(1);
}

// Validate language
const VALID_LANGUAGES = ["apex", "visualforce", "html", "xml", "javascript"];
if (!VALID_LANGUAGES.includes(options.language.toLowerCase())) {
  console.error(`Error: Invalid language "${options.language}". Supported: ${VALID_LANGUAGES.join(", ")}`);
  process.exit(1);
}

// Set defaults
if (!options.description) {
  options.description = options.message;
}

// Generate the PMD ruleset XML
function buildRulesetXml() {
  const escXpath = options.xpath.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const escMessage = options.message.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  const escDescription = options.description.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

  let xml = `<?xml version="1.0" encoding="UTF-8"?>
<ruleset name="${options.name}CustomRules"
    xmlns="http://pmd.sourceforge.net/ruleset/2.0.0"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xsi:schemaLocation="http://pmd.sourceforge.net/ruleset/2.0.0 https://pmd.sourceforge.io/ruleset_2_0_0.xsd">

    <description>Custom rules for ${options.name}</description>

    <rule name="${options.name}"
          language="${options.language}"
          message="${escMessage}"
          class="net.sourceforge.pmd.lang.rule.xpath.XPathRule">

        <description>${escDescription}</description>
        <priority>${options.priority}</priority>

        <properties>
            <property name="xpath">
                <value><![CDATA[
${options.xpath}
]]></value>
            </property>
        </properties>`;

  if (options.example) {
    xml += `

        <example>
<![CDATA[
${options.example}
]]>
        </example>`;
  }

  xml += `
    </rule>
</ruleset>
`;

  return xml;
}

// Create ruleset directory if needed
const rulesetDir = path.resolve(options.rulesetDir);
if (!fs.existsSync(rulesetDir)) {
  fs.mkdirSync(rulesetDir, { recursive: true });
}

// Write ruleset XML
const rulesetFileName = `${options.name}-pmd-ruleset.xml`;
const rulesetPath = path.join(rulesetDir, rulesetFileName);

if (fs.existsSync(rulesetPath)) {
  console.error(`Error: Ruleset file already exists: ${rulesetPath}`);
  process.exit(1);
}

const rulesetXml = buildRulesetXml();
fs.writeFileSync(rulesetPath, rulesetXml, "utf8");

// Update code-analyzer.yml to reference the ruleset
const configPath = path.resolve(options.configFile);
const rulesetRelativePath = path.relative(path.dirname(configPath), rulesetPath);
let configContent = "";

if (fs.existsSync(configPath)) {
  configContent = fs.readFileSync(configPath, "utf8");
}

// Check if this ruleset path is already referenced in config (deduplication)
const alreadyReferenced = configContent.includes(rulesetRelativePath);

if (!configContent) {
  // Create new config
  configContent = `engines:\n  pmd:\n    custom_rulesets:\n      - "${rulesetRelativePath}"\n`;
} else if (alreadyReferenced) {
  // Ruleset path already in config — skip adding duplicate entry
  // (This happens when the XML was deleted and recreated during iteration)
} else if (configContent.includes("custom_rulesets:") && configContent.includes("pmd:")) {
  // Add to existing custom_rulesets
  const insertPoint = configContent.indexOf("custom_rulesets:");
  const afterLine = configContent.indexOf("\n", insertPoint) + 1;
  configContent = configContent.slice(0, afterLine) + `      - "${rulesetRelativePath}"\n` + configContent.slice(afterLine);
} else if (configContent.includes("pmd:")) {
  // Add custom_rulesets under pmd
  const insertPoint = configContent.indexOf("pmd:");
  const afterLine = configContent.indexOf("\n", insertPoint) + 1;
  configContent = configContent.slice(0, afterLine) + `    custom_rulesets:\n      - "${rulesetRelativePath}"\n` + configContent.slice(afterLine);
} else if (configContent.includes("engines:")) {
  // Add pmd section under engines
  const insertPoint = configContent.indexOf("engines:");
  const afterLine = configContent.indexOf("\n", insertPoint) + 1;
  configContent = configContent.slice(0, afterLine) + `  pmd:\n    custom_rulesets:\n      - "${rulesetRelativePath}"\n` + configContent.slice(afterLine);
} else {
  // Append engines section
  configContent += `\nengines:\n  pmd:\n    custom_rulesets:\n      - "${rulesetRelativePath}"\n`;
}

fs.writeFileSync(configPath, configContent, "utf8");

console.log(JSON.stringify({
  status: "success",
  ruleName: options.name,
  engine: "pmd",
  language: options.language,
  rulesetFile: rulesetPath,
  configFile: configPath,
  message: `Rule "${options.name}" created. Validate with: sf code-analyzer rules --rule-selector pmd:${options.name}`
}));
