#!/usr/bin/env node
/**
 * Resolve a record's Id by an exact-match Name query, safely — the Name
 * value is escaped (see soql-escape.js) before being embedded in the SOQL
 * literal, so a Name containing a quote (or a crafted injection payload)
 * can't break out of it or inject additional clauses. Callers never build
 * this WHERE clause by hand.
 *
 * Usage:
 *   node resolve-id-by-name.js --target-org <username> --object <ObjectApiName> --name "<value>"
 *
 * Prints the `sf data query --json` result verbatim to stdout.
 */

const { execFileSync } = require('child_process');
const { escapeSoqlLiteral } = require('./soql-escape');

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 1) {
    if (!argv[i].startsWith('--')) continue;
    args[argv[i].slice(2)] = argv[i + 1];
    i += 1;
  }
  return args;
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetOrg = args['target-org'];
  const object = args['object'];
  const name = args['name'];
  if (!targetOrg || !object || name === undefined) {
    console.error('Usage: resolve-id-by-name.js --target-org <username> --object <ObjectApiName> --name "<value>"');
    process.exit(2);
  }

  const query = `SELECT Id, Name FROM ${object} WHERE Name = '${escapeSoqlLiteral(name)}'`;
  const output = execFileSync(
    'sf',
    ['data', 'query', '--target-org', targetOrg, '--json', '--query', query],
    { encoding: 'utf8' }
  );
  process.stdout.write(output);
}

main();
