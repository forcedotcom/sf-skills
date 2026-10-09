#!/usr/bin/env node
// Create + compile + run a Wave Recipe end-to-end via REST API at ?format=R3.
// POST or PATCH the recipe, assert targetDataflowId is returned, trigger a Run Now, poll until terminal.
// Usage: node scripts/deploy_and_run_recipe.js <alias> <recipeFile.wdpr> <appName> <recipeName>

const { execSync, execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const TERMINAL_STATUSES = new Set(["Success", "Failure", "Warning", "Cancelled"]);
const POLL_INTERVAL_MS = 10000;
const MAX_WAIT_MS = 20 * 60 * 1000;

function getOrgCredentials(alias) {
  const result = execFileSync('sf', ['org', 'display', '-o', alias, '--json'], { encoding: "utf8" });
  const json = JSON.parse(result);
  return { accessToken: json.result.accessToken, instanceUrl: json.result.instanceUrl };
}

function apiFetch(instanceUrl, accessToken, path, method = "GET", body = null) {
  const url = `${instanceUrl}${path}`;
  const args = [
    "-s",
    "-H", `Authorization: Bearer ${accessToken}`,
    "-H", "Content-Type: application/json",
    "-X", method,
    "-w", "\\nHTTP_STATUS:%{http_code}",
  ];
  if (body !== null) args.push("-d", JSON.stringify(body));
  args.push(url);
  const raw = execSync(`curl ${args.map(a => `'${String(a).replace(/'/g, "'\\''")}'`).join(" ")}`, {
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on ${method} ${path}: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
}

function sleep(ms) {
  execSync(`sleep ${ms / 1000}`);
}

const [,, alias, recipeFile, appName, recipeName] = process.argv;
if (!alias || !recipeFile || !appName || !recipeName) {
  console.error("Usage: node deploy_and_run_recipe.js <alias> <recipeFile.wdpr> <appName> <recipeName>");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);

// Read the .wdpr file — it contains only the recipeDefinition object
const recipeDefinition = JSON.parse(fs.readFileSync(path.resolve(recipeFile), "utf8"));

// Look up folder id
const folderList = apiFetch(instanceUrl, accessToken, "/services/data/v59.0/wave/folders");
const folder = (folderList.folders || []).find(f => f.name === appName || f.developerName === appName);
if (!folder) {
  console.error(`Folder "${appName}" not found. Run create_app.js first.`);
  process.exit(1);
}

// Find existing recipe by name
const recipeList = apiFetch(instanceUrl, accessToken, "/services/data/v59.0/wave/recipes");
const existingRecipe = (recipeList.recipes || []).find(r => r.name === recipeName || r.label === recipeName);

let recipe;
if (existingRecipe) {
  // PATCH at ?format=R3
  recipe = apiFetch(instanceUrl, accessToken,
    `/services/data/v59.0/wave/recipes/${existingRecipe.id}?format=R3`,
    "PATCH", { recipeDefinition }
  );
} else {
  // POST at ?format=R3
  recipe = apiFetch(instanceUrl, accessToken,
    `/services/data/v59.0/wave/recipes?format=R3`,
    "POST", {
      recipeDefinition,
      name: recipeName,
      label: recipeName,
      folder: { id: folder.id },
    }
  );
}

const targetDataflowId = recipe.targetDataflowId;
if (!targetDataflowId) {
  console.error("targetDataflowId is null — recipe did not compile. Check recipeDefinition structure.");
  console.error(JSON.stringify(recipe, null, 2));
  process.exit(1);
}

console.log(`Recipe id: ${recipe.id}, targetDataflowId: ${targetDataflowId}`);

// Trigger Run Now
const job = apiFetch(instanceUrl, accessToken, "/services/data/v59.0/wave/dataflowjobs", "POST", {
  dataflowId: targetDataflowId,
  command: "start",
});

const jobId = job.id;
console.log(`Dataflow job started: ${jobId}`);

// Poll until terminal
const deadline = Date.now() + MAX_WAIT_MS;
while (Date.now() < deadline) {
  sleep(POLL_INTERVAL_MS);
  const jobStatus = apiFetch(instanceUrl, accessToken, `/services/data/v59.0/wave/dataflowjobs/${jobId}`);
  const status = jobStatus.status;
  console.log(`Job status: ${status}`);
  if (TERMINAL_STATUSES.has(status)) {
    console.log(JSON.stringify({ jobId, status, recipeId: recipe.id, targetDataflowId }));
    process.exit(status === "Success" || status === "Warning" ? 0 : 1);
  }
}

console.error("Timed out waiting for job to complete.");
process.exit(1);
