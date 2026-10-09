#!/usr/bin/env node
// Schema-driven synthetic data generator. Reads live XMD, classifies each column by name pattern
// (*Id → id, *Industry/*Type/*Status → category, *Year/*Month → date, *Amount/*Revenue/*Count → numeric),
// renames dotted fields to underscored, writes CSV + Wave-compatible metadata.json.
// Default output dataset: <sourceDatasetName>_Synthetic
// Usage: node scripts/gen_synthetic_dataset.js <alias> <sourceDatasetName>

const { execSync, execFileSync } = require("child_process");
const fs = require("fs");
const path = require("path");

function getOrgCredentials(alias) {
  const result = execFileSync('sf', ['org', 'display', '-o', alias, '--json'], { encoding: "utf8" });
  const json = JSON.parse(result);
  return { accessToken: json.result.accessToken, instanceUrl: json.result.instanceUrl };
}

function apiFetch(instanceUrl, accessToken, apiPath) {
  const url = `${instanceUrl}${apiPath}`;
  const args = ["-s", "-H", `Authorization: Bearer ${accessToken}`, "-w", "\\nHTTP_STATUS:%{http_code}", url];
  const raw = execSync(`curl ${args.map(a => `'${String(a).replace(/'/g, "'\\''")}'`).join(" ")}`, {
    encoding: "utf8", maxBuffer: 10 * 1024 * 1024,
  });
  const parts = raw.split("\nHTTP_STATUS:");
  const httpStatus = parseInt(parts[1] || "0", 10);
  if (httpStatus < 200 || httpStatus >= 300) {
    throw new Error(`HTTP ${httpStatus} on GET ${apiPath}: ${parts[0]}`);
  }
  return JSON.parse(parts[0]);
}

function classifyField(name) {
  const n = name.toLowerCase();
  if (/id$/.test(n)) return "id";
  if (/(industry|type|status|stage|source|region|category|priority)/.test(n)) return "category";
  if (/(year|month|quarter)/.test(n)) return "date_part";
  if (/(amount|revenue|count|qty|quantity|size|value|total|sum)/.test(n)) return "numeric";
  return "text";
}

function generateValue(fieldName, type, rowIndex) {
  switch (type) {
    case "id": return `00Q${String(rowIndex).padStart(15, "0")}`;
    case "category": {
      const categories = ["Tech", "Finance", "Healthcare", "Retail", "Manufacturing"];
      return categories[rowIndex % categories.length];
    }
    case "date_part": return String(2020 + (rowIndex % 5));
    case "numeric": return String(Math.round(10000 + rowIndex * 1337.7));
    default: return `Value_${rowIndex % 10}`;
  }
}

const [,, alias, sourceDatasetName] = process.argv;
if (!alias || !sourceDatasetName) {
  console.error("Usage: node gen_synthetic_dataset.js <alias> <sourceDatasetName>");
  process.exit(1);
}

const { accessToken, instanceUrl } = getOrgCredentials(alias);

// Fetch dataset and XMD
const datasets = apiFetch(instanceUrl, accessToken, "/services/data/v59.0/wave/datasets");
const dataset = (datasets.datasets || []).find(d => d.name === sourceDatasetName || d.developerName === sourceDatasetName);
if (!dataset) {
  console.error(`Dataset "${sourceDatasetName}" not found.`);
  process.exit(1);
}

const versionId = dataset.currentVersionId;
const xmdResult = apiFetch(instanceUrl, accessToken,
  `/services/data/v59.0/wave/datasets/${dataset.id}/versions/${versionId}/xmd`
);
const xmd = xmdResult.xmd || xmdResult;

// Collect fields from XMD
const fields = [];
const dimensions = xmd.dimensions || [];
const measures = xmd.measures || [];
const dates = xmd.dates || [];

dimensions.forEach(d => fields.push({ name: d.fieldName || d.name, type: "text" }));
measures.forEach(m => fields.push({ name: m.fieldName || m.name, type: "numeric" }));
dates.forEach(d => fields.push({ name: d.fieldName || d.name, type: "date_part" }));

if (fields.length === 0) {
  console.error("No fields found in XMD. Cannot generate synthetic data.");
  process.exit(1);
}

// Rename dotted field names to underscored
const sanitized = fields.map(f => ({
  ...f,
  name: f.name.replace(/\./g, "_"),
  originalName: f.name,
}));

const ROW_COUNT = 50;
const headers = sanitized.map(f => f.name);
const rows = [headers.join(",")];
for (let i = 0; i < ROW_COUNT; i++) {
  const row = sanitized.map(f => {
    const val = generateValue(f.name, f.type === "text" ? classifyField(f.name) : f.type, i);
    return val.includes(",") ? `"${val}"` : val;
  });
  rows.push(row.join(","));
}

const outputDir = path.join(process.cwd(), "synthetic_data");
fs.mkdirSync(outputDir, { recursive: true });

const csvPath = path.join(outputDir, `${sourceDatasetName}_Synthetic.csv`);
const metaPath = path.join(outputDir, `${sourceDatasetName}_Synthetic_metadata.json`);

fs.writeFileSync(csvPath, rows.join("\n"), "utf8");

// Wave-compatible metadata.json
const metadata = {
  fileFormat: { charsetName: "UTF-8", fieldsDelimitedBy: ",", linesTerminatedBy: "\n" },
  objects: [{
    connector: "CSV",
    fullyQualifiedName: `${sourceDatasetName}_Synthetic`,
    label: `${sourceDatasetName} Synthetic`,
    name: `${sourceDatasetName}_Synthetic`,
    fields: sanitized.map(f => ({
      fullyQualifiedName: f.name,
      name: f.name,
      label: f.name,
      type: f.type === "numeric" ? "Numeric" : "Text",
      ...(f.type === "numeric" ? { precision: 18, scale: 2, defaultValue: "0" } : { length: 255 }),
    })),
  }],
};

fs.writeFileSync(metaPath, JSON.stringify(metadata, null, 2), "utf8");

console.log(JSON.stringify({ csvPath, metaPath, rowCount: ROW_COUNT, fieldCount: fields.length }));
