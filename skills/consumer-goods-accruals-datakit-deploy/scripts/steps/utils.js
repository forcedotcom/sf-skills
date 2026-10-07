const { execSync, execFileSync } = require('child_process');
const fs = require('fs');
const path = require('path');

/** Returns the correct sf binary name for the current OS. */
function getSfBin() {
  return process.platform === 'win32' ? 'sf.cmd' : 'sf';
}

/**
 * sf org display --json stopped returning a real accessToken as of CLI v2.136.8
 * (the field becomes a redacted hint string). Fall back to
 * `sf org auth show-access-token` on those versions.
 */
const ACCESS_TOKEN_VIA_SHOW_SINCE = [2, 136, 8];

function getSfCliVersion() {
  try {
    const raw = execFileSync(getSfBin(), ['version', '--json'], { encoding: 'utf8', stdio: 'pipe' });
    const { cliVersion } = JSON.parse(raw);
    const m = (cliVersion || '').match(/(\d+)\.(\d+)\.(\d+)/);
    return m ? m.slice(1).map(Number) : null;
  } catch (_) {
    return null;
  }
}

function isSfAtLeast(version, min) {
  if (!version) return true; // unknown version → assume new enough
  for (let i = 0; i < min.length; i++) {
    if ((version[i] || 0) !== (min[i] || 0)) return (version[i] || 0) > (min[i] || 0);
  }
  return true;
}

/**
 * Run an sf CLI command with args and return parsed JSON output.
 * Works on both Windows (cmd.exe) and Unix (sh).
 * @param {string[]} args - CLI arguments
 * @returns {any} parsed JSON result
 */
function execSfJson(args) {
  let rawOutput;
  try {
    rawOutput = execFileSync(getSfBin(), args, { encoding: 'utf8', stdio: 'pipe' });
  } catch (err) {
    if (err.stdout) {
      rawOutput = err.stdout;
    } else {
      throw err;
    }
  }
  return JSON.parse(rawOutput);
}

/**
 * Execute a command and return the output
 */
function exec(command, options = {}) {
  try {
    return execSync(command, {
      encoding: 'utf8',
      stdio: options.silent ? 'pipe' : 'inherit',
      ...options
    });
  } catch (error) {
    if (options.ignoreError) {
      // Return the error output if available (for JSON parsing)
      return error.stdout || error.stderr || '{}';
    }
    const safeCmd = command.replace(/Authorization:\s*Bearer\s+[^\s'"\\]+/gi, 'Authorization: Bearer [REDACTED]');
    console.error(`Error executing command: ${safeCmd}`);
    console.error(error.message);
    process.exit(1);
  }
}

/**
 * Get org details including instance URL and access token
 */
function getOrgDetails(orgAlias) {
  const useShowAccessTokenCommand = isSfAtLeast(getSfCliVersion(), ACCESS_TOKEN_VIA_SHOW_SINCE);
  const result = execSfJson(['org', 'display', '--target-org', orgAlias, '--json']);

  if (result.status !== 0) {
    console.error('Error: Failed to get org details');
    process.exit(1);
  }

  let accessToken;
  if (useShowAccessTokenCommand) {
    const tokenResult = execSfJson(['org', 'auth', 'show-access-token', '--target-org', orgAlias, '--no-prompt', '--json']);
    if (!tokenResult.result || !tokenResult.result.accessToken) {
      throw new Error(`Failed to retrieve access token for org "${orgAlias}": ${tokenResult.message || JSON.stringify(tokenResult)}`);
    }
    accessToken = tokenResult.result.accessToken;
  } else {
    if (!result.result || !result.result.accessToken) {
      throw new Error(`Failed to retrieve access token for org "${orgAlias}": ${result.message || JSON.stringify(result)}`);
    }
    accessToken = result.result.accessToken;
  }

  return {
    instanceUrl: result.result.instanceUrl,
    accessToken,
    apiVersion: result.result.apiVersion || '62.0',
    orgId: result.result.id
  };
}

/**
 * Query the org for the TPM Accruals package namespace prefix.
 * Returns the prefix WITH trailing double underscore (e.g. "cgcloud_dev__"),
 * or '' for source-only orgs.
 *
 * Uses the DataCloudExportScheduler Apex class as a probe — its NamespacePrefix
 * is the managed package's prefix regardless of the subscriber org's own
 * namespace. Querying Organization.NamespacePrefix instead would return the
 * subscriber's prefix, which is only ever populated on packaging/scratch orgs
 * and would silently return '' on real cgcloud subscribers.
 */
function getOrgNamespace(orgAlias) {
  try {
    const result = execSfJson(['data', 'query', '--query', "SELECT NamespacePrefix FROM ApexClass WHERE Name = 'DataCloudExportScheduler'", '--target-org', orgAlias, '--json']);
    const records =
      result.status === 0 && result.result && result.result.records
        ? result.result.records
        : [];
    const namespaced = records.find(r => r.NamespacePrefix);
    if (namespaced) {
      return `${namespaced.NamespacePrefix}__`;
    }
  } catch (error) {
    // Fall through to empty
  }
  return '';
}

/**
 * Strip a leading namespace prefix from a name (case-insensitive).
 * Returns a lowercased copy suitable for tolerant comparisons.
 */
function normalizeName(name, namespace) {
  if (!name) return '';
  let normalized = String(name).toLowerCase();
  if (namespace) {
    const nsLower = String(namespace).toLowerCase();
    if (nsLower && normalized.startsWith(nsLower)) {
      normalized = normalized.slice(nsLower.length);
    }
  }
  return normalized;
}

/**
 * Walk a directory recursively returning all file paths (sync).
 */
function walkFiles(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walkFiles(full));
    } else {
      out.push(full);
    }
  }
  return out;
}

