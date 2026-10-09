#!/usr/bin/env node
// Full-cycle PATCH template: GET dashboard state → decodeAll every step query → merge dark theme → PATCH.
// Use as the canonical pattern for future dashboard PATCH scripts.
// Edit DASH_ID and THEME constants before running.
// Usage: node scripts/patch_t_oppo_view.js <alias>

const { execSync, execFileSync } = require("child_process");

// ── Edit these constants before running ──────────────────────────────────────
const DASH_ID = "0FK000000000000AAA";  // Wave Dashboard 18-char ID

const THEME = {
  layoutStyle: { backgroundColor: "#0d1117", cellSpacingX: 8, cellSpacingY: 8, gutterColor: "#0d1117" },
  widgetStyle: { backgroundColor: "#161b22", borderColor: "#30363d", borderEdges: ["all"], borderRadius: 8, borderWidth: 1 },
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
    encoding: "utf8", maxBuffer: 20 * 1024 * 1024,
  });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on ${method} ${apiPath}: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
}

// Always decode all HTML-entity encoding before any mutation + PATCH.
// Doing a GET → PATCH without decoding re-encodes SAQL → double-encoded entities → errorCode 119.
function decodeAll(s) {
  let prev = null;
  while (prev !== s) {
    prev = s;
    s = s.replace(/&quot;/g, '"').replace(/&#39;/g, "'").replace(/&amp;/g, '&');
  }
  return s;
}

const [,, alias] = process.argv;
if (!alias) {
  console.error("Usage: node patch_t_oppo_view.js <alias>");
  console.error("Edit DASH_ID and THEME constants at the top of this file before running.");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);

// Step 1: GET current dashboard state
const current = apiFetch(instanceUrl, accessToken, `/services/data/v59.0/wave/dashboards/${DASH_ID}`);
const state = JSON.parse(JSON.stringify(current.state));

// Step 2: Decode all step queries
const steps = state.steps || {};
for (const stepName of Object.keys(steps)) {
  if (steps[stepName].query) {
    steps[stepName].query = decodeAll(steps[stepName].query);
  }
}

// Step 3: Merge dark theme into layout
const layouts = state.gridLayouts || [];
for (const layout of layouts) {
  layout.style = { ...(layout.style || {}), ...THEME.layoutStyle };
  const pages = layout.pages || [];
  for (const page of pages) {
    const widgets = page.widgets || [];
    for (const widget of widgets) {
      widget.widgetStyle = { ...(widget.widgetStyle || {}), ...THEME.widgetStyle };
    }
  }
}

// Step 4: PATCH with decoded + themed state
const patched = apiFetch(instanceUrl, accessToken, `/services/data/v59.0/wave/dashboards/${DASH_ID}`, "PATCH", { state });

console.log(JSON.stringify({
  status: "patched",
  dashboardId: patched.id,
  label: patched.label,
  stepsDecoded: Object.keys(steps).length,
}));
