/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * BULK INSERT 200+ RECORDS
 * For testing trigger and flow bulkification
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * PURPOSE:
 * Test that triggers and flows handle bulk operations correctly.
 * Salesforce processes up to 200 records per transaction in normal contexts.
 *
 * WHY 251 RECORDS:
 * • 200 is the batch size for triggers (this tests the boundary)
 * • 250+ ensures multiple batches in batch Apex contexts
 * • 251 specifically crosses the 200 boundary
 *
 * WHAT TO VERIFY:
 * • No governor limit exceptions (SOQL, DML, CPU)
 * • All records processed correctly
 * • No N+1 query patterns
 * • Trigger/Flow logic executes correctly for all records
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

Integer recordCount = 251;  // Intentionally over 200 to test batch boundaries
String namePrefix = 'BulkTest';
Boolean enableDebugLimits = true;

// ═══════════════════════════════════════════════════════════════════════════════
// TRACKING COLLECTIONS (for cleanup)
// ═══════════════════════════════════════════════════════════════════════════════

Set<Id> createdAccountIds = new Set<Id>();
Set<Id> createdContactIds = new Set<Id>();
Set<Id> createdOpportunityIds = new Set<Id>();

// ═══════════════════════════════════════════════════════════════════════════════
// CAPTURE INITIAL LIMITS
// ═══════════════════════════════════════════════════════════════════════════════

Integer startQueries = Limits.getQueries();
Integer startDml = Limits.getDmlStatements();
Integer startCpu = Limits.getCpuTime();
Long startHeap = Limits.getHeapSize();

System.debug('═══════════════════════════════════════════════════════════════');
System.debug('Starting Bulk Insert Test: ' + recordCount + ' records');
System.debug('═══════════════════════════════════════════════════════════════');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 1: CREATE ACCOUNTS
// ═══════════════════════════════════════════════════════════════════════════════

List<Account> accounts = new List<Account>();
List<String> industries = new List<String>{
    'Technology', 'Healthcare', 'Finance', 'Manufacturing',
    'Retail', 'Education', 'Energy', 'Media'
};

for (Integer i = 0; i < recordCount; i++) {
    accounts.add(new Account(
        Name = namePrefix + '_Account_' + String.valueOf(i).leftPad(5, '0'),
        Industry = industries[Math.mod(i, industries.size())],
        Type = Math.mod(i, 3) == 0 ? 'Customer' : 'Prospect',
        AnnualRevenue = 100000 + (i * 10000),
        NumberOfEmployees = 50 + (i * 5),
        BillingCity = 'San Francisco',
        BillingState = 'CA',
        BillingCountry = 'USA',
        Description = 'Bulk test account ' + i
    ));
}

