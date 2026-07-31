/*
 * Optional pre-import step: make re-runs idempotent by giving records a stable,
 * unique key so a fresh import can be reconciled against a prior run instead of
 * creating duplicates. Runs before the delete/import cycle when present.
 *
 * Reads each data file listed in data-plan.json, ensures every record has a
 * deterministic external key derived from a natural field, and writes the files
 * back in place.
 *
 * CUSTOMIZATION REQUIRED: Update the keyField mapping below based on the actual
 * sobjects in your data-plan.json and their natural unique fields. Common patterns:
 *   - Standard objects: Account/Contact/Lead → Name/Email
 *   - Custom objects: use a required text field that's naturally unique
 *   - Skip sobjects that lack a suitable natural key (leave them out of the map)
 *
 * Usage:
 *   cd data/
 *   node prepare-import-unique-fields.js
 *
 * Or copy this script to the project's data/ directory and run it from there.
 */
const { readFileSync, writeFileSync } = require('fs');
const { join } = require('path');

const dataDir = __dirname;
const plan = JSON.parse(readFileSync(join(dataDir, 'data-plan.json'), 'utf8'));

// CUSTOMIZE THIS: Map each sobject to its natural unique field.
// Only sobjects listed here will get UniqueKey__c stamped.
const keyField = { Account: 'Name', Contact: 'Email' };

for (const entry of plan) {
  const field = keyField[entry.sobject];
  if (!field) continue;
  for (const file of entry.files) {
    const path = join(dataDir, file);
    const doc = JSON.parse(readFileSync(path, 'utf8'));
    for (const record of doc.records) {
      if (record[field]) {
        record.UniqueKey__c = `${entry.sobject}:${record[field]}`.toLowerCase();
      }
    }
    writeFileSync(path, `${JSON.stringify(doc, null, 2)}\n`);
  }
}
