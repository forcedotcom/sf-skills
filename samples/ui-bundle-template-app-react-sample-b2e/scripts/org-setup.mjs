#!/usr/bin/env node
/**
 * One-command setup: login, deploy, optional permset/data, GraphQL schema/codegen, UI bundle build.
 * Use this script to make setup easier for each app generated from this template.
 *
 * Usage:
 *   node scripts/org-setup.mjs --target-org <alias>           # interactive step picker (all selected)
 *   node scripts/org-setup.mjs                                # prompt to pick an authenticated org
 *   node scripts/org-setup.mjs --target-org <alias> --yes     # skip picker, run all steps
 *   node scripts/org-setup.mjs --target-org afv5 --skip-data --skip-ui-bundle-build
 *   node scripts/org-setup.mjs --target-org myorg --ui-bundle-name my-app
 *
 * Login is an unconditional precondition (not a toggleable step); the dev server
 * is launched separately via `npm run dev:preview` (scripts/org-setup-dev.mjs).
 *
 * Steps (in order):
 *   login (precondition) — sf org login web only if org not already connected; always runs before deploy
 *   1. uiBundle  — (all UI bundles) npm install && npm run build so dist exists for deploy (skip with --skip-ui-bundle-build)
 *   2. deploy    — sf project deploy start --target-org <alias> (requires dist for entity deployment)
 *   3. permset   — assign permsets per org-setup.config.json (skip with --skip-permset; override via --permset-name)
 *   4. data      — prepare unique fields + sf data import tree (skipped if no data dir/plan)
 *   5. graphql   — (in UI bundle) npm run graphql:schema then npm run graphql:codegen
 *
 * Permset assignment config (scripts/org-setup.config.json):
 *   {
 *     "permsetAssignments": {
 *       "defaultAssignee": "skip",
 *       "assignments": {
 *         "My_Permset": { "assignee": "currentUser" },
 *         "Guest_Permset": { "assignee": "guestUser" },
 *         "Internal_Only": { "assignee": "skip" }
 *       }
 *     }
 *   }
 *   Assignee values: "currentUser", "guestUser", or "skip". For "guestUser" the
 *   site is derived from the single networks/<siteName>.network-meta.xml the app
 *   ships — it is not restated per assignment.
 *   Unlisted permsets resolve to "defaultAssignee" (default "skip").
 */

import { spawnSync, spawn as nodeSpawn } from 'node:child_process';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  readdirSync,
  existsSync,
  readFileSync,
  writeFileSync,
  mkdirSync,
  mkdtempSync,
  rmSync,
  openSync,
  closeSync,
} from 'node:fs';
import { tmpdir } from 'node:os';

import { validateConfig } from './org-setup-config-schema.mjs';
import {
  addProfileToMemberGroups,
  enableSelfRegInXml,
  NetworkXmlError,
} from './org-setup-xml.mjs';
import {
  discoverAllUIBundleDirs as discoverAllUIBundleDirsIn,
  discoverUIBundleDir as discoverUIBundleDirIn,
  resolveTargetOrg,
  evaluateLicenseRows,
  validateProfileNameForSoql,
  validateSoqlName,
  validateApiName,
  escapeSoqlString,
  parseApexInsertResults,
  planApexBatches,
} from './org-setup-utils.mjs';

const __dirname = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dirname, '..');

/**
 * Thrown by step runners (run/runAsync) when a subprocess fails. The per-step
 * orchestration in main() catches it, records the failure in the result ledger,
 * and either aborts (fail-fast steps) or continues (skippable steps).
 */
class StepError extends Error {}

const APEX_TMP_PREFIX = 'org-setup-';
// Legacy fixed-name temp files that older versions of this script wrote to ROOT
// and could leave behind on a hard kill. Swept at startup for backward cleanup.
const LEGACY_ROOT_TMP_FILES = ['.tmp-setup-selfreg.apex', '.tmp-setup-delete.apex'];

/**
 * Remove leftover Apex temp artifacts from a prior hard-killed run (cleanup AT
 * START). Two sources: per-run dirs under os.tmpdir() created by
 * withApexTempDir, and legacy fixed-name files this script used to write to
 * ROOT. Best-effort: a failure to remove one entry never blocks setup.
 *
 * Scoped to DIRECTORY entries only: the per-run artifacts are dirs created by
 * withApexTempDir via mkdtempSync, whereas the per-org lock files share the same
 * `org-setup-` prefix but are plain files (`org-setup-lock-<org>.lock`). Sweeping
 * files too would delete a live run's lock before acquireOrgLock could see it,
 * defeating the concurrency guard. The dir sweep is still intentionally broad
 * across PIDs; the per-target-org lock acquired in main() is what makes that
 * safe — only one live run per org.
 */
function sweepStaleApexTempDirs() {
  const base = tmpdir();
  let entries = [];
  try {
    entries = readdirSync(base, { withFileTypes: true });
  } catch {
    /* tmpdir unreadable — nothing to sweep */
  }
  for (const entry of entries) {
    if (entry.isDirectory() && entry.name.startsWith(APEX_TMP_PREFIX)) {
      try {
        rmSync(join(base, entry.name), { recursive: true, force: true });
      } catch {
        /* best effort */
      }
    }
  }
  for (const legacy of LEGACY_ROOT_TMP_FILES) {
    const p = resolve(ROOT, legacy);
    if (existsSync(p)) {
      try {
        rmSync(p, { force: true });
      } catch {
        /* best effort */
      }
    }
  }
}

/**
 * Run `fn(writeApex)` with a private temp dir under os.tmpdir() that is ALWAYS
 * removed afterwards (cleanup IN FINALLY), even when fn throws or
 * the spawned Apex step fails. `writeApex(basename, contents)` writes a file in
 * that dir and returns its absolute path. Replaces the old fixed-name
 * `.tmp-setup-*.apex` files in ROOT, which collided across concurrent runs and
 * leaked on throw.
 */
function withApexTempDir(fn) {
  const dir = mkdtempSync(join(tmpdir(), APEX_TMP_PREFIX));
  try {
    return fn((basename, contents) => {
      const p = join(dir, basename);
      writeFileSync(p, contents);
      return p;
    });
  } finally {
    try {
      rmSync(dir, { recursive: true, force: true });
    } catch {
      /* best effort */
    }
  }
}

/** Filesystem-safe lock path for a target org. */
function orgLockPath(targetOrg) {
  const safe = String(targetOrg).replace(/[^a-zA-Z0-9._-]/g, '_');
  return join(tmpdir(), `org-setup-lock-${safe}.lock`);
}

/**
 * Liveness probe: signal 0 throws ESRCH if the pid is gone, EPERM if it exists
 * but we can't signal it (still alive, owned by another user).
 */
function isProcessAlive(pid) {
  try {
    process.kill(pid, 0);
    return true;
  } catch (e) {
    return e.code === 'EPERM';
  }
}

/**
 * Acquire a single-host advisory per-target-org lock. If a LIVE
 * run already holds it, exit early with a clear message rather than interleaving
 * destructive Apex (deletes/imports) against the same org. A lock left by a
 * hard-killed run (dead pid) is reclaimed. Different-org runs use different lock
 * files and proceed in parallel.
 *
 * Released via process.on('exit') — NOT a finally block — because main() exits
 * through process.exit() (the runStep fail-fast path, the end-of-run summary,
 * and the top-level .catch), and process.exit() does not run finally blocks.
 */
function acquireOrgLock(targetOrg) {
  const lockPath = orgLockPath(targetOrg);
  if (existsSync(lockPath)) {
    const holder = Number(readFileSync(lockPath, 'utf8').trim());
    if (holder && isProcessAlive(holder)) {
      console.error(
        `\nAnother org-setup run (pid ${holder}) is already targeting "${targetOrg}".\n` +
          `Wait for it to finish, or if it was killed, remove ${lockPath} and retry.`,
      );
      process.exit(1);
    }
    // Stale lock (holder dead / hard-killed) — reclaim it.
    rmSync(lockPath, { force: true });
  }
  // O_EXCL ('wx') create closes the check-then-write race between two
  // near-simultaneous runs: the loser gets EEXIST.
  let fd;
  try {
    fd = openSync(lockPath, 'wx');
  } catch (e) {
    if (e.code === 'EEXIST') {
      console.error(
        `\nAnother org-setup run just acquired the lock for "${targetOrg}". Retry shortly.`,
      );
      process.exit(1);
    }
    throw e;
  }
  writeFileSync(fd, String(process.pid));
  closeSync(fd);

  process.on('exit', () => {
    try {
      rmSync(lockPath, { force: true });
    } catch {
      /* best effort */
    }
  });
}

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
    skipDeploy: false,
    skipPermset: false,
    skipRole: false,
    skipData: false,
    skipGraphql: false,
    skipUIBundleBuild: false,
    skipSelfReg: false,
    skipSocialLogin: false,
  };
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '--target-org' && args[i + 1]) {
      targetOrg = args[++i];
    } else if (args[i] === '--ui-bundle-name' && args[i + 1]) {
      uiBundleName = args[++i];
    } else if (args[i] === '--permset-name' && args[i + 1]) {
      permsetNamesExplicit.push(args[++i]);
    } else if (args[i] === '--skip-deploy') flags.skipDeploy = true;
    else if (args[i] === '--skip-permset') flags.skipPermset = true;
    else if (args[i] === '--skip-role') flags.skipRole = true;
    else if (args[i] === '--skip-data') flags.skipData = true;
    else if (args[i] === '--skip-self-reg') flags.skipSelfReg = true;
    else if (args[i] === '--skip-social-login') flags.skipSocialLogin = true;
    else if (args[i] === '--skip-graphql') flags.skipGraphql = true;
    else if (args[i] === '--skip-ui-bundle-build') flags.skipUIBundleBuild = true;
    // --skip-login and --skip-dev are retired: login is now an unconditional
    // precondition and the dev step moved to `npm run dev:preview`.
    // Accept them silently as no-ops so existing invocations don't hard-error.
    else if (args[i] === '--skip-login' || args[i] === '--skip-dev') {
      /* no-op (retired flag) */
    } else if (args[i] === '--yes' || args[i] === '-y') yes = true;
    else if (args[i] === '--help' || args[i] === '-h') {
      console.log(`
Setup CLI — one-command setup for apps in this project

Usage:
  node scripts/org-setup.mjs [--target-org <alias>] [options]

Options:
  --target-org <alias>   Target Salesforce org alias (e.g. myorg). If omitted, you
                         are prompted to pick from authenticated orgs (or the
                         default org is used when not running interactively).
  --ui-bundle-name <name> UI bundle folder name under uiBundles/ (default: auto-detect)
  --permset-name <name>  Assign only this permission set (repeatable). Default: all sets under permissionsets/
  --skip-deploy          Do not deploy metadata
  --skip-permset         Do not assign permission set
  --skip-social-login    Do not enable social login (auth providers + community profile)
  --skip-data            Do not prepare data or run data import
  --skip-graphql         Do not fetch schema or run GraphQL codegen
  --skip-ui-bundle-build Do not npm install / build the UI bundle
  -y, --yes              Skip interactive step picker; run all enabled steps immediately
  -h, --help             Show this help

To launch the dev server after setup, run:  npm run dev:preview

Permset config (scripts/org-setup.config.json):
  Control per-permset assignment via a config file. Example:
    {
      "permsetAssignments": {
        "defaultAssignee": "skip",
        "assignments": {
          "My_Permset": { "assignee": "currentUser" },
          "Guest_Permset": { "assignee": "guestUser" },
          "Internal_Only": { "assignee": "skip" }
        }
      }
    }
  Assignee values: "currentUser", "guestUser", or "skip". For "guestUser" the site
  is derived from the single networks/<siteName>.network-meta.xml the app ships.
  Unlisted permsets resolve to "defaultAssignee" (default "skip").
`);
      process.exit(0);
    }
  }
  // NOTE: no hard-exit on a missing --target-org here. Resolution is
  // deferred to resolveTargetOrg(), which either prompts (TTY) or falls back to
  // the default org / exits with a clear message (non-TTY).
  return { targetOrg, uiBundleName, permsetNamesExplicit, yes, ...flags };
}

