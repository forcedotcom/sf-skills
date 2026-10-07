#!/usr/bin/env node

const path = require('path');
const { getOrgDetails, getOrgNamespace } = require('./steps/utils');

// Import all step modules
const checkPrerequisites = require('./steps/00-check-prerequisites');
const downloadStaticResource = require('./steps/01-download-static-resource');
const replaceOrgId = require('./steps/02-replace-org-id');
const deployMetadata = require('./steps/03-deploy-metadata');
const deployEngine = require('./steps/04-deploy-engine');
const deployTPMAccruals = require('./steps/05-deploy-tpm-accruals');
const createDataSpace = require('./steps/06-create-dataspace');
const deployAccrualsReports = require('./steps/07-deploy-accruals-reports');
const deployUI = require('./steps/08-deploy-ui');
const completion = require('./steps/09-completion');

/**
 * Parse command line arguments
 * Supports both flags (--flag=value, --flag value, -f value) and positional arguments
 * @returns {{ orgAlias: string|null, skipDataSpace: boolean, salesOrg: string, dryRun: boolean, namespace: string|null }}
 */
function parseArgs() {
  const args = process.argv.slice(2);
  const result = {
    orgAlias: null,
    skipDataSpace: false,
    salesOrg: null,
    dryRun: false,
    namespace: null,
  };

  for (let i = 0; i < args.length; i++) {
    const arg = args[i];

    // Handle --flag=value format
    if (arg.includes('=')) {
      const [key, value] = arg.split('=');
      switch (key) {
        case '--org':
        case '-o':
          result.orgAlias = value;
          break;
        case '--sales-org':
        case '-s':
          result.salesOrg = value;
          break;
        case '--skip-dataspace':
          result.skipDataSpace = value === 'true';
          break;
        case '--dry-run':
          result.dryRun = value === 'true';
          break;
        case '--namespace':
        case '-n':
          result.namespace = value;
          break;
      }
      continue;
    }

    // Handle --flag value format and boolean flags
    switch (arg) {
      case '--org':
      case '-o':
        result.orgAlias = args[++i];
        break;
      case '--sales-org':
      case '-s':
        result.salesOrg = args[++i];
        break;
      case '--skip-dataspace':
        result.skipDataSpace = true;
        break;
      case '--dry-run':
      case '-d':
        result.dryRun = true;
        break;
      case '--namespace':
      case '-n':
        result.namespace = args[++i];
        break;
      case '--help':
      case '-h':
        printHelp();
        process.exit(0);
        break;
      default:
        // Positional argument (org alias for backward compatibility)
        if (!arg.startsWith('-') && !result.orgAlias) {
          result.orgAlias = arg;
        }
        break;
    }
  }

  return result;
}

/**
 * Print help message
 */
function printHelp() {
  console.log(`
Usage: node setup.js [options] [org-alias]

Options:
  -o, --org <alias>       Salesforce org alias (can also use SF_ORG_ALIAS env var)
  -s, --sales-org <org>   Sales org identifier (required; can also use SALES_ORG env var)
  -n, --namespace <ns>    Org namespace prefix WITHOUT trailing "__" (e.g. "cgcloud_dev").
                          If omitted, the namespace is auto-detected from the org.
                          Use empty string ("") to force unmanaged behavior.
      --skip-dataspace    Skip Data Space creation (can also use SKIP_DATASPACE=true env var)
  -d, --dry-run           Show what would be done without making any changes
  -h, --help              Show this help message

Examples:
  node setup.js --org my-org --sales-org 0001
  node setup.js --org my-org --sales-org 0002
  node setup.js -o my-org -s 0002 --skip-dataspace
  node setup.js --dry-run --org my-org --sales-org 0001
  node setup.js --org my-org --namespace cgcloud_dev

Environment variables:
  SF_ORG_ALIAS      Salesforce org alias
  SALES_ORG         Sales org identifier (required)
  SKIP_DATASPACE    Set to "true" to skip Data Space creation
  DRY_RUN           Set to "true" for dry run mode
  ORG_NAMESPACE     Org namespace prefix WITHOUT trailing "__" (overrides auto-detection)
`);
}