/**
 * Build a map of dataSourceBundleDefinition name -> [dataStreamTemplate developer names]
 * by scanning the dataStreamTemplates folder under a Data Kit's force-app tree.
 *
 * This is needed because deploying a DataStreamBundle does not always create a
 * DataKitDeploymentLog row matching the bundle name itself; instead, rows are
 * created for the underlying DataStreamTemplates contained in the bundle.
 *
 * @param {string} dataKitPath - Path to the Data Kit root (containing force-app/)
 * @returns {Map<string, string[]>}
 */
function getBundleStreamMap(dataKitPath) {
  const map = new Map();
  if (!dataKitPath) return map;

  const templatesDir = path.join(
    dataKitPath,
    'force-app',
    'main',
    'default',
    'dataStreamTemplates'
  );

  if (!fs.existsSync(templatesDir)) return map;

  const files = fs
    .readdirSync(templatesDir)
    .filter(f => f.endsWith('.dataStreamTemplate-meta.xml'));

  const bundleRegex = /<dataSourceBundleDefinition>\s*([^<\s]+)\s*<\/dataSourceBundleDefinition>/i;

  for (const file of files) {
    const fullPath = path.join(templatesDir, file);
    let content;
    try {
      content = fs.readFileSync(fullPath, 'utf8');
    } catch (error) {
      continue;
    }

    const match = content.match(bundleRegex);
    if (!match) continue;

    const bundleName = match[1];
    const streamDevName = file.replace(/\.dataStreamTemplate-meta\.xml$/, '');

    if (!map.has(bundleName)) {
      map.set(bundleName, []);
    }
    map.get(bundleName).push(streamDevName);
  }

  return map;
}

/**
 * Determine if any record in the deployment log matches one of the given spec names.
 *
 * Matching is namespace-tolerant (prefix is stripped before comparison) and
 * uses strict equality by default. For DataStreamBundle specs we additionally
 * allow `endsWith` so a bundle is recognised as deployed when any of its child
 * stream developer names appears as the suffix of a log entry — which is how
 * DataKitDeploymentLog records bundle children under managed-package prefixes.
 *
 * @param {Array<{ComponentName?: string}>} deploymentLog
 * @param {{type?: string, names: string[]}} spec
 * @param {string} namespace
 */
