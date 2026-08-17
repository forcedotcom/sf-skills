/**
 * Shared helpers for the org-setup scripts.
 *
 * Factored out of org-setup.mjs so BOTH `org-setup.mjs` and `org-setup-dev.mjs` import the
 * same primitives instead of duplicating them:
 *   - process runners (`run`, `runAsync`, `spawnAsync`)
 *   - SFDX path + UI-bundle discovery (`resolveSfdxSource`, `discoverAllUIBundleDirs`,
 *     `discoverUIBundleDir` — with the multi-bundle acknowledgment)
 *   - the interactive `--target-org` fallback (`resolveTargetOrg`) and its
 *     single-select picker (`promptSelect`)
 *   - pure, unit-testable logic for the license gate, SOQL-name validation, org-list
 *     parsing, and the non-TTY multi-bundle warning
 *
 * IMPORTANT: this module is side-effect-free at import time — no top-level
 * readFileSync / process.exit / CLI run — so it can be imported by tests and by
 * org-setup-dev.mjs without triggering org-setup's main(). All I/O happens inside the
 * exported functions, only when they are called. Errors are plain `Error`s (not
 * org-setup's StepError) to avoid an import cycle; runStep handles both alike.
 */

import { spawnSync } from 'node:child_process';
import { readdirSync, existsSync, readFileSync } from 'node:fs';
import { resolve } from 'node:path';

// ---------------------------------------------------------------------------
// Pure logic (no I/O) — unit-testable in isolation.
// ---------------------------------------------------------------------------

/**
 * Validate that a config-authored identifier is safe to interpolate into a SOQL
 * `WHERE <field> = '<value>'` clause (validate-and-fail with a strict whitelist,
 * NOT an escaper). These values (role name, site name,
 * self-reg profile name) are developer-authored identifiers the app ships, not
 * end-user data, and legitimate identifiers are drawn from letters, digits,
 * spaces, hyphens, and underscores. Anything outside that set — a `'`, `\`, `=`,
 * `"`, `&`, `<`, `>`, punctuation, or a control char — is treated as a config
 * mistake to surface loudly rather than a value to silently escape. The
 * whitelist is deliberately broader than the injection characters alone so a
 * single positive rule covers every SOQL/quoting hazard at once.
 *
 * NOTE: this is for config *identifiers*. Free-form display values that
 * legitimately contain punctuation (e.g. an Account name like `O'Brien Rentals`)
 * are escaped at their call site instead — see org-setup.mjs's Account path.
 *
 * @param {*} value        the value to validate (coerced to string)
 * @param {string} fieldLabel  how to name the field in an error (e.g. "roleName")
 * @param {object} [opts]
 * @param {string} [opts.remediation]  where the author fixes it, e.g.
 *   "org-setup.config.json" or "the networks/<siteName>.network-meta.xml filename".
 *   Defaults to org-setup.config.json.
 * @returns {string} the value unchanged when valid; throws otherwise.
 */
export function validateSoqlName(value, fieldLabel, opts = {}) {
  const { remediation = 'org-setup.config.json' } = opts;
  const s = String(value);
  if (!/^[A-Za-z0-9 _-]+$/.test(s)) {
    throw new Error(
      `${fieldLabel} "${value}" contains an unsupported character ` +
        `(only letters, digits, spaces, hyphens, and underscores are allowed). ` +
        `Fix it in ${remediation}.`,
    );
  }
  return s;
}

/**
 * Back-compat wrapper for the self-reg profile name (the original call site).
 * Delegates to the strict whitelist above; kept as a named export so
 * existing importers and tests need no change beyond the tightened rule.
 */
export function validateProfileNameForSoql(name) {
  return validateSoqlName(name, 'selfRegProfile name');
}

