#!/usr/bin/env node
/**
 * Grants FieldPermissions rows, and object-level ObjectPermissions
 * (PermissionsRead + PermissionsViewAllRecords), on a permission set for the
 * {sobject, fields[]} list produced by extract-crm-field-permissions.js.
 * Add-only by design at both levels: an existing row/flag already granting
 * access is left untouched, and this script never deletes a row or flips a
 * granted boolean back to false — the only operations are "insert a new
 * row" (nothing granted yet) and "flip an existing false flag to true"
 * (row exists but the flag is explicitly off). Neither operation ever
 * removes access, and object-level writes never touch PermissionsCreate/
 * Edit/Delete/ModifyAllRecords — only Read and ViewAllRecords are ever set,
 * and only ever to true. The caller (this skill's Phase 2) is responsible
 * for getting the user's explicit go-ahead before invoking this without
 * --dry-run — this script performs whatever it's told, same as every other
 * write helper in this skill.
 *
 * Reads (permission set lookup, existing FieldPermissions/ObjectPermissions)
 * go through `sf data query`, consistent with the rest of this skill.
 * Writes go through the sObject Collections API (POST/PATCH
 * .../composite/sobjects, batches of 200) instead of one `sf data create
 * record` process per field — dozens of fields across a dozen-plus objects
 * would otherwise mean dozens of CLI spawns. The org's own `sf`-authenticated
 * access token drives every call, never a hardcoded credential, and it is
 * never printed.
 *
 * Usage:
 *   node update-field-permissions.js \
 *     --target-org <username> \
 *     --input <path-to-extract-output.json | -> \
 *     [--permission-set-name sfdc_a360_sfcrm_data_extract] \
 *     [--dry-run]
 *
 * --input accepts a file path or "-" to read the extract script's JSON
 * array (`[{sobject, fields[]}, ...]`) from stdin.
 *
 * Before diffing fields, every field is checked against a live
 * `sobject/describe` call for its object: fields absent from the object
 * entirely, or present but not FLS-controllable (master-detail/required
 * lookups, standard system fields like Id/Name/SystemModstamp — describe's
 * own `permissionable: false`), are filtered out into `notFlsEligible`
 * rather than attempted — no hardcoded field-name guessing. Object-level
 * permissions have no such eligibility gate — every sobject in the input is
 * a real object the data kit reads, so Read + ViewAllRecords are always
 * in scope for it.
 *
 * Prints one line of JSON to stdout:
 *   {
 *     permissionSetId, permissionSetLabel, dryRun,
 *     alreadyGranted: [{sobject, field}],
 *     notFlsEligible: [{sobject, field, onObject}],
 *     granted / wouldGrant: [{sobject, field}],
 *     failed: [{sobject, field, error}],
 *     objectAlreadyGranted: [{sobject, permissionsRead, permissionsViewAllRecords}],
 *     objectGranted / objectWouldGrant: [{sobject, permissionsRead, permissionsViewAllRecords}],
 *     objectFailed: [{sobject, error}]
 *   }
 * `failed`/`objectFailed` are exactly the manual-Setup punch list to hand
 * back to the user when a grant can't be automated. `notFlsEligible` entries
 * with `onObject: false` mean the package expects a field this org's object
 * doesn't actually have — a package/org data mismatch, not something to
 * grant manually. A small set of sobjects (currently just Product2 — see
 * OBJECT_VIEWALL_INELIGIBLE) never get PermissionsViewAllRecords requested
 * at all, because the org's own API rejects that specific flag with a
 * license-constraint error; PermissionsRead is still granted normally for
 * them. This is a known, permanent platform restriction, not a per-run
 * failure — it's applied silently and surfaces as an ordinary
 * `objectGranted`/`objectAlreadyGranted` entry with `permissionsViewAllRecords: false`,
 * never as `objectFailed` and never something to ask the user about.
 *
 * Exit codes: 0 = no failures (includes dry-run and nothing-to-grant),
 * 1 = permission set not found or bad input, 3 = one or more fields or
 * objects failed to grant.
 */

const fs = require('fs');
const { sfJson, getAccessToken } = require('./sf-rest');

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i];
    if (token === '--dry-run') {
      args['dry-run'] = true;
      continue;
    }
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

