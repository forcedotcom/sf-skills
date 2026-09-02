// Idempotent upsert of the Data_Cloud_Enabled System_Setting__c row.
// Query-then-upsert instead of `sf data upsert record` — that CLI subcommand
// only supports bulk/resume CSV, not a single record. Placeholder:
//   %NS% -> namespace field prefix, e.g. "cgcloud_dev__" (empty for source org)
List<%NS%System_Setting__c> existing = [
  SELECT Id
  FROM %NS%System_Setting__c
  WHERE Name = 'Data_Cloud_Enabled'
  WITH USER_MODE
  LIMIT 1
];
%NS%System_Setting__c row;
if (existing.isEmpty()) {
  row = new %NS%System_Setting__c();
  row.Name = 'Data_Cloud_Enabled';
} else {
  row = existing[0];
}
row.%NS%Value__c = 'true';
upsert as user row;
System.debug(LoggingLevel.INFO, 'RTR_DATACLOUD_SETTING_ID=' + row.Id);
