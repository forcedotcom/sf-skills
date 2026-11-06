#!/usr/bin/env node
// List MCP candidates from active Prompt Builder templates and runtime actions.
// Usage: node retrieve_existing_prompts.mjs <target-org-alias>
import fs from "node:fs";
import { execFileSync } from "node:child_process";

function fail(message) {
  process.stderr.write(`ERROR: ${message}\n`);
  process.exit(1);
}

const args = process.argv.slice(2);
if (args.length !== 1) fail("usage: retrieve_existing_prompts.mjs <target-org-alias>");
const [targetOrg] = args;
const apiVersion = JSON.parse(fs.readFileSync("sfdx-project.json", "utf-8")).sourceApiVersion;
const base = `/services/data/v${apiVersion}`;

function sfJson(args, label) {
  let raw;
  try {
    raw = execFileSync("sf", args, {
      encoding: "utf-8",
      stdio: ["ignore", "pipe", "pipe"],
    });
  } catch (error) {
    fail(`${label} failed: ${error.stderr?.trim() || error.message}`);
  }
  try {
    return JSON.parse(raw);
  } catch (error) {
    fail(`${label} returned invalid JSON: ${error.message}`);
  }
}

function get(url) {
  return sfJson(["api", "request", "rest", url, "--target-org", targetOrg, "--method", "GET"],
    `prompt discovery request: ${url}`);
}

function fieldValue(template, name) {
  return template.fields[name].value;
}

const templates = [];
let offset = 0;
while (true) {
  const url = `${base}/einstein/prompt-templates?isActive=true&pageLimit=50&offset=${offset}`;
  const page = get(url);
  if (!Array.isArray(page.promptRecords) || typeof page.hasMoreRecords !== "boolean" ||
      !page.promptRecords.every((record) => typeof record.apiName === "string" &&
        typeof record.fields?.Type?.value === "string" &&
        typeof record.fields?.DeveloperName?.value === "string")) {
    fail(`prompt template list returned an unrecognized response: ${url}`);
  }
  templates.push(...page.promptRecords);
  if (!page.hasMoreRecords) break;
  if (page.promptRecords.length === 0) fail("prompt template list reports more records but returned an empty page");
  offset += page.promptRecords.length;
}

const actionUrl = `${base}/actions/custom/generatePromptResponse`;
const actionList = get(actionUrl);
let actions = actionList.actions;
if (actions && !Array.isArray(actions) && typeof actions === "object") {
  actions = Object.entries(actions).map(([name, action]) => {
    if (!action || typeof action !== "object" || Array.isArray(action)) {
      fail("prompt-template action list contains an invalid action");
    }
    return {
      ...action,
      name: action.name ?? name,
      url: action.url ?? `${actionUrl}/${encodeURIComponent(name)}`,
    };
  });
}
if (!Array.isArray(actions) ||
    !actions.every((action) => typeof action.name === "string" && typeof action.url === "string")) {
  fail("prompt-template action list returned an unrecognized response");
}

const metadataList = sfJson(["org", "list", "metadata", "--metadata-type", "GenAiPromptTemplate",
  "--target-org", targetOrg, "--json"], "custom prompt metadata listing");
if (!Array.isArray(metadataList.result) ||
    !metadataList.result.every((entry) => typeof entry.fullName === "string")) {
  fail("custom prompt metadata listing returned an unrecognized response");
}

const listedNames = new Set(templates.map((template) => fieldValue(template, "DeveloperName")));
const customTemplates = metadataList.result
  .filter((entry) => !listedNames.has(entry.fullName))
  .map((entry) => get(`${base}/einstein/prompt-templates/${encodeURIComponent(entry.fullName)}`))
  .filter((template) => template.isStandard === false);
if (!customTemplates.every((template) => typeof template.fields?.Type?.value === "string" &&
    typeof template.fields?.DeveloperName?.value === "string" &&
    typeof template.fields?.MasterLabel?.value === "string")) {
  fail("custom prompt template returned an unrecognized response");
}

const publishedCustomTemplates = customTemplates
  .filter((template) => template.childRelationships?.GenAiPromptTemplateVersions?.some(
    (version) => version.fields?.Status?.value === "Published"))
  .map((template) => {
    const { Type, IsActive, MasterLabel, DeveloperName } = template.fields;
    return {
      apiName: template.apiName,
      fields: { Type, IsActive, MasterLabel, DeveloperName },
      isStandard: false,
      hasPublishedVersion: true,
    };
  });
const candidateTemplates = [...templates, ...publishedCustomTemplates];
const prompts = publishedCustomTemplates.filter((template) =>
  fieldValue(template, "Type") === "einstein_gpt__flex" && fieldValue(template, "IsActive") === true);
const inactivePublishedFlexTemplates = publishedCustomTemplates.filter((template) =>
  fieldValue(template, "Type") === "einstein_gpt__flex" && fieldValue(template, "IsActive") !== true);
const unverifiedFlexTemplates = templates.filter((template) => fieldValue(template, "Type") === "einstein_gpt__flex");
const toolTemplateNames = new Set(candidateTemplates
  .filter((template) => ["einstein_gpt__flex", "einstein_gpt__global"].includes(fieldValue(template, "Type")))
  .map((template) => fieldValue(template, "DeveloperName")));
const promptTools = actions.filter((action) => toolTemplateNames.has(action.name));
const listedActions = new Set(promptTools.map((action) => action.name));
for (const template of publishedCustomTemplates) {
  const name = fieldValue(template, "DeveloperName");
  if (!toolTemplateNames.has(name) || listedActions.has(name)) continue;
  const url = `${actionUrl}/${encodeURIComponent(name)}`;
  const action = get(url);
  if (action.name !== name || action.type !== "PROMPT_GENERATIONS") {
    fail(`prompt-template action describe returned an unrecognized response: ${url}`);
  }
  promptTools.push({ label: action.label, name, type: action.type, url });
}

console.log(JSON.stringify({
  apiVersion,
  inventoryCounts: {
    activeTemplates: templates.length,
    customTemplates: customTemplates.length,
    runtimeActions: actions.length,
  },
  candidateCounts: { prompts: prompts.length, promptTools: promptTools.length },
  prompts,
  inactivePublishedFlexTemplates,
  unverifiedFlexTemplates,
  promptTools,
}));