function readInput(inputArg) {
  const raw = inputArg === '-' ? fs.readFileSync(0, 'utf8') : fs.readFileSync(inputArg, 'utf8');
  let parsed;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    console.error(`update-field-permissions: --input is not valid JSON — ${error.message}`);
    process.exit(1);
  }
  if (!Array.isArray(parsed)) {
    console.error('update-field-permissions: --input must be a JSON array of {sobject, fields[]}');
    process.exit(1);
  }
  return parsed;
}

function soqlQuote(value) {
  // Escape backslashes before quotes — otherwise a value ending in `\`
  // combines with the following escaped quote to unescape itself.
  return value.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

// Observed live: this org's license rejects any ObjectPermissions write that
// sets PermissionsViewAllRecords=true on Product2 —
// "c2c.integrationconstraints.LicenselessIntegrationPermConstrainer does not
// allow type=permission, label= View All Product2". Not a guess; a
// licenseless-integration-user platform restriction confirmed by the API's
// own error. PermissionsRead is unaffected and still granted normally —
// only ViewAllRecords is never requested for these sobjects, silently.
const OBJECT_VIEWALL_INELIGIBLE = new Set(['Product2']);

function chunk(list, size) {
  const out = [];
  for (let i = 0; i < list.length; i += size) out.push(list.slice(i, i + size));
  return out;
}

async function describeSobject(instanceUrl, apiVersion, accessToken, sobject) {
  const response = await fetch(`${instanceUrl}/services/data/v${apiVersion}/sobjects/${sobject}/describe`, {
    headers: { Authorization: `Bearer ${accessToken}` },
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`describe ${sobject} failed — HTTP ${response.status}: ${text}`);
  }
  const { fields } = await response.json();
  return new Map(fields.map((f) => [f.name, f.permissionable]));
}

async function postCollection(instanceUrl, apiVersion, accessToken, method, records) {
  const response = await fetch(`${instanceUrl}/services/data/v${apiVersion}/composite/sobjects`, {
    method,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ allOrNone: false, records }),
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`HTTP ${response.status}: ${text}`);
  }
  return response.json();
}

