/**
 * Salesforce Data + Tooling API - Section-Specific Loading Examples (Node.js)
 *
 * Demonstrates loading only the sections you need from the enterprise (SOQL/DML
 * sObject) and Tooling (developer record) JSON files, and how to traverse this
 * skill's surface-specific structure:
 *   - enterprise `fields` carry query/DML `properties` (Create/Filter/Sort/Group/
 *     Nillable/Update) plus relationship metadata (relationship_name / refers_to)
 *   - `field_reference` is a SEPARATE catalog, not a subset of `fields`
 *   - Tooling records expose supported_rest_api_http_methods / supported_soap_calls
 *
 * CRITICAL: Do NOT Read/cat these JSON files whole — Account.json etc. carry a
 * huge wsdl_segment. Extract only the section you need.
 */

const fs = require('fs');
const path = require('path');

const ENTERPRISE_DIR = ['assets', 'enterprise_api'];
const TOOLING_DIR = ['assets', 'tooling_api'];

function load(dirParts, file) {
  return JSON.parse(fs.readFileSync(path.join(...dirParts, file), 'utf-8'));
}

// Example 1: Load ONLY the 'fields' section from an enterprise sObject
function loadFieldsSection() {
  console.log('Example 1: enterprise fields section');
  const data = load(ENTERPRISE_DIR, 'Account.json');
  const fields = data.fields || {};
  // Skip wsdl_segment (verbose) and field_reference (load separately if needed)
  console.log(`Account has ${Object.keys(fields).length} fields in the 'fields' section`);
}

// Example 2: Find filterable fields (usable in a SOQL WHERE clause)
//
// The `properties` string controls capability: Filter -> WHERE, Sort ->
// ORDER BY, Group -> GROUP BY, Create/Update -> DML. Compare case-insensitively.
function findFilterableFields() {
  console.log('\nExample 2: filterable fields (WHERE-safe)');
  const data = load(ENTERPRISE_DIR, 'Opportunity.json');
  const filterable = Object.entries(data.fields || {})
    .filter(([, meta]) => (meta.properties || '').toLowerCase().includes('filter'))
    .map(([name]) => name);
  console.log(`Opportunity has ${filterable.length} filterable fields; first 5: ${filterable.slice(0, 5).join(', ')}`);
}

// Example 3: Traverse a relationship (reference field -> parent object)
//
// relationship_name is the SOQL traversal path; refers_to names the target.
function traverseRelationship() {
  console.log('\nExample 3: relationship traversal');
  const data = load(ENTERPRISE_DIR, 'Contact.json');
  const account = (data.fields || {}).AccountId || {};
  console.log(`AccountId -> relationship_name=${account.relationship_name} refers_to=${account.refers_to}`);
  console.log('SOQL: SELECT Id, Account.Name FROM Contact');
}

// Example 4: Check BOTH catalogs — field_reference is NOT a subset of fields
//
// System/audit fields (Id, CreatedDate, ...) frequently live ONLY in
// field_reference. If a field isn't in `fields`, check `field_reference`.
function checkBothCatalogs() {
  console.log('\nExample 4: fields vs field_reference (dual catalog)');
  const data = load(ENTERPRISE_DIR, 'Account.json');
  const fields = new Set(Object.keys(data.fields || {}));
  const ref = Object.keys(data.field_reference || {});
  const onlyInRef = ref.filter((k) => !fields.has(k));
  console.log(`Account: fields=${fields.size} field_reference=${ref.length}`);
  console.log(`Only in field_reference (first 5): ${onlyInRef.slice(0, 5).join(', ')}`);
}

// Example 5: Tooling record — check supported HTTP methods before querying
//
// Tooling objects query against /services/data/vXX.0/tooling/query, not the
// regular Data API. Many are read-only; check the methods first.
function toolingSupportedMethods() {
  console.log('\nExample 5: Tooling API supported methods');
  const data = load(TOOLING_DIR, 'ApexClass.json');
  console.log(`ApexClass REST methods: ${data.supported_rest_api_http_methods || ''}`);
  console.log(`First 5 ApexClass fields: ${Object.keys(data.fields || {}).slice(0, 5).join(', ')}`);
}

// WRONG APPROACH - DO NOT USE
//   fs.readFileSync('assets/enterprise_api/Account.json')  // then use whole object
// loads the huge wsdl_segment into memory. Extract only the section you need.

if (require.main === module) {
  console.log('Salesforce Data + Tooling API - Section-Specific Loading (Node.js)');
  console.log('==================================================================');
  console.log('');
  loadFieldsSection();
  findFilterableFields();
  traverseRelationship();
  checkBothCatalogs();
  toolingSupportedMethods();
}
