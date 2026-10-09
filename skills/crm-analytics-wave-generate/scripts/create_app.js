#!/usr/bin/env node
// Idempotently create a CRMA app (folder). Lists existing folders first; only creates if missing.
// Do NOT include assetIcon — it is rejected by the Wave REST API.
// Usage: node scripts/create_app.js <alias> <appName>

const { execSync, execFileSync } = require("child_process");

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
  if (body) args.push("-d", JSON.stringify(body));
  args.push(url);
  const raw = execSync(`curl ${args.map(a => `'${String(a).replace(/'/g, "'\\''")}'`).join(" ")}`, { encoding: "utf8" });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on ${method} ${path}: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
}

const [,, alias, appName] = process.argv;
if (!alias || !appName) {
  console.error("Usage: node create_app.js <alias> <appName>");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);

// List existing folders
const listResult = apiFetch(instanceUrl, accessToken, "/services/data/v59.0/wave/folders");
const folders = listResult.folders || [];
const existing = folders.find(f => f.name === appName || f.developerName === appName);

if (existing) {
  console.log(JSON.stringify({ status: "exists", folderId: existing.id, folderName: existing.name }));
  process.exit(0);
}

// Create the folder
const created = apiFetch(instanceUrl, accessToken, "/services/data/v59.0/wave/folders", "POST", {
  name: appName,
  developerName: appName,
  folderType: "Shared",
});

console.log(JSON.stringify({ status: "created", folderId: created.id, folderName: created.name }));
