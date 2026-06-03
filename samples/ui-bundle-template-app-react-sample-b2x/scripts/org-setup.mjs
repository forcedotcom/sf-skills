#!/usr/bin/env node
/**
 * One-command setup: login, deploy, optional permset/data, GraphQL schema/codegen, UI bundle build.
 * Use this script to make setup easier for each app generated from this template.
 *
 * Usage:
 *   node scripts/org-setup.mjs --target-org <alias>           # interactive step picker (all selected)
 *   node scripts/org-setup.mjs --target-org <alias> --yes     # skip picker, run all steps
 *   node scripts/org-setup.mjs --target-org afv5 --skip-login
 *   node scripts/org-setup.mjs --target-org afv5 --skip-data --skip-ui-bundle-build
 *   node scripts/org-setup.mjs --target-org myorg --ui-bundle-name my-app
 *
 * Steps (in order):
 *   1. login     — sf org login web only if org not already connected (skip with --skip-login)
 *   2. uiBundle  — (all UI bundles) npm install && npm run build so dist exists for deploy (skip with --skip-ui-bundle-build)
 *   3. deploy    — sf project deploy start --target-org <alias> (requires dist for entity deployment)
 *   4. permset   — assign permsets per org-setup.config.json (skip with --skip-permset; override via --permset-name)
 *   5. data      — prepare unique fields + sf data import tree (skipped if no data dir/plan)
 *   6. graphql   — (in UI bundle) npm run graphql:schema then npm run graphql:codegen
 *   7. dev       — (in UI bundle) npm run dev — launch dev server (skip with --skip-dev)
 *
 * Permset assignment config (scripts/org-setup.config.json):
 *   {
 *     "permsetAssignments": {
 *       "assignments": {
 *         "My_Permset": { "assignee": "currentUser" },
 *         "Guest_Permset": { "assignee": "guestUser", "siteName": "mysite" },
 *         "Internal_Only": { "assignee": "skip" }
 *       }
 *     }
 *   }
 *   Assignee values: "currentUser", "skip", "guestUser" (requires siteName), or a specific username.
 *   Only permsets explicitly listed in assignments are assigned; unlisted permsets are skipped.
 */

import { spawnSync, spawn as nodeSpawn } from 'node:child_process';
import { resolve, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { readdirSync, existsSync, readFileSync, writeFileSync, unlinkSync } from 'node:fs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

/**
 * npm strips .gitignore from published packages — generate them on first run.
 * Templates are stored in scripts/gitignore-templates.json (generated at build
 * time from the actual .gitignore files) so the content lives in one place.
 * The JSON may not exist in git-cloned distributions where .gitignore is
 * already present, so loading is best-effort.
 */
function loadGitignoreTemplates() {
  const templatesPath = resolve(__dirname, 'gitignore-templates.json');
  if (!existsSync(templatesPath)) return null;
  try {
    return JSON.parse(readFileSync(templatesPath, 'utf8'));
  } catch {
    return null;
  }
}

function ensureGitignore(dir, content) {
  if (!content) return;
  const gitignorePath = resolve(dir, '.gitignore');
  if (!existsSync(gitignorePath)) {
    writeFileSync(gitignorePath, content, 'utf8');
    console.log(`Created .gitignore in ${dir}`);
  }
}

function resolveSfdxSource() {
  const sfdxPath = resolve(ROOT, 'sfdx-project.json');
  if (!existsSync(sfdxPath)) {
    console.error('Error: sfdx-project.json not found at project root.');
    process.exit(1);
  }
  const sfdxProject = JSON.parse(readFileSync(sfdxPath, 'utf8'));
  const pkgDir = sfdxProject?.packageDirectories?.[0]?.path;
  if (!pkgDir) {
    console.error('Error: No packageDirectories[].path found in sfdx-project.json.');
    process.exit(1);
  }
  return resolve(ROOT, pkgDir, 'main', 'default');
}

const SFDX_SOURCE = resolveSfdxSource();
const UIBUNDLES_DIR = resolve(SFDX_SOURCE, 'uiBundles');
const DATA_DIR = resolve(SFDX_SOURCE, 'data');
const DATA_PLAN = resolve(SFDX_SOURCE, 'data/data-plan.json');

function parseArgs() {
  const args = process.argv.slice(2);
  let targetOrg = null;
  let uiBundleName = null;
  /** If non-empty, only these names are assigned; otherwise all discovered from the project. */
  const permsetNamesExplicit = [];
  let yes = false;
  const flags = {
    skipLogin: false,
    skipDeploy: false,
    skipPermset: false,
    skipRole: false,
    skipData: false,
    skipGraphql: false,
    skipUIBundleBuild: false,
    skipSelfReg: false,
    skipDev: false,
  };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--target-org' && args[i + 1]) {
      targetOrg = args[++i];
    } else if (args[i] === '--ui-bundle-name' && args[i + 1]) {
      uiBundleName = args[++i];
    } else if (args[i] === '--permset-name' && args[i + 1]) {
      permsetNamesExplicit.push(args[++i]);
    } else if (args[i] === '--skip-login') flags.skipLogin = true;
    else if (args[i] === '--skip-deploy') flags.skipDeploy = true;
    else if (args[i] === '--skip-permset') flags.skipPermset = true;
    else if (args[i] === '--skip-role') flags.skipRole = true;
    else if (args[i] === '--skip-data') flags.skipData = true;
    else if (args[i] === '--skip-self-reg') flags.skipSelfReg = true;
    else if (args[i] === '--skip-graphql') flags.skipGraphql = true;
    else if (args[i] === '--skip-ui-bundle-build') flags.skipUIBundleBuild = true;
    else if (args[i] === '--skip-dev') flags.skipDev = true;
    else if (args[i] === '--yes' || args[i] === '-y') yes = true;
    else if (args[i] === '--help' || args[i] === '-h') {
      console.log(`
Setup CLI — one-command setup for apps in this project

Usage:
  node scripts/org-setup.mjs --target-org <alias> [options]

Required:
  --target-org <alias>   Target Salesforce org alias (e.g. myorg)

Options:
  --ui-bundle-name <name> UI bundle folder name under uiBundles/ (default: auto-detect)
  --permset-name <name>  Assign only this permission set (repeatable). Default: all sets under permissionsets/
  --skip-login           Skip login step (login is auto-skipped if org is already connected)
  --skip-deploy          Do not deploy metadata
  --skip-permset         Do not assign permission set
  --skip-data            Do not prepare data or run data import
  --skip-graphql         Do not fetch schema or run GraphQL codegen
  --skip-ui-bundle-build Do not npm install / build the UI bundle
  --skip-dev             Do not launch the dev server at the end
  -y, --yes              Skip interactive step picker; run all enabled steps immediately
  -h, --help             Show this help

Permset config (scripts/org-setup.config.json):
  Control per-permset assignment via a config file. Example:
    {
      "permsetAssignments": {
        "assignments": {
          "My_Permset": { "assignee": "currentUser" },
          "Guest_Permset": { "assignee": "guestUser", "siteName": "mysite" },
          "Internal_Only": { "assignee": "skip" }
        }
      }
    }
  Assignee values: "currentUser", "skip", "guestUser" (requires siteName), or a specific username.
  Only permsets explicitly listed in assignments are assigned; unlisted permsets are skipped.
`);
      process.exit(0);
    }
  }
  if (!targetOrg) {
    console.error('Error: --target-org <alias> is required.');
    process.exit(1);
  }
  return { targetOrg, uiBundleName, permsetNamesExplicit, yes, ...flags };
}