/**
 * Escape a free-form value for safe interpolation inside a single-quoted SOQL
 * string literal. Unlike validateSoqlName, this is for display
 * values that legitimately contain punctuation — e.g. an Account name like
 * `O'Brien Rentals & Co.` — where rejecting the value would be wrong. Escapes
 * the backslash FIRST (so an already-present `\` isn't double-counted) then the
 * quote, matching SOQL's `\'` / `\\` escape rules. Returns the escaped inner
 * string (no surrounding quotes — the caller supplies those).
 */
export function escapeSoqlString(value) {
  return String(value).replace(/\\/g, '\\\\').replace(/'/g, "\\'");
}

/**
 * Validate a Salesforce API name (an SObject type or a field API name) that is
 * interpolated as a bare identifier into generated Apex / dynamic SOQL — e.g.
 * `new ${sobject}()`, `r.put('${field}', …)`, or `Database.query('SELECT Id FROM
 * ${sobject} …')`. Unlike a WHERE value, an identifier can't be
 * quoted-and-escaped, so the only safe treatment is a strict whitelist. Valid API
 * names are letters, digits, and underscores only (the `__c` / `__r` custom and
 * namespace suffixes are already covered by that set); anything else — a quote,
 * space, dot, or `)` — would let a crafted seed-data field name or sobject break
 * out of the surrounding statement, so it is rejected loudly. These identifiers
 * come from the app-shipped data plan / seed JSON, so a violation is a fixture
 * bug, not user input; this keeps the identifier hardening symmetric with the
 * value escaping (apexLiteral / escapeSoqlString) already applied around them.
 *
 * @param {*} value  the identifier to validate (coerced to string)
 * @param {string} fieldLabel  how to name it in an error (e.g. "sobject type")
 * @returns {string} the value unchanged when valid; throws otherwise.
 */
export function validateApiName(value, fieldLabel) {
  const s = String(value);
  if (!/^[A-Za-z0-9_]+$/.test(s)) {
    throw new Error(
      `${fieldLabel} "${value}" is not a valid Salesforce API name ` +
        `(only letters, digits, and underscores are allowed). ` +
        `Check the seed data plan (data-plan.json) and record field names.`,
    );
  }
  return s;
}

/**
 * Parse the single `SETUP_RESULT_JSON:` marker line that buildApexInsert emits
 * from anonymous Apex. Replaces the old per-record REF:/ERR: debug
 * scraping. The marker carries a JSON array of `{ ref, id? , err? }` — one entry
 * per inserted record.
 *
 * Robustness is the whole point: a debug log can be truncated, so a missing
 * marker or a payload that doesn't parse as the expected array is reported as a
 * hard failure via `ok: false` rather than silently reading as "0 records, 0
 * errors" (which would let a partial import look successful).
 *
 * @param {string} apexOut  raw stdout from `sf apex run`
 * @returns {{ ok: boolean, error: string|null,
 *             successes: Array<{ref:string, id:string}>,
 *             errors: Array<{ref:string, message:string}> }}
 */
export function parseApexInsertResults(apexOut) {
  const text = String(apexOut ?? '');

  // Strategy: the actual System.debug output appears somewhere in the log as a JSON array.
  // First, try to find it via the USER_DEBUG line format (most reliable).
  // The line looks like: `...|USER_DEBUG|[line]|ERROR|SETUP_RESULT_JSON:[{"ref":"a","id":"001..."}]`.
  // The array can be empty ([]) for zero records, so use .*? instead of .+? to allow empty arrays.
  // Accept any log level (DEBUG, ERROR, etc) to handle both old and new logging configurations.
  const userDebugPattern = /\|USER_DEBUG\|.*?\|(DEBUG|ERROR|INFO|WARN)\|SETUP_RESULT_JSON:(\[.*?\])(?:\n|$)/s;
  let match = text.match(userDebugPattern);

  if (match) {
    return parseJsonPayload(match[2].trim());
  }

  // Fallback: look for the marker followed by a JSON array, but skip "Execute Anonymous:" lines
  const markerIdx = text.indexOf('SETUP_RESULT_JSON:');
  if (markerIdx === -1) {
    return {
      ok: false,
      error: 'no SETUP_RESULT_JSON marker found in Apex output (log may be truncated or the insert did not run)',
      successes: [],
      errors: [],
    };
  }

  // Check if this is the source code line, not the debug output
  const lineStart = text.lastIndexOf('\n', markerIdx) + 1;
  const line = text.slice(lineStart, Math.min(text.length, lineStart + 200));
  if (line.includes('Execute Anonymous:')) {
    return {
      ok: false,
      error: 'found SETUP_RESULT_JSON in source code but not in debug output (debug output may be missing or truncated)',
      successes: [],
      errors: [],
    };
  }

  // Extract what follows the marker up to end of line. Pass it to parseJsonPayload
  // which will validate it's proper JSON and an array, giving specific error messages.
  const afterMarker = text.slice(markerIdx + 'SETUP_RESULT_JSON:'.length);
  const payload = afterMarker.split('\n')[0].trim();

  return parseJsonPayload(payload);
}

function parseJsonPayload(payload) {
  let parsed;
  try {
    parsed = JSON.parse(payload);
  } catch {
    return {
      ok: false,
      error: 'SETUP_RESULT_JSON payload was not valid JSON (log line may be truncated)',
      successes: [],
      errors: [],
    };
  }
  if (!Array.isArray(parsed)) {
    return {
      ok: false,
      error: 'SETUP_RESULT_JSON payload was not a JSON array',
      successes: [],
      errors: [],
    };
  }

  const successes = [];
  const errors = [];
  for (const entry of parsed) {
    if (!entry || typeof entry !== 'object') continue;
    const ref = entry.ref != null ? String(entry.ref) : '';
    if (entry.err != null) {
      errors.push({ ref, message: String(entry.err) });
    } else if (entry.id != null) {
      successes.push({ ref, id: String(entry.id) });
    }
  }
  return { ok: true, error: null, successes, errors };
}

/**
 * Group serialized-record sizes into batches whose combined Apex character count
 * (fixed per-batch overhead + each record's rendered size) stays under
 * `charLimit`, subject to `maxBatch` records per batch. Replaces the
 * old `estCharsPerRec = 40 + fields*55` heuristic with a measurement the caller
 * supplies via `recordSizes`.
 *
 * Guarantees at least one record per batch even when a single record's size (plus
 * overhead) already exceeds `charLimit` — otherwise a large record would loop
 * forever or emit an empty batch. That oversized record is placed alone in its
 * own batch and left for Apex to accept or reject.
 *
 * @param {number[]} recordSizes  rendered Apex char length of each record, in order
 * @param {object} opts
 * @param {number} opts.charLimit  max total chars per batch (record chars + overhead)
 * @param {number} opts.maxBatch   max records per batch
 * @param {number} [opts.overhead] fixed per-batch char cost (DML boilerplate); default 0
 * @returns {Array<{start:number, count:number}>}  batch slices over the input order
 */
export function planApexBatches(recordSizes, { charLimit, maxBatch, overhead = 0 }) {
  const batches = [];
  let start = 0;
  const n = recordSizes.length;
  while (start < n) {
    let count = 0;
    let total = overhead;
    while (start + count < n && count < maxBatch) {
      const next = recordSizes[start + count];
      // Always take at least one record, even if it alone busts the limit.
      if (count > 0 && total + next > charLimit) break;
      total += next;
      count += 1;
    }
    batches.push({ start, count });
    start += count;
  }
  return batches;
}

/**
 * Decide whether the self-reg profile's UserLicense is satisfied, from the rows
 * a `SELECT UserLicense.LicenseDefinitionKey, UserLicense.Name, UserLicense.Status,
 * UserLicense.TotalLicenses, UserLicense.UsedLicenses FROM Profile WHERE Name = '…'`
 * query returns. The seat math MUST be done here in JS — SOQL cannot
 * compare two fields. Matches/report on the stable
 * `LicenseDefinitionKey`, never the display Name.
 *
 * satisfied ⇔ Status === 'Active' && (total === -1 [unlimited sentinel] || total - used > 0).
 * 0 rows / null UserLicense ⇒ not satisfied, with a reason naming the profile.
 *
 * @returns {{ satisfied: boolean, reason: string|null, license: {key,label,status,total,used}|null }}
 */
export function evaluateLicenseRows(rows, profileName) {
  const lic = Array.isArray(rows) ? rows[0]?.UserLicense : null;
  if (!lic) {
    return {
      satisfied: false,
      reason: `no UserLicense found for profile "${profileName}" — the profile is missing in the org or its name is misspelled`,
      license: null,
    };
  }
  const key = lic.LicenseDefinitionKey ?? null;
  const label = lic.Name ?? key ?? 'unknown license';
  const total = Number(lic.TotalLicenses);
  const used = Number(lic.UsedLicenses);
  const license = { key, label, status: lic.Status, total, used };

  if (lic.Status !== 'Active') {
    return { satisfied: false, reason: `license ${label} (${key}) is not Active (Status=${lic.Status})`, license };
  }
  // Seat counts should always be integers in practice, but guard against a
  // missing/non-numeric field so the skip reason stays legible (not "NaN/NaN").
  if (!Number.isFinite(total) || !Number.isFinite(used)) {
    return { satisfied: false, reason: `could not read seat counts for license ${label} (${key})`, license };
  }
  // -1 is the documented "unlimited" sentinel (defensive — unverified live).
  if (total === -1 || total - used > 0) {
    return { satisfied: true, reason: null, license };
  }
  return {
    satisfied: false,
    reason: `license ${label} (${key}) has no available seats (${used}/${total} used)`,
    license,
  };
}

/**
 * Parse `sf org list --json` defensively into a flat org list + the default org
 * (mirrors isOrgConnected's try/catch tolerance). Collects
 * every array under `result` (nonScratchOrgs, scratchOrgs, sandboxes, devHubs, …)
 * so the picker sees all authenticated orgs; the default is the entry marked
 * `isDefaultUsername`. Malformed / unexpected JSON ⇒ empty result (caller then
 * falls back to the clear error).
 *
 * @returns {{ orgs: Array<{alias:string|null, username:string, isDefault:boolean}>, defaultOrg: string|null }}
 */
export function parseOrgList(jsonText) {
  let parsed;
  try {
    parsed = JSON.parse(jsonText);
  } catch {
    return { orgs: [], defaultOrg: null };
  }
  const result = parsed?.result;
  if (!result || typeof result !== 'object') return { orgs: [], defaultOrg: null };

  const orgs = [];
  const seen = new Set();
  for (const val of Object.values(result)) {
    if (!Array.isArray(val)) continue;
    for (const entry of val) {
      if (!entry || typeof entry !== 'object' || !entry.username) continue;
      if (seen.has(entry.username)) continue;
      seen.add(entry.username);
      orgs.push({
        alias: entry.alias ?? null,
        username: entry.username,
        isDefault: entry.isDefaultUsername === true,
      });
    }
  }
  const def = orgs.find((o) => o.isDefault);
  return { orgs, defaultOrg: def ? (def.alias ?? def.username) : null };
}

/**
 * Multi-line warning for the non-TTY multi-bundle case: there is nothing to
 * interactively acknowledge, so keep the deterministic
 * `all[0]` pick but never do it silently — name every bundle, the chosen one, and
 * the `--ui-bundle-name` remedy.
 */
export function buildMultiBundleWarning(allBundleNames, chosen) {
  return [
    `⚠ Multiple UI bundles found under uiBundles/ (${allBundleNames.length}):`,
    ...allBundleNames.map((n) => `    - ${n}${n === chosen ? '   ← using this one' : ''}`),
    `  Using "${chosen}" (first alphabetically). To deploy a different bundle, re-run with:`,
    `    --ui-bundle-name <name>`,
  ].join('\n');
}

// ---------------------------------------------------------------------------
// Process runner (moved from org-setup.mjs; plain Error to avoid an import cycle).
// Only the synchronous `run` is shared — org-setup-dev.mjs runs its steps serially. The
// async spawn variants stay local to org-setup.mjs where the parallel permset
// path uses them, so this module exposes no caller-less surface.
// ---------------------------------------------------------------------------

export function run(name, cmd, args, opts = {}) {
  const { cwd = process.cwd(), optional = false } = opts;
  console.log('\n---', name, '---');
  const result = spawnSync(cmd, args, {
    cwd,
    stdio: 'inherit',
    shell: true,
    ...(opts.env && { env: opts.env }),
    ...(opts.timeout && { timeout: opts.timeout }),
  });
  if (result.status !== 0 && !optional) {
    throw new Error(`${name} (exit ${result.status ?? 1})`);
  }
  return result;
}

// ---------------------------------------------------------------------------
// SFDX paths + UI-bundle discovery.
// ---------------------------------------------------------------------------

/**
 * Resolve the first package directory's source root (main/default) from
 * sfdx-project.json under `root`. Exits non-zero with a clear message when the
 * project file or packageDirectories path is missing. Called explicitly by each
 * entry script (not at import) so this module stays side-effect-free.
 */
export function resolveSfdxSource(root) {
  const sfdxPath = resolve(root, 'sfdx-project.json');
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
  return resolve(root, pkgDir, 'main', 'default');
}

/** Basename of a bundle dir path, cross-platform. */
function bundleName(dir) {
  return dir.split(/[/\\]/).pop();
}

/**
 * All UI bundle directories under `uiBundlesDir` (alphabetical, hidden dirs
 * excluded). When `uiBundleName` is given, returns just that one (erroring if it
 * doesn't exist). Exits non-zero when the uiBundles dir or a named bundle is
 * missing.
 */
export function discoverAllUIBundleDirs(uiBundlesDir, uiBundleName) {
  if (!existsSync(uiBundlesDir)) {
    console.error(`Error: uiBundles directory not found: ${uiBundlesDir}`);
    process.exit(1);
  }
  const entries = readdirSync(uiBundlesDir, { withFileTypes: true });
  const dirs = entries.filter((e) => e.isDirectory() && !e.name.startsWith('.'));
  if (dirs.length === 0) {
    console.error(`Error: No UI bundle folder found under ${uiBundlesDir}`);
    process.exit(1);
  }
  if (uiBundleName) {
    const requested = dirs.find((d) => d.name === uiBundleName);
    if (!requested) {
      console.error(`Error: UI bundle directory not found: ${uiBundleName}`);
      process.exit(1);
    }
    return [resolve(uiBundlesDir, requested.name)];
  }
  return dirs.map((d) => resolve(uiBundlesDir, d.name));
}

/**
 * Resolve the single UI bundle to operate on, with the multi-bundle
 * acknowledgment. When >1 bundle exists and no `--ui-bundle-name` was given:
 *   - TTY: present a single-select picker (all bundles, alphabetical all[0]
 *     preselected) — enter accepts all[0], arrows choose another.
 *   - non-TTY: keep the deterministic all[0] pick but emit the multi-line warning
 *     — never a silent pick.
 * Explicit `--ui-bundle-name` short-circuits both (no prompt, no warning).
 */
export async function discoverUIBundleDir(uiBundlesDir, uiBundleName) {
  const all = discoverAllUIBundleDirs(uiBundlesDir, uiBundleName);
  if (all.length > 1 && !uiBundleName) {
    const names = all.map(bundleName);
    if (process.stdin.isTTY) {
      const idx = await promptSelect(names, {
        prompt: 'Multiple UI bundles found — select which one to deploy:',
        preselectedIndex: 0,
      });
      return all[idx];
    }
    console.warn(buildMultiBundleWarning(names, names[0]));
  }
  return all[0];
}

// ---------------------------------------------------------------------------
// Interactive single-select picker + --target-org fallback.
// ---------------------------------------------------------------------------

/**
 * Interactive single-select: arrow keys navigate, enter confirms. Returns the
 * chosen index. Falls through to `preselectedIndex` immediately when stdin is not
 * a TTY. Built on the same raw-mode scaffolding as promptSteps (org-setup.mjs)
 * but selects exactly one item.
 */
export function promptSelect(options, { prompt = 'Select an option:', preselectedIndex = 0 } = {}) {
  if (!process.stdin.isTTY || options.length === 0) return Promise.resolve(preselectedIndex);

  let cursor = Math.min(Math.max(0, preselectedIndex), options.length - 1);
  const RST = '\x1B[0m';
  const CYAN = '\x1B[36m';
  const GREEN = '\x1B[32m';

  function render() {
    return options.map((label, row) => {
      const ptr = row === cursor ? `${CYAN}❯${RST}` : ' ';
      const chk = row === cursor ? `${GREEN}●${RST}` : '○';
      return `${ptr} ${chk} ${label}`;
    });
  }

  return new Promise((resolvePromise) => {
    process.stdin.setRawMode(true);
    process.stdin.resume();
    process.stdin.setEncoding('utf8');
    process.stdout.write('\x1B[?25l');
    console.log(`\n${prompt} (↑↓ move, enter confirm):\n`);
    let prevRows = options.length;
    process.stdout.write(render().join('\n') + '\n');

    function redraw() {
      process.stdout.write(`\x1B[${prevRows}A`);
      const lines = render();
      for (const line of lines) process.stdout.write(`\x1B[2K${line}\n`);
      prevRows = lines.length;
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
        resolvePromise(cursor);
        return;
      }
      if (key === '\x1B[A' || key === 'k') {
        cursor = Math.max(0, cursor - 1);
        redraw();
      } else if (key === '\x1B[B' || key === 'j') {
        cursor = Math.min(options.length - 1, cursor + 1);
        redraw();
      }
    });
  });
}