function findMatchingRecords(deploymentLog, spec, namespace) {
  const names = (spec && spec.names) || [];
  if (names.length === 0) return [];
  const normalizedNames = names.map(n => normalizeName(n, namespace)).filter(n => n.length > 0);
  if (normalizedNames.length === 0) return [];
  // DataStreamBundle: deployed stream names carry namespace prefixes and hex
  // suffixes (e.g. cgcloud_Promotion_c_Home, tpm_accrualrule_ingest_71560164).
  // Match when the template dev-name appears as a substring of the log name.
  const allowSubstring = spec && spec.type === 'DataStreamBundle';
  return deploymentLog.filter(record => {
    if (!record.ComponentName) return false;
    const normalizedLog = normalizeName(record.ComponentName, namespace);
    return normalizedNames.some(
      n => n === normalizedLog || (allowSubstring && (normalizedLog.endsWith(n) || normalizedLog.includes(n)))
    );
  });
}

/**
 * Query DataKitDeploymentLog. The componentSpecs param is kept only for
 * informational logging; the query returns recent records that we filter later.
 *
 * @param {string} orgAlias
 * @param {Array<{id: string, names: string[]}>} componentSpecs
 */
function getDeploymentLogForComponents(orgAlias, componentSpecs) {
  console.log(`Checking deployment status for ${componentSpecs.length} components...`);

  const query = `SELECT ComponentName, DeploymentStatus, DeploymentError FROM DataKitDeploymentLog ORDER BY CreatedDate DESC`;

  try {
    const result = execSfJson(['data', 'query', '--query', query, '--target-org', orgAlias, '--json']);

    if (result.status === 0 && result.result && result.result.records) {
      return result.result.records;
    }
    return [];
  } catch (error) {
    console.log('No existing deployment log found (this is okay for first deployment)');
    return [];
  }
}

/**
 * Determine which component specs are already successfully deployed.
 * A spec is considered deployed when at least one matching record in the
 * deployment log has DeploymentStatus = 'Successful'.
 *
 * @param {Array<{ComponentName?: string, DeploymentStatus?: string}>} deploymentLog
 * @param {Array<{id: string, names: string[]}>} componentSpecs
 * @param {string} namespace
 * @returns {Set<string>} set of deployed component ids
 */
function getDeployedComponents(deploymentLog, componentSpecs, namespace = '') {
  const deployed = new Set();

  componentSpecs.forEach(spec => {
    const matches = findMatchingRecords(deploymentLog, spec, namespace);
    const hasSuccess = matches.some(r => r.DeploymentStatus === 'Successful');
    if (hasSuccess) {
      deployed.add(spec.id);
    }
  });

  return deployed;
}

/**
 * Query the Salesforce server clock via Organization.SystemModstamp.
 *
 * Returns the MAX(CreatedDate) of existing DataKitDeploymentLog rows as a
 * server-side baseline timestamp. Rows created after this point belong to the
 * current deploy. Using MAX(CreatedDate) — a value already on the server —
 * avoids local clock-skew entirely.
 *
 * Returns null if no rows exist yet (caller should omit the WHERE clause).
 *
 * @param {string} orgAlias
 * @returns {string|null} ISO-8601 timestamp or null
 */
function getMaxCreatedDate(orgAlias) {
  const result = execSfJson(['data', 'query', '--query', 'SELECT MAX(CreatedDate) maxDate FROM DataKitDeploymentLog', '--target-org', orgAlias, '--json']);
  if (result.status === 0 && result.result && result.result.records && result.result.records.length > 0) {
    return result.result.records[0].maxDate ?? null;
  }
  return null;
}

/**
 * Wait for data kit deployment to complete.
 *
 * Uses a server-side timestamp boundary (WHERE CreatedDate > deploymentStartTime)
 * rather than an opaque Id comparison to isolate log rows created by this deploy.
 * The timestamp is obtained from the Salesforce server via getMaxCreatedDate() just
 * before the deploy is triggered, making the filter immune to local clock-skew.
 *
 * @param {string} orgAlias
 * @param {Array<{id: string, names: string[]}>} componentSpecs
 * @param {string|null} deploymentStartTime - MAX(CreatedDate) from DataKitDeploymentLog captured before deploy; null = no filter (no prior rows)
 * @param {string} namespace - Optional org namespace prefix (e.g. "cgcloud_dev__")
 */
