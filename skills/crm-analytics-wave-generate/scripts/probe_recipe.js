#!/usr/bin/env node
// Fetch a recipe with ?format=R3 and print compile status + targetDataflowId.
// Usage: node scripts/probe_recipe.js <alias> <recipeId>

const { execSync, execFileSync } = require("child_process");

function getOrgCredentials(alias) {
  const result = execFileSync('sf', ['org', 'display', '-o', alias, '--json'], { encoding: "utf8" });
  const json = JSON.parse(result);
  return { accessToken: json.result.accessToken, instanceUrl: json.result.instanceUrl };
}

function apiFetch(instanceUrl, accessToken, path) {
  const url = `${instanceUrl}${path}`;
  const args = [
    "-s",
    "-H", `Authorization: Bearer ${accessToken}`,
    "-H", "Content-Type: application/json",
    "-w", "\\nHTTP_STATUS:%{http_code}",
    url,
  ];
  const raw = execSync(`curl ${args.map(a => `'${String(a).replace(/'/g, "'\\''")}'`).join(" ")}`, { encoding: "utf8" });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on GET ${path}: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
}

const [,, alias, recipeId] = process.argv;
if (!alias || !recipeId) {
  console.error("Usage: node probe_recipe.js <alias> <recipeId>");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);
const recipe = apiFetch(instanceUrl, accessToken, `/services/data/v59.0/wave/recipes/${recipeId}?format=R3`);

console.log(JSON.stringify({
  id: recipe.id,
  name: recipe.name,
  label: recipe.label,
  status: recipe.status,
  targetDataflowId: recipe.targetDataflowId || null,
  folderId: recipe.folder?.id || null,
}, null, 2));
