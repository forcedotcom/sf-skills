#!/usr/bin/env node
// Look up a dataset by name and dump its current-version XMD (dimensions / measures / dates).
// Use before generating synthetic data so the schema matches the live dataset.
// Usage: node scripts/fetch_dataset_xmd.js <alias> <datasetName>

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
    "-w", "\\nHTTP_STATUS:%{http_code}",
    url,
  ];
  const raw = execSync(`curl ${args.map(a => `'${String(a).replace(/'/g, "'\\''")}'`).join(" ")}`, {
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on GET ${path}: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
}

const [,, alias, datasetName] = process.argv;
if (!alias || !datasetName) {
  console.error("Usage: node fetch_dataset_xmd.js <alias> <datasetName>");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);

// Find the dataset by name
const datasets = apiFetch(instanceUrl, accessToken, `/services/data/v59.0/wave/datasets`);
const dataset = (datasets.datasets || []).find(d => d.name === datasetName || d.developerName === datasetName);
if (!dataset) {
  console.error(`Dataset "${datasetName}" not found.`);
  process.exit(1);
}

// Fetch XMD for the current version
const versionId = dataset.currentVersionId;
const xmd = apiFetch(instanceUrl, accessToken, `/services/data/v59.0/wave/datasets/${dataset.id}/versions/${versionId}/xmd`);

console.log(JSON.stringify({
  datasetId: dataset.id,
  datasetName: dataset.name,
  versionId,
  xmd,
}, null, 2));
