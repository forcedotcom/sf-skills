#!/usr/bin/env node
/**
 * Detects this org's namespace and derives every prefixed form this skill
 * needs, replacing the manual "run sf, read the JSON, compute NS_* by hand"
 * steps in SKILL.md's Namespace detection section. Same canonical procedure
 * as `setup-tpe-dashboard`'s Namespace detection step — never re-derive a
 * different way:
 *   1. `sf package installed list` — find the "Consumer Goods Cloud" entry,
 *      NS = its SubscriberPackageNamespace.
 *   2. Not found (source-deployed/dev-beta org) ⇒ `sf org display`'s
 *      `result.namespace`.
 *   3. Still null/blank ⇒ NS = "" (genuinely unnamespaced org).
 *
 * CLI usage:
 *   node detect-namespace.js --target-org <username>
 *
 * Prints one line of JSON to stdout: {"NS","NS_SEGMENT","NS_APEX","NS_FIELD"}.
 * Exit codes: 0 = success, 2 = usage/CLI error.
 */

const { execFileSync } = require('child_process');

function sfJson(cliArgs) {
  const raw = execFileSync('sf', cliArgs, { encoding: 'utf8' });
  return JSON.parse(raw).result;
}

function detectNamespace(targetOrg) {
  const packages = sfJson([
    'package', 'installed', 'list',
    '--target-org', targetOrg, '--json',
  ]);
  const cgCloud = (packages || []).find(
    (p) => p.SubscriberPackageName === 'Consumer Goods Cloud'
  );
  if (cgCloud && cgCloud.SubscriberPackageNamespace) {
    return cgCloud.SubscriberPackageNamespace;
  }

  const { namespace } = sfJson([
    'org', 'display',
    '--target-org', targetOrg, '--json',
  ]);
  return namespace || '';
}

function deriveForms(NS) {
  return {
    NS,
    NS_SEGMENT: NS ? `${NS}/` : '',
    NS_APEX: NS ? `${NS}.` : '',
    NS_FIELD: NS ? `${NS}__` : '',
  };
}

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
    process.exit(2);
  }
  return args[name];
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  const targetOrg = requireArg(args, 'target-org');
  const NS = detectNamespace(targetOrg);
  process.stdout.write(JSON.stringify(deriveForms(NS)));
}

if (require.main === module) {
  main();
}

module.exports = { detectNamespace, deriveForms };
