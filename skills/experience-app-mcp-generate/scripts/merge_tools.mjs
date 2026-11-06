#!/usr/bin/env node
// Merge tools into McpServerDefinition metadata by apiIdentifier.
//
// Usage:
//     node merge_tools.mjs <SERVER_META_XML> <TOOLS_JSON> [--dry-run] [--skip-existing]
//
// SERVER_META_XML is modified in place. TOOLS_JSON accepts one tool, an array,
// or { tools: [...], prompts: [...] }; use '-' for stdin. Each tool requires
// apiIdentifier and the five JSON booleans
// destructive, idempotent, openWorld, readOnly, and returnDirect. operation is also
// required unless derived from an aa:apex-, fa:flow-, or pr: identifier. apiSource
// defaults to API_CATALOG and toolName defaults to operation. Non-empty toolTitle
// and descriptionOverride values are required. Unknown fields are rejected.
//
// Existing uiResource links survive tool updates; widget linkage is not a JSON input.
// Existing tools, prompts, and resources are preserved. --dry-run prints without
// writing; --skip-existing preserves already-bound entries. stderr receives a
// JSON summary of tool and prompt changes.
//
// This is a minimal, dependency-free XML reader/writer scoped to the flat,
// single-namespace, non-mixed-content shape of Salesforce metadata XML — not a
// general-purpose parser.
import fs from "node:fs";

const DOC = `Merge tools into McpServerDefinition metadata by apiIdentifier.

Usage:
    node merge_tools.mjs <SERVER_META_XML> <TOOLS_JSON> [--dry-run] [--skip-existing]

SERVER_META_XML is modified in place. TOOLS_JSON accepts one tool, an array,
or { tools: [...], prompts: [...] }; use '-' for stdin. Each tool requires
apiIdentifier and the five JSON booleans
destructive, idempotent, openWorld, readOnly, and returnDirect. operation is also
required unless derived from an aa:apex-, fa:flow-, or pr: identifier. apiSource
defaults to API_CATALOG and toolName defaults to operation. Non-empty toolTitle
and descriptionOverride values are required. Unknown fields are rejected.

Each prompt requires promptName, promptTemplateName, promptTitle, and
descriptionOverride. Existing tools, prompts, and resources are preserved.
--dry-run prints without writing; --skip-existing preserves already-bound
entries. stderr receives a JSON summary of tool and prompt changes.`;

const API_DEF_ORDER = ["apiIdentifier", "apiSource", "operation"];
const BOOL_FIELDS = ["destructive", "idempotent", "openWorld", "readOnly", "returnDirect"];
const REQUIRED_TEXT_FIELDS = ["descriptionOverride", "toolTitle"];
const LIVE_PREFIXES = ["aa:apex-", "fa:flow-", "pr:"];
const PROMPT_FIELDS = ["descriptionOverride", "promptName", "promptTemplateName", "promptTitle"];
const ALLOWED_KEYS = new Set([
  "apiIdentifier",
  "apiSource",
  "operation",
  "toolName",
  "toolTitle",
  "descriptionOverride",
  ...BOOL_FIELDS,
]);

// --- minimal XML parser/serializer, scoped to Salesforce metadata XML shape ---

