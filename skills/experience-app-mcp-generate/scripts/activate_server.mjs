#!/usr/bin/env node
// Activate a deployed MCP server by setting Tooling McpServerAccess.Active=true.
// Output the re-queried state so active=true signals successful activation.
//
// Usage: node activate_server.mjs <TARGET_ORG_ALIAS> <SERVER_DEVELOPER_NAME> [--confirm]
//
//   default   : resolve, query, and print the proposed action without writing.
//   --confirm : perform that Tooling write.
//
// Output: a JSON object on stdout with the server state and plannedRequest.
// plannedRequest is the write preview when --confirm is omitted, and null after a write.
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { isValidDeveloperName } from "./utils/developer_name.mjs";

function fail(msg, code = 1) {
  process.stderr.write(msg + "\n");
  process.exit(code);
}

const positional = [];
let confirm = false;
for (const arg of process.argv.slice(2)) {
  if (arg === "--confirm") {
    confirm = true;
  } else if (arg.startsWith("--")) {
    fail(`ABORT: unknown option '${arg}' — the only option is --confirm, which performs the write. The default previews it.`);
  } else {
    positional.push(arg);
  }
}
const [targetOrg, serverName, extra] = positional;
if (!targetOrg) fail("ABORT: target org alias required");
if (!serverName) fail("ABORT: McpServerDefinition DeveloperName required");
if (extra !== undefined) {
  fail("ABORT: too many arguments — usage: activate_server.mjs <org> <ServerDevName> [--confirm]");
}

// SERVER_NAME is embedded in SOQL.
if (!isValidDeveloperName(serverName)) {
  fail(
    `ABORT: invalid DeveloperName '${serverName}' — letters/digits/single underscores, optional namespace__ prefix, start with a letter, <= 80 chars.`,
  );
}

const V = JSON.parse(fs.readFileSync("sfdx-project.json", "utf-8")).sourceApiVersion;

function sf(argv) {
  return execFileSync("sf", argv, { encoding: "utf-8" });
}

let disp;
try {
  disp = JSON.parse(sf(["org", "display", "--target-org", targetOrg, "--json"]));
} catch {
  disp = null;
}
const instanceUrl = disp?.result?.instanceUrl ?? "";
if (!instanceUrl) fail(`ABORT: could not read org connection for ${targetOrg}`);

const toolingPath = `/services/data/v${V}/tooling`;
const toolingUrl = `${instanceUrl}${toolingPath}`;

function toolingQuery(soql) {
  const encoded = encodeURIComponent(soql);
  try {
    return sf(["api", "request", "rest", `${toolingPath}/query?q=${encoded}`, "--target-org", targetOrg, "--method", "GET"]);
  } catch {
    fail("ABORT: authenticated Tooling query failed.");
  }
}

// A malformed successful response must not fall through to a write.
function requireRecords(jsonText, label) {
  let parsed;
  try {
    parsed = JSON.parse(jsonText);
  } catch {
    parsed = null;
  }
  if (!parsed || !Array.isArray(parsed.records)) {
    fail(`ABORT: malformed ${label} query response (no .records array) — failing closed before any write.`);
  }
  return parsed;
}

let mcpId, accessId, active;

// Propagate query failures out before any write.
function readAccess() {
  const json = toolingQuery(`SELECT Id,Active FROM McpServerAccess WHERE McpServerId='${mcpId}'`);
  const parsed = requireRecords(json, "McpServerAccess");
  accessId = parsed.records[0]?.Id ?? "";
  active = String(parsed.records[0]?.Active ?? "");
}

const mcpJson = requireRecords(
  toolingQuery(`SELECT Id FROM McpServerDefinition WHERE DeveloperName='${serverName}'`),
  "McpServerDefinition",
);
mcpId = mcpJson.records[0]?.Id ?? "";
if (!mcpId) {
  fail(`ABORT: no McpServerDefinition named '${serverName}' — deploy the prepared metadata before activating.`);
}

readAccess();

function emit(action, activeVal, method = "", url = "", body = null) {
  return JSON.stringify({
    mcpServerId: mcpId,
    accessId: accessId ?? "",
    action,
    active: activeVal === "true",
    plannedRequest: method === "" ? null : { method, url, body },
  });
}

if (accessId && active === "true") {
  console.log(emit("already_active", "true"));
  process.exit(0);
}

if (!confirm) {
  if (!accessId) {
    const payload = { DeveloperName: serverName, MasterLabel: serverName, Active: true, McpServerId: mcpId };
    console.log(emit("would_create", "false", "POST", `${toolingUrl}/sobjects/McpServerAccess`, payload));
  } else {
    console.log(
      emit("would_activate", "false", "PATCH", `${toolingUrl}/sobjects/McpServerAccess/${accessId}`, { Active: true }),
    );
  }
  process.exit(0);
}

function toolingWrite(method, urlPath, data) {
  try {
    sf(["api", "request", "rest", urlPath, "--target-org", targetOrg, "--method", method, "--body", JSON.stringify(data)]);
  } catch {
    fail(`ABORT: authenticated Tooling ${method} failed.`);
  }
}

let did = "";
if (!accessId) {
  const payload = { DeveloperName: serverName, MasterLabel: serverName, Active: true, McpServerId: mcpId };
  toolingWrite("POST", `${toolingPath}/sobjects/McpServerAccess`, payload);
  readAccess();
  did = "created";
  if (!accessId) {
    fail(`ABORT: no McpServerAccess row exists after the create attempt for '${serverName}'.`);
  }
}

if (active !== "true") {
  toolingWrite("PATCH", `${toolingPath}/sobjects/McpServerAccess/${accessId}`, { Active: true });
  did = "activated";
}

readAccess();
if (active !== "true") {
  process.stderr.write(`ABORT: wrote access row but Active is still '${active}' — activation failed.\n`);
  process.stderr.write(emit(did, active) + "\n");
  process.exit(1);
}

console.log(emit(did, "true"));