function discoverAllUIBundleDirs(uiBundleName) {
  if (!existsSync(UIBUNDLES_DIR)) {
    console.error(`Error: uiBundles directory not found: ${UIBUNDLES_DIR}`);
    process.exit(1);
  }
  const entries = readdirSync(UIBUNDLES_DIR, { withFileTypes: true });
  const dirs = entries.filter((e) => e.isDirectory() && !e.name.startsWith('.'));
  if (dirs.length === 0) {
    console.error(`Error: No UI bundle folder found under ${UIBUNDLES_DIR}`);
    process.exit(1);
  }
  if (uiBundleName) {
    const requested = dirs.find((d) => d.name === uiBundleName);
    if (!requested) {
      console.error(`Error: UI bundle directory not found: ${uiBundleName}`);
      process.exit(1);
    }
    return [resolve(UIBUNDLES_DIR, requested.name)];
  }
  return dirs.map((d) => resolve(UIBUNDLES_DIR, d.name));
}

function discoverUIBundleDir(uiBundleName) {
  const all = discoverAllUIBundleDirs(uiBundleName);
  if (all.length > 1 && !uiBundleName) {
    console.log(`Multiple UI bundles found; using first: ${all[0].split(/[/\\]/).pop()}`);
  }
  return all[0];
}

/** API names from permissionsets/*.permissionset-meta.xml in the first package directory. */
function discoverPermissionSetNames() {
  const dir = resolve(SFDX_SOURCE, 'permissionsets');
  if (!existsSync(dir)) return [];
  const names = [];
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (!entry.isFile()) continue;
    const m = entry.name.match(/^(.+)\.permissionset-meta\.xml$/);
    if (m) names.push(m[1]);
  }
  return names.sort();
}

/**
 * Load permset assignment configuration from org-setup.config.json.
 *
 * Config shape:
 *   {
 *     "permsetAssignments": {
 *       "assignments": {
 *         "My_Permset":       { "assignee": "currentUser" },
 *         "My_Guest_Permset": { "assignee": "guestUser", "siteName": "mysite" },
 *         "Internal_Only":    { "assignee": "skip" }
 *       }
 *     }
 *   }
 *
 * Assignee values:
 *   "currentUser" — assign to the user running the script
 *   "skip"        — do not assign this permset
 *   "guestUser"   — resolve the site guest user automatically (requires siteName)
 *   "<username>"  — assign to a specific user via --on-behalf-of
 *
 * Only permsets explicitly listed in assignments are assigned; unlisted permsets are skipped.
 *
 * Returns { assignments: Record<string, { assignee: string, siteName?: string }> }
 */
function loadPermsetConfig() {
  const configPath = resolve(__dirname, 'org-setup.config.json');
  const defaults = { assignments: {} };
  if (!existsSync(configPath)) return defaults;
  try {
    const raw = JSON.parse(readFileSync(configPath, 'utf8'));
    const section = raw?.permsetAssignments;
    if (!section) return defaults;
    return {
      assignments: section.assignments || {},
    };
  } catch (err) {
    console.warn(`Warning: failed to parse org-setup.config.json: ${err.message}; using defaults.`);
    return defaults;
  }
}

/** Resolve the effective assignment config for a given permset name. */
function resolveAssignment(permsetName, permsetConfig) {
  const override = permsetConfig.assignments[permsetName];
  if (!override) return { assignee: 'skip' };
  return { assignee: override.assignee || 'skip', siteName: override.siteName };
}

/**
 * Load role assignment config from org-setup.config.json.
 *
 * Config shape:
 *   { "role": { "assignee": "currentUser", "roleName": "Admin" } }
 *
 * Returns null if no "role" section exists in config (the step is hidden).
 */
function loadRoleConfig() {
  const configPath = resolve(__dirname, 'org-setup.config.json');
  if (!existsSync(configPath)) return null;
  try {
    const raw = JSON.parse(readFileSync(configPath, 'utf8'));
    const section = raw?.role;
    if (!section) return null;
    return {
      assignee: section.assignee || 'currentUser',
      roleName: section.roleName || null,
    };
  } catch {
    return null;
  }
}