function decodeEntities(s) {
  return s.replace(/&(amp|lt|gt|quot|apos);/g, (_, e) => ({ amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" }[e]));
}

function parseXml(text) {
  let i = 0;
  const n = text.length;

  function skipWs() {
    while (i < n && /\s/.test(text[i])) i++;
  }

  function parseElement() {
    skipWs();
    if (text[i] !== "<") throw new Error(`expected '<' at offset ${i}`);
    i++;
    const tagStart = i;
    while (i < n && !/[\s>/]/.test(text[i])) i++;
    const tag = text.slice(tagStart, i);
    const attrs = {};
    while (true) {
      skipWs();
      if (text[i] === "/" && text[i + 1] === ">") {
        i += 2;
        return { tag, attrs, children: [], text: null };
      }
      if (text[i] === ">") {
        i++;
        break;
      }
      const nameStart = i;
      while (i < n && text[i] !== "=" && !/\s/.test(text[i])) i++;
      const name = text.slice(nameStart, i);
      skipWs();
      if (text[i] === "=") {
        i++;
        skipWs();
        const quote = text[i];
        i++;
        const valStart = i;
        while (i < n && text[i] !== quote) i++;
        attrs[name] = decodeEntities(text.slice(valStart, i));
        i++;
      }
    }
    const node = { tag, attrs, children: [], text: null };
    let textBuf = "";
    while (true) {
      if (text.slice(i, i + 2) === "</") {
        i += 2;
        const closeStart = i;
        while (i < n && text[i] !== ">") i++;
        const closeTag = text.slice(closeStart, i);
        i++;
        if (closeTag !== tag) {
          throw new Error(`mismatched close tag: expected </${tag}>, got </${closeTag}>`);
        }
        break;
      } else if (text.slice(i, i + 4) === "<!--") {
        const end = text.indexOf("-->", i);
        i = end === -1 ? n : end + 3;
      } else if (text[i] === "<") {
        node.children.push(parseElement());
      } else {
        textBuf += text[i];
        i++;
      }
    }
    if (node.children.length === 0) {
      const decoded = decodeEntities(textBuf).trim();
      node.text = decoded.length ? decoded : textBuf.length ? "" : null;
    }
    return node;
  }

  skipWs();
  if (text.slice(i, i + 2) === "<?") {
    const end = text.indexOf("?>", i);
    i = end === -1 ? i : end + 2;
  }
  return parseElement();
}

function escapeText(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function escapeAttr(s) {
  return escapeText(s).replace(/"/g, "&quot;");
}

function serializeNode(node, depth) {
  const indent = "    ".repeat(depth);
  const attrs = Object.entries(node.attrs || {})
    .map(([k, v]) => ` ${k}="${escapeAttr(v)}"`)
    .join("");
  if (node.children && node.children.length) {
    const inner = node.children.map((c) => serializeNode(c, depth + 1)).join("\n");
    return `${indent}<${node.tag}${attrs}>\n${inner}\n${indent}</${node.tag}>`;
  }
  const text = node.text == null ? "" : escapeText(node.text);
  return `${indent}<${node.tag}${attrs}>${text}</${node.tag}>`;
}

function serialize(root) {
  return '<?xml version="1.0" encoding="UTF-8"?>\n' + serializeNode(root, 0) + "\n";
}

// --- tool-element model ---

function el(tag, { children, text } = {}) {
  return { tag, attrs: {}, children: children ?? [], text: text ?? null };
}

function deriveOperation(ident) {
  for (const p of LIVE_PREFIXES) {
    if (ident.startsWith(p)) return ident.slice(p.length);
  }
  return null;
}

function toolIdentifier(toolEl) {
  const api = toolEl.children.find((c) => c.tag === "apiDefinition");
  if (!api) return null;
  const ident = api.children.find((c) => c.tag === "apiIdentifier");
  return ident ? ident.text : null;
}

function promptIdentifier(promptEl) {
  return promptEl.children.find((c) => c.tag === "promptName")?.text ?? null;
}

function buildPromptElement(spec) {
  if (typeof spec !== "object" || spec === null || Array.isArray(spec)) {
    throw new Error("each prompt spec must be a JSON object");
  }
  const unknown = Object.keys(spec).filter((k) => !PROMPT_FIELDS.includes(k));
  if (unknown.length) throw new Error(`unknown prompt field(s) ${JSON.stringify(unknown.sort())}`);
  for (const field of PROMPT_FIELDS) {
    if (typeof spec[field] !== "string" || !spec[field].trim()) {
      throw new Error(`'${field}' is required and must be a non-empty string`);
    }
  }
  return el("prompts", {
    children: PROMPT_FIELDS.map((field) => el(field, { text: spec[field].trim() })),
  });
}

function buildToolElement(spec) {
  if (typeof spec !== "object" || spec === null || Array.isArray(spec)) {
    throw new Error(
      `each tool spec must be a JSON object, got ${spec === null ? "null" : Array.isArray(spec) ? "array" : typeof spec}`,
    );
  }
  const unknown = Object.keys(spec).filter((k) => !ALLOWED_KEYS.has(k));
  if (unknown.length) {
    throw new Error(`unknown tool field(s) ${JSON.stringify(unknown.sort())} — allowed: ${JSON.stringify([...ALLOWED_KEYS].sort())}`);
  }

  const ident = spec.apiIdentifier;
  if (!ident || typeof ident !== "string") {
    throw new Error(`tool spec missing valid string 'apiIdentifier': ${JSON.stringify(spec)}`);
  }

  let operation = spec.operation;
  if (operation === undefined || operation === null) {
    operation = deriveOperation(ident);
    if (operation === null) {
      throw new Error(
        `'operation' is required for '${ident}' — only derivable for aa:apex-<X>/fa:flow-<X>/pr:<X> ids`,
      );
    }
  }
  if (typeof operation !== "string" || !operation.trim()) {
    throw new Error(`'operation' must be a non-empty string: ${JSON.stringify(operation)}`);
  }
  operation = operation.trim();

  for (const name of REQUIRED_TEXT_FIELDS) {
    const value = spec[name];
    if (typeof value !== "string" || !value.trim()) {
      throw new Error(`'${name}' is required and must be a non-empty string`);
    }
  }

  let toolName = spec.toolName ?? operation;
  if (typeof toolName !== "string" || !toolName.trim()) {
    throw new Error(`'toolName' must be a non-empty string: ${JSON.stringify(toolName)}`);
  }
  toolName = toolName.trim();

  for (const name of BOOL_FIELDS) {
    if (!(name in spec)) {
      throw new Error(
        `'${name}' is required — set all five behavior booleans explicitly (${BOOL_FIELDS.join(", ")}); don't blind-default them`,
      );
    }
    if (typeof spec[name] !== "boolean") {
      throw new Error(`'${name}' must be a JSON boolean (true/false), got ${typeof spec[name]}: ${JSON.stringify(spec[name])}`);
    }
  }

  if (spec.readOnly === spec.destructive) {
    throw new Error("writes (including create, update, upsert and delete) require readOnly: false and destructive: true; reads require readOnly: true and destructive: false");
  }

  const apiDefValues = { apiIdentifier: ident, apiSource: spec.apiSource ?? "API_CATALOG", operation };
  const apiDef = el("apiDefinition", { children: API_DEF_ORDER.map((name) => el(name, { text: apiDefValues[name] })) });

  const children = [apiDef, el("descriptionOverride", { text: spec.descriptionOverride.trim() })];
  for (const name of BOOL_FIELDS) children.push(el(name, { text: spec[name] ? "true" : "false" }));
  children.push(el("toolName", { text: toolName }));
  children.push(el("toolTitle", { text: spec.toolTitle.trim() }));

  return el("tools", { children });
}

function reorderRoot(root) {
  root.children = [...root.children].sort((a, b) => (a.tag < b.tag ? -1 : a.tag > b.tag ? 1 : 0));
}

// --- main ---

function main() {
  const positional = process.argv.slice(2).filter((a) => !a.startsWith("--"));
  const flags = new Set(process.argv.slice(2).filter((a) => a.startsWith("--")));
  const unknownFlags = [...flags].filter((f) => f !== "--dry-run" && f !== "--skip-existing");
  if (unknownFlags.length) {
    throw new Error(`unknown option(s) ${JSON.stringify(unknownFlags.sort())} — allowed: --dry-run, --skip-existing`);
  }
  if (positional.length !== 2) {
    console.log(DOC);
    process.exit(1);
  }
  const [xmlPath, toolsArg] = positional;
  const dryRun = flags.has("--dry-run");
  const skipExisting = flags.has("--skip-existing");

  const raw = toolsArg === "-" ? fs.readFileSync(0, "utf-8") : fs.readFileSync(toolsArg, "utf-8");
  const input = JSON.parse(raw);
  let toolSpecs;
  let promptSpecs;
  if (Array.isArray(input)) {
    toolSpecs = input;
    promptSpecs = [];
  } else if (input && typeof input === "object" && ("tools" in input || "prompts" in input)) {
    const unknown = Object.keys(input).filter((k) => k !== "tools" && k !== "prompts");
    if (unknown.length) throw new Error(`unknown binding group(s) ${JSON.stringify(unknown.sort())}`);
    toolSpecs = input.tools ?? [];
    promptSpecs = input.prompts ?? [];
    if (!Array.isArray(toolSpecs) || !Array.isArray(promptSpecs)) {
      throw new Error("'tools' and 'prompts' must be arrays");
    }
  } else {
    toolSpecs = [input];
    promptSpecs = [];
  }

  const xmlText = fs.readFileSync(xmlPath, "utf-8");
  const root = parseXml(xmlText);

  const summary = { added: [], updated: [], skipped: [], deduped_existing: [], total_tools: 0, prompts_added: [], prompts_updated: [], prompts_skipped: [], prompts_deduped_existing: [], total_prompts: 0 };

  const existingTools = root.children.filter((c) => c.tag === "tools");
  const existingPrompts = root.children.filter((c) => c.tag === "prompts");
  root.children = root.children.filter((c) => c.tag !== "tools" && c.tag !== "prompts");

  const byId = new Map();
  const order = [];
  for (const t of existingTools) {
    const ident = toolIdentifier(t);
    if (!ident) throw new Error("existing <tools> block is missing apiDefinition/apiIdentifier");
    if (byId.has(ident)) summary.deduped_existing.push(ident);
    else order.push(ident);
    byId.set(ident, t);
  }
  const originalIds = new Set(byId.keys());

  for (const spec of toolSpecs) {
    const newEl = buildToolElement(spec);
    const ident = spec.apiIdentifier;
    if (originalIds.has(ident)) {
      if (skipExisting) {
        summary.skipped.push(ident);
        continue;
      }
      summary.updated.push(ident);
    } else if (byId.has(ident)) {
      summary.updated.push(ident);
    } else {
      summary.added.push(ident);
      order.push(ident);
    }
    // Rebuilding behavior fields must not detach a previously linked widget.
    const uiResource = byId.get(ident)?.children.find((c) => c.tag === "uiResource");
    if (uiResource) newEl.children.push(uiResource);
    byId.set(ident, newEl);
  }

  for (const ident of order) root.children.push(byId.get(ident));

  const promptsByName = new Map();
  const promptOrder = [];
  for (const prompt of existingPrompts) {
    const name = promptIdentifier(prompt);
    if (!name) throw new Error("existing <prompts> block is missing promptName");
    if (promptsByName.has(name)) summary.prompts_deduped_existing.push(name);
    else promptOrder.push(name);
    promptsByName.set(name, prompt);
  }
  const originalPromptNames = new Set(promptsByName.keys());
  for (const spec of promptSpecs) {
    const prompt = buildPromptElement(spec);
    const name = spec.promptName.trim();
    if (originalPromptNames.has(name)) {
      if (skipExisting) {
        summary.prompts_skipped.push(name);
        continue;
      }
      summary.prompts_updated.push(name);
    } else if (promptsByName.has(name)) {
      summary.prompts_updated.push(name);
    } else {
      summary.prompts_added.push(name);
      promptOrder.push(name);
    }
    promptsByName.set(name, prompt);
  }
  for (const name of promptOrder) root.children.push(promptsByName.get(name));
  reorderRoot(root);
  summary.total_tools = root.children.filter((c) => c.tag === "tools").length;
  summary.total_prompts = root.children.filter((c) => c.tag === "prompts").length;

  const output = serialize(root);
  if (dryRun) {
    process.stdout.write(output);
  } else {
    fs.writeFileSync(xmlPath, output, "utf-8");
  }
  process.stderr.write(JSON.stringify(summary) + "\n");
}

try {
  main();
} catch (e) {
  process.stderr.write(`ERROR: ${e.message}\n`);
  process.exit(1);
}