async function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetOrg = requireArg(args, 'target-org');
  const inputArg = requireArg(args, 'input');
  const permissionSetName = args['permission-set-name'] || 'sfdc_a360_sfcrm_data_extract';
  const dryRun = Boolean(args['dry-run']);

  const entries = readInput(inputArg).filter(
    (e) => e && e.sobject && Array.isArray(e.fields) && e.fields.length
  );
  if (!entries.length) {
    process.stdout.write(JSON.stringify({ error: 'no_fields_in_input' }));
    process.exit(1);
  }

  const psResult = sfJson([
    'data', 'query', '--target-org', targetOrg, '--json',
    '--query', `SELECT Id, Label FROM PermissionSet WHERE Name = '${soqlQuote(permissionSetName)}'`,
  ]);
  if (!psResult.records || psResult.records.length < 1) {
    process.stdout.write(JSON.stringify({ error: 'permission_set_not_found', permissionSetName }));
    process.exit(1);
  }
  const permissionSetId = psResult.records[0].Id;
  const permissionSetLabel = psResult.records[0].Label;

  const sobjectList = entries.map((e) => `'${soqlQuote(e.sobject)}'`).join(',');
  const existingResult = sfJson([
    'data', 'query', '--target-org', targetOrg, '--json',
    '--query',
    `SELECT Id, Field, SobjectType, PermissionsRead FROM FieldPermissions WHERE ParentId = '${permissionSetId}' AND SobjectType IN (${sobjectList})`,
  ]);
  const existingByField = new Map(
    (existingResult.records || []).map((r) => [r.Field, r])
  );

  const existingObjectResult = sfJson([
    'data', 'query', '--target-org', targetOrg, '--json',
    '--query',
    `SELECT Id, SobjectType, PermissionsRead, PermissionsViewAllRecords FROM ObjectPermissions WHERE ParentId = '${permissionSetId}' AND SobjectType IN (${sobjectList})`,
  ]);
  const existingObjectBySobject = new Map(
    (existingObjectResult.records || []).map((r) => [r.SobjectType, r])
  );

  const orgDetails = sfJson(['org', 'display', '--target-org', targetOrg, '--json']);
  const instanceUrl = orgDetails.instanceUrl;
  const apiVersion = orgDetails.apiVersion || '60.0';
  const accessToken = getAccessToken(targetOrg);

  const sobjectNames = [...new Set(entries.map((e) => e.sobject))];
  const describeResults = await Promise.all(
    sobjectNames.map((sobject) => describeSobject(instanceUrl, apiVersion, accessToken, sobject))
  );
  const describeBySobject = new Map(sobjectNames.map((sobject, i) => [sobject, describeResults[i]]));

  const alreadyGranted = [];
  const toInsert = [];
  const toUpdate = [];
  const notFlsEligible = [];
  for (const entry of entries) {
    const describeFields = describeBySobject.get(entry.sobject);
    for (const field of entry.fields) {
      if (!describeFields.has(field) || describeFields.get(field) !== true) {
        // Not on the object at all, or present but not FLS-controllable
        // (master-detail/required lookup, standard system field, etc.) —
        // confirmed live from this org's own sobject describe.
        notFlsEligible.push({ sobject: entry.sobject, field, onObject: describeFields.has(field) });
        continue;
      }
      const fieldApiName = `${entry.sobject}.${field}`;
      const existing = existingByField.get(fieldApiName);
      if (existing && existing.PermissionsRead) {
        alreadyGranted.push({ sobject: entry.sobject, field });
      } else if (existing) {
        // Row exists but Read is explicitly off — flip it on, never off.
        toUpdate.push({ sobject: entry.sobject, field, fieldApiName, id: existing.Id });
      } else {
        toInsert.push({ sobject: entry.sobject, field, fieldApiName });
      }
    }
  }
  const missing = [...toInsert, ...toUpdate];

  const objectAlreadyGranted = [];
  const toInsertObject = [];
  const toUpdateObject = [];
  for (const sobject of new Set(entries.map((e) => e.sobject))) {
    const viewAllEligible = !OBJECT_VIEWALL_INELIGIBLE.has(sobject);
    const existing = existingObjectBySobject.get(sobject);
    if (!existing) {
      toInsertObject.push({ sobject, permissionsRead: true, permissionsViewAllRecords: viewAllEligible });
      continue;
    }
    const needsRead = !existing.PermissionsRead;
    const needsViewAll = viewAllEligible && !existing.PermissionsViewAllRecords;
    if (!needsRead && !needsViewAll) {
      objectAlreadyGranted.push({
        sobject,
        permissionsRead: existing.PermissionsRead,
        permissionsViewAllRecords: viewAllEligible ? existing.PermissionsViewAllRecords : false,
      });
    } else {
      // Row exists but Read and/or ViewAllRecords is explicitly off —
      // flip only the off flag(s) on, never off, and never touch
      // Create/Edit/Delete/ModifyAllRecords.
      toUpdateObject.push({
        sobject,
        id: existing.Id,
        permissionsRead: needsRead ? true : undefined,
        permissionsViewAllRecords: needsViewAll ? true : undefined,
      });
    }
  }
  const missingObject = [...toInsertObject, ...toUpdateObject];

  if (dryRun || (missing.length === 0 && missingObject.length === 0)) {
    process.stdout.write(JSON.stringify({
      permissionSetId,
      permissionSetLabel,
      dryRun,
      alreadyGranted,
      notFlsEligible,
      wouldGrant: missing.map(({ sobject, field }) => ({ sobject, field })),
      granted: [],
      failed: [],
      objectAlreadyGranted,
      objectWouldGrant: missingObject.map(({ sobject, permissionsRead, permissionsViewAllRecords }) => ({
        sobject,
        permissionsRead: Boolean(permissionsRead),
        permissionsViewAllRecords: Boolean(permissionsViewAllRecords),
      })),
      objectGranted: [],
      objectFailed: [],
    }));
    process.exit(0);
  }

  const granted = [];
  const failed = [];

  for (const batch of chunk(toInsert, 200)) {
    const records = batch.map((item) => ({
      attributes: { type: 'FieldPermissions' },
      ParentId: permissionSetId,
      SobjectType: item.sobject,
      Field: item.fieldApiName,
      PermissionsRead: true,
    }));
    try {
      const results = await postCollection(instanceUrl, apiVersion, accessToken, 'POST', records);
      results.forEach((result, idx) => {
        const item = batch[idx];
        if (result.success) {
          granted.push({ sobject: item.sobject, field: item.field });
        } else {
          const error = (result.errors || []).map((e) => e.message).join('; ') || 'unknown error';
          failed.push({ sobject: item.sobject, field: item.field, error });
        }
      });
    } catch (error) {
      batch.forEach((item) => failed.push({ sobject: item.sobject, field: item.field, error: error.message }));
    }
  }

  for (const batch of chunk(toUpdate, 200)) {
    const records = batch.map((item) => ({
      attributes: { type: 'FieldPermissions' },
      Id: item.id,
      PermissionsRead: true,
    }));
    try {
      const results = await postCollection(instanceUrl, apiVersion, accessToken, 'PATCH', records);
      results.forEach((result, idx) => {
        const item = batch[idx];
        if (result.success) {
          granted.push({ sobject: item.sobject, field: item.field });
        } else {
          const error = (result.errors || []).map((e) => e.message).join('; ') || 'unknown error';
          failed.push({ sobject: item.sobject, field: item.field, error });
        }
      });
    } catch (error) {
      batch.forEach((item) => failed.push({ sobject: item.sobject, field: item.field, error: error.message }));
    }
  }

  const objectGranted = [];
  const objectFailed = [];

  for (const batch of chunk(toInsertObject, 200)) {
    const records = batch.map((item) => {
      const record = {
        attributes: { type: 'ObjectPermissions' },
        ParentId: permissionSetId,
        SobjectType: item.sobject,
        PermissionsRead: true,
        PermissionsCreate: false,
        PermissionsEdit: false,
        PermissionsDelete: false,
        PermissionsModifyAllRecords: false,
      };
      if (item.permissionsViewAllRecords) record.PermissionsViewAllRecords = true;
      return record;
    });
    try {
      const results = await postCollection(instanceUrl, apiVersion, accessToken, 'POST', records);
      results.forEach((result, idx) => {
        const item = batch[idx];
        if (result.success) {
          objectGranted.push({ sobject: item.sobject, permissionsRead: true, permissionsViewAllRecords: Boolean(item.permissionsViewAllRecords) });
        } else {
          const error = (result.errors || []).map((e) => e.message).join('; ') || 'unknown error';
          objectFailed.push({ sobject: item.sobject, error });
        }
      });
    } catch (error) {
      batch.forEach((item) => objectFailed.push({ sobject: item.sobject, error: error.message }));
    }
  }

  for (const batch of chunk(toUpdateObject, 200)) {
    const records = batch.map((item) => {
      const record = { attributes: { type: 'ObjectPermissions' }, Id: item.id };
      if (item.permissionsRead) record.PermissionsRead = true;
      if (item.permissionsViewAllRecords) record.PermissionsViewAllRecords = true;
      return record;
    });
    try {
      const results = await postCollection(instanceUrl, apiVersion, accessToken, 'PATCH', records);
      results.forEach((result, idx) => {
        const item = batch[idx];
        if (result.success) {
          objectGranted.push({
            sobject: item.sobject,
            permissionsRead: Boolean(item.permissionsRead),
            permissionsViewAllRecords: Boolean(item.permissionsViewAllRecords),
          });
        } else {
          const error = (result.errors || []).map((e) => e.message).join('; ') || 'unknown error';
          objectFailed.push({ sobject: item.sobject, error });
        }
      });
    } catch (error) {
      batch.forEach((item) => objectFailed.push({ sobject: item.sobject, error: error.message }));
    }
  }

  process.stdout.write(JSON.stringify({
    permissionSetId,
    permissionSetLabel,
    dryRun: false,
    alreadyGranted,
    notFlsEligible,
    granted,
    failed,
    objectAlreadyGranted,
    objectGranted,
    objectFailed,
  }));
  process.exit(failed.length || objectFailed.length ? 3 : 0);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
