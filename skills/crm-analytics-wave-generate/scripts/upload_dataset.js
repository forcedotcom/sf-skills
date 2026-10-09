#!/usr/bin/env node
// Upload a CSV to a new or existing dataset via InsightsExternalData API.
// Polls InsightsExternalDataPart and InsightsExternalData until ingestion is terminal.
// Usage: node scripts/upload_dataset.js <alias> <csvPath> <metadataJsonPath> <datasetAlias> <folderId>

const { execSync, execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

const TERMINAL_STATUSES = new Set(["Completed", "CompletedWithWarnings", "Failed", "NotProcessed"]);
const POLL_INTERVAL_MS = 8000;
const MAX_WAIT_MS = 15 * 60 * 1000;

function getOrgCredentials(alias) {
  const result = execFileSync('sf', ['org', 'display', '-o', alias, '--json'], { encoding: "utf8" });
  const json = JSON.parse(result);
  return { accessToken: json.result.accessToken, instanceUrl: json.result.instanceUrl };
}

function soqlQuery(instanceUrl, accessToken, soql) {
  const encoded = encodeURIComponent(soql);
  const args = [
    "-s",
    "-H", `Authorization: Bearer ${accessToken}`,
    "-w", "\\nHTTP_STATUS:%{http_code}",
    `${instanceUrl}/services/data/v59.0/query?q=${encoded}`,
  ];
  const raw = execSync(`curl ${args.map(a => `'${String(a).replace(/'/g, "'\\''")}'`).join(" ")}`, { encoding: "utf8" });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on SOQL query: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
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
  const raw = execSync(`curl ${args.map(a => `'${String(a).replace(/'/g, "'\\''")}'`).join(" ")}`, { encoding: "utf8" });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on ${method} ${apiPath}: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
}

function sleep(ms) {
  execSync(`sleep ${ms / 1000}`);
}

const [,, alias, csvPath, metadataJsonPath, datasetAlias, folderId] = process.argv;
if (!alias || !csvPath || !metadataJsonPath || !datasetAlias || !folderId) {
  console.error("Usage: node upload_dataset.js <alias> <csvPath> <metadataJsonPath> <datasetAlias> <folderId>");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);

const metadataJson = fs.readFileSync(path.resolve(metadataJsonPath), "utf8");
const csvContent = fs.readFileSync(path.resolve(csvPath), "utf8");
const csvBase64 = Buffer.from(csvContent, "utf8").toString("base64");
const metaBase64 = Buffer.from(metadataJson, "utf8").toString("base64");

// Create InsightsExternalData record
const edRecord = apiFetch(instanceUrl, accessToken, "/services/data/v59.0/sobjects/InsightsExternalData", "POST", {
  EdgemartAlias: datasetAlias,
  EdgemartLabel: datasetAlias,
  MetadataJson: metaBase64,
  Format: "Csv",
  Operation: "Overwrite",
  Action: "None",
  EdgemartContainer: folderId,
});

const edId = edRecord.id;
console.log(`InsightsExternalData created: ${edId}`);

// Upload CSV part
apiFetch(instanceUrl, accessToken, "/services/data/v59.0/sobjects/InsightsExternalDataPart", "POST", {
  DataFile: csvBase64,
  InsightsExternalDataId: edId,
  PartNumber: 1,
});
console.log("CSV part uploaded.");

// Trigger processing
apiFetch(instanceUrl, accessToken, `/services/data/v59.0/sobjects/InsightsExternalData/${edId}`, "PATCH", {
  Action: "Process",
});
console.log("Processing triggered.");

// Poll until terminal
const deadline = Date.now() + MAX_WAIT_MS;
while (Date.now() < deadline) {
  sleep(POLL_INTERVAL_MS);
  const result = soqlQuery(instanceUrl, accessToken,
    `SELECT Status, StatusMessage FROM InsightsExternalData WHERE Id = '${edId}'`
  );
  const record = result.records?.[0];
  if (!record) continue;
  console.log(`Status: ${record.Status}`);
  if (TERMINAL_STATUSES.has(record.Status)) {
    console.log(JSON.stringify({ edId, status: record.Status, message: record.StatusMessage || null }));
    process.exit(record.Status === "Completed" ? 0 : 1);
  }
}

console.error("Timed out waiting for ingestion to complete.");
process.exit(1);
