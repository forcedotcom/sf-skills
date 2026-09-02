// Idempotent upsert of an RTR_Report_Configuration__c row by
// (Usage__c, Internal_Name__c, Sales_Organization__c). Usage is restricted to
// the two Data-Cloud-targeted values this skill supports:
// 'datacloudpromotionmeasuresmeta' or 'datacloudaccountplanmeasuresmeta'
// (distinct from the CSV-export 'integrationmeta'/'reportmeta' pair used by
// the sibling setup-rtr-export skill). JSON__c is assembled off-Salesforce as
// {"measurecodes":[...],"datefrom":"YYYY-MM-DD","object":"promotionmeasures"
// |"accountplanmeasures"} and passed in as %JSON_LITERAL%. Each placeholder
// below is substituted exactly once, into a String variable declaration —
// the only place a raw value is embedded as an Apex literal, and
// render-apex.js escapes it there (see soql-escape.js). The SOQL WHERE
// clause and every field assignment then use the resulting Apex variables as
// SOQL bind variables (:usage, :internalName, ...) or plain assignments —
// never a second literal substitution of the same placeholder. Pass raw,
// unescaped values for every placeholder below.
//
//   %NS%             -> namespace field prefix e.g. "cgcloud_dev__"
//   %USAGE%          -> 'datacloudpromotionmeasuresmeta' or
//                       'datacloudaccountplanmeasuresmeta'
//   %INTERNAL_NAME%  -> free-text admin-supplied name (e.g. "O'Brien Foods")
//   %SALES_ORG_ID%   -> 15/18-char Sales_Organization__c Id
//   %KPI_SET_ID%     -> 15/18-char KPI_Set__c Id
//   %JSON_LITERAL%   -> the full JSON body, raw (not pre-escaped)
String usage = '%USAGE%';
String internalName = '%INTERNAL_NAME%';
String salesOrgId = '%SALES_ORG_ID%';
String kpiSetId = '%KPI_SET_ID%';
String jsonLiteral = '%JSON_LITERAL%';

List<%NS%RTR_Report_Configuration__c> existing = [
  SELECT Id
  FROM %NS%RTR_Report_Configuration__c
  WHERE %NS%Usage__c = :usage
    AND %NS%Internal_Name__c = :internalName
    AND %NS%Sales_Organization__c = :salesOrgId
  WITH USER_MODE
  LIMIT 1
];
%NS%RTR_Report_Configuration__c row;
if (existing.isEmpty()) {
  row = new %NS%RTR_Report_Configuration__c();
  row.%NS%Usage__c = usage;
  row.%NS%Internal_Name__c = internalName;
  row.%NS%Sales_Organization__c = salesOrgId;
} else {
  row = existing[0];
}
row.%NS%Reporting_KPI_Set__c = kpiSetId;
row.%NS%JSON__c = jsonLiteral;
upsert as user row;
System.debug(LoggingLevel.INFO, 'RTR_DATACLOUD_CONFIG_ID=' + row.Id);
