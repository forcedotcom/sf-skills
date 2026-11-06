#!/usr/bin/env node
// Read-only progress observations after preflight and target selection.
// Usage: node check_setup_progress.mjs <org> <server> <eca> [--site <bundle>]
// Exit 0: audit returned, not setup completion; 2: some reads failed; 1: invalid input.
import fs from "node:fs";
import path from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { isValidDeveloperName } from "./utils/developer_name.mjs";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const checks = [];
let readFailed = false;

function check(area, status, evidence, nextAction) {
  checks.push({ area, status, evidence, nextAction });
}

function unknown(area, nextAction) {
  readFailed = true;
  check(area, "unknown", "Read failed or returned ambiguous/malformed data.", nextAction);
}

function sfJson(args) {
  return JSON.parse(execFileSync("sf", args, {
    encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], timeout: 30000,
  }));
}

function localFiles(roots, folder, file) {
  return roots.map((root) => path.join(root, folder, file))
    .filter((candidate) => fs.lstatSync(candidate, { throwIfNoEntry: false }));
}

function localPresence(area, files, expectedCount, nextAction, ambiguous = false) {
  try {
    if (files.some((file) => {
      const entry = fs.lstatSync(file);
      return !entry.isFile() || entry.size === 0;
    })) {
      throw new Error("Not a non-empty file");
    }
    const status = ambiguous || files.length > expectedCount ? "unknown" : files.length === expectedCount ? "complete" : "incomplete";
    if (status === "unknown") readFailed = true;
    check(area, status, { files, scope: "File presence only; contents and intent are unverified." }, nextAction);
  } catch {
    unknown(area, nextAction);
  }
}

function toolingQuery(apiVersion, org, query) {
  const result = sfJson(["api", "request", "rest",
    `/services/data/v${apiVersion}/tooling/query?q=${encodeURIComponent(query)}`,
    "--target-org", org, "--method", "GET"]);
  if (!Array.isArray(result?.records) || result.done !== true ||
      !Number.isInteger(result.totalSize) || result.totalSize !== result.records.length) {
    throw new Error("Incomplete query response");
  }
  return result.records;
}

function sitePresence(siteBundle) {
  const nextAction = "Phase 1: confirm the selected site's bundle and source readiness; a site is not required for org-level server checks.";
  if (!siteBundle) {
    check("site.local", "unknown", "No site bundle supplied.", nextAction);
    return;
  }
  try {
    const result = JSON.parse(execFileSync(process.execPath, [path.join(scriptDir, "list_sites.mjs")], {
      encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], timeout: 30000,
    }));
    if (!Array.isArray(result?.sites)) throw new Error("Invalid inventory");
    const sites = result.sites.filter((site) => site.bundle === siteBundle);
    if (sites.length > 1) throw new Error("Ambiguous site");
    check("site.local", sites[0]?.status === "ready" ? "complete" : "incomplete",
      { bundle: siteBundle, status: sites[0]?.status ?? "not-found", scope: "Local source readiness only." }, nextAction);
  } catch {
    unknown("site.local", nextAction);
  }
}

