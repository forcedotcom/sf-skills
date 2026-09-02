#!/usr/bin/env node
/**
 * Escape a value for safe interpolation into a single-quoted SOQL/Apex
 * string literal — escape backslashes first, then single quotes, so a value
 * like `O'Brien Foods` (or one ending in a backslash) can't break out of the
 * literal it's placed in. Shared by render-apex.js (Apex template
 * substitution) and any SKILL step that builds a `sf data query` string by
 * hand from admin-supplied free text (Sales Org / KPI Set names).
 *
 * CLI usage: node scripts/soql-escape.js "O'Brien Foods"
 */

function escapeSoqlLiteral(value) {
  return value.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

if (require.main === module) {
  const value = process.argv[2];
  if (value === undefined) {
    console.error('Usage: soql-escape.js <value>');
    process.exit(2);
  }
  console.log(escapeSoqlLiteral(value));
}

module.exports = { escapeSoqlLiteral };
