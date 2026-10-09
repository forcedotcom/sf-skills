#!/usr/bin/env node
// For each step in a deployed dashboard, GET stored SAQL, decode HTML entities,
// swap dataset name for id/version, POST to /wave/query. Prints HTTP status + row count per step.
// Edit DASH_ID and DS constants at the top before running.
// Usage: node scripts/verify_dashboard_steps.js <alias>

const { execSync, execFileSync } = require("child_process");

// ── Edit these constants before running ──────────────────────────────────────
const DASH_ID = "0FK000000000000AAA";  // Wave Dashboard 18-char ID
const DS = {
  name: "MyDataset",     // Name-based load identifier used in stored SAQL
  id: "0Fb000000000000AAA",          // Dataset 18-char ID
  versionId: "0Fc000000000000AAA",   // Current version ID
};
// ─────────────────────────────────────────────────────────────────────────────

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
  let parsed = null;
  try { parsed = JSON.parse(parts[0]); } catch { parsed = parts[0]; }
  return { httpStatus, body: parsed };
}

function decodeHtmlEntities(s) {
  let prev = null;
  while (prev !== s) {
    prev = s;
    s = s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
  }
  return s;
}

const [,, alias] = process.argv;
if (!alias) {
  console.error("Usage: node verify_dashboard_steps.js <alias>");
  console.error("Edit DASH_ID and DS constants at the top of this file before running.");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);

// Fetch dashboard state
const { httpStatus: dashStatus, body: dash } = apiFetch(instanceUrl, accessToken, `/services/data/v59.0/wave/dashboards/${DASH_ID}`);
if (dashStatus !== 200) {
  console.error(`Failed to fetch dashboard ${DASH_ID}: HTTP ${dashStatus}`);
  process.exit(1);
}

const steps = dash.state?.steps || {};
const stepNames = Object.keys(steps);
const results = [];

for (const stepName of stepNames) {
  const step = steps[stepName];
  if (step.type !== "saql") {
    results.push({ step: stepName, type: step.type, skipped: true, reason: "non-saql step" });
    continue;
  }

  const decoded = decodeHtmlEntities(step.query || "");
  // Swap name-based load for id/version for /wave/query
  const queryForVerify = decoded.replace(
    new RegExp(`"${DS.name}"`, "g"),
    `"${DS.id}/${DS.versionId}"`
  );

  const { httpStatus, body: queryResult } = apiFetch(
    instanceUrl, accessToken, "/services/data/v59.0/wave/query", "POST",
    { query: queryForVerify, queryLanguage: "SAQL" }
  );

  const rowCount = queryResult.results?.records?.length ?? null;
  results.push({ step: stepName, httpStatus, rowCount, ok: httpStatus === 200 && rowCount !== null });
}

const allOk = results.every(r => r.skipped || r.ok);
console.log(JSON.stringify({ allOk, steps: results }, null, 2));
process.exit(allOk ? 0 : 1);