function ecaProgress(roots, apiVersion, org, ecaName) {
  const components = [
    ["ExternalClientApplication", "externalClientApps", ".eca-meta.xml", ""],
    ["ExtlClntAppGlobalOauthSettings", "extlClntAppGlobalOauthSets", ".ecaGlblOauth-meta.xml", ""],
    ["ExtlClntAppOauthSettings", "extlClntAppOauthSettings", ".ecaOauth-meta.xml", ""],
    ["ExtlClntAppOauthConfigurablePolicies", "extlClntAppOauthPolicies", ".ecaOauthPlcy-meta.xml", ""],
    ["ExtlClntAppConfigurablePolicies", "extlClntAppPolicies", ".ecaPlcy-meta.xml", "_defaultPolicy"],
  ];
  const localAction = "Phase 2: review and reuse compatible files, verifying differently named child ownership before creating components. Complete confirmed partial sets from templates; render only when no destinations exist.";
  try {
    const groups = components.map(([, folder, suffix, nameSuffix]) => localFiles(roots, folder, `${ecaName}${nameSuffix}${suffix}`));
    localPresence("eca.local", groups.flat(), components.length, localAction, groups.some((files) => files.length > 1));
  } catch {
    unknown("eca.local", localAction);
  }
  for (const [type, , , nameSuffix] of components) {
    const name = `${ecaName}${nameSuffix}`;
    const nextAction = type === "ExternalClientApplication"
      ? "Phase 5: reuse the verified parent or deploy the approved parent file before its children."
      : "Phases 2/5: verify child ownership and settings before reuse or deployment; preserve the verified parent and deploy only approved tracked child files. Reused apps can have differently named children.";
    try {
      const response = sfJson(["org", "list", "metadata", "--metadata-type", type,
        "--target-org", org, "--api-version", apiVersion, "--json"]);
      if (response.status !== 0 || !Array.isArray(response.result) ||
          !response.result.every((record) => typeof record?.fullName === "string")) {
        throw new Error("Invalid metadata listing");
      }
      const matches = response.result.filter((record) => record.fullName === name);
      if (matches.length > 1) throw new Error("Ambiguous metadata");
      if (!matches.length && (response.result.length >= 1000 ||
          (type !== "ExternalClientApplication" && response.result.length > 0))) {
        readFailed = true;
        check(`eca.deployed.${type}`, "unknown",
          { fullName: name, listed: false, scope: "Other component names or listing limits prevent inferring absence; association requires verification." }, nextAction);
        continue;
      }
      check(`eca.deployed.${type}`, matches.length ? "complete" : "incomplete",
        { fullName: name, present: matches.length === 1, scope: "Bundled component name presence only; ownership and settings are unverified." }, nextAction);
    } catch {
      unknown(`eca.deployed.${type}`, nextAction);
    }
  }
}

function serverProgress(roots, apiVersion, org, serverName) {
  const localAction = "Phases 3–4: reconcile and reuse existing local metadata, preserving bindings and resources; retrieve an existing deployed server with prior overwrite consent, and render only when no local or deployed definition exists.";
  try {
    localPresence("server.local", localFiles(roots, "mcpServerDefinitions", `${serverName}.mcpServerDefinition-meta.xml`), 1, localAction);
  } catch {
    unknown("server.local", localAction);
  }
  let server;
  try {
    const records = toolingQuery(apiVersion, org,
      `SELECT Id,DeveloperName FROM McpServerDefinition WHERE DeveloperName='${serverName}'`);
    if (records.length > 1 || records.some((record) => record?.DeveloperName !== serverName ||
        !/^[a-zA-Z0-9]{15}(?:[a-zA-Z0-9]{3})?$/.test(record.Id))) throw new Error("Ambiguous server");
    server = records[0];
    check("server.deployed", server ? "complete" : "incomplete", { developerName: serverName, present: !!server },
      "Phases 3–5: reuse compatible local work and deployed bindings; deploy only approved changes if needed.");
  } catch {
    unknown("server.deployed", "Resolve the named server lookup before dependent deployment or activation.");
  }
  if (!server) {
    check("activation", "unknown", "No verified server ID; activation was not queried.", "Resolve server deployment before checking activation.");
    return;
  }
  try {
    const tools = toolingQuery(apiVersion, org,
      `SELECT ToolName,ToolTitle FROM McpServerToolDefinition WHERE McpServerId='${server.Id}'`);
    if (!tools.every((tool) => typeof tool?.ToolName === "string" && tool.ToolName.trim())) throw new Error("Invalid tools");
    check("tools.inventory", "complete", { names: tools.map((tool) => tool.ToolName), scope: "Observed tools only; expected bindings, prompts and resources are unverified." },
      "Phase 4: compare the authoritative definition with prior approved selections, including prompts and field values; an empty tool list can be valid for a prompt-only server.");
  } catch {
    unknown("tools.inventory", "Resolve tool inventory reads before comparing intended bindings.");
  }
  try {
    const access = toolingQuery(apiVersion, org, `SELECT Active FROM McpServerAccess WHERE McpServerId='${server.Id}'`);
    if (access.length > 1 || access.some((record) => typeof record?.Active !== "boolean")) throw new Error("Invalid activation");
    const active = access[0]?.Active === true;
    check("activation", active ? "complete" : "incomplete", { active },
      "Phase 7: preview and perform only authorized activation after all backing actions and widget dependencies are verified.");
  } catch {
    unknown("activation", "Resolve the activation read; do not infer active state or retry a write from an error.");
  }
}

