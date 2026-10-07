const { exec, execDeployJson, getSfBin } = require('./utils');

/**
 * Step 3: Deploy TPM Accruals Data Kit metadata to the org
 * @param {string} orgAlias - The Salesforce org alias
 * @param {string} dataKitPath - Path to the data kit
 * @param {boolean} dryRun - If true, skip actual deployment
 */
async function deployMetadata(orgAlias, dataKitPath, dryRun = false) {
  console.log('\n=== Step 3: Deploying TPM Accruals Data Kit ===');
  console.log(`Source: ${dataKitPath}`);
  console.log(`Target org: ${orgAlias}`);

  if (dryRun) {
    console.log('[DRY RUN] Skipping deployment - files prepared at:');
    console.log(`  ${dataKitPath}/force-app`);
    console.log('[OK] Step 3 completed (dry run)\n');
    return;
  }

  // Deploy using sf project deploy start from the data kit root so the
  // sfdx-project.json sourceApiVersion is respected.
  console.log('Deploying metadata...');
  execDeployJson(['project', 'deploy', 'start', '--source-dir', 'force-app', '--target-org', orgAlias], { cwd: dataKitPath });

  console.log('[OK] TPM Accruals Data Kit deployed successfully\n');
}

module.exports = deployMetadata;
