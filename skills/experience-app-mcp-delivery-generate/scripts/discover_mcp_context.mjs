#!/usr/bin/env node
// Read-only inventory. Never print the full org-display response: it contains
// an access token. Only selected non-secret fields leave this process.
import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { isValidDeveloperName } from "./developer_name.mjs";

function sfJson(args) {
  return JSON.parse(execFileSync("sf", args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"] }));
}

function normalizeSalesforceId(id) {
  return typeof id === "string" && /^[A-Za-z0-9]{15}(?:[A-Za-z0-9]{3})?$/.test(id) ? id.slice(0, 15) : null;
}

// Enhanced-domain instance hosts encode both the routing token and the environment.
const HOST_PATTERNS = [
  [/^([a-z0-9-]+--[a-z0-9]+)\.sandbox\.my\.salesforce\.com$/i, "sandbox"],
  [/^([a-z0-9-]+)\.develop\.my\.salesforce\.com$/i, "developer"],
  [/^([a-z0-9-]+)\.scratch\.my\.salesforce\.com$/i, "scratch"],
  [/^([a-z0-9-]+)\.my\.salesforce\.com$/i, "production"],
];

function domainFromHost(hostname) {
  for (const [pattern, hostEnvironment] of HOST_PATTERNS) {
    const match = hostname.match(pattern);
    if (match) return { value: match[1].toLowerCase(), hostEnvironment };
  }
  return null;
}

// Scratch orgs report IsSandbox and carry a trial expiration; production trials do not report IsSandbox.
function classifyOrg({ IsSandbox, TrialExpirationDate, OrganizationType }) {
  if (IsSandbox && TrialExpirationDate != null) return "scratch";
  if (IsSandbox) return "sandbox";
  if (typeof OrganizationType === "string" && OrganizationType.toLowerCase().includes("developer")) return "developer";
  return "production";
}

function main() {
  const [targetOrg, serverName, ...extra] = process.argv.slice(2);
  if (!targetOrg || targetOrg.startsWith("-") || extra.length || (serverName && !isValidDeveloperName(serverName))) {
    throw new Error("Usage: discover_mcp_context.mjs <target-org-alias> [SERVER_DEV_NAME]");
  }
  const { sourceApiVersion: apiVersion } = JSON.parse(fs.readFileSync("sfdx-project.json", "utf8"));
  if (!/^\d{2,3}\.0$/.test(apiVersion)) throw new Error("SFDX project sourceApiVersion is missing or invalid");
  let displayed;
  try { displayed = sfJson(["org", "display", "--target-org", targetOrg, "--json"]); }
  catch { throw new Error("Org lookup failed; authenticate the selected org with sf before retrying"); }
  if (displayed.status !== 0 || !displayed.result?.instanceUrl || !displayed.result?.id) throw new Error("Org lookup returned an unrecognized response");
  const instance = new URL(displayed.result.instanceUrl);
  if (instance.protocol !== "https:" || instance.username || instance.password) throw new Error("Org instance URL is invalid");
  const domain = domainFromHost(instance.hostname);
  const errors = [];
  function listNetworkMetadata() {
    try {
      const response = sfJson([
        "org", "list", "metadata", "--metadata-type", "Network",
        "--target-org", targetOrg, "--api-version", apiVersion, "--json",
      ]);
      if (response.status !== 0 || !Array.isArray(response.result) ||
          response.result.some((record) => typeof record.fullName !== "string" || !record.fullName)) {
        throw new Error();
      }
      return response.result.map(({ id, fullName }) => ({ id, fullName }));
    } catch {
      errors.push("Network Metadata API lookup failed or returned incomplete results; this does not prove absence");
      return null;
    }
  }
  function query(label, soql, tooling, fields) {
    try {
      const args = ["data", "query", "--query", soql, "--target-org", targetOrg, "--api-version", apiVersion, "--json"];
      if (tooling) args.push("--use-tooling-api");
      const response = sfJson(args);
      if (response.status !== 0 || !Array.isArray(response.result?.records) || response.result.totalSize !== response.result.records.length) throw new Error();
      return response.result.records.map((record) => Object.fromEntries(fields.map((field) => [field, record[field]])));
    } catch {
      errors.push(`${label} lookup failed or returned incomplete results; this does not prove absence`);
      return null;
    }
  }
  const orgs = query("Org environment", "SELECT IsSandbox, TrialExpirationDate, OrganizationType FROM Organization", false, ["IsSandbox", "TrialExpirationDate", "OrganizationType"]);
  const environment = orgs?.length === 1 ? { value: classifyOrg(orgs[0]), source: "Organization query" } : null;
  if (orgs && orgs.length !== 1) errors.push("Org environment lookup returned no single Organization record");
  const servers = query("MCP server", `SELECT Id, DeveloperName, MasterLabel FROM McpServerDefinition${serverName ? ` WHERE DeveloperName = '${serverName}'` : ""}`, true, ["Id", "DeveloperName", "MasterLabel"]);
  const serverAccess = query("MCP activation", "SELECT Id, McpServerId, Active FROM McpServerAccess", true, ["Id", "McpServerId", "Active"]);
  const networkMetadata = listNetworkMetadata();
  const sites = query("Experience Site", "SELECT Id, Name, UrlPathPrefix FROM Network", false, ["Id", "Name", "UrlPathPrefix"]);
  const siteDeveloperNames = new Map(
    (networkMetadata ?? []).map((record) => [normalizeSalesforceId(record.id), record.fullName])
      .filter(([id]) => id !== null),
  );
  const sitesWithDeveloperNames = sites?.map((site) => ({
    ...site,
    DeveloperName: siteDeveloperNames.get(normalizeSalesforceId(site.Id)) ?? null,
  }));
  const ecas = query("ECA", "SELECT Id, DeveloperName FROM ExternalClientApplication", false, ["Id", "DeveloperName"]);
  console.log(JSON.stringify({
    status: errors.length ? "incomplete" : "discovered",
    targetOrg, apiVersion,
    org: { id: displayed.result.id, instanceUrl: instance.origin },
    environment,
    domainCandidate: domain ? { ...domain, source: "selected org instance hostname", routingVerified: false } : null,
    servers, serverAccess, sites: sitesWithDeveloperNames,
    networkMetadataFullNames: networkMetadata?.map((record) => record.fullName) ?? null,
    ecas, errors,
  }, null, 2));
}

try { main(); } catch (error) {
  console.log(JSON.stringify({ status: "blocked", error: error.message }, null, 2));
  process.exitCode = 1;
}