/**
 * Get configuration from CLI args and environment variables
 * CLI args take precedence over environment variables
 * @returns {{ orgAlias: string, skipDataSpace: boolean, salesOrg: string, dryRun: boolean, namespaceOverride: string|null }}
 */
function getConfig() {
  const cliArgs = parseArgs();

  // CLI args take precedence over environment variables
  const orgAlias = cliArgs.orgAlias || process.env.SF_ORG_ALIAS;
  const skipDataSpace = cliArgs.skipDataSpace || process.env.SKIP_DATASPACE === 'true';
  const salesOrg = cliArgs.salesOrg || process.env.SALES_ORG || null;
  const dryRun = cliArgs.dryRun || process.env.DRY_RUN === 'true';

  // namespaceOverride is null when neither CLI nor env was provided (=> auto-detect),
  // or a string (possibly empty) when the user explicitly specified one.
  let namespaceOverride = null;
  if (cliArgs.namespace !== null && cliArgs.namespace !== undefined) {
    namespaceOverride = cliArgs.namespace;
  } else if (process.env.ORG_NAMESPACE !== undefined) {
    namespaceOverride = process.env.ORG_NAMESPACE;
  }

  if (!orgAlias) {
    console.error('Error: Org alias not provided.');
    console.error('Usage: node setup.js <org-alias>');
    console.error('   OR: node setup.js --org <org-alias>');
    console.error('   OR: SF_ORG_ALIAS=<org-alias> node setup.js');
    console.error('\nRun "node setup.js --help" for more options.');
    process.exit(1);
  }

  if (!salesOrg) {
    console.error('Error: Sales org not provided.');
    console.error('Usage: node setup.js --sales-org <value>');
    console.error('   OR: SALES_ORG=<value> node setup.js');
    console.error('\nRun "node setup.js --help" for available options.');
    process.exit(1);
  }

  return { orgAlias, skipDataSpace, salesOrg, dryRun, namespaceOverride };
}

/**
 * Validate salesOrg and namespaceOverride inputs.
 * Exits the process with an error message if validation fails.
 * @param {string} salesOrg - Must be exactly 4 alphanumeric characters.
 * @param {string|null} namespaceOverride - When non-null, must be 1-15 alphanumeric characters.
 */
function validateInputs(salesOrg, namespaceOverride) {
  if (!/^[A-Za-z0-9]{4}$/.test(salesOrg)) {
    console.error('Error: Invalid sales org.');
    process.exit(1);
  }

  if (namespaceOverride !== null && namespaceOverride !== '' && !/^[A-Za-z0-9]{1,15}$/.test(namespaceOverride)) {
    console.error('Error: Invalid namespace.');
    process.exit(1);
  }
}

/**
 * Format a namespace value into the prefix form used in metadata
 * (i.e. always ends with "__", or is the empty string).
 */
function formatNamespace(value) {
  if (!value) return '';
  return value.endsWith('__') ? value : `${value}__`;
}

/**
 * Derive Data Space name and prefix from sales org
 * @param {string} salesOrg - The sales org value
 * @returns {{ dataSpaceName: string, dataSpacePrefix: string }}
 */
function getDataSpaceConfig(salesOrg) {
  const lastChar = salesOrg.slice(-1);
  return {
    dataSpaceName: `DataSpace_${salesOrg}`,
    dataSpacePrefix: `DS${lastChar}_`,
  };
}

/**
 * Main setup function
 */
