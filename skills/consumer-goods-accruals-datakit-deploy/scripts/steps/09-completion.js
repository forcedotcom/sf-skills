/**
 * Step 9: Completion and Scheduling Instructions
 * Informs the user about successful deployment and next steps for scheduling accrual calculations
 * @param {boolean} dryRun - If true, show dry run completion message
 */
async function completion(dryRun = false) {
  console.log('\n=== Step 9: Setup Complete ===');

  if (dryRun) {
    console.log('\n+============================================================================+');
    console.log('|                         DRY RUN COMPLETED                                  |');
    console.log('+============================================================================+');
    console.log('\nThe following directories contain the prepared files for inspection:');
    console.log('  • CGCloudAddons/        - Downloaded and modified static resource');
    console.log('  • temp-accruals-reports/  - Accruals Reports with placeholders replaced');
    console.log('  • temp-ui/                - UI components with placeholders replaced');
    console.log('\nTo execute the actual deployment, run the same command without --dry-run');
    console.log('\n');
    return;
  }

  console.log('\n[OK] The Accruals solution has been successfully deployed to your Salesforce org!');

  console.log('\n=== Next Steps: Scheduling Accrual Calculations ===');
  console.log('\nTo calculate accruals, you need to schedule two processes in the following order:');

  console.log('\n1. Schedule Data Cloud Connector Export');
  console.log('   - Use the DataCloudExportScheduler class');
  console.log('   - Schedule exports for the following tables:');
  console.log('     • promotionmeasures');
  console.log('     • paymenttacticmeasures');
  console.log('     • dailymeasurereal');
  console.log('   - Documentation: https://developer.salesforce.com/docs/atlas.en-us.retail_api.meta/retail_api/cg_tpm_apex_datacloudexportscheduler.htm');
  console.log('   - This class can be executed ad-hoc or scheduled to run at a specific interval');

  console.log('\n2. Schedule Accrual Calculation Chain');
  console.log('   - Use the ScheduleTPMAccrualProcessChain class');
  console.log('   - Documentation: https://developer.salesforce.com/docs/atlas.en-us.retail_api.meta/retail_api/global_tpm_accrual_process.htm');
  console.log('   - This class can be executed ad-hoc or scheduled to run at a specific interval');

  console.log('\n');
}

module.exports = completion;
