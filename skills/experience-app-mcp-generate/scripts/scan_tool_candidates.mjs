#!/usr/bin/env node
// Scan a source tree for MCP-tool-able backing types and report how each would
// bind (apiSource / apiIdentifier) and how it becomes available.
//
// Covers:
//   - Apex @InvocableMethod (class, method, types, and fields global) -> aa:apex-<Class>
//   - Autolaunched Flow (input AND output <variables>)                 -> fa:flow-<Flow>
// Usage: node scan_tool_candidates.mjs [SOURCE_ROOT]
import fs from "node:fs";
import path from "node:path";

function fail(msg) {
  process.stderr.write(msg + "\n");
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length > 1) {
  fail("Usage: scan_tool_candidates.mjs [source-root]");
}

let scanRoot = args[0] ?? process.cwd();
if (!fs.existsSync(scanRoot) || !fs.statSync(scanRoot).isDirectory()) {
  process.stderr.write(`ERROR: source root does not exist: ${scanRoot}\n`);
  process.exit(1);
}
scanRoot = fs.realpathSync(scanRoot);

function* walk(dir) {
  let entries;
  try {
    entries = fs.readdirSync(dir, { withFileTypes: true });
  } catch {
    return;
  }
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      yield* walk(full);
    } else if (e.isFile()) {
      yield full;
    }
  }
}

function stripComments(src) {
  return src.replace(/\/\*[\s\S]*?\*\//g, " ").replace(/\/\/[^\n]*/g, " ");
}

function annotationBodyEnd(rest) {
  if (!/^\s*\(/.test(rest)) return 0;
  let depth = 0;
  let k = rest.indexOf("(");
  for (; k < rest.length; k++) {
    if (rest[k] === "(") depth++;
    else if (rest[k] === ")") {
      depth--;
      if (depth === 0) return k + 1;
    }
  }
  return rest.length;
}

const APEX_PRIMITIVE_TYPES = new Set([
  "blob",
  "boolean",
  "date",
  "datetime",
  "decimal",
  "double",
  "id",
  "integer",
  "long",
  "string",
  "time",
]);

function globalClassBody(src, className) {
  const header = new RegExp(
    `global(?:\\s+(?:with|without|inherited)\\s+sharing)?\\s+class\\s+${className}\\b[^\\{]*\\{`,
  ).exec(src);
  if (!header) return null;

  const open = header.index + header[0].lastIndexOf("{");
  let depth = 0;
  for (let i = open; i < src.length; i++) {
    if (src[i] === "{") depth++;
    else if (src[i] === "}") {
      depth--;
      if (depth === 0) return src.slice(open + 1, i);
    }
  }
  return null;
}

function hasOnlyGlobalInvocableFields(typeBody) {
  const annotations = [...typeBody.matchAll(/@InvocableVariable\b/g)];
  if (annotations.length === 0) return false;
  return annotations.every((annotation) => {
    const rest = typeBody.slice(annotation.index + annotation[0].length);
    const declaration = rest.slice(annotationBodyEnd(rest));
    return /^\s*global\b/.test(declaration);
  });
}

function isSupportedListType(src, typeName) {
  if (APEX_PRIMITIVE_TYPES.has(typeName.toLowerCase())) return true;
  const typeBody = globalClassBody(src, typeName);
  return typeBody !== null && hasOnlyGlobalInvocableFields(typeBody);
}

// Eligibility matches the invocable contract the skill serves: the outer class
// and method must be global. Custom List types and all their exposed fields must
// also be global; supported Apex primitive List types need no wrapper class.
function invocableEligibility(src, className) {
  const stripped = stripComments(src);
  if (!stripped.includes("@InvocableMethod")) return null;
  const globalClass = new RegExp(
    `global(?:\\s+(?:with|without|inherited)\\s+sharing)?\\s+class\\s+${className}\\b`,
  ).test(stripped);
  if (!globalClass) return "containing class must be global";

  const re = /@InvocableMethod\b/g;
  let found = false;
  let m;
  while ((m = re.exec(stripped)) !== null) {
    found = true;
    const rest = stripped.slice(m.index + m[0].length);
    const decl = rest.slice(annotationBodyEnd(rest));
    const sig = decl.split("(")[0];
    const params = decl.slice(sig.length + 1);
    if (!/\bglobal\b/.test(sig)) continue;
    const resultMatch = sig.match(/List\s*<\s*([A-Za-z][A-Za-z0-9_]*)\s*>/);
    const requestMatch = params.match(/List\s*<\s*([A-Za-z][A-Za-z0-9_]*)\s*>/);
    if (!resultMatch || !requestMatch) {
      return "global @InvocableMethod must take and return List types";
    }
    const typesOk = [requestMatch[1], resultMatch[1]].every((typeName) =>
      isSupportedListType(stripped, typeName),
    );
    if (typesOk) return "";
    return "custom request and result types and every @InvocableVariable field must be global";
  }
  return found ? "@InvocableMethod method must be global" : null;
}

function flowVariableBlocks(src) {
  return [...src.matchAll(/<variables\b[^>]*>[\s\S]*?<\/variables>/g)].map((match) =>
    match[0].replace(/<description>[\s\S]*?<\/description>/g, ""),
  );
}

function variableFlag(blocks, flag) {
  const re = new RegExp(`<${flag}>\\s*true\\s*</${flag}>`);
  return blocks.some((block) => re.test(block));
}

console.log("Candidate | Type | apiSource | apiIdentifier | Availability");
console.log("--------- | ---- | --------- | ------------- | ------------");

// --- Apex classes: full global invocable contract ---
for (const f of walk(scanRoot)) {
  if (!f.endsWith(".cls")) continue;
  const className = path.basename(f, ".cls");
  const src = fs.readFileSync(f, "utf-8");
  const reason = invocableEligibility(src, className);
  if (reason === null) continue;
  if (reason === "") {
    console.log(`${className} | Apex @InvocableMethod | API_CATALOG | aa:apex-${className} | eligible (global)`);
  } else {
    console.log(`${className} | Apex @InvocableMethod | — | — | SKIP — ${reason}`);
  }
}

// --- Flows: autolaunched only, and only with <variables> that are input and output ---
for (const f of walk(scanRoot)) {
  if (!f.endsWith(".flow-meta.xml")) continue;
  const flowName = path.basename(f, ".flow-meta.xml");
  const src = fs.readFileSync(f, "utf-8");
  if (!/<processType>\s*AutoLaunchedFlow\s*<\/processType>/.test(src)) {
    console.log(`${flowName} | Flow (NOT autolaunched) | — | — | SKIP — only autolaunched flows are MCP-able`);
    continue;
  }
  const blocks = flowVariableBlocks(src);
  if (variableFlag(blocks, "isInput") && variableFlag(blocks, "isOutput")) {
    console.log(`${flowName} | Autolaunched Flow | API_CATALOG | fa:flow-${flowName} | eligible`);
  } else {
    console.log(`${flowName} | Autolaunched Flow | — | — | SKIP — needs both input and output variables`);
  }
}

console.log();
console.log("Notes:");
console.log("  - This scan reports global invocable Apex actions with supported primitive or fully global custom types, plus autolaunched Flows with input and output variables.");
console.log("  - Confirm add-or-skip per candidate before adding its <tools> block.");
