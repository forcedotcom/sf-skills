// Triggers SCHEDULE_RTR_EXPORT for the tpmbusinessperiod object, across every
// Sales Org ("salesorg":"*" in the JSON body — a business-level "export for
// every sales org" instruction, not a platform-level wildcard).
//
// This must stay anonymous Apex, not a direct REST call to
// ScheduleRTRExportService (/measures/export/schedule): that REST resource
// reads a single "salesorg" field out of its JSON body and uses that same
// value for BOTH tenant/substrate routing (SalesOrgSubstrate mode —
// SalesOrganizationServiceWOSharing.getTenantSubstrateEnum(salesorg)) and the
// forwarded payload. "*" doesn't resolve to a real Sales_Organization__c, so
// it can't be used for routing. This template decouples the two: %SALES_ORG%
// (a real Hyperforce-substrate Sales Org Name) drives routing via the
// OffPlatformCallout constructor; the JSON body's "salesorg" stays "*".
//
// Placeholders (each substituted exactly once, into a String variable
// declaration below — render-apex.js escapes it there; see soql-escape.js):
//   %NS_APEX%   -> Apex class-reference prefix, e.g. "cgcloud_dev." (empty for unnamespaced)
//   %SALES_ORG% -> Name of a real Hyperforce-substrate Sales_Organization__c, resolved by the caller (step 1's `sf data query`)
String salesOrg = '%SALES_ORG%';
Map<String, Object> data = new Map<String, Object>();
data.put('salesorg', '*');
data.put('object', 'tpmbusinessperiod');
%NS_APEX%OffPlatformCallout request = new %NS_APEX%OffPlatformCallout('SCHEDULE_RTR_EXPORT', salesOrg);
%NS_APEX%OffPlatformCalloutResponse response = request.execute(
  %NS_APEX%TransactionHandler.getTransactionIdentifier(), null, JSON.serialize(data, true)
);
System.debug(LoggingLevel.INFO, 'SCHEDULE_RTR_EXPORT_RESPONSE=' + response);
