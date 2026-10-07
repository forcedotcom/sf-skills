const readline = require('readline');

/**
 * Step 6: Manual Data Space creation with DLO configuration
 * @param {string} orgAlias - The Salesforce org alias
 * @param {string} salesOrg - The sales org value (e.g., "0001")
 * @param {string} dataSpaceName - The data space name (e.g., "DataSpace_0001")
 * @param {string} dataSpacePrefix - The data space prefix (e.g., "DS1")
 * @param {boolean} dryRun - If true, skip user prompt
 */
async function createDataSpace(orgAlias, salesOrg, dataSpaceName, dataSpacePrefix, dryRun = false) {
  console.log('\n=== Step 6: Create Data Space (Manual Step) ===');

  console.log('\nData Space configuration:');
  console.log(`   - Name: ${dataSpaceName}`);
  console.log(`   - Prefix: ${dataSpacePrefix}`);
  console.log(`   - DLO: accrualoutput_decorated__dll`);
  console.log(`   - Filter: SalesOrg equals "${salesOrg}"`);

  if (dryRun) {
    console.log('\n[DRY RUN] Skipping manual step prompt');
    console.log('[OK] Step 6 completed (dry run)\n');
    return;
  }

  console.log('\nPlease complete the following manual steps in your Salesforce org:');
  console.log('\n1. Navigate to the Data Spaces tab in your org');
  console.log('2. Create a new Data Space with the details shown above');
  console.log('3. Go into the newly created Data Space');
  console.log('4. Add the DLO: accrualoutput_decorated__dll');
  console.log('5. Apply the filter shown above');

  console.log('\n');

  // Wait for user confirmation
  await waitForUserConfirmation();

  console.log('[OK] Data Space creation confirmed. Proceeding to next step...\n');
}

/**
 * Wait for user to press Enter
 */
function waitForUserConfirmation() {
  return new Promise((resolve) => {
    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    rl.question('Press Enter when you have completed these steps...', () => {
      rl.close();
      resolve();
    });
  });
}

module.exports = createDataSpace;
