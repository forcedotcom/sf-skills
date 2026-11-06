#!/usr/bin/env node
// Render the McpServerDefinition metadata component into the current SFDX
// project. Approved tools and prompts are merged into the rendered file
// before deploy — see references/mcp-objects.md.
//
// Usage: node render_mcp_server.mjs <METADATA_DIR> <SERVER_DEV_NAME> <SERVER_LABEL> <SERVER_DESC>
//
// METADATA_DIR is <default-package>/main/default, passed by the skill.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { isValidDeveloperName } from "./utils/developer_name.mjs";
import { requireProjectDestination } from "./utils/metadata_path.mjs";

function fail(msg) {
  process.stderr.write(msg + "\n");
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length !== 4) {
  fail("Usage: render_mcp_server.mjs <METADATA_DIR> <SERVER_DEV_NAME> <SERVER_LABEL> <SERVER_DESC>");
}
const [metadataDirArg, serverName, serverLabel, serverDesc] = args;

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const template = path.join(scriptDir, "..", "assets", "__MCP_SERVER_NAME__.mcpServerDefinition-meta.xml");
const projectRoot = path.resolve(process.cwd());
const metadataDir = path.resolve(projectRoot, metadataDirArg);
if (metadataDir !== projectRoot && !metadataDir.startsWith(projectRoot + path.sep)) {
  fail(`ABORT: metadata directory '${metadataDirArg}' escapes the project root`);
}

// DeveloperName is used in the filename, so validate it before constructing paths.
if (!isValidDeveloperName(serverName) || serverName.length < 2 || serverName.length > 60) {
  fail(
    `Invalid MCP server name '${serverName}': start with a letter, use letters, digits, or single underscores, optional namespace__ prefix, 2–60 chars.`,
  );
}

const destDir = path.join(metadataDir, "mcpServerDefinitions");
const dest = path.join(destDir, `${serverName}.mcpServerDefinition-meta.xml`);
try {
  requireProjectDestination(projectRoot, dest);
} catch {
  fail("ABORT: metadata destination is unreadable or resolves outside the project root");
}
if (fs.lstatSync(dest, { throwIfNoEntry: false })) {
  fail(`Refuse to overwrite existing file: ${dest}`);
}

fs.mkdirSync(destDir, { recursive: true });

function escapeXml(s) {
  return String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

// Escape free-text values while substituting the template.
let text = fs.readFileSync(template, "utf-8");
text = text.split("__MCP_SERVER_LABEL__").join(escapeXml(serverLabel));
text = text.split("__MCP_SERVER_DESC__").join(escapeXml(serverDesc));
fs.writeFileSync(dest, text, "utf-8");

console.log(`Rendered MCP server component at ${dest}`);