/**
 * Load self-registration config from org-setup.config.json.
 *
 * Config shape:
 *   {
 *     "selfRegistration": {
 *       "siteName": "myapp",
 *       "selfRegProfile": "myapp Profile",
 *       "accountName": "My Self-Reg Account"
 *     }
 *   }
 *
 * Returns null if no "selfRegistration" section exists in config (the step is hidden).
 */
function loadSelfRegConfig() {
  const configPath = resolve(__dirname, 'org-setup.config.json');
  if (!existsSync(configPath)) return null;
  try {
    const raw = JSON.parse(readFileSync(configPath, 'utf8'));
    const section = raw?.selfRegistration;
    if (!section) return null;
    return {
      siteName: section.siteName || null,
      selfRegProfile: section.selfRegProfile || null,
      accountName: section.accountName || null,
    };
  } catch {
    return null;
  }
}

/**
 * Ensure the self-registration profile is listed in networkMemberGroups.
 * This must happen BEFORE the initial deploy so that the profile is a recognised
 * site member when subsequent steps (selfRegProfile, selfRegistration=true) are deployed.
 */
function ensureNetworkMemberProfile(selfRegConfig) {
  const { siteName, selfRegProfile } = selfRegConfig;
  if (!siteName || !selfRegProfile) return;

  const networkXmlPath = resolve(SFDX_SOURCE, 'networks', `${siteName}.network-meta.xml`);
  if (!existsSync(networkXmlPath)) {
    console.log(`  Network metadata not found: ${networkXmlPath}; skipping member group update.`);
    return;
  }
  const xml = readFileSync(networkXmlPath, 'utf8');

  // Check if profile is already in networkMemberGroups
  const profileEscaped = selfRegProfile.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const profileRegex = new RegExp(`<profile>\\s*${profileEscaped}\\s*</profile>`);
  if (profileRegex.test(xml)) {
    console.log(`  Profile "${selfRegProfile}" already in networkMemberGroups; no update needed.`);
    return;
  }

  // Add the profile to networkMemberGroups
  const updatedXml = xml.replace(
    /(<networkMemberGroups>)/,
    `$1\n        <profile>${selfRegProfile}</profile>`
  );
  writeFileSync(networkXmlPath, updatedXml);
  console.log(`  Added profile "${selfRegProfile}" to networkMemberGroups in ${siteName}.network-meta.xml`);
}

/**
 * Enable self-registration for an Experience Cloud network.
 *
 * 1. Modify the network metadata XML to set selfRegistration=true and add selfRegProfile.
 * 2. Re-deploy the modified network metadata.
 * 3. Create an Account record (idempotent).
 * 4. Create a NetworkSelfRegistration record linking the Account to the Network (idempotent).
 */
