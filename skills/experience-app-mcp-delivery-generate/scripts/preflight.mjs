#!/usr/bin/env node
// Run from the SFDX project root; read the JSON `decision`. Exit 0 = decision reached (incl. skip, needs_input); exit 1 = error.
// Usage: node preflight.mjs <target-org-alias> --skill-named <true|false>
import fs from "node:fs";
import { execFileSync } from "node:child_process";

const [org, option, skillNamed, ...extra] = process.argv.slice(2);
const requestNamesSkill = skillNamed === "true";
let gatePassed = false;

function finish(report, code = 0) {
  console.log(JSON.stringify(report));
  process.exit(code);
}

function skip(disabled = false) {
  finish({
    decision: disabled && requestNamesSkill ? "disabled" : "skip",
    nextAction: "continue_without_this_skill",
    userMessage: disabled && requestNamesSkill ? "The App MCP skill is not enabled for this org." : null,
  });
}

function problem(errorCode, userMessage, nextAction, needsInput = false) {
  if (!needsInput && !gatePassed && !requestNamesSkill) skip();
  finish({ decision: needsInput ? "needs_input" : "error", errorCode, userMessage, nextAction, gatePassed }, needsInput ? 0 : 1);
}

if (!org || org.startsWith("--") || option !== "--skill-named" ||
    !["true", "false"].includes(skillNamed) || extra.length) {
  problem("invalid_arguments", "Provide a target org alias and --skill-named true or false.", "Correct the preflight arguments.", true);
}

let project;
try {
  project = JSON.parse(fs.readFileSync("sfdx-project.json", "utf8"));
} catch {
  problem("invalid_project", "Could not read sfdx-project.json.", "Select a valid SFDX project root, then rerun preflight.");
}
const version = project?.sourceApiVersion;
if (typeof version !== "string" || !/^\d+\.\d+$/.test(version) || Number(version) < 68) {
  problem("invalid_api_version", "sfdx-project.json sourceApiVersion must use X.Y format and be at least 68.0.",
    "Ask the user to correct sourceApiVersion to an org-supported version, then rerun preflight.", true);
}

function sf(args) {
  let output;
  let failed = false;
  try {
    output = execFileSync("sf", args, {
      encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], timeout: 30000,
    });
  } catch (error) {
    output = error.stdout ?? "";
    failed = true;
  }
  let response;
  try {
    response = JSON.parse(output);
  } catch {
    return { failed: true, response: null };
  }
  if (response?.name === "NamedOrgNotFoundError" || response?.code === "NamedOrgNotFoundError") {
    problem("invalid_org_alias", "No authenticated org matches the target org alias.",
      "Ask the user for a valid authenticated org alias, then rerun preflight.", true);
  }
  return { failed, response };
}

const versionsResult = sf(["api", "request", "rest", "/services/data/",
  "--target-org", org, "--method", "GET", "--json"]);
const versions = versionsResult.response?.result?.body;
if (versionsResult.failed || versionsResult.response?.status !== 0 ||
    versionsResult.response?.result?.statusCode !== 200 || !Array.isArray(versions) || !versions.length ||
    !versions.every((entry) => typeof entry?.version === "string" && /^\d+\.\d+$/.test(entry.version))) {
  problem("gate_check_failed", "Could not determine the target org's supported API versions.",
    "Check target-org authentication and connectivity, then rerun preflight.");
}
const compatibleVersions = versions.filter((entry) => Number(entry.version) >= 68).map((entry) => entry.version);
if (!compatibleVersions.length) {
  problem("invalid_api_version", "The target org does not advertise an API version of at least 68.0.",
    "Ask the user for an org alias supporting API 68.0 or later, then rerun preflight.", true);
}
if (!compatibleVersions.includes(version)) {
  problem("invalid_api_version", "sfdx-project.json sourceApiVersion is not supported by the target org.",
    "Ask the user to select a supported sourceApiVersion of at least 68.0 from: " +
    compatibleVersions.join(", ") +
    ". Then rerun preflight.", true);
}

const gateResult = sf(["api", "request", "rest", `/services/data/v${version}/headless/invocableaction`,
  "--target-org", org, "--method", "POST", "--body",
  JSON.stringify({ action: "getExperienceAppMcpMetadata-getExperienceAppMcpMetadata", inputs: {} }), "--json"]);
const gate = gateResult.response;
const body = gate?.result?.body;
if (gate?.result?.statusCode === 400 && Array.isArray(body) &&
    body.some((error) => error?.errorCode === "INVALID_INPUT")) skip(true);
const unsupportedGateActionMessage = /Unsupported action type: GET_EXPERIENCE_APP_MCP_METADATA(?![A-Za-z0-9_])/;
if (Array.isArray(body) && body.some((error) =>
    typeof error?.message === "string" && unsupportedGateActionMessage.test(error.message))) skip(true);
if (gateResult.failed || gate?.status !== 0 || gate?.result?.statusCode !== 200 ||
    typeof body?.outputs?.isAppMcpEnabled !== "boolean") {
  problem("gate_check_failed", "Could not verify whether the App MCP skill is enabled.",
    "Check target-org authentication and connectivity, then rerun preflight.");
}
if (!body.outputs.isAppMcpEnabled) skip(true);
gatePassed = true;

finish({ decision: "continue" });
