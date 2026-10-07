const readline = require('readline');

/**
 * Step 0: Check Prerequisites
 * Presents prerequisites to the user and waits for confirmation
 */
async function checkPrerequisites() {
  console.log('\n=== Step 0: Prerequisites ===');

  console.log('\nBefore proceeding with the setup, please ensure the following prerequisites are met:');
  console.log('\n1. Enable Data Cloud and Analytics Studio');
  console.log('   - Navigate to Setup > Data Cloud Setup');
  console.log('   - Ensure Data Cloud and Analytics Studio are enabled');
  console.log('\n2. Ensure there is a user assigned in the Processing Services Pairing app to the Accrual Ingestion Process');
  console.log('   - The user must have the Data Cloud Architect permission set');
  console.log('   - Alternatively, a System Admin or user with Data Cloud Architect can be assigned to all processes');
  console.log('\n3. Ensure the connected app or external client app for TPM Offcore has the oauth scope "cdp_ingest_api"');
  console.log('   - Navigate to Setup > App Manager');
  console.log('   - Edit your connected app and verify the oauth scope includes "cdp_ingest_api"');
  console.log('   - Note: Depending on your org setup, this permission may already be included');

  console.log('\n');

  // Wait for user confirmation
  await waitForUserConfirmation();

  console.log('[OK] Prerequisites confirmed. Proceeding to next step...\n');
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

    rl.question('Press Enter when you have confirmed all prerequisites are met...', () => {
      rl.close();
      resolve();
    });
  });
}

module.exports = checkPrerequisites;