function enableSelfRegistration(selfRegConfig, targetOrg) {
  const { siteName, selfRegProfile, accountName } = selfRegConfig;

  // 1. Modify network metadata XML
  const networkXmlPath = resolve(SFDX_SOURCE, 'networks', `${siteName}.network-meta.xml`);
  if (!existsSync(networkXmlPath)) {
    console.error(`  Network metadata not found: ${networkXmlPath}`);
    return;
  }
  const xml = readFileSync(networkXmlPath, 'utf8');

  // Skip network modification and deploy if self-registration is already configured
  const alreadyEnabled = /<selfRegistration>true<\/selfRegistration>/.test(xml);
  const alreadyHasProfile = /<selfRegProfile>/.test(xml);
  if (alreadyEnabled || alreadyHasProfile) {
    console.log(`  Network "${siteName}" already has self-registration configured; skipping metadata update and deploy.`);
  } else {
    // Set selfRegistration to true and add selfRegProfile
    let updatedXml = xml.replace(
      /<selfRegistration>false<\/selfRegistration>/,
      '<selfRegistration>true</selfRegistration>'
    );
    updatedXml = updatedXml.replace(
      /(\s*)(<selfRegistration>)/,
      `$1<selfRegProfile>${selfRegProfile}</selfRegProfile>\n$1$2`
    );

    writeFileSync(networkXmlPath, updatedXml);
    console.log(`  Updated ${siteName}.network-meta.xml: selfRegistration=true, selfRegProfile=${selfRegProfile}`);

    // Re-deploy only the network file
    const deployResult = spawnSync('sf', [
      'project', 'deploy', 'start',
      '--target-org', targetOrg,
      '--source-dir', networkXmlPath,
    ], { cwd: ROOT, stdio: 'inherit', shell: true, timeout: 120000 });
    if (deployResult.status !== 0) {
      console.error('  Failed to deploy updated network metadata.');
      process.exit(deployResult.status ?? 1);
    }
  }

  // 3. Create Account (idempotent)
  const acctQuery = `SELECT Id FROM Account WHERE Name = '${accountName.replace(/'/g, "\\'")}' LIMIT 1`;
  const acctQueryResult = spawnSync('sf', [
    'data', 'query',
    '--query', acctQuery,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  let accountId = null;
  if (acctQueryResult.status === 0) {
    try {
      const json = JSON.parse(acctQueryResult.stdout);
      accountId = json.result?.records?.[0]?.Id || null;
    } catch { /* proceed to create */ }
  }
  if (accountId) {
    console.log(`  Account "${accountName}" already exists (${accountId}); skipping creation.`);
  } else {
    const createResult = spawnSync('sf', [
      'data', 'create', 'record',
      '--sobject', 'Account',
      '--values', `Name='${accountName}'`,
      '--target-org', targetOrg,
      '--json',
    ], { cwd: ROOT, encoding: 'utf8' });
    if (createResult.status !== 0) {
      console.error(`  Failed to create Account "${accountName}".`);
      if (createResult.stderr) console.error(createResult.stderr);
      return;
    }
    try {
      const json = JSON.parse(createResult.stdout);
      accountId = json.result?.id;
      console.log(`  Created Account "${accountName}" (${accountId}).`);
    } catch {
      console.error('  Failed to parse Account creation result.');
      return;
    }
  }

  // 4. Query Network Id
  const netQuery = `SELECT Id FROM Network WHERE Name = '${siteName}'`;
  const netResult = spawnSync('sf', [
    'data', 'query',
    '--query', netQuery,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  let networkId = null;
  if (netResult.status === 0) {
    try {
      const json = JSON.parse(netResult.stdout);
      networkId = json.result?.records?.[0]?.Id || null;
    } catch { /* fall through */ }
  }
  if (!networkId) {
    console.error(`  Could not find Network "${siteName}" in org.`);
    return;
  }
  console.log(`  Found Network "${siteName}" (${networkId}).`);

  // 5. Create NetworkSelfRegistration (idempotent)
  const nsrQuery = `SELECT Id FROM NetworkSelfRegistration WHERE NetworkId = '${networkId}'`;
  const nsrResult = spawnSync('sf', [
    'data', 'query',
    '--query', nsrQuery,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  let nsrExists = false;
  if (nsrResult.status === 0) {
    try {
      const json = JSON.parse(nsrResult.stdout);
      nsrExists = (json.result?.records?.length || 0) > 0;
    } catch { /* proceed to create */ }
  }
  if (nsrExists) {
    console.log('  NetworkSelfRegistration record already exists; skipping.');
  } else {
    const tmpApex = resolve(ROOT, '.tmp-setup-selfreg.apex');
    const apex = [
      `Account acct = [SELECT Id FROM Account WHERE Id = '${accountId}' LIMIT 1];`,
      `NetworkSelfRegistration nsr = new NetworkSelfRegistration();`,
      `nsr.AccountId = acct.Id;`,
      `nsr.NetworkId = '${networkId}';`,
      `insert nsr;`,
      `System.debug('NSR_CREATED:' + nsr.Id);`,
    ].join('\n');
    writeFileSync(tmpApex, apex);
    const apexResult = spawnSync('sf', [
      'apex', 'run', '--target-org', targetOrg, '--file', tmpApex,
    ], { cwd: ROOT, stdio: 'pipe', shell: true, timeout: 60000 });
    const apexOut = apexResult.stdout?.toString() || '';
    if (existsSync(tmpApex)) unlinkSync(tmpApex);
    if (apexResult.status !== 0 && !apexOut.includes('Compiled successfully')) {
      console.error('  Failed to create NetworkSelfRegistration record.');
      process.stderr.write(apexResult.stderr?.toString() || apexOut);
      return;
    }
    const nsrMatch = apexOut.match(/NSR_CREATED:(\w+)/);
    if (nsrMatch) {
      console.log(`  Created NetworkSelfRegistration (${nsrMatch[1]}).`);
    } else {
      console.log('  NetworkSelfRegistration creation executed.');
    }
  }
}

/**
 * Assign a role to the current user so that Experience Cloud self-registration
 * works correctly.
 */
function assignRoleToCurrentUser(roleName, targetOrg) {
  const roleQuery = `SELECT Id FROM UserRole WHERE Name = '${roleName}'`;
  const roleResult = spawnSync('sf', [
    'data', 'query',
    '--query', roleQuery,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  if (roleResult.status !== 0) {
    console.error(`  Failed to query role "${roleName}" in org.`);
    if (roleResult.stderr) console.error(roleResult.stderr);
    return;
  }
  let roleId;
  try {
    const json = JSON.parse(roleResult.stdout);
    const records = json.result?.records;
    if (!records || records.length === 0) {
      console.error(`  Role "${roleName}" not found in org; skipping.`);
      return;
    }
    roleId = records[0].Id;
  } catch {
    console.error(`  Failed to parse role query result for "${roleName}".`);
    return;
  }

  const orgResult = spawnSync('sf', [
    'org', 'display',
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  if (orgResult.status !== 0) {
    console.error('  Failed to resolve current user from org.');
    return;
  }
  let username;
  try {
    const json = JSON.parse(orgResult.stdout);
    username = json.result?.username;
    if (!username) {
      console.error('  Could not determine current username from org display.');
      return;
    }
  } catch {
    console.error('  Failed to parse org display result.');
    return;
  }

  const userQuery = `SELECT Id, UserRoleId FROM User WHERE Username = '${username}'`;
  const userResult = spawnSync('sf', [
    'data', 'query',
    '--query', userQuery,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  if (userResult.status === 0) {
    try {
      const json = JSON.parse(userResult.stdout);
      const userRecord = json.result?.records?.[0];
      if (userRecord?.UserRoleId) {
        console.log(`  User ${username} already has a role assigned; skipping to avoid overriding.`);
        return;
      }
    } catch { /* continue */ }
  }

  const updateResult = spawnSync('sf', [
    'data', 'update', 'record',
    '--sobject', 'User',
    '--where', `Username='${username}'`,
    '--values', `UserRoleId='${roleId}'`,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  if (updateResult.status === 0) {
    console.log(`  Role "${roleName}" assigned to ${username}.`);
  } else {
    const out = (updateResult.stderr?.toString() || '') + (updateResult.stdout?.toString() || '');
    console.error(`  Failed to assign role "${roleName}" to ${username}.`);
    if (out) console.error(out);
  }
}

/**
 * Query the org for a guest user whose profile name matches the given site name.
 */
function resolveGuestUsername(siteName, targetOrg) {
  const query = `SELECT Username FROM User WHERE Profile.Name LIKE '%${siteName}%' AND UserType = 'Guest'`;
  const result = spawnSync('sf', [
    'data', 'query',
    '--query', query,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  if (result.status !== 0) {
    console.error(`  Failed to query guest user for site "${siteName}".`);
    if (result.stderr) console.error(result.stderr);
    return null;
  }
  try {
    const json = JSON.parse(result.stdout);
    const records = json.result?.records;
    if (!records || records.length === 0) {
      console.error(`  No guest user found for site "${siteName}".`);
      return null;
    }
    return records[0].Username;
  } catch {
    console.error(`  Failed to parse guest user query result for site "${siteName}".`);
    return null;
  }
}

function isOrgConnected(targetOrg) {
  const result = spawnSync('sf', ['org', 'display', '--target-org', targetOrg, '--json'], {
    cwd: ROOT,
    stdio: 'pipe',
    shell: true,
  });
  return result.status === 0;
}

function apexLiteral(value) {
  if (value === null || value === undefined) return 'null';
  if (typeof value === 'boolean') return String(value);
  if (typeof value === 'number') return String(value);
  const s = String(value);
  if (/^\d{4}-\d{2}-\d{2}$/.test(s)) return `Date.valueOf('${s}')`;
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(s)) {
    const dt = s.replace('T', ' ').replace(/\.\d+/, '').replace('Z', '');
    return `DateTime.valueOf('${dt}')`;
  }
  return "'" + s.replace(/\\/g, '\\\\').replace(/'/g, "\\'") + "'";
}

function buildApexInsert(sobject, records, refIds) {
  const lines = [
    'Database.DMLOptions dmlOpts = new Database.DMLOptions();',
    'dmlOpts.DuplicateRuleHeader.allowSave = true;',
    `List<${sobject}> recs = new List<${sobject}>();`,
  ];
  for (const rec of records) {
    lines.push(`{ ${sobject} r = new ${sobject}();`);
    for (const [key, val] of Object.entries(rec)) {
      if (key === 'attributes') continue;
      lines.push(`r.put('${key}', ${apexLiteral(val)});`);
    }
    lines.push('recs.add(r); }');
  }
  lines.push('Database.SaveResult[] results = Database.insert(recs, dmlOpts);');
  const refArray = refIds.map((r) => `'${r}'`).join(',');
  lines.push(`String[] refs = new String[]{${refArray}};`);
  lines.push('for (Integer i = 0; i < results.size(); i++) {');
  lines.push("  if (results[i].isSuccess()) System.debug('REF:' + refs[i] + ':' + results[i].getId());");
  lines.push("  else System.debug('ERR:' + refs[i] + ':' + results[i].getErrors()[0].getMessage());");
  lines.push('}');
  return lines.join('\n');
}

/**
 * Interactive multi-select: arrow keys navigate, space toggles, 'a' toggles all, enter confirms.
 * Returns a boolean[] matching the input order.  Falls through immediately when stdin is not a TTY.
 */
async function promptSteps(steps) {
  if (!process.stdin.isTTY) return steps.map((s) => s.enabled);

  const selected = steps.map((s) => s.enabled);
  let cursor = 0;
  const DIM = '\x1B[2m';
  const RST = '\x1B[0m';
  const CYAN = '\x1B[36m';
  const GREEN = '\x1B[32m';

  /** Strip ANSI escape sequences to get visible character count. */
  function visibleLength(str) {
    return str.replace(/\x1B\[[0-9;]*m/g, '').length;
  }

  /** Count how many terminal rows a set of lines occupies (accounting for wrapping). */
  function terminalRows(lines) {
    const cols = process.stdout.columns || 80;
    let rows = 0;
    for (const line of lines) {
      const len = visibleLength(line);
      rows += len === 0 ? 1 : Math.ceil(len / cols);
    }
    return rows;
  }

  function render() {
    return steps.map((s, i) => {
      const ptr = i === cursor ? `${CYAN}❯${RST}` : ' ';
      if (!s.available) return `${ptr} ${DIM}○ ${s.label} (n/a)${RST}`;
      const chk = selected[i] ? `${GREEN}●${RST}` : '○';
      return `${ptr} ${chk} ${s.label}`;
    });
  }

  let prevRows = 0;

  return new Promise((resolve) => {
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.setEncoding('utf8');
    process.stdout.write('\x1B[?25l');
    console.log('\nSelect steps (↑↓ move, space toggle, a all, enter confirm):\n');
    const initialLines = render();
    prevRows = terminalRows(initialLines);
    process.stdout.write(initialLines.join('\n') + '\n');

    function redraw() {
      process.stdout.write(`\x1B[${prevRows}A`);
      const lines = render();
      for (const line of lines) process.stdout.write(`\x1B[2K${line}\n`);
      prevRows = terminalRows(lines);
    }

    process.stdin.on('data', (key) => {
      if (key === '\x03') {
        process.stdout.write('\x1B[?25h\n');
        process.exit(0);
      }
      if (key === '\r' || key === '\n') {
        process.stdout.write('\x1B[?25h');
        process.stdin.setRawMode(false);
        process.stdin.pause();
        process.stdin.removeAllListeners('data');
        console.log();
        resolve(selected);
        return;
      }
      if (key === ' ') {
        if (steps[cursor].available) selected[cursor] = !selected[cursor];
        redraw();
        return;
      }
      if (key === 'a') {
        const allOn = steps.every((s, i) => !s.available || selected[i]);
        for (let i = 0; i < steps.length; i++) {
          if (steps[i].available) selected[i] = !allOn;
        }
        redraw();
        return;
      }
      if (key === '\x1B[A' || key === 'k') {
        cursor = Math.max(0, cursor - 1);
        redraw();
      } else if (key === '\x1B[B' || key === 'j') {
        cursor = Math.min(steps.length - 1, cursor + 1);
        redraw();
      }
    });
  });
}

function run(name, cmd, args, opts = {}) {
  const { cwd = ROOT, optional = false } = opts;
  console.log('\n---', name, '---');
  const result = spawnSync(cmd, args, {
    cwd,
    stdio: 'inherit',
    shell: true,
    ...(opts.timeout && { timeout: opts.timeout }),
  });
  if (result.status !== 0 && !optional) {
    console.error(`\nSetup failed at step: ${name}`);
    process.exit(result.status ?? 1);
  }
  return result;
}

/** Promise-based spawn for parallel execution. Always uses stdio: 'pipe'. */
function spawnAsync(cmd, args, opts = {}) {
  return new Promise((resolve, reject) => {
    const proc = nodeSpawn(cmd, args, {
      cwd: opts.cwd || ROOT,
      stdio: 'pipe',
      shell: true,
      ...(opts.timeout && { timeout: opts.timeout }),
    });
    let stdout = '';
    let stderr = '';
    proc.stdout.on('data', (d) => { stdout += d.toString(); });
    proc.stderr.on('data', (d) => { stderr += d.toString(); });
    proc.on('close', (code) => resolve({ status: code, stdout, stderr }));
    proc.on('error', reject);
  });
}

/** Async version of run() for parallel steps. Captures output and prints on failure. */
async function runAsync(name, cmd, args, opts = {}) {
  const { cwd = ROOT, optional = false } = opts;
  const result = await spawnAsync(cmd, args, { cwd, ...(opts.timeout && { timeout: opts.timeout }) });
  if (result.status !== 0 && !optional) {
    if (result.stdout) process.stdout.write(result.stdout);
    if (result.stderr) process.stderr.write(result.stderr);
    console.error(`\nSetup failed at step: ${name}`);
    process.exit(result.status ?? 1);
  }
  return result;
}

async function main() {
  // Ensure .gitignore files exist (npm strips them from published packages).
  const gitignoreTemplates = loadGitignoreTemplates();
  if (gitignoreTemplates) {
    ensureGitignore(ROOT, gitignoreTemplates.sfdx);
    if (existsSync(UIBUNDLES_DIR)) {
      for (const entry of readdirSync(UIBUNDLES_DIR, { withFileTypes: true })) {
        if (entry.isDirectory() && !entry.name.startsWith('.')) {
          ensureGitignore(resolve(UIBUNDLES_DIR, entry.name), gitignoreTemplates.webapp);
        }
      }
    }
  }

  const {
    targetOrg,
    uiBundleName,
    permsetNamesExplicit,
    yes,
    skipLogin: argSkipLogin,
    skipDeploy: argSkipDeploy,
    skipPermset: argSkipPermset,
    skipRole: argSkipRole,
    skipSelfReg: argSkipSelfReg,
    skipData: argSkipData,
    skipGraphql: argSkipGraphql,
    skipUIBundleBuild: argSkipUIBundleBuild,
    skipDev: argSkipDev,
  } = parseArgs();

  const permsetNames =
    permsetNamesExplicit.length > 0 ? permsetNamesExplicit : discoverPermissionSetNames();
  const permsetStepLabel =
    permsetNames.length === 0
      ? 'Permset — (none under permissionsets/)'
      : permsetNames.length <= 3
        ? `Permset — assign ${permsetNames.join(', ')}`
        : `Permset — assign ${permsetNames.length} permission sets`;

  const hasDataPlan = existsSync(DATA_PLAN) && existsSync(DATA_DIR);
  const roleConfig = loadRoleConfig();
  const hasRoleConfig = roleConfig !== null;
  const selfRegConfig = loadSelfRegConfig();
  const hasSelfRegConfig = selfRegConfig !== null;

  const stepDefs = [
    { key: 'login', label: 'Login — org authentication', enabled: !argSkipLogin, available: true },
    { key: 'uiBundleBuild', label: 'UI Bundle Build — npm install + build (pre-deploy)', enabled: !argSkipUIBundleBuild, available: true },
    { key: 'deploy', label: 'Deploy — sf project deploy start', enabled: !argSkipDeploy, available: true },
    { key: 'permset', label: permsetStepLabel, enabled: !argSkipPermset, available: true },
    { key: 'role', label: `Role — assign "${roleConfig?.roleName ?? '?'}" to current user`, enabled: !argSkipRole && hasRoleConfig, available: hasRoleConfig },
    { key: 'selfReg', label: `Self-Registration — enable for "${selfRegConfig?.siteName ?? '?'}"`, enabled: !argSkipSelfReg && hasSelfRegConfig, available: hasSelfRegConfig },
    { key: 'data', label: 'Data — delete + import records via Apex', enabled: !argSkipData && hasDataPlan, available: hasDataPlan },
    { key: 'graphql', label: 'GraphQL — schema introspect + codegen', enabled: !argSkipGraphql, available: true },
    { key: 'dev', label: 'Dev — launch dev server', enabled: !argSkipDev, available: true },
  ];

  const selections = yes ? stepDefs.map((s) => s.enabled) : await promptSteps(stepDefs);
  const on = {};
  stepDefs.forEach((s, i) => {
    on[s.key] = selections[i];
  });

  const skipLogin = !on.login;
  const skipUIBundleBuild = !on.uiBundleBuild;
  const skipDeploy = !on.deploy;
  const skipPermset = !on.permset;
  const skipRole = !on.role;
  const skipSelfReg = !on.selfReg;
  const skipData = !on.data;
  const skipGraphql = !on.graphql;
  const skipDev = !on.dev;

  const needsUIBundle = !skipUIBundleBuild || !skipGraphql || !skipDev;
  const uiBundleDir = needsUIBundle ? discoverUIBundleDir(uiBundleName) : null;
  const doData = !skipData;

  console.log('Setup — target org:', targetOrg, '| UI bundle:', uiBundleDir ?? '(none)');
  console.log(
    'Steps: login=%s deploy=%s permset=%s role=%s selfReg=%s data=%s graphql=%s uiBundle=%s dev=%s',
    !skipLogin,
    !skipDeploy,
    !skipPermset,
    !skipRole,
    !skipSelfReg,
    doData,
    !skipGraphql,
    !skipUIBundleBuild,
    !skipDev
  );

  if (!skipLogin) {
    if (isOrgConnected(targetOrg)) {
      console.log('\n--- Login ---');
      console.log(`Org ${targetOrg} is already authenticated; skipping browser login.`);
    } else {
      run('Login (browser)', 'sf', ['org', 'login', 'web', '--alias', targetOrg], { optional: true });
    }
  }

  // Ensure the self-reg profile is in networkMemberGroups before deploy so that
  // subsequent selfRegProfile / selfRegistration updates don't fail.
  if (!skipDeploy && selfRegConfig) {
    console.log('\n--- Ensure network member profile (pre-deploy) ---');
    ensureNetworkMemberProfile(selfRegConfig);
  }

  // Build all UI Bundles before deploy so dist exists for entity deployment
  if (!skipDeploy && !skipUIBundleBuild) {
    const allUIBundleDirs = discoverAllUIBundleDirs(uiBundleName);
    for (const dir of allUIBundleDirs) {
      const name = dir.split(/[/\\]/).pop();
      run(`UI Bundle install (${name})`, 'npm', ['install'], { cwd: dir });
      run(`UI Bundle build (${name})`, 'npm', ['run', 'build'], { cwd: dir });
    }
  }

  if (!skipDeploy) {
    run('Deploy metadata', 'sf', ['project', 'deploy', 'start', '--target-org', targetOrg], {
      timeout: 180000,
    });
  }

  if (!skipPermset) {
    const permsetConfig = loadPermsetConfig();
    if (permsetNames.length === 0) {
      console.log('\n--- Assign permission sets ---');
      console.log('No permission sets found under permissionsets/ and none passed via --permset-name; skipping.');
    } else {
      console.log('\n--- Assign permission sets ---');

      // Resolve assignments (guest user lookups etc.) then run all sf assign calls in parallel.
      const assignmentJobs = [];
      for (const permsetName of permsetNames) {
        const assignment = resolveAssignment(permsetName, permsetConfig);
        if (assignment.assignee === 'skip') {
          console.log(`Permission set "${permsetName}" — skipped (config).`);
          continue;
        }
        let effectiveUsername = null;
        if (assignment.assignee === 'guestUser') {
          if (!assignment.siteName) {
            console.error(`Permission set "${permsetName}" — assignee is "guestUser" but no "siteName" configured; skipping.`);
            continue;
          }
          effectiveUsername = resolveGuestUsername(assignment.siteName, targetOrg);
          if (!effectiveUsername) {
            console.error(`Permission set "${permsetName}" — could not resolve guest user for site "${assignment.siteName}"; skipping.`);
            continue;
          }
          console.log(`  Resolved guest user for site "${assignment.siteName}": ${effectiveUsername}`);
        } else if (assignment.assignee !== 'currentUser') {
          effectiveUsername = assignment.assignee;
        }
        assignmentJobs.push({ permsetName, effectiveUsername });
      }

      // Run all permset assignment calls in parallel.
      const assignResults = await Promise.all(assignmentJobs.map(async ({ permsetName, effectiveUsername }) => {
        const sfArgs = ['org', 'assign', 'permset', '--name', permsetName, '--target-org', targetOrg];
        if (effectiveUsername) {
          sfArgs.push('--on-behalf-of', effectiveUsername);
        }
        const assigneeLabel = effectiveUsername || 'current user';
        const result = await spawnAsync('sf', sfArgs);
        return { permsetName, assigneeLabel, result };
      }));

      for (const { permsetName, assigneeLabel, result } of assignResults) {
        if (result.status === 0) {
          console.log(`Permission set "${permsetName}" assigned to ${assigneeLabel}.`);
        } else {
          const out = (result.stderr || '') + (result.stdout || '');
          if (out.includes('Duplicate') && out.includes('PermissionSet')) {
            console.log(`Permission set "${permsetName}" already assigned to ${assigneeLabel}; skipping.`);
          } else if (out.includes('not found') && out.includes('target org')) {
            console.log(`Permission set "${permsetName}" not in org; skipping.`);
          } else {
            if (result.stdout) process.stdout.write(result.stdout);
            if (result.stderr) process.stderr.write(result.stderr);
            console.error(`\nSetup failed at step: Assign permission set (${permsetName})`);
            process.exit(result.status ?? 1);
          }
        }
      }
    }
  }

  if (!skipRole) {
    console.log('\n--- Assign role ---');
    if (roleConfig?.assignee !== 'currentUser') {
      console.error(`Role assignee "${roleConfig?.assignee}" is not supported; only "currentUser" is allowed. Skipping.`);
    } else if (!roleConfig?.roleName) {
      console.error('Role step enabled but no "roleName" specified in org-setup.config.json; skipping.');
    } else {
      assignRoleToCurrentUser(roleConfig.roleName, targetOrg);
    }
  }

  if (!skipSelfReg) {
    console.log('\n--- Enable self-registration ---');
    if (!selfRegConfig?.siteName || !selfRegConfig?.selfRegProfile || !selfRegConfig?.accountName) {
      console.error('Self-registration config is incomplete (need siteName, selfRegProfile, accountName); skipping.');
    } else {
      enableSelfRegistration(selfRegConfig, targetOrg);
    }
  }

  if (doData) {
    // Prepare data for uniqueness (run before import so repeat imports don't conflict)
    const prepareScript = resolve(__dirname, 'prepare-import-unique-fields.js');
    run('Prepare data (unique fields)', 'node', [prepareScript, '--data-dir', DATA_DIR], {
      cwd: ROOT,
    });
    // Normalize Lease__c Tenant refs to 1–15 so all refs resolve (Tenant__c.json has 15 records)
    const leasePath = resolve(DATA_DIR, 'Lease__c.json');
    if (existsSync(leasePath)) {
      let leaseContent = readFileSync(leasePath, 'utf8');
      leaseContent = leaseContent.replace(/@TenantRef(\d+)/g, (_m, n) => {
        const k = ((parseInt(n, 10) - 1) % 15) + 1;
        return `@TenantRef${k}`;
      });
      writeFileSync(leasePath, leaseContent);
    }

    // Delete existing records so every run inserts the full dataset without duplicate conflicts.
    // Reverse plan order ensures children are removed before parents (FK safety).
    console.log('\n--- Clean existing data for fresh import ---');
    const planEntries = JSON.parse(readFileSync(DATA_PLAN, 'utf8'));
    const sobjectsReversed = [...planEntries.map((e) => e.sobject)].reverse();
    const tmpApex = resolve(ROOT, '.tmp-setup-delete.apex');
    for (const sobject of sobjectsReversed) {
      const apexCode = [
        'try {',
        `  List<SObject> recs = Database.query('SELECT Id FROM ${sobject} LIMIT 10000');`,
        '  if (!recs.isEmpty()) {',
        '    Database.delete(recs, false);',
        '    Database.emptyRecycleBin(recs);',
        '  }',
        '} catch (Exception e) {',
        '  // non-deletable records (e.g. Contact linked to Case) are skipped via allOrNone=false',
        '}',
      ].join('\n');
      writeFileSync(tmpApex, apexCode);
      spawnSync('sf', ['apex', 'run', '--target-org', targetOrg, '--file', tmpApex], {
        cwd: ROOT,
        stdio: 'pipe',
        shell: true,
        timeout: 60000,
      });
      console.log(`  ${sobject}: cleaned`);
    }
    if (existsSync(tmpApex)) unlinkSync(tmpApex);

    // Import via Anonymous Apex with Database.DMLOptions.duplicateRuleHeader.allowSave = true.
    // This bypasses both duplicate-rule blocks AND matching-service timeouts that the REST
    // API headers (Sforce-Duplicate-Rule-Action) cannot override.
    console.log('\n--- Data import tree ---');
    const refMap = new Map();
    const APEX_CHAR_LIMIT = 25000;
    const APEX_MAX_BATCH = 200;

    for (const entry of planEntries) {
      for (const file of entry.files) {
        const data = JSON.parse(readFileSync(resolve(DATA_DIR, file), 'utf8'));
        const records = data.records || [];

        for (const rec of records) {
          for (const key of Object.keys(rec)) {
            if (key === 'attributes') continue;
            const val = rec[key];
            if (typeof val === 'string' && val.startsWith('@')) {
              const actual = refMap.get(val.slice(1));
              if (actual) {
                rec[key] = actual;
              } else if (refMap.size > 0) {
                console.warn(`    Warning: unresolved ref ${val} in ${file}`);
              }
            }
          }
        }

        let imported = 0;
        const sampleRec = records[0] || {};
        const fieldsPerRec = Object.keys(sampleRec).filter((k) => k !== 'attributes').length;
        const estCharsPerRec = 40 + fieldsPerRec * 55;
        const batchSize = Math.min(APEX_MAX_BATCH, Math.max(5, Math.floor(APEX_CHAR_LIMIT / estCharsPerRec)));
        for (let i = 0; i < records.length; i += batchSize) {
          const batch = records.slice(i, i + batchSize);
          const refIds = batch.map((r) => r.attributes?.referenceId || `_idx${i}`);
          const apex = buildApexInsert(entry.sobject, batch, refIds);
          writeFileSync(tmpApex, apex);
          const apexResult = spawnSync(
            'sf',
            ['apex', 'run', '--target-org', targetOrg, '--file', tmpApex],
            { cwd: ROOT, stdio: 'pipe', shell: true, timeout: 120000 }
          );
          const apexOut = apexResult.stdout?.toString() || '';
          const apexErr = apexResult.stderr?.toString() || '';
          if (apexResult.status !== 0 && !apexOut.includes('Compiled successfully')) {
            console.error(`  ${entry.sobject}: apex execution failed`);
            process.stderr.write(apexErr || apexOut);
            process.exit(1);
          }
          const okMatches = [...apexOut.matchAll(/\|DEBUG\|REF:([^:\n]+):(\w+)/g)];
          const errMatches = [...apexOut.matchAll(/\|DEBUG\|ERR:([^:\n]+):([^\n]+)/g)];
          if (errMatches.length) {
            for (const m of errMatches.slice(0, 5)) {
              console.error(`    ${m[1]}: ${m[2].trim()}`);
            }
            if (errMatches.length > 5) console.error(`    ... and ${errMatches.length - 5} more`);
            console.error(`\nSetup failed at step: Data import tree (${entry.sobject})`);
            process.exit(1);
          }
          if (entry.saveRefs) {
            for (const m of okMatches) refMap.set(m[1], m[2]);
          }
          imported += okMatches.length;
        }
        console.log(`  ${entry.sobject}: imported ${imported} records`);
      }
    }
    if (existsSync(tmpApex)) unlinkSync(tmpApex);
  }

  if (!skipGraphql) {
    run('UI Bundle npm install', 'npm', ['install'], { cwd: uiBundleDir });
    run('Set default org for schema', 'sf', ['config', 'set', 'target-org', targetOrg, '--global']);
    run('GraphQL schema (introspect)', 'npm', ['run', 'graphql:schema'], { cwd: uiBundleDir });
    run('GraphQL codegen', 'npm', ['run', 'graphql:codegen'], { cwd: uiBundleDir });
    run('UI Bundle build (post-codegen)', 'npm', ['run', 'build'], { cwd: uiBundleDir });
  } else if (!skipUIBundleBuild && skipDeploy) {
    // Only build here if the pre-deploy build didn't already run
    run('UI Bundle npm install', 'npm', ['install'], { cwd: uiBundleDir });
    run('UI Bundle build', 'npm', ['run', 'build'], { cwd: uiBundleDir });
  }

  console.log('\n--- Setup complete ---');

  if (!skipDev) {
    console.log('\n--- Launching dev server (Ctrl+C to stop) ---\n');
    run('Dev server', 'npm', ['run', 'dev'], { cwd: uiBundleDir });
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