try {
    insert accounts;
    for (Account acc : accounts) {
        createdAccountIds.add(acc.Id);
    }
    System.debug('✓ Created ' + accounts.size() + ' Accounts');
} catch (DmlException e) {
    System.debug('✗ Account creation failed: ' + e.getMessage());
    throw e;
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 2: CREATE CONTACTS (2 per Account = 502 Contacts)
// ═══════════════════════════════════════════════════════════════════════════════

List<Contact> contacts = new List<Contact>();
Integer contactIndex = 0;

for (Account acc : accounts) {
    for (Integer i = 0; i < 2; i++) {
        String idx = String.valueOf(contactIndex++).leftPad(5, '0');
        contacts.add(new Contact(
            FirstName = namePrefix,
            LastName = 'Contact_' + idx,
            AccountId = acc.Id,
            Email = namePrefix.toLowerCase() + '.contact' + idx + '@bulktest.example.com',
            Phone = '(555) 100-' + String.valueOf(1000 + contactIndex),
            Title = Math.mod(contactIndex, 2) == 0 ? 'Manager' : 'Director'
        ));
    }
}

try {
    insert contacts;
    for (Contact con : contacts) {
        createdContactIds.add(con.Id);
    }
    System.debug('✓ Created ' + contacts.size() + ' Contacts');
} catch (DmlException e) {
    System.debug('✗ Contact creation failed: ' + e.getMessage());
    throw e;
}

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 3: CREATE OPPORTUNITIES (1 per Account = 251 Opportunities)
// ═══════════════════════════════════════════════════════════════════════════════

List<Opportunity> opportunities = new List<Opportunity>();
List<String> stages = new List<String>{
    'Prospecting', 'Qualification', 'Needs Analysis', 'Proposal/Price Quote'
};

Integer oppIndex = 0;
for (Account acc : accounts) {
    String idx = String.valueOf(oppIndex++).leftPad(5, '0');
    opportunities.add(new Opportunity(
        Name = namePrefix + '_Opportunity_' + idx,
        AccountId = acc.Id,
        StageName = stages[Math.mod(oppIndex, stages.size())],
        CloseDate = Date.today().addDays(30 + oppIndex),
        Amount = 10000 + (oppIndex * 1000),
        Type = 'New Customer',
        LeadSource = 'Web'
    ));
}

try {
    insert opportunities;
    for (Opportunity opp : opportunities) {
        createdOpportunityIds.add(opp.Id);
    }
    System.debug('✓ Created ' + opportunities.size() + ' Opportunities');
} catch (DmlException e) {
    System.debug('✗ Opportunity creation failed: ' + e.getMessage());
    throw e;
}

// ═══════════════════════════════════════════════════════════════════════════════
// CAPTURE FINAL LIMITS
// ═══════════════════════════════════════════════════════════════════════════════

Integer endQueries = Limits.getQueries();
Integer endDml = Limits.getDmlStatements();
Integer endCpu = Limits.getCpuTime();
Long endHeap = Limits.getHeapSize();

// ═══════════════════════════════════════════════════════════════════════════════
// REPORT RESULTS
// ═══════════════════════════════════════════════════════════════════════════════

System.debug('═══════════════════════════════════════════════════════════════');
System.debug('BULK INSERT TEST COMPLETE');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('');
System.debug('📊 RECORDS CREATED:');
System.debug('   Accounts:      ' + createdAccountIds.size());
System.debug('   Contacts:      ' + createdContactIds.size());
System.debug('   Opportunities: ' + createdOpportunityIds.size());
System.debug('   TOTAL:         ' + (createdAccountIds.size() + createdContactIds.size() + createdOpportunityIds.size()));
System.debug('');
System.debug('📈 GOVERNOR LIMITS USED:');
System.debug('   SOQL Queries:     ' + (endQueries - startQueries) + ' / 100');
System.debug('   DML Statements:   ' + (endDml - startDml) + ' / 150');
System.debug('   CPU Time (ms):    ' + (endCpu - startCpu) + ' / 10000');
System.debug('   Heap Size (bytes): ' + endHeap + ' / 6000000');
System.debug('');
System.debug('═══════════════════════════════════════════════════════════════');

// ═══════════════════════════════════════════════════════════════════════════════
// CLEANUP SCRIPT (Run separately after testing)
// ═══════════════════════════════════════════════════════════════════════════════
/*
CLEANUP - Copy and run this separately after testing:

// Delete in correct order (children first)
DELETE [SELECT Id FROM Opportunity WHERE Name LIKE 'BulkTest%'];
DELETE [SELECT Id FROM Contact WHERE LastName LIKE 'Contact_%' AND Email LIKE '%bulktest.example.com'];
DELETE [SELECT Id FROM Account WHERE Name LIKE 'BulkTest%'];

System.debug('Cleanup complete');
*/

// ═══════════════════════════════════════════════════════════════════════════════
// OUTPUT RECORD IDS FOR MANUAL CLEANUP
// ═══════════════════════════════════════════════════════════════════════════════

System.debug('');
System.debug('Record IDs for cleanup (first 10 of each):');
System.debug('Account IDs: ' + new List<Id>(createdAccountIds).subList(0, Math.min(10, createdAccountIds.size())));
System.debug('Contact IDs: ' + new List<Id>(createdContactIds).subList(0, Math.min(10, createdContactIds.size())));
System.debug('Opportunity IDs: ' + new List<Id>(createdOpportunityIds).subList(0, Math.min(10, createdOpportunityIds.size())));