function main() {
  const args = process.argv.slice(2);
  if (args.length !== 3 && !(args.length === 5 && args[3] === "--site")) throw new Error("Invalid arguments.");
  const [org, serverName, ecaName, , siteBundle] = args;
  if (!org.trim() || org.startsWith("-") || !isValidDeveloperName(serverName) || serverName.length > 60 || serverName.length < 2 ||
      !isValidDeveloperName(ecaName) || (siteBundle !== undefined && !siteBundle.trim())) {
    throw new Error("Invalid target org or metadata name.");
  }
  const project = JSON.parse(fs.readFileSync("sfdx-project.json", "utf8"));
  const roots = project.packageDirectories?.map((pkg) => {
    if (typeof pkg.path !== "string" || !pkg.path.trim()) throw new Error("Invalid package path.");
    return path.resolve(pkg.path, "main/default");
  });
  if (!roots?.length || typeof project.sourceApiVersion !== "string") throw new Error("Run preflight from the SFDX project root first.");
  sitePresence(siteBundle);
  ecaProgress(roots, project.sourceApiVersion, org, ecaName);
  serverProgress(roots, project.sourceApiVersion, org, serverName);
  console.log(JSON.stringify({
    scope: { org, serverName, ecaName, siteBundle: siteBundle ?? null },
    auditStatus: readFailed ? "partial" : "completed", setupStatus: "unverified",
    statusMeaning: "Complete applies only to the stated observation, not the whole phase or setup. Exit 0 means the audit ran; preflight remains a prerequisite.",
    checks,
    pendingVerification: [
      { area: "intent", phase: 1, nextAction: "Recover the confirmed site, ECA/client callbacks, intended tools/prompts/widgets and prior approvals from conversation; ask only for unrecoverable decisions. Metadata does not prove user intent or authorization." },
      { area: "eca.settings", phase: 2, nextAction: "Run render_eca.mjs <metadata-dir> <eca-name> --check locally; rerun with confirmed Phase 2 inputs plus --check for unverifiedFields. Verify deployed settings and policy review separately; component presence does not prove compatibility." },
      { area: "bindings", phase: 4, nextAction: "Use references/mcp-objects.md and references/tool-bindings.md to verify all approved bindings and backing actions/templates in the authoritative server; never infer completeness from tool count or local files." },
      { area: "widgets", phase: 6, nextAction: "Use references/widget-resources.md to verify applicable response/widget/envelope dependencies and deployed links; rerun missing or stale gates. Report no eligible Apex tools explicitly when applicable." },
      { area: "clientAccess", phase: 7, nextAction: "Remind the admin to check end-user API, Apex/Flow, object, field, record and tool-specific permissions; do not audit or configure them. Verify OAuth protected-resource scopes, client discovery and widget rendering separately; keep client testing pending until confirmed." },
    ],
    resumeRules: [
      "Continue from the earliest unmet dependency, reusing verified local and deployed work. Failed reads mean unknown, never absence.",
      "Inspect and preserve local edits before retrieval or writes. Never bypass renderer overwrite protection or replace live bindings with an empty template.",
      "Retain prior explicit approvals only for the same target, files and actions. Use existing phase confirmation rules for uncovered writes.",
      "The explicit Phase 7 preview/activate-only bypass still applies to requests limited to that operation.",
    ],
  }, null, 2));
}

try {
  main();
} catch {
  console.error("ERROR: invalid arguments or unreadable project configuration. Run preflight first. Usage: check_setup_progress.mjs <org> <server> <eca> [--site <bundle>]");
  process.exitCode = 1;
}
