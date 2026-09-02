#!/usr/bin/env node
/**
 * Extracts the exact {sobject, fields[]} list the TPM Accruals Data Kit
 * reads from Salesforce, straight out of the downloaded package's
 * `dataSourceObjects` metadata — so the field-permissions grant step never
 * has to guess or hardcode which objects/fields matter. Scans every
 * `*.dataSourceObject-meta.xml` in the given directory, keeps only the ones
 * with `<dataSource>Salesforce_Home</dataSource>` (the CRM streams; every
 * other `dataSource` value in that folder is a Data Cloud-side or
 * already-computed object, not a CRM read), and for each one collects
 * `<externalName>` from every `<dataSourceFields>` block EXCEPT the
 * `isFormula=true` ones (`DataSource`, `DataSourceObject` — computed
 * literals baked into the package, never real Salesforce fields).
 * `<externalName>` values are already namespace-resolved for the org this
 * package was downloaded from — never re-prefix them.
 *
 * Deliberately regex-based, not a full XML parser — this metadata format is
 * simple/flat enough (no nested same-name tags, no CDATA) and this keeps the
 * skill dependency-free per this repo's self-contained-skills rule.
 *
 * Usage:
 *   node extract-crm-field-permissions.js --dir <path-to-dataSourceObjects>
 *
 * Prints one line of JSON to stdout: [{"sobject":"Account","fields":[...]}, ...]
 * Exit codes: 0 = success (including a directory with zero Salesforce_Home
 * files — an empty array is printed), 1 = usage/read error.
 */

const fs = require('fs');
const path = require('path');

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith('--')) continue;
    args[token.slice(2)] = argv[i + 1];
    i += 1;
  }
  return args;
}

function requireArg(args, name) {
  if (!args[name]) {
    console.error(`Missing required --${name}`);
    process.exit(1);
  }
  return args[name];
}

function unescapeXml(value) {
  return value
    .replace(/&apos;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&amp;/g, '&');
}

function extractTag(xml, tagName) {
  const match = new RegExp(`<${tagName}>([^<]*)</${tagName}>`).exec(xml);
  return match ? unescapeXml(match[1]) : undefined;
}

function parseDataSourceObjectXml(xml) {
  const dataSource = extractTag(xml, 'dataSource');
  const sobject = extractTag(xml, 'externalRecordIdentifier');
  const fields = [];
  const fieldBlockRe = /<dataSourceFields>([\s\S]*?)<\/dataSourceFields>/g;
  let blockMatch;
  while ((blockMatch = fieldBlockRe.exec(xml))) {
    const block = blockMatch[1];
    const isFormula = extractTag(block, 'isFormula') === 'true';
    const externalName = extractTag(block, 'externalName');
    if (!isFormula && externalName) {
      fields.push(externalName);
    }
  }
  return { dataSource, sobject, fields };
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const dir = requireArg(args, 'dir');

  let files;
  try {
    files = fs.readdirSync(dir).filter((f) => f.endsWith('.dataSourceObject-meta.xml'));
  } catch (error) {
    console.error(`extract-crm-field-permissions: could not read --dir "${dir}" — ${error.message}`);
    process.exit(1);
  }

  const bySobject = new Map();
  for (const file of files) {
    const xml = fs.readFileSync(path.join(dir, file), 'utf8');
    const { dataSource, sobject, fields } = parseDataSourceObjectXml(xml);
    if (dataSource !== 'Salesforce_Home' || !sobject || !fields.length) continue;
    const existing = bySobject.get(sobject) || new Set();
    fields.forEach((f) => existing.add(f));
    bySobject.set(sobject, existing);
  }

  const result = Array.from(bySobject.entries()).map(([sobject, fields]) => ({
    sobject,
    fields: Array.from(fields).sort(),
  }));
  process.stdout.write(JSON.stringify(result));
}

if (require.main === module) {
  main();
}

module.exports = { parseDataSourceObjectXml };