/**
 * Resolve the target org. When `--target-org` is supplied it is returned
 * verbatim with NO `sf org list` call (byte-for-byte the scripted path).
 * Otherwise discover authenticated orgs via `sf org list --json` and:
 *   - TTY: present a picker with the default org at the top and preselected;
 *     enter selects the default.
 *   - non-TTY: use the default org if resolvable, else exit 1 with a clear
 *     message.
 */
export async function resolveTargetOrg(parsed) {
  if (parsed.targetOrg) return parsed.targetOrg;

  const listResult = spawnSync('sf', ['org', 'list', '--json'], {
    encoding: 'utf8',
    shell: true,
  });
  const { orgs, defaultOrg } = parseOrgList(listResult.status === 0 ? listResult.stdout : '');

  if (process.stdin.isTTY && orgs.length > 0) {
    // Default org first + preselected; the rest keep sf's order.
    const ordered = [...orgs].sort((a, b) => (b.isDefault ? 1 : 0) - (a.isDefault ? 1 : 0));
    const labels = ordered.map((o) => {
      const name = o.alias ?? o.username;
      const suffix = o.alias && o.alias !== o.username ? ` (${o.username})` : '';
      return `${name}${suffix}${o.isDefault ? '  [default]' : ''}`;
    });
    const idx = await promptSelect(labels, { prompt: 'Select the target org:', preselectedIndex: 0 });
    const chosen = ordered[idx];
    return chosen.alias ?? chosen.username;
  }

  if (defaultOrg) {
    console.log(`No --target-org given; using the default org: ${defaultOrg}`);
    return defaultOrg;
  }

  console.error(
    'Error: --target-org <alias> is required. No default org is set and this is not an ' +
      'interactive terminal. Set a default org (sf config set target-org=<alias>) or pass --target-org.',
  );
  process.exit(1);
}