// Bundle discovery lives in org-setup-utils.mjs so org-setup-dev.mjs shares it verbatim.
// These thin wrappers bind the shared helpers to this script's UIBUNDLES_DIR and
// keep the existing call-site signatures. discoverUIBundleDir carries the
// multi-bundle acknowledgment (TTY picker / non-TTY warning).
function discoverAllUIBundleDirs(uiBundleName) {
  return discoverAllUIBundleDirsIn(UIBUNDLES_DIR, uiBundleName);
}

function discoverUIBundleDir(uiBundleName) {
  return discoverUIBundleDirIn(UIBUNDLES_DIR, uiBundleName);
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

const CONFIG_PATH = resolve(__dirname, 'org-setup.config.json');

/**
 * Read + validate org-setup.config.json ONCE, against the shared zod schema
 * (the same `validateConfig` the build/CI gate uses). Exits non-zero with the
 * precise zod issues if the config is invalid — before any step runs.
 *
 * Returns the validated config object (zod defaults applied), or an empty
 * object when the file is absent (every section is optional).
 *
 * This is the single source of truth: loadPermsetConfig / loadRoleConfig /
 * loadSelfRegConfig all read from the object it returns, so they no longer
 * parse or defensively swallow errors.
 */
function loadValidatedConfig() {
  if (!existsSync(CONFIG_PATH)) return {};
  const result = validateConfig(readFileSync(CONFIG_PATH, 'utf8'), CONFIG_PATH);
  if (!result.ok) {
    console.error('Invalid org-setup.config.json:');
    for (const err of result.errors) console.error(`  - ${err}`);
    process.exit(1);
  }
  return result.data;
}

/**
 * Derive the site name from the single networks/<siteName>.network-meta.xml the
 * app ships. An app ships exactly one site, so the site name is derivable from
 * deployed metadata rather than restated per-assignment. Returns
 * null when there is no networks dir or no .network-meta.xml file.
 */
function deriveSiteName() {
  const networksDir = resolve(SFDX_SOURCE, 'networks');
  if (!existsSync(networksDir)) return null;
  const files = readdirSync(networksDir)
    .filter((f) => f.endsWith('.network-meta.xml'))
    .sort();
  if (files.length === 0) return null;
  // An app ships exactly one site; if a developer added a second, derivation is
  // ambiguous — fail loudly rather than silently bind to an arbitrary site.
  if (files.length > 1) {
    throw new StepError(
      `cannot derive guest site: multiple network metadata files found in ${networksDir} (${files.join(', ')}); guestUser assignment requires exactly one`,
    );
  }
  const siteName = files[0].replace(/\.network-meta\.xml$/, '');
  // The site name is interpolated into SOQL (Network lookup, guest-user lookup),
  // so validate it here — the single chokepoint both callers pass through. Its
  // source is the metadata filename, not org-setup.config.json, so point the fix
  // there.
  validateSoqlName(siteName, 'site name', {
    remediation: `the networks/<siteName>.network-meta.xml filename (currently "${files[0]}")`,
  });
  return siteName;
}

/**
 * Permset assignment configuration, read from the already-validated config.
 *
 * Config shape:
 *   {
 *     "permsetAssignments": {
 *       "defaultAssignee": "skip",
 *       "assignments": {
 *         "My_Permset":       { "assignee": "currentUser" },
 *         "My_Guest_Permset": { "assignee": "guestUser" },
 *         "Internal_Only":    { "assignee": "skip" }
 *       }
 *     }
 *   }
 *
 * Assignee values:
 *   "currentUser" — assign to the user running the script
 *   "skip"        — do not assign this permset
 *   "guestUser"   — resolve the site guest user automatically (site derived from
 *                   the single networks/<siteName>.network-meta.xml the app ships)
 *
 * Unlisted permsets resolve to `defaultAssignee` (default "skip").
 *
 * Returns { defaultAssignee: string, assignments: Record<string, { assignee: string }> }
 */
function loadPermsetConfig(config) {
  const section = config.permsetAssignments;
  if (!section) return { defaultAssignee: 'skip', assignments: {} };
  return {
    defaultAssignee: section.defaultAssignee,
    assignments: section.assignments,
  };
}

/** Resolve the effective assignment config for a given permset name. */
function resolveAssignment(permsetName, permsetConfig) {
  const override = permsetConfig.assignments[permsetName];
  if (!override) return { assignee: permsetConfig.defaultAssignee };
  return { assignee: override.assignee };
}

/**
 * Role assignment config, read from the already-validated config.
 *
 * Config shape:
 *   { "role": { "assignee": "currentUser", "roleName": "Admin" } }
 *
 * Returns null if no "role" section exists in config (the step is hidden).
 */
function loadRoleConfig(config) {
  const section = config.role;
  if (!section) return null;
  return {
    assignee: section.assignee,
    roleName: section.roleName,
  };
}

/**
 * Self-registration config, read from the already-validated config. The site is
 * NOT stored here — it is derived from the single
 * networks/<siteName>.network-meta.xml the app ships, exactly like
 * the guestUser permset path. deriveSiteName() is called lazily inside the
 * selfReg step body so its "multiple network files" StepError is recorded in
 * the ledger rather than escaping config load.
 *
 * Config shape:
 *   {
 *     "selfRegistration": {
 *       "selfRegProfile": "myapp Profile",
 *       "accountName": "My Self-Reg Account"
 *     }
 *   }
 *
 * Returns null if no "selfRegistration" section exists in config (the step is hidden).
 */
function loadSelfRegConfig(config) {
  const section = config.selfRegistration;
  if (!section) return null;
  return {
    selfRegProfile: section.selfRegProfile,
    accountName: section.accountName,
  };
}

/**
 * Social login config, read from the already-validated config.
 *
 * Config shape:
 *   {
 *     "socialLogin": {
 *       "communityMemberProfile": "Customer Community User",
 *       "authProviderNames": ["Google", "Facebook", "My_SAML_Provider"],
 *       "communityUserPermset": "myapp_Guest_User_Api_Access"   // optional
 *     }
 *   }
 *
 * - communityMemberProfile: profile added to NetworkMemberGroup (required for access)
 * - authProviderNames: DeveloperNames of AuthProvider (OAuth) or SamlSsoConfig (SAML) records to link to site
 * - communityUserPermset: permset assigned to community users so getCurrentUser()
 *   works (requires PermissionsApiEnabled for /chatter/users/me via /sf/api/)
 *
 * Returns null if no "socialLogin" section exists in config (the step is hidden).
 */
function loadSocialLoginConfig(config) {
  const section = config.socialLogin;
  if (!section) return null;
  return {
    communityMemberProfile: section.communityMemberProfile,
    authProviderNames: section.authProviderNames,
    communityUserPermset: section.communityUserPermset || null,
  };
}

/**
 * Enable the "Allow using standard external profiles for self-registration,
 * user creation, and login" org setting via Metadata API deploy.
 *
 * This setting is required for SSO registration handlers to create users with
 * standard community profiles (e.g. "Customer Community User"). Without it,
 * auth providers return FIELD_INTEGRITY_EXCEPTION on user insert.
 *
 * The correct metadata field is `enableOotbProfExtUserOpsEnable` in
 * CommunitiesSettings. The REST/Tooling API approaches also fail on many
 * org types. Deploying via Metadata API is the most reliable method.
 */
function enableExternalProfiles(targetOrg) {
  const dir = mkdtempSync(join(tmpdir(), APEX_TMP_PREFIX));
  try {
    // Create a minimal sfdx project with just the Communities setting
    const settingsDir = join(dir, 'force-app', 'main', 'default', 'settings');
    mkdirSync(settingsDir, { recursive: true });

    writeFileSync(join(dir, 'sfdx-project.json'), JSON.stringify({
      packageDirectories: [{ path: 'force-app', default: true }],
      sourceApiVersion: '68.0',
    }));

    writeFileSync(join(settingsDir, 'Communities.settings-meta.xml'), [
      '<?xml version="1.0" encoding="UTF-8"?>',
      '<CommunitiesSettings xmlns="http://soap.sforce.com/2006/04/metadata">',
      '    <enableOotbProfExtUserOpsEnable>true</enableOotbProfExtUserOpsEnable>',
      '</CommunitiesSettings>',
    ].join('\n'));

    const result = spawnSync('sf', [
      'project', 'deploy', 'start',
      '--target-org', targetOrg,
      '--source-dir', join(dir, 'force-app'),
      '--json',
    ], { cwd: dir, stdio: 'pipe', shell: true, timeout: 120000 });

    const out = result.stdout?.toString() || '';
    let deployResult;
    try { deployResult = JSON.parse(out); } catch { deployResult = null; }

    if (deployResult?.status === 0 || deployResult?.result?.status === 'Succeeded') {
      console.log('  Enabled "Allow using standard external profiles" org setting.');
    } else {
      // Check if it failed because the setting is already enabled or not deployable
      const errMsg = deployResult?.message || deployResult?.result?.details?.componentFailures?.[0]?.problem || '';
      if (errMsg.includes('already') || errMsg.includes('enableOotbProfExtUserOpsEnable')) {
        console.log('  Warning: could not deploy "Allow standard external profiles" setting.');
        console.log(`  Detail: ${errMsg}`);
        console.log('  The setting may already be active. Enable manually via Setup > Digital Experiences > Settings if needed.');
      } else {
        console.log('  Warning: could not enable "Allow standard external profiles".');
        console.log(`  Deploy result: ${errMsg || 'unknown error'}`);
        console.log('  Enable manually via Setup > Digital Experiences > Settings.');
      }
    }
  } finally {
    try { rmSync(dir, { recursive: true, force: true }); } catch { /* best effort */ }
  }
}

/**
 * Enable Auth Providers for a community by creating AuthConfigProviders junction
 * records via Anonymous Apex + REST API callouts.
 *
 * React (Site Container) sites intentionally hide SSO configuration in the Admin
 * UI, so this must be done programmatically. The approach:
 *   1. Query the AuthConfig record for the site (one per community).
 *   2. Query AuthProvider records by DeveloperName.
 *   3. Query SamlSsoConfig records by DeveloperName (for SAML providers).
 *   4. Check existing AuthConfigProviders to avoid duplicates.
 *   5. Create missing AuthConfigProviders via REST API (DML is not allowed on this object).
 *
 * AuthConfig.AuthOptionsAuthProvider auto-flips to true when AuthConfigProviders
 * are inserted — no separate update needed.
 *
 * @param {string[]} authProviderNames - DeveloperNames of AuthProvider or SamlSsoConfig records
 * @param {string} siteName - Name of the Network/community
 * @param {string} targetOrg - Target org alias
 */
function enableAuthProvidersForSite(authProviderNames, siteName, targetOrg) {
  // DML is not allowed on AuthConfigProviders, so we use Anonymous Apex with
  // HTTP callouts to the REST API to create the junction records.
  // Whitelist each DeveloperName before it is interpolated into the generated
  // Apex `DeveloperName IN (…)` literal — same call-site guard the data-import
  // path applies with validateApiName, and defense-in-depth alongside the
  // up-front socialLogin validation in main(). loadSocialLoginConfig already
  // rejects an empty list, so the resulting literal is never empty here.
  const providerNamesLiteral = authProviderNames
    .map((n) => `'${validateSoqlName(n, 'socialLogin.authProviderNames entry')}'`)
    .join(', ');

  const apex = `
// Enable Auth Providers (OAuth + SAML) for community "${siteName}"
Http http = new Http();
String baseUrl = Url.getOrgDomainUrl().toExternalForm();
String token = UserInfo.getSessionId();

// Step 1: Find the AuthConfig for this site
List<AuthConfig> authConfigs = [
    SELECT Id, Url
    FROM AuthConfig
    WHERE Url LIKE '%${siteName}%'
    LIMIT 1
];
if (authConfigs.isEmpty()) {
    System.debug('ERROR_NO_AUTHCONFIG');
    return;
}
AuthConfig ac = authConfigs[0];
System.debug('AUTHCONFIG_FOUND:' + ac.Id + ':' + ac.Url);

// Step 2: Query AuthProvider records by DeveloperName (OAuth providers)
List<AuthProvider> oauthProviders = [
    SELECT Id, DeveloperName, FriendlyName
    FROM AuthProvider
    WHERE DeveloperName IN (${providerNamesLiteral})
];
System.debug('OAUTH_PROVIDERS_FOUND:' + oauthProviders.size());

// Step 3: Query SamlSsoConfig records by DeveloperName (SAML providers)
List<SamlSsoConfig> samlProviders = [
    SELECT Id, DeveloperName
    FROM SamlSsoConfig
    WHERE DeveloperName IN (${providerNamesLiteral})
];
System.debug('SAML_PROVIDERS_FOUND:' + samlProviders.size());

// Combine both into a unified list with (Id, DeveloperName, Type)
List<Map<String, String>> allProviders = new List<Map<String, String>>();
for (AuthProvider ap : oauthProviders) {
    allProviders.add(new Map<String, String>{
        'Id' => ap.Id,
        'DeveloperName' => ap.DeveloperName,
        'Type' => 'OAuth'
    });
}
for (SamlSsoConfig sp : samlProviders) {
    allProviders.add(new Map<String, String>{
        'Id' => sp.Id,
        'DeveloperName' => sp.DeveloperName,
        'Type' => 'SAML'
    });
}

if (allProviders.isEmpty()) {
    System.debug('ERROR_NO_PROVIDERS');
    return;
}
System.debug('TOTAL_PROVIDERS_FOUND:' + allProviders.size());

// Step 4: Check existing AuthConfigProviders to avoid duplicates
Set<Id> existingProviderIds = new Set<Id>();
for (AuthConfigProviders acp : [
    SELECT AuthProviderId FROM AuthConfigProviders WHERE AuthConfigId = :ac.Id
]) {
    existingProviderIds.add(acp.AuthProviderId);
}

// Step 5: Create missing junction records via REST API
Integer inserted = 0;
for (Map<String, String> provider : allProviders) {
    String providerId = provider.get('Id');
    String providerName = provider.get('DeveloperName');
    String providerType = provider.get('Type');

    if (existingProviderIds.contains(providerId)) {
        System.debug('ALREADY_LINKED:' + providerName + ':' + providerType);
        continue;
    }
    HttpRequest req = new HttpRequest();
    req.setEndpoint(baseUrl + '/services/data/v62.0/sobjects/AuthConfigProviders');
    req.setMethod('POST');
    req.setHeader('Authorization', 'Bearer ' + token);
    req.setHeader('Content-Type', 'application/json');
    req.setBody('{"AuthConfigId":"' + ac.Id + '","AuthProviderId":"' + providerId + '"}');
    HttpResponse res = http.send(req);
    if (res.getStatusCode() == 201 || res.getStatusCode() == 200) {
        System.debug('INSERTED:' + providerName + ':' + providerType);
        inserted++;
    } else {
        System.debug('INSERT_FAILED:' + providerName + ':' + providerType + ':' + res.getStatusCode() + ':' + res.getBody());
    }
}
if (inserted == 0 && existingProviderIds.size() >= allProviders.size()) {
    System.debug('ALL_ALREADY_LINKED');
} else {
    System.debug('TOTAL_INSERTED:' + inserted);
}
`;

  const apexOut = withApexTempDir((writeApex) => {
    const tmpApex = writeApex('auth-providers.apex', apex);
    const result = spawnSync('sf', [
      'apex', 'run', '--target-org', targetOrg, '--file', tmpApex,
    ], { cwd: ROOT, stdio: 'pipe', shell: true, timeout: 60000 });
    const out = result.stdout?.toString() || '';
    const err = result.stderr?.toString() || '';
    if (result.status !== 0 && !out.includes('Compiled successfully')) {
      process.stderr.write(err || out);
      throw new StepError('failed to execute AuthConfigProviders apex');
    }
    return out;
  });

  // Parse output for status — match only |DEBUG| lines to avoid false positives
  // from the "Execute Anonymous:" source echo that sf apex run always prints.
  if (apexOut.match(/\|DEBUG\|ERROR_NO_AUTHCONFIG/)) {
    throw new StepError(`no AuthConfig found for site "${siteName}" — ensure the site is published/active`);
  }
  if (apexOut.match(/\|DEBUG\|ERROR_NO_PROVIDERS/)) {
    throw new StepError(`no AuthProvider or SamlSsoConfig records found for names: ${authProviderNames.join(', ')} — create them in Setup first`);
  }

  // Check for insert failures
  const insertFails = [...apexOut.matchAll(/\|DEBUG\|INSERT_FAILED:([^:]+):(OAuth|SAML):(\d+):([^\n]+)/g)];
  if (insertFails.length > 0) {
    for (const m of insertFails) {
      console.error(`    ✖ ${m[1]} (${m[2]}) — HTTP ${m[3]}: ${m[4].trim()}`);
    }
    throw new StepError(`failed to link ${insertFails.length} Auth Provider(s) to site AuthConfig`);
  }

  const totalMatch = apexOut.match(/\|DEBUG\|TOTAL_INSERTED:(\d+)/);
  if (totalMatch) {
    console.log(`  Linked ${totalMatch[1]} Auth Provider(s) to site "${siteName}".`);
  } else if (apexOut.match(/\|DEBUG\|ALL_ALREADY_LINKED/)) {
    console.log(`  All Auth Provider(s) already linked to site "${siteName}"; no changes needed.`);
  }

  // Log individual provider statuses
  const alreadyLinked = [...apexOut.matchAll(/\|DEBUG\|ALREADY_LINKED:([^:]+):(OAuth|SAML)/g)];
  for (const m of alreadyLinked) {
    console.log(`    ✔ ${m[1]} (${m[2]}, already linked)`);
  }
  const inserted = [...apexOut.matchAll(/\|DEBUG\|INSERTED:([^:]+):(OAuth|SAML)/g)];
  for (const m of inserted) {
    console.log(`    + ${m[1]} (${m[2]}, newly linked)`);
  }
}

/**
 * Add a community user profile to the NetworkMemberGroup so that SSO-registered
 * users (who get assigned this profile by the registration handler) can access
 * the community.
 *
 * Without this, users created by the SSO registration handler get
 * "NO_ACCESS: User was not authorized for the community".
 *
 * @param {string} profileName - Profile name to add (e.g. "Customer Community User")
 * @param {string} siteName - Name of the Network/community
 * @param {string} targetOrg - Target org alias
 */
function addCommunityMemberProfile(profileName, siteName, targetOrg) {
  // Query Network Id
  const netQuery = `SELECT Id FROM Network WHERE Name = '${siteName}'`;
  const netResult = spawnSync('sf', [
    'data', 'query', '--query', netQuery, '--target-org', targetOrg, '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  let networkId = null;
  if (netResult.status === 0) {
    try {
      const json = JSON.parse(netResult.stdout);
      networkId = json.result?.records?.[0]?.Id || null;
    } catch { /* fall through */ }
  }
  if (!networkId) {
    throw new StepError(`could not find Network "${siteName}" in org`);
  }

  // Query Profile Id
  const profQuery = `SELECT Id FROM Profile WHERE Name = '${profileName}'`;
  const profResult = spawnSync('sf', [
    'data', 'query', '--query', profQuery, '--target-org', targetOrg, '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  let profileId = null;
  if (profResult.status === 0) {
    try {
      const json = JSON.parse(profResult.stdout);
      profileId = json.result?.records?.[0]?.Id || null;
    } catch { /* fall through */ }
  }
  if (!profileId) {
    throw new StepError(`could not find Profile "${profileName}" in org`);
  }

  // Check if already a member
  const memberQuery = `SELECT Id FROM NetworkMemberGroup WHERE NetworkId = '${networkId}' AND ParentId = '${profileId}'`;
  const memberResult = spawnSync('sf', [
    'data', 'query', '--query', memberQuery, '--target-org', targetOrg, '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  let alreadyExists = false;
  if (memberResult.status === 0) {
    try {
      const json = JSON.parse(memberResult.stdout);
      alreadyExists = (json.result?.records?.length || 0) > 0;
    } catch { /* proceed to create */ }
  }
  if (alreadyExists) {
    console.log(`  Profile "${profileName}" is already a member of community "${siteName}"; skipping.`);
    return;
  }

  // Create NetworkMemberGroup record
  const createResult = spawnSync('sf', [
    'data', 'create', 'record',
    '--sobject', 'NetworkMemberGroup',
    '--values', `NetworkId='${networkId}' ParentId='${profileId}'`,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  if (createResult.status !== 0) {
    const out = (createResult.stderr || '') + (createResult.stdout || '');
    if (out) process.stderr.write(out);
    throw new StepError(`failed to add profile "${profileName}" to NetworkMemberGroup for "${siteName}"`);
  }
  try {
    const json = JSON.parse(createResult.stdout);
    const id = json.result?.id;
    console.log(`  Added profile "${profileName}" to community "${siteName}" (NetworkMemberGroup: ${id}).`);
  } catch {
    console.log(`  Added profile "${profileName}" to community "${siteName}".`);
  }
}

/**
 * Assign a permission set to all existing community users with a given profile.
 *
 * After SSO login, community users need the app's API-enabled permset so that
 * getCurrentUser() (which calls /chatter/users/me via the /sf/api/ proxy) works.
 * Without PermissionsApiEnabled the proxy returns API_DISABLED_FOR_ORG and the
 * React app treats the user as unauthenticated.
 *
 * This is idempotent: already-assigned users are skipped.
 */
function assignPermsetToCommunityUsers(permsetName, profileName, targetOrg) {
  // Resolve PermissionSet Id
  const psQuery = `SELECT Id FROM PermissionSet WHERE Name = '${permsetName}'`;
  const psResult = spawnSync('sf', [
    'data', 'query', '--query', psQuery, '--target-org', targetOrg, '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  let permsetId = null;
  if (psResult.status === 0) {
    try {
      const json = JSON.parse(psResult.stdout);
      permsetId = json.result?.records?.[0]?.Id || null;
    } catch { /* fall through */ }
  }
  if (!permsetId) {
    throw new StepError(`could not find PermissionSet "${permsetName}" in org`);
  }

  // Find community users on the given profile who do NOT already have the permset
  const usersQuery = [
    `SELECT Id, Username FROM User`,
    `WHERE Profile.Name = '${profileName}'`,
    `AND IsActive = true`,
    `AND UserType IN ('CspLitePortal', 'CustomerSuccess', 'PowerCustomerSuccess')`,
    `AND Id NOT IN (SELECT AssigneeId FROM PermissionSetAssignment WHERE PermissionSetId = '${permsetId}')`,
  ].join(' ');
  const usersResult = spawnSync('sf', [
    'data', 'query', '--query', usersQuery, '--target-org', targetOrg, '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  let users = [];
  if (usersResult.status === 0) {
    try {
      const json = JSON.parse(usersResult.stdout);
      users = json.result?.records || [];
    } catch { /* empty list */ }
  }

  if (users.length === 0) {
    console.log(`  No community users on profile "${profileName}" need permset "${permsetName}"; skipping.`);
    return;
  }

  // Assign the permset to each user
  let assigned = 0;
  for (const user of users) {
    const createResult = spawnSync('sf', [
      'data', 'create', 'record',
      '--sobject', 'PermissionSetAssignment',
      '--values', `PermissionSetId='${permsetId}' AssigneeId='${user.Id}'`,
      '--target-org', targetOrg,
      '--json',
    ], { cwd: ROOT, encoding: 'utf8' });
    if (createResult.status === 0) {
      assigned++;
    } else {
      // Log but don't fail — user might already have it via race condition
      const out = (createResult.stdout || '') + (createResult.stderr || '');
      if (!out.includes('DUPLICATE_VALUE')) {
        console.warn(`  Warning: could not assign "${permsetName}" to ${user.Username}: ${out.slice(0, 120)}`);
      }
    }
  }
  console.log(`  Assigned permset "${permsetName}" to ${assigned}/${users.length} community user(s).`);
}

/**
 * Ensure the self-registration profile is listed in networkMemberGroups.
 * This must happen BEFORE the initial deploy so that the profile is a recognised
 * site member when subsequent steps (selfRegProfile, selfRegistration=true) are deployed.
 */
function ensureNetworkMemberProfile(selfRegConfig, siteName) {
  const { selfRegProfile } = selfRegConfig;
  if (!siteName || !selfRegProfile) return;

  const networkXmlPath = resolve(SFDX_SOURCE, 'networks', `${siteName}.network-meta.xml`);
  if (!existsSync(networkXmlPath)) {
    console.log(`  Network metadata not found: ${networkXmlPath}; skipping member group update.`);
    return;
  }
  const xml = readFileSync(networkXmlPath, 'utf8');

  // Parse + assert the target node exists, then mutate via a targeted edit.
  // This is the BEST-EFFORT pre-deploy prep (not inside runStep, see lines
  // ~1050): on a missing <networkMemberGroups> node we surface a LOUD
  // console.error but do NOT throw — a bare throw here aborts before deploy and
  // bypasses the ledger. The authoritative failure is recorded later by the
  // post-deploy selfReg step.
  let result;
  try {
    result = addProfileToMemberGroups(xml, selfRegProfile);
  } catch (e) {
    if (e instanceof NetworkXmlError) {
      console.error(
        `  ERROR: cannot add self-reg profile to ${siteName}.network-meta.xml — ${e.message}. ` +
        `Continuing pre-deploy; the self-registration step will record the authoritative failure.`,
      );
      return;
    }
    throw e;
  }

  if (!result.changed) {
    console.log(`  Profile "${selfRegProfile}" already in networkMemberGroups; no update needed.`);
    return;
  }
  writeFileSync(networkXmlPath, result.xml);
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
function enableSelfRegistration(selfRegConfig, siteName, targetOrg) {
  const { selfRegProfile, accountName } = selfRegConfig;

  // 1. Modify network metadata XML
  const networkXmlPath = resolve(SFDX_SOURCE, 'networks', `${siteName}.network-meta.xml`);
  if (!existsSync(networkXmlPath)) {
    throw new StepError(`network metadata not found: ${networkXmlPath}`);
  }
  const xml = readFileSync(networkXmlPath, 'utf8');

  // Parse + assert the <selfRegistration> node exists, then mutate via a
  // targeted edit. This runs inside
  // runStep(selfReg, failFast:false) (line ~1211), so a missing node must throw
  // a StepError — caught, recorded `failed`, non-zero exit — rather than the
  // old silent no-op. The helper's idempotency check
  // (already true / selfRegProfile present) yields changed:false here.
  let result;
  try {
    result = enableSelfRegInXml(xml, selfRegProfile);
  } catch (e) {
    if (e instanceof NetworkXmlError) {
      throw new StepError(`${siteName}.network-meta.xml: ${e.message}`);
    }
    throw e;
  }

  if (!result.changed) {
    console.log(`  Network "${siteName}" already has self-registration configured; skipping metadata update and deploy.`);
  } else {
    writeFileSync(networkXmlPath, result.xml);
    console.log(`  Updated ${siteName}.network-meta.xml: selfRegistration=true, selfRegProfile=${selfRegProfile}`);

    // Re-deploy only the network file
    const deployResult = spawnSync('sf', [
      'project', 'deploy', 'start',
      '--target-org', targetOrg,
      '--source-dir', networkXmlPath,
    ], { cwd: ROOT, stdio: 'inherit', shell: true, timeout: 120000 });
    if (deployResult.status !== 0) {
      throw new StepError(`failed to deploy updated network metadata (exit ${deployResult.status ?? 1})`);
    }
  }

  // 3. Create Account (idempotent).
  // accountName is a free-form display value (e.g. "O'Brien Rentals & Co.") that
  // legitimately contains punctuation, so it is ESCAPED rather than whitelisted:
  // escape it for the SOQL read here, and create it via Apex below
  // (apexLiteral-escaped) rather than the `--values Name='...'` CLI arg, whose
  // space-separated key=value parsing an escaped name cannot safely satisfy.
  const acctQuery = `SELECT Id FROM Account WHERE Name = '${escapeSoqlString(accountName)}' LIMIT 1`;
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
    // Create via Anonymous Apex (apexLiteral escapes the name) instead of
    // `sf data create record --values`: the CLI parses --values as
    // space-separated key=value pairs, so a name with a space, quote, or `&`
    // either mis-parses or opens a field-injection surface. Apex string
    // escaping closes that off and mirrors the NSR create just below.
    const apex = [
      `Account acct = new Account(Name = ${apexLiteral(accountName)});`,
      `insert acct;`,
      `System.debug('ACCOUNT_CREATED:' + acct.Id);`,
    ].join('\n');
    const apexOut = withApexTempDir((writeApex) => {
      const tmpApex = writeApex('account.apex', apex);
      const apexResult = spawnSync('sf', [
        'apex', 'run', '--target-org', targetOrg, '--file', tmpApex,
      ], { cwd: ROOT, stdio: 'pipe', shell: true, timeout: 60000 });
      const out = apexResult.stdout?.toString() || '';
      if (apexResult.status !== 0 && !out.includes('Compiled successfully')) {
        process.stderr.write(apexResult.stderr?.toString() || out);
        throw new StepError(`failed to create Account "${accountName}"`);
      }
      return out;
    });
    const acctMatch = apexOut.match(/ACCOUNT_CREATED:(\w+)/);
    if (!acctMatch) {
      throw new StepError('failed to parse Account creation result');
    }
    accountId = acctMatch[1];
    console.log(`  Created Account "${accountName}" (${accountId}).`);
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
    throw new StepError(`could not find Network "${siteName}" in org`);
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
    const apex = [
      `Account acct = [SELECT Id FROM Account WHERE Id = '${accountId}' LIMIT 1];`,
      `NetworkSelfRegistration nsr = new NetworkSelfRegistration();`,
      `nsr.AccountId = acct.Id;`,
      `nsr.NetworkId = '${networkId}';`,
      `insert nsr;`,
      `System.debug('NSR_CREATED:' + nsr.Id);`,
    ].join('\n');
    const apexOut = withApexTempDir((writeApex) => {
      const tmpApex = writeApex('selfreg.apex', apex);
      const apexResult = spawnSync('sf', [
        'apex', 'run', '--target-org', targetOrg, '--file', tmpApex,
      ], { cwd: ROOT, stdio: 'pipe', shell: true, timeout: 60000 });
      const out = apexResult.stdout?.toString() || '';
      if (apexResult.status !== 0 && !out.includes('Compiled successfully')) {
        process.stderr.write(apexResult.stderr?.toString() || out);
        throw new StepError('failed to create NetworkSelfRegistration record');
      }
      return out;
    });
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
  validateSoqlName(roleName, 'role name');
  const roleQuery = `SELECT Id FROM UserRole WHERE Name = '${roleName}'`;
  const roleResult = spawnSync('sf', [
    'data', 'query',
    '--query', roleQuery,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  if (roleResult.status !== 0) {
    if (roleResult.stderr) console.error(roleResult.stderr);
    throw new StepError(`failed to query role "${roleName}" in org`);
  }
  let roleId;
  try {
    const json = JSON.parse(roleResult.stdout);
    const records = json.result?.records;
    if (!records || records.length === 0) {
      throw new StepError(`role "${roleName}" not found in org`);
    }
    roleId = records[0].Id;
  } catch (err) {
    if (err instanceof StepError) throw err;
    throw new StepError(`failed to parse role query result for "${roleName}"`);
  }

  const orgResult = spawnSync('sf', [
    'org', 'display',
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });
  if (orgResult.status !== 0) {
    throw new StepError('failed to resolve current user from org');
  }
  let username;
  try {
    const json = JSON.parse(orgResult.stdout);
    username = json.result?.username;
    if (!username) {
      throw new StepError('could not determine current username from org display');
    }
  } catch (err) {
    if (err instanceof StepError) throw err;
    throw new StepError('failed to parse org display result');
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
    if (out) console.error(out);
    throw new StepError(`failed to assign role "${roleName}" to ${username}`);
  }
}

/**
 * Query the org for the guest user of the given site.
 *
 * Salesforce auto-creates a guest profile named "<Site> Profile" for each
 * Experience Cloud site. The old `Profile.Name LIKE '%<siteName>%'` substring
 * match collided across sites — e.g. site "shop" also matched "shop-admin"'s
 * guest profile — and then blindly took records[0]. This uses an exact match on
 * the profile name instead. SOQL string equality on a text field is
 * case-insensitive by default (it wraps both sides in UPPER()), so a site whose
 * label casing differs from the derived name still matches without explicit
 * normalization. siteName is whitelist-validated at the deriveSiteName()
 * chokepoint, so it is safe to interpolate here.
 *
 * Residual limitation: on a non-English org the auto-generated " Profile" suffix
 * may be localized, in which case no row matches and the assignment soft-skips
 * (returned null) with a clear message — the caller records that as a skip, not
 * a crash.
 *
 * Returns the guest Username, or null (with a logged reason) when the query
 * fails, no guest user exists, or the match is ambiguous.
 */
function resolveGuestUsername(siteName, targetOrg) {
  const query =
    `SELECT Username FROM User ` +
    `WHERE Profile.Name = '${siteName} Profile' AND UserType = 'Guest'`;
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
      console.error(`  No guest user found for site "${siteName}" (looked for profile "${siteName} Profile").`);
      return null;
    }
    if (records.length > 1) {
      const names = records.map((r) => r.Username).join(', ');
      console.error(
        `  Ambiguous guest user for site "${siteName}": ${records.length} guest users share ` +
          `profile "${siteName} Profile" (${names}); refusing to guess.`,
      );
      return null;
    }
    return records[0].Username;
  } catch {
    console.error(`  Failed to parse guest user query result for site "${siteName}".`);
    return null;
  }
}

/**
 * License pre-check for self-registration. Query the UserLicense that the
 * selfRegProfile belongs to and decide whether self-registration can proceed.
 * The profile name is validate-and-fail: a SOQL-special character throws a config
 * error rather than being escaped — profile names are developer-authored config,
 * not user input, so a `'` / `\` / control char is a mistake to surface loudly.
 *
 * Selection is on the stable LicenseDefinitionKey; the seat math lives in JS
 * (evaluateLicenseRows) because SOQL cannot compare two fields. A query failure
 * or 0 rows is treated as "not satisfied" (soft skip), not a hard error.
 *
 * @returns {{ satisfied: boolean, reason: string|null }}
 */
function checkSelfRegLicense(selfRegConfig, targetOrg) {
  const profileName = validateProfileNameForSoql(selfRegConfig.selfRegProfile);
  const query =
    `SELECT UserLicense.LicenseDefinitionKey, UserLicense.Name, UserLicense.Status, ` +
    `UserLicense.TotalLicenses, UserLicense.UsedLicenses ` +
    `FROM Profile WHERE Name = '${profileName}'`;
  const result = spawnSync('sf', [
    'data', 'query',
    '--query', query,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });

  if (result.status !== 0) {
    if (result.stderr) console.error(result.stderr);
    return {
      satisfied: false,
      reason: `could not query the UserLicense for profile "${profileName}" (sf data query failed)`,
    };
  }
  let rows;
  try {
    rows = JSON.parse(result.stdout).result?.records ?? [];
  } catch {
    return {
      satisfied: false,
      reason: `could not parse the UserLicense query result for profile "${profileName}"`,
    };
  }
  const { satisfied, reason } = evaluateLicenseRows(rows, profileName);
  return { satisfied, reason };
}

/**
 * Read the UserLicense the selfRegProfile requires straight from the local
 * profile metadata's <userLicense> element. The deploy pre-check runs BEFORE
 * the profile is deployed, so querying the org's Profile table returns 0 rows
 * and can only report "profile missing" — which never tells the user which
 * license to add. The profile source we are about to deploy is the
 * authoritative declaration of the required license.
 *
 * @returns {string|null} the license name, or null if the file / field is absent
 */
function readProfileUserLicense(selfRegProfile) {
  const profilePath = resolve(SFDX_SOURCE, 'profiles', `${selfRegProfile}.profile-meta.xml`);
  if (!existsSync(profilePath)) return null;
  const xml = readFileSync(profilePath, 'utf8');
  const m = xml.match(/<userLicense>\s*([^<]+?)\s*<\/userLicense>/);
  return m ? m[1].trim() : null;
}

/**
 * Deploy license pre-check. `sf project deploy start` fails with a
 * cryptic error when the org lacks the UserLicense the selfRegProfile's metadata
 * declares. Resolve the required license NAME from the local profile source, then
 * query the org's UserLicense by that name so a miss names the actual license the
 * admin must add — not the not-yet-deployed profile. Seat/status math is shared
 * with the self-reg gate via evaluateLicenseRows.
 *
 * @returns {{ satisfied: boolean, reason: string|null }}
 */
function checkDeployLicense(selfRegConfig, targetOrg) {
  const licenseName = readProfileUserLicense(selfRegConfig.selfRegProfile);
  // No <userLicense> in the profile source (or profile file absent) — nothing to
  // gate on; let deploy proceed and surface any real error on its own.
  if (!licenseName) return { satisfied: true, reason: null };

  const query =
    `SELECT LicenseDefinitionKey, Name, Status, TotalLicenses, UsedLicenses ` +
    `FROM UserLicense WHERE Name = '${escapeSoqlString(licenseName)}'`;
  const result = spawnSync('sf', [
    'data', 'query',
    '--query', query,
    '--target-org', targetOrg,
    '--json',
  ], { cwd: ROOT, encoding: 'utf8' });

  if (result.status !== 0) {
    if (result.stderr) console.error(result.stderr);
    return { satisfied: false, reason: `could not query UserLicense "${licenseName}" (sf data query failed)` };
  }
  let rows;
  try {
    rows = JSON.parse(result.stdout).result?.records ?? [];
  } catch {
    return { satisfied: false, reason: `could not parse the UserLicense query result for "${licenseName}"` };
  }
  if (rows.length === 0) {
    return {
      satisfied: false,
      reason: `required license "${licenseName}" is not present in the org — add it before deploying`,
    };
  }
  // evaluateLicenseRows expects the license nested under `.UserLicense` (its
  // Profile-query shape); reshape the direct UserLicense rows to match so the
  // seat/status logic — and its license-named messages — stay shared.
  return evaluateLicenseRows(rows.map((r) => ({ UserLicense: r })), selfRegConfig.selfRegProfile);
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
  // The sobject type and every field key land as bare identifiers inside the
  // generated Apex (`new ${sobject}()`, `r.put('${key}', …)`), where they can't
  // be quoted-and-escaped like a value — so they get the strict API-name
  // whitelist. refIds are the record referenceIds echoed back through a JSON
  // marker; they carry no Apex-identifier role, so escaping (not whitelisting)
  // is the right treatment for their single-quoted literal. All three come from
  // app-shipped seed fixtures, so a violation is a fixture bug surfaced loudly.
  validateApiName(sobject, 'sobject type');
  const lines = [
    'Database.DMLOptions dmlOpts = new Database.DMLOptions();',
    // Intentional: bypass duplicate rules for seed-data import. These are
    // controlled fixtures the app ships, not user input, and duplicate-rule
    // blocks (plus matching-service timeouts the REST Sforce-Duplicate-Rule-Action
    // header can't override) would abort an otherwise-valid setup.
    'dmlOpts.DuplicateRuleHeader.allowSave = true;',
    `List<${sobject}> recs = new List<${sobject}>();`,
  ];
  for (const rec of records) {
    lines.push(`{ ${sobject} r = new ${sobject}();`);
    for (const [key, val] of Object.entries(rec)) {
      if (key === 'attributes') continue;
      validateApiName(key, `field API name on ${sobject}`);
      lines.push(`r.put('${key}', ${apexLiteral(val)});`);
    }
    lines.push('recs.add(r); }');
  }
  lines.push('Database.SaveResult[] results = Database.insert(recs, dmlOpts);');
  const refArray = refIds.map((r) => `'${escapeSoqlString(r)}'`).join(',');
  lines.push(`String[] refs = new String[]{${refArray}};`);
  // Emit ONE machine-readable line instead of one System.debug per record: a
  // JSON array of {ref, id?|err?}. The Node side parses this with
  // parseApexInsertResults and treats a missing/unparseable marker as a hard
  // batch failure (a truncated debug line must not read as "0 errors"). Measured
  // batching keeps each batch — and thus this payload — well under the log line
  // size.
  lines.push('List<Object> setupOut = new List<Object>();');
  lines.push('for (Integer i = 0; i < results.size(); i++) {');
  lines.push('  Map<String,Object> m = new Map<String,Object>{ \'ref\' => refs[i] };');
  lines.push('  if (results[i].isSuccess()) { m.put(\'id\', results[i].getId()); }');
  lines.push('  else { m.put(\'err\', results[i].getErrors()[0].getMessage()); }');
  lines.push('  setupOut.add(m);');
  lines.push('}');
  // Use LoggingLevel.ERROR to ensure this critical line appears near the end of
  // the debug log and isn't truncated by excessive DEBUG-level noise from DML
  // operations, workflow rules, or process builders that fire during insert.
  lines.push("System.debug(LoggingLevel.ERROR, 'SETUP_RESULT_JSON:' + JSON.serialize(setupOut));");
  return lines.join('\n');
}

/**
 * Interactive multi-select: arrow keys navigate, space toggles, 'a' toggles all, enter confirms.
 * Returns a boolean[] matching the input order.  Falls through immediately when stdin is not a TTY.
 */
async function promptSteps(steps) {
  if (!process.stdin.isTTY) return steps.map((s) => s.enabled);

  // `selected` stays indexed by ORIGINAL step order (so the caller's
  // selections[i] → stepDefs[i] mapping is unchanged); unavailable steps remain
  // false. Only available steps are shown and navigable — unavailable steps are
  // hidden entirely rather than rendered greyed-out.
  const selected = steps.map((s) => s.enabled);
  const visible = steps.map((s, i) => ({ step: s, index: i })).filter(({ step }) => step.available);
  let cursor = 0;
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
    return visible.map(({ step, index }, row) => {
      const ptr = row === cursor ? `${CYAN}❯${RST}` : ' ';
      const chk = selected[index] ? `${GREEN}●${RST}` : '○';
      return `${ptr} ${chk} ${step.label}`;
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
      // Note: `cursor` indexes `visible`; `selected` is indexed by ORIGINAL step
      // order. Map through visible[cursor].index before touching `selected`.
      if (key === ' ') {
        const { index } = visible[cursor];
        selected[index] = !selected[index];
        redraw();
        return;
      }
      if (key === 'a') {
        const allOn = visible.every(({ index }) => selected[index]);
        for (const { index } of visible) selected[index] = !allOn;
        redraw();
        return;
      }
      if (key === '\x1B[A' || key === 'k') {
        cursor = Math.max(0, cursor - 1);
        redraw();
      } else if (key === '\x1B[B' || key === 'j') {
        cursor = Math.min(visible.length - 1, cursor + 1);
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
    ...(opts.env && { env: opts.env }),
    ...(opts.timeout && { timeout: opts.timeout }),
  });
  if (result.status !== 0 && !optional) {
    throw new StepError(`${name} (exit ${result.status ?? 1})`);
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
    throw new StepError(`${name} (exit ${result.status ?? 1})`);
  }
  return result;
}

/**
 * In-memory result ledger. Each selected step records exactly one outcome:
 *   ok      — the step ran and succeeded
 *   skipped — the step was not selected, or had no config section (intentional)
 *   failed  — the step ran and failed (with a human-readable reason)
 * The end-of-run summary is rendered from this ledger and the process exits
 * non-zero whenever any step is `failed` (fail-fast or skippable alike).
 *
 * @typedef {{ key: string, label: string, status: 'ok'|'skipped'|'failed', reason?: string, failFast?: boolean }} StepResult
 */
const results = [];
function recordOk(step) {
  results.push({ key: step.key, label: step.label, status: 'ok', failFast: step.failFast });
}
function recordSkipped(step, reason) {
  results.push({ key: step.key, label: step.label, status: 'skipped', reason, failFast: step.failFast });
}
function recordFailed(step, reason) {
  results.push({ key: step.key, label: step.label, status: 'failed', reason, failFast: step.failFast });
}

/** True if any step in the ledger failed. */
function finalExitCode() {
  return results.some((r) => r.status === 'failed') ? 1 : 0;
}

const SUMMARY_GLYPH = { ok: '✔', skipped: '–', failed: '✖' };

/**
 * Render the end-of-run summary. Always called — on success, on a fail-fast
 * abort (partial: only steps reached so far are present), and on a clean finish
 * that had skippable failures. Failed rows are listed last so the real problem
 * is the last thing the developer sees.
 */
function printSummary(targetOrg) {
  const ordered = [
    ...results.filter((r) => r.status !== 'failed'),
    ...results.filter((r) => r.status === 'failed'),
  ];
  const pad = Math.max(0, ...ordered.map((r) => r.key.length));
  console.log(`\nSetup summary (target org: ${targetOrg})`);
  for (const r of ordered) {
    const glyph = SUMMARY_GLYPH[r.status] ?? ' ';
    const key = r.key.padEnd(pad);
    let line = `  ${glyph} ${key}  ${r.status}`;
    if (r.reason) line += ` (${r.reason})`;
    if (r.status === 'failed') line += r.failFast ? '   [fail-fast — aborted]' : '   [skippable — continued]';
    console.log(line);
  }
  const failures = results.filter((r) => r.status === 'failed').length;
  if (failures > 0) {
    console.log(`Setup completed with ${failures} failure(s). Exiting 1.`);
  } else {
    console.log('Setup complete.');
  }
}

/**
 * Run one step body, recording its outcome in the ledger and honoring the
 * step's fixed `failFast` classification. The body either completes (→ ok),
 * throws a StepError (→ failed), or throws something unexpected (→ failed,
 * with the raw message). On a fail-fast failure this prints the partial
 * summary and exits non-zero immediately; on a skippable failure it records
 * and returns so the run continues.
 */
async function runStep(step, targetOrg, body) {
  try {
    await body();
    recordOk(step);
  } catch (err) {
    const reason = err instanceof StepError ? err.message : (err?.message ?? String(err));
    recordFailed(step, reason);
    console.error(`\nStep "${step.key}" failed: ${reason}`);
    if (step.failFast) {
      printSummary(targetOrg);
      process.exit(1);
    }
  }
}

async function main() {
  // Cleanup AT START: remove Apex temp artifacts left by a prior hard-killed run.
  // Safe to run before the per-org lock is acquired because it only removes
  // org-setup-* temp DIRECTORIES and legacy ROOT temp files — never the
  // org-setup-lock-<org>.lock files (plain files), so it cannot clobber a
  // concurrent run's live lock.
  sweepStaleApexTempDirs();

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

  const parsed = parseArgs();
  const {
    uiBundleName,
    permsetNamesExplicit,
    yes,
    skipDeploy: argSkipDeploy,
    skipPermset: argSkipPermset,
    skipRole: argSkipRole,
    skipSelfReg: argSkipSelfReg,
    skipSocialLogin: argSkipSocialLogin,
    skipData: argSkipData,
    skipGraphql: argSkipGraphql,
    skipUIBundleBuild: argSkipUIBundleBuild,
  } = parsed;

  // Resolve the target org up front: explicit --target-org is used verbatim;
  // otherwise prompt (TTY) or fall back to the default org / exit.
  const targetOrg = await resolveTargetOrg(parsed);

  // Per-target-org lock: acquired right after the start-of-run
  // sweep and before any step runs, so two runs against the same org cannot
  // interleave destructive Apex. The startup sweep above deliberately skips lock
  // files, so it never races this. Released on process exit.
  acquireOrgLock(targetOrg);

  const permsetNames =
    permsetNamesExplicit.length > 0 ? permsetNamesExplicit : discoverPermissionSetNames();
  const permsetStepLabel =
    permsetNames.length === 0
      ? 'Permset — (none under permissionsets/)'
      : permsetNames.length <= 3
        ? `Permset — assign ${permsetNames.join(', ')}`
        : `Permset — assign ${permsetNames.length} permission sets`;

  // Validate org-setup.config.json ONCE, before any step runs. The three
  // load*Config helpers read from this already-validated object.
  const config = loadValidatedConfig();

  const hasDataPlan = existsSync(DATA_PLAN) && existsSync(DATA_DIR);
  const roleConfig = loadRoleConfig(config);
  const hasRoleConfig = roleConfig !== null;
  const selfRegConfig = loadSelfRegConfig(config);
  const hasSelfRegConfig = selfRegConfig !== null;
  const socialLoginConfig = loadSocialLoginConfig(config);
  const hasSocialLoginConfig = socialLoginConfig !== null;

  // Validate the selfRegProfile name for SOQL-safety up front, alongside the
  // config validation and BEFORE any org mutation (login/deploy). A quote /
  // backslash / control char is a config mistake, not a runtime value to
  // escape — fail fast here with a clean, actionable message rather than
  // letting the license gate throw a raw stack trace deep in the run after deploy.
  if (hasSelfRegConfig) {
    try {
      validateProfileNameForSoql(selfRegConfig.selfRegProfile);
    } catch (err) {
      console.error(`Invalid org-setup.config.json:\n  - ${err.message}`);
      process.exit(1);
    }
  }

  // Same fail-fast treatment for the socialLogin identifiers, alongside the
  // self-reg guard above and BEFORE any org mutation. communityMemberProfile,
  // every authProviderNames entry, and the optional communityUserPermset are all
  // interpolated into generated SOQL / CLI value strings — the Profile and
  // PermissionSet `WHERE Name = '…'` lookups, the AuthProvider/SamlSsoConfig
  // `DeveloperName IN (…)` list, and the NetworkMemberGroup/User queries. These
  // are developer-authored identifiers the app ships, so a quote / backslash /
  // control char is a config mistake to surface loudly here rather than a value
  // to silently escape (same rationale as validateSoqlName's self-reg use).
  if (hasSocialLoginConfig) {
    try {
      validateSoqlName(socialLoginConfig.communityMemberProfile, 'socialLogin.communityMemberProfile');
      for (const providerName of socialLoginConfig.authProviderNames ?? []) {
        validateSoqlName(providerName, 'socialLogin.authProviderNames entry');
      }
      if (socialLoginConfig.communityUserPermset) {
        validateSoqlName(socialLoginConfig.communityUserPermset, 'socialLogin.communityUserPermset');
      }
    } catch (err) {
      console.error(`Invalid org-setup.config.json:\n  - ${err.message}`);
      process.exit(1);
    }
  }

  // failFast is a fixed, implementer-owned classification — NOT
  // user-configurable. A fail-fast failure aborts the run immediately; a
  // skippable failure is recorded and the run continues. The exit code is
  // non-zero on any failure regardless of class.
  // Login is NOT in this picker: it is an unconditional precondition run before
  // deploy, not a toggleable step. The dev step is also gone: launching the dev
  // server moved to `npm run dev:preview`, so setup terminates cleanly after
  // graphql.
  const stepDefs = [
    { key: 'uiBundleBuild', label: 'UI Bundle Build — npm install + build (pre-deploy)', enabled: !argSkipUIBundleBuild, available: true, failFast: true },
    { key: 'deploy', label: 'Deploy — sf project deploy start', enabled: !argSkipDeploy, available: true, failFast: true },
    { key: 'permset', label: permsetStepLabel, enabled: !argSkipPermset, available: true, failFast: false },
    { key: 'role', label: `Role — assign "${roleConfig?.roleName ?? '?'}" to current user`, enabled: !argSkipRole && hasRoleConfig, available: hasRoleConfig, failFast: false },
    { key: 'selfReg', label: 'Self-Registration — enable for site', enabled: !argSkipSelfReg && hasSelfRegConfig, available: hasSelfRegConfig, failFast: false },
    { key: 'socialLogin', label: 'Social Login — enable auth providers + community profile', enabled: !argSkipSocialLogin && hasSocialLoginConfig, available: hasSocialLoginConfig, failFast: false },
    { key: 'data', label: 'Data — delete + import records via Apex', enabled: !argSkipData && hasDataPlan, available: hasDataPlan, failFast: true },
    { key: 'graphql', label: 'GraphQL — schema introspect + codegen', enabled: !argSkipGraphql, available: true, failFast: true },
  ];

  const selections = yes ? stepDefs.map((s) => s.enabled) : await promptSteps(stepDefs);
  const on = {};
  stepDefs.forEach((s, i) => {
    on[s.key] = selections[i];
  });

  const skipUIBundleBuild = !on.uiBundleBuild;
  const skipDeploy = !on.deploy;
  const skipPermset = !on.permset;
  const skipRole = !on.role;
  const skipSelfReg = !on.selfReg;
  const skipSocialLogin = !on.socialLogin;
  const skipData = !on.data;
  const skipGraphql = !on.graphql;

  const needsUIBundle = !skipUIBundleBuild || !skipGraphql;
  const uiBundleDir = needsUIBundle ? await discoverUIBundleDir(uiBundleName) : null;
  const doData = !skipData;

  console.log('Setup — target org:', targetOrg, '| UI bundle:', uiBundleDir ?? '(none)');
  console.log(
    'Steps: login=always deploy=%s permset=%s role=%s selfReg=%s socialLogin=%s data=%s graphql=%s uiBundle=%s',
    !skipDeploy,
    !skipPermset,
    !skipRole,
    !skipSelfReg,
    !skipSocialLogin,
    doData,
    !skipGraphql,
    !skipUIBundleBuild
  );

  // Login is an unconditional precondition: it is not part of
  // the step picker and cannot be skipped. It still no-ops when the org is already
  // connected, and stays fail-fast — a failed browser login aborts before deploy.
  const loginStep = { key: 'login', label: 'Login — org authentication', failFast: true };
  await runStep(loginStep, targetOrg, async () => {
    if (isOrgConnected(targetOrg)) {
      console.log('\n--- Login ---');
      console.log(`Org ${targetOrg} is already authenticated; skipping browser login.`);
    } else {
      run('Login (browser)', 'sf', ['org', 'login', 'web', '--alias', targetOrg]);
    }
  });

  // Ensure the self-reg profile is in networkMemberGroups before deploy so that
  // subsequent selfRegProfile / selfRegistration updates don't fail. This is
  // best-effort prep: if the site can't be derived (no network file, or the
  // ambiguous multi-network case where deriveSiteName throws), skip the prep
  // silently here — the selfReg step records that derivation failure as a
  // skippable StepError, so it stays in the ledger instead of aborting pre-deploy.
  if (!skipDeploy && selfRegConfig) {
    let preDeploySiteName = null;
    try {
      preDeploySiteName = deriveSiteName();
    } catch {
      // ambiguous derivation — surfaced by the selfReg step below
    }
    if (preDeploySiteName) {
      console.log('\n--- Ensure network member profile (pre-deploy) ---');
      ensureNetworkMemberProfile(selfRegConfig, preDeploySiteName);
    }
  }

  // Build all UI Bundles before deploy so dist exists for entity deployment
  const uiBundleBuildStep = stepDefs.find((s) => s.key === 'uiBundleBuild');
  let preDeployBundlesBuilt = false;
  if (!skipUIBundleBuild) {
    if (!skipDeploy) {
      await runStep(uiBundleBuildStep, targetOrg, () => {
        const allUIBundleDirs = discoverAllUIBundleDirs(uiBundleName);
        for (const dir of allUIBundleDirs) {
          const name = dir.split(/[/\\]/).pop();
          run(`UI Bundle install (${name})`, 'npm', ['install'], { cwd: dir });
          run(`UI Bundle build (${name})`, 'npm', ['run', 'build'], { cwd: dir });
        }
      });
      preDeployBundlesBuilt = true;
    }
    // When skipDeploy, the bundle build happens in the GraphQL section below;
    // its outcome is recorded there.
  } else {
    recordSkipped(uiBundleBuildStep, 'not selected');
  }

  const deployStep = stepDefs.find((s) => s.key === 'deploy');
  if (!skipDeploy) {
    await runStep(deployStep, targetOrg, () => {
      // License pre-check: deploy fails with a cryptic error when the
      // org lacks the UserLicense the selfRegProfile's metadata requires. Verify a
      // seat is available BEFORE `sf project deploy start` so the run aborts with a
      // clean message NAMING the missing license. The required license is read from
      // the local profile source (the profile isn't in the org yet pre-deploy, so
      // querying it would only report "profile missing"). Only gates when self-reg
      // is configured — that config names the profile the license is derived from.
      if (selfRegConfig) {
        const licenseGate = checkDeployLicense(selfRegConfig, targetOrg);
        if (!licenseGate.satisfied) {
          throw new StepError(`deploy blocked — ${licenseGate.reason}`);
        }
      }
      run('Deploy metadata', 'sf', ['project', 'deploy', 'start', '--target-org', targetOrg], {
        timeout: 180000,
      });
    });
  } else {
    recordSkipped(deployStep, 'not selected');
  }

  const permsetStep = stepDefs.find((s) => s.key === 'permset');
  if (!skipPermset) {
    await runStep(permsetStep, targetOrg, async () => {
      const permsetConfig = loadPermsetConfig(config);
      if (permsetNames.length === 0) {
        console.log('\n--- Assign permission sets ---');
        console.log('No permission sets found under permissionsets/ and none passed via --permset-name; skipping.');
        return;
      }
      console.log('\n--- Assign permission sets ---');

      // Resolve assignments (guest user lookups etc.) then run all sf assign calls in parallel.
      //
      // A guest-user resolution failure (no derivable site, or no guest user yet)
      // is collected — NOT thrown mid-loop. Throwing here would unwind the whole
      // runStep body before Promise.all and silently drop every assignment already
      // queued (e.g. a currentUser permset that sorts ahead of a guestUser one and
      // never depended on the site at all). Resolvable assignments still run; the
      // combined failure is thrown at the end so the step is still recorded failed.
      const assignmentJobs = [];
      const resolutionFailures = [];
      for (const permsetName of permsetNames) {
        const assignment = resolveAssignment(permsetName, permsetConfig);
        if (assignment.assignee === 'skip') {
          console.log(`Permission set "${permsetName}" — skipped (config).`);
          continue;
        }
        let effectiveUsername = null;
        if (assignment.assignee === 'guestUser') {
          // Site name is derived from the single network metadata file the app
          // ships — never restated per-assignment.
          const siteName = deriveSiteName();
          if (!siteName) {
            console.error(`Permission set "${permsetName}" — assignee is "guestUser" but no networks/<siteName>.network-meta.xml was found to derive the site; skipping.`);
            resolutionFailures.push(`${permsetName} (no network metadata to derive site)`);
            continue;
          }
          effectiveUsername = resolveGuestUsername(siteName, targetOrg);
          if (!effectiveUsername) {
            console.error(`Permission set "${permsetName}" — could not resolve guest user for site "${siteName}"; skipping.`);
            resolutionFailures.push(`${permsetName} (could not resolve guest user for site "${siteName}")`);
            continue;
          }
          console.log(`  Resolved guest user for site "${siteName}": ${effectiveUsername}`);
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

      const failures = [];
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
            failures.push(`${permsetName} (exit ${result.status ?? 1})`);
          }
        }
      }
      const allFailures = [...resolutionFailures, ...failures];
      if (allFailures.length > 0) {
        throw new StepError(`failed to assign permission set(s): ${allFailures.join(', ')}`);
      }
    });
  } else {
    recordSkipped(permsetStep, 'not selected');
  }

  const roleStep = stepDefs.find((s) => s.key === 'role');
  if (!skipRole) {
    console.log('\n--- Assign role ---');
    // Config shape (assignee === 'currentUser', non-empty roleName) is guaranteed
    // by the schema, so there is nothing to re-check here — the step either ran
    // (ok) or its assignment threw (failed). No manual recordSkipped inference.
    await runStep(roleStep, targetOrg, () => {
      assignRoleToCurrentUser(roleConfig.roleName, targetOrg);
    });
  } else {
    recordSkipped(roleStep, roleStep.available ? 'not selected' : 'no config');
  }

  const selfRegStep = stepDefs.find((s) => s.key === 'selfReg');
  if (!skipSelfReg) {
    // License pre-check: self-registration requires a seat on the
    // UserLicense the selfRegProfile belongs to. Verify it BEFORE running the step
    // — recordSkipped is only reachable here, ahead of runStep (mirroring the
    // not-selected branch); once inside a step body an unmet precondition could
    // only record `failed`. A missing / inactive / seatless license is a soft
    // precondition, not a setup failure, so warn + recordSkipped and move on.
    const licenseGate = checkSelfRegLicense(selfRegConfig, targetOrg);
    if (!licenseGate.satisfied) {
      console.warn(`\n--- Self-registration skipped ---\n  ⚠ ${licenseGate.reason}`);
      recordSkipped(selfRegStep, licenseGate.reason);
    } else {
      console.log('\n--- Enable self-registration ---');
      // Config shape (selfRegProfile, accountName) is guaranteed by the schema.
      // The site is derived inside the step body so a "multiple network files"
      // StepError is recorded in the ledger rather than escaping. No manual
      // recordSkipped inference.
      await runStep(selfRegStep, targetOrg, () => {
        const siteName = deriveSiteName();
        if (!siteName) {
          throw new StepError(
            'self-registration is configured but no networks/<siteName>.network-meta.xml was found to derive the site',
          );
        }
        enableSelfRegistration(selfRegConfig, siteName, targetOrg);
      });
    }
  } else {
    recordSkipped(selfRegStep, selfRegStep.available ? 'not selected' : 'no config');
  }

  const socialLoginStep = stepDefs.find((s) => s.key === 'socialLogin');
  if (!skipSocialLogin) {
    console.log('\n--- Social Login — enable auth providers + community profile ---');
    await runStep(socialLoginStep, targetOrg, () => {
      const siteName = deriveSiteName();
      if (!siteName) {
        throw new StepError(
          'socialLogin is configured but no networks/<siteName>.network-meta.xml was found to derive the site',
        );
      }

      const totalSubSteps = socialLoginConfig.communityUserPermset ? 4 : 3;

      // Sub-step 1: Enable "Allow using standard external profiles" org setting.
      // This is required so the SSO registration handler can create users with
      // standard community profiles (e.g. "Customer Community User").
      console.log(`  [1/${totalSubSteps}] Enabling "Allow standard external profiles" setting...`);
      enableExternalProfiles(targetOrg);

      // Sub-step 2: Link Auth Providers to the site's AuthConfig.
      // React (Site Container) sites hide SSO config in Admin UI, so this must
      // be done programmatically via AuthConfig/AuthConfigProviders records.
      console.log(`  [2/${totalSubSteps}] Linking Auth Providers to site AuthConfig...`);
      enableAuthProvidersForSite(socialLoginConfig.authProviderNames, siteName, targetOrg);

      // Sub-step 3: Add the community member profile to NetworkMemberGroup.
      // Without this, users created by the registration handler get
      // "NO_ACCESS: User was not authorized for the community".
      console.log(`  [3/${totalSubSteps}] Adding community member profile to NetworkMemberGroup...`);
      addCommunityMemberProfile(socialLoginConfig.communityMemberProfile, siteName, targetOrg);

      // Sub-step 4 (optional): Assign API-enabled permset to community users.
      // Without this, getCurrentUser() fails because /chatter/users/me requires
      // PermissionsApiEnabled which the standard community profile lacks.
      if (socialLoginConfig.communityUserPermset) {
        console.log(`  [4/${totalSubSteps}] Assigning API permset to community users...`);
        assignPermsetToCommunityUsers(
          socialLoginConfig.communityUserPermset,
          socialLoginConfig.communityMemberProfile,
          targetOrg,
        );
      }
    });
  } else {
    recordSkipped(socialLoginStep, socialLoginStep.available ? 'not selected' : 'no config');
  }

  const dataStep = stepDefs.find((s) => s.key === 'data');
  if (doData) {
   await runStep(dataStep, targetOrg, () => {
    // Prepare data for uniqueness (run before import so repeat imports don't conflict).
    // Per-app data normalization (reference remapping, unique-field mangling) ships with
    // the app's seed data as data/prepare-import-unique-fields.js — this script stays
    // object-agnostic and simply runs it if present.
    const prepareScript = resolve(DATA_DIR, 'prepare-import-unique-fields.js');
    if (existsSync(prepareScript)) {
      run('Prepare data (unique fields)', 'node', [prepareScript, '--data-dir', DATA_DIR], {
        cwd: ROOT,
      });
    }

    // Delete existing records so every run inserts the full dataset without duplicate conflicts.
    // Reverse plan order ensures children are removed before parents (FK safety).
    console.log('\n--- Clean existing data for fresh import ---');
    const planEntries = JSON.parse(readFileSync(DATA_PLAN, 'utf8'));
    const sobjectsReversed = [...planEntries.map((e) => e.sobject)].reverse();
    // One private temp dir for both the delete sweep and the import batches;
    // always removed in finally, even if a batch throws.
    withApexTempDir((writeApex) => {
    for (const sobject of sobjectsReversed) {
      // Bare identifier inside a dynamic-SOQL string literal — whitelist it (the
      // same guard buildApexInsert applies) so a malformed data-plan sobject
      // can't alter the delete query.
      validateApiName(sobject, 'sobject type');
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
      const tmpApex = writeApex('data.apex', apexCode);
      spawnSync('sf', ['apex', 'run', '--target-org', targetOrg, '--file', tmpApex], {
        cwd: ROOT,
        stdio: 'pipe',
        shell: true,
        timeout: 60000,
      });
      console.log(`  ${sobject}: cleaned`);
    }

    // Import via Anonymous Apex with Database.DMLOptions.duplicateRuleHeader.allowSave = true.
    // This bypasses both duplicate-rule blocks AND matching-service timeouts that the REST
    // API headers (Sforce-Duplicate-Rule-Action) cannot override.
    console.log('\n--- Data import (Apex) ---');
    const refMap = new Map();
    // Apex anonymous code is capped at ~1M chars total, but each batch is much
    // smaller in practice. The real constraint is the SETUP_RESULT_JSON debug log
    // line: Salesforce truncates debug lines at ~5KB, and large batches produce
    // JSON arrays that exceed that limit. With RESULT_JSON_PER_RECORD = 150 and
    // MAX_BATCH = 100, the worst-case output is ~15KB of JSON, which fits
    // comfortably after the debug-line prefix and the marker.
    const APEX_CHAR_LIMIT = 25000;
    const APEX_MAX_BATCH = 100;

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

        // Measured batching: size each record's rendered Apex (using
        // the same apexLiteral the insert uses) and pack batches under the char
        // limit, instead of the old estCharsPerRec = 40 + fields*55 guess that
        // under-counted long text fields and could overflow the anon-Apex limit.
        // Overhead is measured from the real builder with zero records so the
        // fixed boilerplate can't drift from buildApexInsert. Each record also
        // grows the per-batch `String[] refs = new String[]{'…',…}` line, so its
        // rendered refId literal is counted here too (mirroring the same
        // referenceId/_idx fallback the batch emit uses) — otherwise sizing
        // under-counts and a packed batch could edge past APEX_CHAR_LIMIT.
        //
        // CRITICAL: also account for the SETUP_RESULT_JSON output size. The
        // System.debug line can exceed the Salesforce debug log line limit when
        // the serialized JSON array is large. Estimate ~85 chars per success
        // result ({"ref":"_idxNNN","id":"001XXXXXXXXXXXXXXX"}) and ~150 chars per
        // potential error ({"ref":"_idxNNN","err":"typical error message"}), taking
        // the higher value to be conservative. This ensures the batching prevents
        // log truncation that would fail parseApexInsertResults.
        const overhead = buildApexInsert(entry.sobject, [], []).length;
        const RESULT_JSON_PER_RECORD = 150;
        const recordSizes = records.map((rec, i) => {
          let size = `{ ${entry.sobject} r = new ${entry.sobject}();\n`.length + 'recs.add(r); }\n'.length;
          for (const [key, val] of Object.entries(rec)) {
            if (key === 'attributes') continue;
            size += `r.put('${key}', ${apexLiteral(val)});\n`.length;
          }
          const refId = rec.attributes?.referenceId || `_idx${i}`;
          size += `'${escapeSoqlString(refId)}',`.length;
          // Add the estimated size of this record's JSON result entry in the
          // SETUP_RESULT_JSON output. Without this, large batches can produce
          // debug log lines that exceed Salesforce's limit and get truncated.
          size += RESULT_JSON_PER_RECORD;
          return size;
        });
        const batches = planApexBatches(recordSizes, {
          charLimit: APEX_CHAR_LIMIT,
          maxBatch: APEX_MAX_BATCH,
          overhead,
        });

        let imported = 0;
        for (const { start, count } of batches) {
          const batch = records.slice(start, start + count);
          const refIds = batch.map((r, j) => r.attributes?.referenceId || `_idx${start + j}`);
          const apex = buildApexInsert(entry.sobject, batch, refIds);
          const tmpApex = writeApex('data.apex', apex);
          const apexResult = spawnSync(
            'sf',
            ['apex', 'run', '--target-org', targetOrg, '--file', tmpApex],
            { cwd: ROOT, stdio: 'pipe', shell: true, timeout: 120000 }
          );
          const apexOut = apexResult.stdout?.toString() || '';
          const apexErr = apexResult.stderr?.toString() || '';
          if (apexResult.status !== 0 && !apexOut.includes('Compiled successfully')) {
            process.stderr.write(apexErr || apexOut);
            throw new StepError(`${entry.sobject}: apex execution failed`);
          }
          const parsed = parseApexInsertResults(apexOut);
          if (!parsed.ok) {
            // A missing/truncated result marker must fail loudly — never read as
            // "0 errors" and let a partial import look successful.
            process.stderr.write(apexErr || apexOut);
            throw new StepError(`data import (${entry.sobject}) — ${parsed.error}`);
          }
          if (parsed.errors.length) {
            for (const e of parsed.errors.slice(0, 5)) {
              console.error(`    ${e.ref}: ${e.message.trim()}`);
            }
            if (parsed.errors.length > 5) console.error(`    ... and ${parsed.errors.length - 5} more`);
            throw new StepError(`data import (${entry.sobject}) — ${parsed.errors.length} record error(s)`);
          }
          if (entry.saveRefs) {
            for (const s of parsed.successes) refMap.set(s.ref, s.id);
          }
          imported += parsed.successes.length;
        }
        console.log(`  ${entry.sobject}: imported ${imported} records`);
      }
    }
    });
   });
  } else {
    recordSkipped(dataStep, dataStep.available ? 'not selected' : 'no data plan');
  }

  const graphqlStep = stepDefs.find((s) => s.key === 'graphql');
  if (!skipGraphql) {
    await runStep(graphqlStep, targetOrg, () => {
      run('UI Bundle npm install', 'npm', ['install'], { cwd: uiBundleDir });
      run('GraphQL schema (introspect)', 'npm', ['run', 'graphql:schema'], {
        cwd: uiBundleDir,
        env: { ...process.env, SF_TARGET_ORG: targetOrg },
      });
      run('GraphQL codegen', 'npm', ['run', 'graphql:codegen'], { cwd: uiBundleDir });
      run('UI Bundle build (post-codegen)', 'npm', ['run', 'build'], { cwd: uiBundleDir });
    });
  } else {
    recordSkipped(graphqlStep, 'not selected');
    if (!skipUIBundleBuild && skipDeploy && !preDeployBundlesBuilt) {
      // The pre-deploy build never ran (deploy was skipped); build here and
      // record the uiBundleBuild outcome that the pre-deploy branch would have.
      await runStep(uiBundleBuildStep, targetOrg, () => {
        run('UI Bundle npm install', 'npm', ['install'], { cwd: uiBundleDir });
        run('UI Bundle build', 'npm', ['run', 'build'], { cwd: uiBundleDir });
      });
      preDeployBundlesBuilt = true;
    }
  }

  // When uiBundleBuild was selected but the dedicated pre-deploy build never ran
  // (deploy skipped and graphql selected), the build happened inside the graphql
  // step — which is fail-fast, so reaching here means it succeeded. Record ok.
  if (!skipUIBundleBuild && !preDeployBundlesBuilt && !results.some((r) => r.key === 'uiBundleBuild')) {
    recordOk(uiBundleBuildStep);
  }

  // Setup terminates cleanly here. Launching the dev server is
  // no longer part of setup — run `npm run dev:preview` (scripts/org-setup-dev.mjs) for that.
  printSummary(targetOrg);
  if (finalExitCode() === 0) {
    console.log('\nTo launch the dev server, run:  npm run dev:preview');
  }
  process.exit(finalExitCode());
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
