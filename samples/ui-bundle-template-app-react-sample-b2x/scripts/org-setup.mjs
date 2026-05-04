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
 *       "defaultAssignee": "currentUser",
 *       "assignments": {
 *         "Guest_Permset": { "assignee": "guest@mysite.example.com" },
 *         "Internal_Only": { "assignee": "skip" }
 *       }
 *     }
 *   }
 *   Assignee values: "currentUser" (default), "skip", or a specific username.
 */

import { spawnSync } from 'node:child_process';
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
    skipData: false,
    skipGraphql: false,
    skipUIBundleBuild: false,
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
    else if (args[i] === '--skip-data') flags.skipData = true;
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
        "defaultAssignee": "currentUser",
        "assignments": {
          "Guest_Permset": { "assignee": "guest@mysite.example.com" },
          "Internal_Only": { "assignee": "skip" }
        }
      }
    }
  Assignee values: "currentUser" (default), "skip", or a specific username.
  Without this file, all discovered permsets are assigned to the current user.
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
 *       "defaultAssignee": "currentUser",          // "currentUser" (default) or "skip"
 *       "assignments": {
 *         "My_Guest_Permset": { "assignee": "guest@mysite.example.com" },
 *         "Internal_Only":    { "assignee": "skip" }
 *       }
 *     }
 *   }
 *
 * Assignee values:
 *   "currentUser" — assign to the user running the script (default)
 *   "skip"        — do not assign this permset
 *   "<username>"  — assign to a specific user via --on-behalf-of
 *
 * Returns { defaultAssignee: string, assignments: Record<string, { assignee: string }> }
 */
function loadPermsetConfig() {
  const configPath = resolve(__dirname, 'org-setup.config.json');
  const defaults = { defaultAssignee: 'currentUser', assignments: {} };
  if (!existsSync(configPath)) return defaults;
  try {
    const raw = JSON.parse(readFileSync(configPath, 'utf8'));
    const section = raw?.permsetAssignments;
    if (!section) return defaults;
    return {
      defaultAssignee: section.defaultAssignee || 'currentUser',
      assignments: section.assignments || {},
    };
  } catch (err) {
    console.warn(`Warning: failed to parse org-setup.config.json: ${err.message}; using defaults.`);
    return defaults;
  }
}

/** Resolve the effective assignee for a given permset name. */
function resolveAssignee(permsetName, permsetConfig) {
  const override = permsetConfig.assignments[permsetName];
  return override?.assignee || permsetConfig.defaultAssignee;
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

  function render() {
    return steps.map((s, i) => {
      const ptr = i === cursor ? `${CYAN}❯${RST}` : ' ';
      if (!s.available) return `${ptr} ${DIM}○ ${s.label} (n/a)${RST}`;
      const chk = selected[i] ? `${GREEN}●${RST}` : '○';
      return `${ptr} ${chk} ${s.label}`;
    });
  }

  return new Promise((resolve) => {
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.setEncoding('utf8');
    process.stdout.write('\x1B[?25l');
    console.log('\nSelect steps (↑↓ move, space toggle, a all, enter confirm):\n');
    process.stdout.write(render().join('\n') + '\n');

    function redraw() {
      process.stdout.write(`\x1B[${steps.length}A`);
      for (const line of render()) process.stdout.write(`\x1B[2K${line}\n`);
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

  const stepDefs = [
    { key: 'login', label: 'Login — org authentication', enabled: !argSkipLogin, available: true },
    { key: 'uiBundleBuild', label: 'UI Bundle Build — npm install + build (pre-deploy)', enabled: !argSkipUIBundleBuild, available: true },
    { key: 'deploy', label: 'Deploy — sf project deploy start', enabled: !argSkipDeploy, available: true },
    { key: 'permset', label: permsetStepLabel, enabled: !argSkipPermset, available: true },
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
  const skipData = !on.data;
  const skipGraphql = !on.graphql;
  const skipDev = !on.dev;

  const needsUIBundle = !skipUIBundleBuild || !skipGraphql || !skipDev;
  const uiBundleDir = needsUIBundle ? discoverUIBundleDir(uiBundleName) : null;
  const doData = !skipData;

  console.log('Setup — target org:', targetOrg, '| UI bundle:', uiBundleDir ?? '(none)');
  console.log(
    'Steps: login=%s deploy=%s permset=%s data=%s graphql=%s uiBundle=%s dev=%s',
    !skipLogin,
    !skipDeploy,
    !skipPermset,
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
      for (const permsetName of permsetNames) {
        const assignee = resolveAssignee(permsetName, permsetConfig);
        if (assignee === 'skip') {
          console.log(`Permission set "${permsetName}" — skipped (config).`);
          continue;
        }
        const sfArgs = ['org', 'assign', 'permset', '--name', permsetName, '--target-org', targetOrg];
        if (assignee !== 'currentUser') {
          sfArgs.push('--on-behalf-of', assignee);
        }
        const assigneeLabel = assignee === 'currentUser' ? 'current user' : assignee;
        const permsetResult = spawnSync('sf', sfArgs, {
          cwd: ROOT,
          stdio: 'pipe',
          shell: true,
        });
        if (permsetResult.status === 0) {
          console.log(`Permission set "${permsetName}" assigned to ${assigneeLabel}.`);
        } else {
          const out =
            (permsetResult.stderr?.toString() || '') + (permsetResult.stdout?.toString() || '');
          if (out.includes('Duplicate') && out.includes('PermissionSet')) {
            console.log(`Permission set "${permsetName}" already assigned to ${assigneeLabel}; skipping.`);
          } else if (out.includes('not found') && out.includes('target org')) {
            console.log(`Permission set "${permsetName}" not in org; skipping.`);
          } else {
            process.stdout.write(permsetResult.stdout?.toString() || '');
            process.stderr.write(permsetResult.stderr?.toString() || '');
            console.error(`\nSetup failed at step: Assign permission set (${permsetName})`);
            process.exit(permsetResult.status ?? 1);
          }
        }
      }
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

  if (!skipGraphql || !skipUIBundleBuild) {
    run('UI Bundle npm install', 'npm', ['install'], { cwd: uiBundleDir });
  }

  if (!skipGraphql) {
    run('Set default org for schema', 'sf', ['config', 'set', 'target-org', targetOrg, '--global']);
    run('GraphQL schema (introspect)', 'npm', ['run', 'graphql:schema'], { cwd: uiBundleDir });
    run('GraphQL codegen', 'npm', ['run', 'graphql:codegen'], { cwd: uiBundleDir });
  }

  if (!skipUIBundleBuild) {
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
