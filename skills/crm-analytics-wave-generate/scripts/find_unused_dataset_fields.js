#!/usr/bin/env node
// Given a dataset name, list every XMD field that no deployed dashboard SAQL references.
// Caveat: aggregateflex steps, multi-dataset SAQL, and archived app dashboards are out of scope.
// Usage: node scripts/find_unused_dataset_fields.js <alias> <datasetName>

const { execSync, execFileSync } = require("child_process");

function getOrgCredentials(alias) {
  const result = execFileSync('sf', ['org', 'display', '-o', alias, '--json'], { encoding: "utf8" });
  const json = JSON.parse(result);
  return { accessToken: json.result.accessToken, instanceUrl: json.result.instanceUrl };
}

function apiFetch(instanceUrl, accessToken, apiPath) {
  const url = `${instanceUrl}${apiPath}`;
  const args = ["-s", "-H", `Authorization: Bearer ${accessToken}`, "-w", "\\nHTTP_STATUS:%{http_code}", url];
  const raw = execSync(`curl ${args.map(a => `'${String(a).replace(/'/g, "'\\''")}'`).join(" ")}`, {
    encoding: "utf8", maxBuffer: 20 * 1024 * 1024,
  });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on GET ${apiPath}: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
}

function decodeHtmlEntities(s) {
  let prev = null;
  while (prev !== s) {
    prev = s;
    s = s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
  }
  return s;
}

const [,, alias, datasetName] = process.argv;
if (!alias || !datasetName) {
  console.error("Usage: node find_unused_dataset_fields.js <alias> <datasetName>");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);

// Fetch dataset XMD
const datasets = apiFetch(instanceUrl, accessToken, "/services/data/v59.0/wave/datasets");
const dataset = (datasets.datasets || []).find(d => d.name === datasetName || d.developerName === datasetName);
if (!dataset) {
  console.error(`Dataset "${datasetName}" not found.`);
  process.exit(1);
}

const versionId = dataset.currentVersionId;
const xmdResult = apiFetch(instanceUrl, accessToken,
  `/services/data/v59.0/wave/datasets/${dataset.id}/versions/${versionId}/xmd`
);
const xmd = xmdResult.xmd || xmdResult;

const allFields = [
  ...(xmd.dimensions || []).map(d => d.fieldName || d.name),
  ...(xmd.measures || []).map(m => m.fieldName || m.name),
  ...(xmd.dates || []).map(d => d.fieldName || d.name),
];

// Collect all SAQL from deployed dashboards
const dashboards = apiFetch(instanceUrl, accessToken, "/services/data/v59.0/wave/dashboards");
let allSaql = "";

for (const dash of (dashboards.dashboards || [])) {
  try {
    const detail = apiFetch(instanceUrl, accessToken, `/services/data/v59.0/wave/dashboards/${dash.id}`);
    const steps = detail.state?.steps || {};
    for (const step of Object.values(steps)) {
      if (step.query) allSaql += " " + decodeHtmlEntities(step.query);
    }
  } catch {
    // Skip inaccessible dashboards
  }
}

// Check which fields are referenced
const unusedFields = allFields.filter(field => {
  const escaped = field.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return !new RegExp(escaped).test(allSaql);
});

const usedFields = allFields.filter(f => !unusedFields.includes(f));

console.log(JSON.stringify({
  datasetName,
  totalFields: allFields.length,
  usedCount: usedFields.length,
  unusedCount: unusedFields.length,
  unusedFields,
  note: "aggregateflex steps, multi-dataset SAQL, and archived app dashboards are not scanned",
}, null, 2));