async function main() {
  console.log('=== Salesforce Org Setup ===\n');

  const config = getConfig();
  const { orgAlias, skipDataSpace, salesOrg, dryRun, namespaceOverride } = config;

  // Validate inputs before any org access or step execution
  validateInputs(salesOrg, namespaceOverride);

  const { dataSpaceName, dataSpacePrefix } = getDataSpaceConfig(salesOrg);

  if (dryRun) {
    console.log('+============================================================================+');
    console.log('|                              DRY RUN MODE                                  |');
    console.log('|  All read-only steps will execute. Deployments to org will be skipped.    |');
    console.log('|  Temp directories will be preserved for inspection.                       |');
    console.log('+============================================================================+\n');
  }

  console.log(`Target org: ${orgAlias}`);

  // Verify org is accessible and get org details
  console.log('Verifying org connection...');
  let orgId;
  try {
    const orgDetails = getOrgDetails(orgAlias);
    orgId = orgDetails.orgId;
    console.log(`[OK] Org connection verified (Org ID: ${orgId})\n`);
  } catch (error) {
    console.error(`Error: Cannot connect to org "${orgAlias}"`);
    console.error('Make sure you are logged in via: sf org login web');
    process.exit(1);
  }

  // Resolve org namespace: CLI/env override wins; otherwise query the org.
  // This is needed because component names in DataKitDeploymentLog and field
  // references in the Accruals Reports payload can carry a namespace prefix
  // depending on the org (e.g. "cgcloud_dev__" in this repo's dev org).
  let namespace;
  if (namespaceOverride !== null && namespaceOverride !== undefined) {
    namespace = formatNamespace(namespaceOverride);
    console.log(`Using namespace override: "${namespace || '(none)'}"`);
  } else {
    console.log('Detecting org namespace...');
    namespace = getOrgNamespace(orgAlias);
    console.log(`Detected namespace: "${namespace || '(none)'}"`);
  }

  const setupDir = __dirname;
  const dataKitPath = path.join(setupDir, 'CGCloudAddons', 'TPM', 'Accruals', 'TPM Accruals Data Kit');
  const scriptsDir = path.join(setupDir, 'CGCloudAddons', 'TPM', 'Accruals', 'Accruals Data Kit Deployment Scripts');

  console.log(`Sales Org: ${salesOrg}`);
  if (!skipDataSpace) {
    console.log(`Data Space Name: ${dataSpaceName}`);
    console.log(`Data Space Prefix: ${dataSpacePrefix}\n`);
  }

  // Step 0: Check Prerequisites (skip in dry run)
  if (!dryRun) {
    await checkPrerequisites();
  } else {
    console.log('\n=== Step 0: Check Prerequisites (skipped in dry run) ===\n');
  }

  // Run all steps in order
  await downloadStaticResource(orgAlias, setupDir);
  await replaceOrgId(orgId, dataKitPath);
  await deployMetadata(orgAlias, dataKitPath, dryRun);
  await deployEngine(orgAlias, scriptsDir, orgId, namespace, dryRun);
  await deployTPMAccruals(orgAlias, scriptsDir, dataKitPath, orgId, namespace, dryRun);

  // Step 6: Create Data Space (only if Data Spaces are available)
  if (!skipDataSpace) {
    await createDataSpace(orgAlias, salesOrg, dataSpaceName, dataSpacePrefix, dryRun);
  } else {
    console.log('\n=== Step 6: Skipping Data Space creation (--skip-dataspace) ===\n');
  }

  // Step 7: Deploy Accruals Reports with Data Space replacements
  await deployAccrualsReports(orgAlias, setupDir, skipDataSpace, dataSpaceName, dataSpacePrefix, namespace, dryRun);

  // Step 8: Deploy UI components (TPMAccrualTacticSummary)
  await deployUI(orgAlias, setupDir, skipDataSpace, dataSpaceName, dataSpacePrefix, salesOrg, namespace, dryRun);

  // Step 9: Completion and next steps
  await completion(dryRun);

  console.log('=== Setup completed successfully ===');
}

// Run the script
main().catch(error => {
  console.error('Unexpected error:', error);
  process.exit(1);
});
