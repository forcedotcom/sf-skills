#!/usr/bin/env node
/**
 * Render one of this skill's `scripts/*.apex` templates by substituting
 * `%TOKEN%` placeholders, writing the result to a temp file, and printing
 * that file's path on stdout (so a caller can pipe it straight into
 * `sf apex run -f <path>`).
 *
 * Usage:
 *   node render-apex.js <template-path> --var NS=cgcloud_dev__ --var NAME="My Set"
 *
 * Every `%TOKEN%` in the template must have a matching --var — this script
 * fails loudly on any leftover `%TOKEN%` after substitution rather than
 * silently sending unrendered Apex to the org.
 *
 * Every --var value is escaped (see soql-escape.js) before substitution, so
 * callers must pass raw values — never pre-escape a value before handing it
 * to this script, that would double-escape it.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const { escapeSoqlLiteral } = require('./soql-escape');

function parseArgs(argv) {
  const templatePath = argv[0];
  const vars = {};
  for (let i = 1; i < argv.length; i += 1) {
    if (argv[i] !== '--var') continue;
    const pair = argv[i + 1];
    const eq = pair.indexOf('=');
    vars[pair.slice(0, eq)] = pair.slice(eq + 1);
    i += 1;
  }
  return { templatePath, vars };
}

function main() {
  const { templatePath, vars } = parseArgs(process.argv.slice(2));
  if (!templatePath) {
    console.error('Missing required <template-path>');
    process.exit(2);
  }

  let rendered = fs.readFileSync(templatePath, 'utf8');
  for (const [key, value] of Object.entries(vars)) {
    rendered = rendered.split(`%${key}%`).join(escapeSoqlLiteral(value));
  }

  const leftover = rendered.match(/%[A-Z_]+%/g);
  if (leftover) {
    console.error(`render-apex: unresolved placeholder(s): ${leftover.join(', ')}`);
    process.exit(2);
  }

  const outPath = path.join(
    os.tmpdir(),
    `rtr-datacloud-${path.basename(templatePath, '.apex')}-${process.pid}.apex`
  );
  fs.writeFileSync(outPath, rendered, 'utf8');
  console.log(outPath);
}

main();
