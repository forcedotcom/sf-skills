#!/usr/bin/env node
// Read the deployed MCP server, bound tools, and activation state. Read-only.
//
// Usage: node verify_server.mjs <TARGET_ORG_ALIAS> <SERVER_DEVELOPER_NAME> [--json]
//
//   --json : emit one JSON object instead of the human-readable table.
//
// Exit: 0 when verification ran; read `status` (ready | not_found | inactive | no_tools)
// and `ready`. 1 on connection, query, or argument error.
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { isValidDeveloperName } from "./utils/developer_name.mjs";

function fail(msg, code = 1) {
  process.stderr.write(msg + "\n");
  process.exit(code);
}

const [targetOrg, serverName, opt, extra] = process.argv.slice(2);
if (!targetOrg) fail("ABORT: target org alias required");
if (!serverName) fail("ABORT: McpServerDefinition DeveloperName required");
if (extra !== undefined) {
  fail("ABORT: too many arguments — usage: verify_server.mjs <org> <ServerDevName> [--json]");
}
let asJson = false;
if (opt !== undefined) {
  if (opt === "--json") asJson = true;
  else fail(`ABORT: unknown option '${opt}' — the only supported option is --json.`);
}

// SERVER_NAME is embedded in SOQL.
if (!isValidDeveloperName(serverName)) {
  fail(
    `ABORT: invalid DeveloperName '${serverName}' — letters/digits/single underscores, optional namespace__ prefix, start with a letter, <= 80 chars.`,
  );
}

const V = JSON.parse(fs.readFileSync("sfdx-project.json", "utf-8")).sourceApiVersion;
const toolingPath = `/services/data/v${V}/tooling`;

function toolingQuery(soql) {
  const encoded = encodeURIComponent(soql);
  try {
    return execFileSync(
      "sf",
      ["api", "request", "rest", `${toolingPath}/query?q=${encoded}`, "--target-org", targetOrg, "--method", "GET"],
      { encoding: "utf-8" },
    );
  } catch {
    fail("ABORT: authenticated Tooling query failed.");
  }
}

// Fail on a malformed 200 rather than misreport an empty tree.
function requireRecords(jsonText, label) {
  let parsed;
  try {
    parsed = JSON.parse(jsonText);
  } catch {
    parsed = null;
  }
  if (!parsed || !Array.isArray(parsed.records)) {
    fail(`ABORT: malformed ${label} query response (no .records array).`);
  }
  return parsed;
}

const mcpJson = requireRecords(
  toolingQuery(`SELECT Id,DeveloperName,MasterLabel FROM McpServerDefinition WHERE DeveloperName='${serverName}'`),
  "McpServerDefinition",
);
const mcpId = mcpJson.records[0]?.Id ?? "";
if (!mcpId) {
  if (asJson) {
    console.log(JSON.stringify({ status: "not_found", ready: false, developerName: serverName }));
  } else {
    console.log(`NOT FOUND: no McpServerDefinition named '${serverName}' in ${targetOrg}.`);
  }
  process.exit(0);
}

const toolsJson = requireRecords(
  toolingQuery(`SELECT ToolName,ToolTitle FROM McpServerToolDefinition WHERE McpServerId='${mcpId}'`),
  "McpServerToolDefinition",
);
const accessJson = requireRecords(
  toolingQuery(`SELECT Active FROM McpServerAccess WHERE McpServerId='${mcpId}'`),
  "McpServerAccess",
);
const toolCount = toolsJson.records.length;
const active = String(accessJson.records[0]?.Active ?? "false");
const status = active !== "true" ? "inactive" : toolCount === 0 ? "no_tools" : "ready";

if (asJson) {
  console.log(
    JSON.stringify({
      status,
      ready: status === "ready",
      mcpServerId: mcpId,
      developerName: serverName,
      active: active === "true",
      toolCount,
      tools: toolsJson.records.map((r) => ({ toolName: r.ToolName, toolTitle: r.ToolTitle })),
    }),
  );
} else {
  console.log(`McpServerDefinition : ${serverName} (${mcpId})`);
  console.log(`McpServerAccess.Active : ${active}`);
  console.log(`Bound tools (${toolCount}):`);
  for (const r of toolsJson.records) {
    console.log(`  - ${r.ToolName}  [${r.ToolTitle ?? "-"}]`);
  }
  if (toolCount === 0) console.log("  (none — deploy created no tool rows)");
  console.log(`Status : ${status}`);
}

// Readiness (exists + active + at least one tool) is reported via `status`, not the exit code.
process.exit(0);
