#!/usr/bin/env node
// Post-upload SAQL sanity checks: row count, sum/min/max on numeric fields, group-by-dimension breakdowns.
// Usage: node scripts/verify_synthetic_dataset.js <alias> <datasetId> <versionId>

const { execSync, execFileSync } = require("child_process");

function getOrgCredentials(alias) {
  const result = execFileSync('sf', ['org', 'display', '-o', alias, '--json'], { encoding: "utf8" });
  const json = JSON.parse(result);
  return { accessToken: json.result.accessToken, instanceUrl: json.result.instanceUrl };
}

function apiFetch(instanceUrl, accessToken, apiPath, method = "GET", body = null) {
  const url = `${instanceUrl}${apiPath}`;
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
    encoding: "utf8", maxBuffer: 10 * 1024 * 1024,
  });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on ${method} ${apiPath}: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
}

function runSaql(instanceUrl, accessToken, datasetId, versionId, saql) {
  const body = {
    query: saql,
    queryLanguage: "SAQL",
    overrideHeadProcessing: true,
  };
  // Substitute dataset id/version for /wave/query
  const boundQuery = saql.replace(/"__DATASET__"/, `"${datasetId}/${versionId}"`);
  body.query = boundQuery;
  return apiFetch(instanceUrl, accessToken, "/services/data/v59.0/wave/query", "POST", body);
}

const [,, alias, datasetId, versionId] = process.argv;
if (!alias || !datasetId || !versionId) {
  console.error("Usage: node verify_synthetic_dataset.js <alias> <datasetId> <versionId>");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);

// Fetch XMD to know field names
const xmdResult = apiFetch(instanceUrl, accessToken,
  `/services/data/v59.0/wave/datasets/${datasetId}/versions/${versionId}/xmd`
);
const xmd = xmdResult.xmd || xmdResult;
const measures = (xmd.measures || []).slice(0, 3);
const dimensions = (xmd.dimensions || []).slice(0, 2);

const results = {};

// Row count
const countSaql = `q = load "__DATASET__"; q = group q by all; q = foreach q generate count() as count;`;
const countResult = runSaql(instanceUrl, accessToken, datasetId, versionId, countSaql);
results.rowCount = countResult.results?.records?.[0]?.count ?? null;

// Sum/min/max for first measure
if (measures.length > 0) {
  const m = measures[0].fieldName || measures[0].name;
  const statSaql = `q = load "__DATASET__"; q = group q by all; q = foreach q generate sum('${m}') as total, min('${m}') as minVal, max('${m}') as maxVal;`;
  const statResult = runSaql(instanceUrl, accessToken, datasetId, versionId, statSaql);
  results.measureStats = statResult.results?.records?.[0] || null;
}

// Group-by for first dimension
if (dimensions.length > 0) {
  const d = dimensions[0].fieldName || dimensions[0].name;
  const groupSaql = `q = load "__DATASET__"; q = group q by '${d}'; q = foreach q generate '${d}' as dim, count() as count; q = limit q 10;`;
  const groupResult = runSaql(instanceUrl, accessToken, datasetId, versionId, groupSaql);
  results.dimensionBreakdown = groupResult.results?.records || null;
}

console.log(JSON.stringify(results, null, 2));