async function waitForDeploymentCompletion(orgAlias, componentSpecs, deploymentStartTime, namespace = '') {
  console.log(`\nWaiting for deployment to complete...`);
  console.log(`Tracking ${componentSpecs.length} components`);

  const maxWaitTime = 30 * 60 * 1000; // 30 minutes
  const pollInterval = 60_000; // 60 seconds
  const startTime = Date.now();

  const completedComponents = new Set();
  const failedComponents = new Map();

  while (Date.now() - startTime < maxWaitTime) {
    const whereClause = deploymentStartTime ? `WHERE CreatedDate > ${deploymentStartTime}` : '';
    const query = `SELECT ComponentName, DeploymentStatus, DeploymentError FROM DataKitDeploymentLog ${whereClause} ORDER BY CreatedDate DESC`;

    let deploymentLog = [];
    try {
      const result = execSfJson(['data', 'query', '--query', query, '--target-org', orgAlias, '--json']);
      if (result.status === 0 && result.result && result.result.records) {
        deploymentLog = result.result.records;
      }
    } catch (error) {
      console.warn(`Polling query failed (will retry): ${error.message}`);
    }

    componentSpecs.forEach(spec => {
      if (completedComponents.has(spec.id) || failedComponents.has(spec.id)) {
        return;
      }
      const matches = findMatchingRecords(deploymentLog, spec, namespace);
      if (matches.length === 0) return;

      const failure = matches.find(r => r.DeploymentStatus === 'Failure');
      const hasSuccess = matches.some(r => r.DeploymentStatus === 'Successful');

      if (failure) {
        failedComponents.set(spec.id, failure.DeploymentError || 'Unknown error');
      } else if (hasSuccess) {
        completedComponents.add(spec.id);
      }
    });

    const inProgressCount = componentSpecs.length - completedComponents.size - failedComponents.size;

    console.log(`  Status: ${completedComponents.size} succeeded, ${failedComponents.size} failed, ${inProgressCount} in progress`);

    if (failedComponents.size > 0) {
      console.error('\nERROR: Deployment failed with errors:');
      failedComponents.forEach((error, component) => {
        console.error(`  - ${component}: ${error}`);
      });
      process.exit(1);
    }

    if (completedComponents.size === componentSpecs.length) {
      console.log(`[OK] Deployment completed successfully!\n`);
      return true;
    }

    await new Promise(resolve => setTimeout(resolve, pollInterval));
  }

  console.error(`\nERROR: Deployment timed out after ${maxWaitTime / 1000 / 60} minutes`);
  console.error(`Completed: ${completedComponents.size}/${componentSpecs.length}`);
  const pending = componentSpecs.filter(s => !completedComponents.has(s.id)).map(s => s.id);
  if (pending.length > 0) {
    console.error(`Pending: ${pending.join(', ')}`);
  }
  process.exit(1);
}

/**
 * Run `sf project deploy start` with --json, validate via status fields.
 * SF CLI exits 1 even on success when warnings are present.
 */
function execDeployJson(deployArgs, options) {
  options = options || {};
  const allArgs = deployArgs.concat(['--json']);
  let rawOutput;
  try {
    rawOutput = execFileSync(getSfBin(), allArgs, { encoding: 'utf8', stdio: 'pipe', cwd: options.cwd });
  } catch (err) {
    if (err.stdout) {
      rawOutput = err.stdout;
    } else {
      throw err;
    }
  }
  const result = JSON.parse(rawOutput);
  if (result.status !== 0) {
    const failures = (((result.result || {}).details) || {}).componentFailures || [];
    const msg = failures.length
      ? failures.map(f => f.fullName + ': ' + f.problem).join('\n')
      : (result.message || 'Deploy failed');
    throw new Error(msg);
  }
  if (result.result && result.result.status === 'Failed') {
    const failures2 = ((result.result.details || {}).componentFailures) || [];
    const msg2 = failures2.length
      ? failures2.map(f => f.fullName + ': ' + f.problem).join('\n')
      : 'Deploy failed';
    throw new Error(msg2);
  }
  return result;
}
module.exports = {
  exec,
  execDeployJson,
  getOrgDetails,
  getOrgNamespace,
  getMaxCreatedDate,
  normalizeName,
  walkFiles,
  getBundleStreamMap,
  getDeploymentLogForComponents,
  getDeployedComponents,
  waitForDeploymentCompletion,
  getSfBin,
  execSfJson
};
