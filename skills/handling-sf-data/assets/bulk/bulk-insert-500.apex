/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * BULK INSERT 500+ RECORDS
 * For testing batch Apex and queueable job bulkification
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * PURPOSE:
 * Test that batch Apex classes and queueable jobs handle larger datasets.
 * Default batch size is 200, so 500+ tests multiple batch iterations.
 *
 * WHY 500 RECORDS:
 * • Tests 2-3 batch iterations (200 records per batch)
 * • Validates stateful processing across batches
 * • Ensures aggregate operations work correctly
 *
 * BATCH APEX CONTEXT:
 * • Default scope is 200 records per execute()
 * • Maximum scope is 2000 records per execute()
 * • 50 million records can be processed total
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

Integer accountCount = 100;     // 100 accounts
Integer contactsPerAccount = 3; // 300 contacts total
Integer oppsPerAccount = 2;     // 200 opportunities total
// Total: ~600 records

String namePrefix = 'BatchTest';
DateTime testStartTime = DateTime.now();

// ═══════════════════════════════════════════════════════════════════════════════
// TRACKING COLLECTIONS
// ═══════════════════════════════════════════════════════════════════════════════

Map<String, Set<Id>> createdRecords = new Map<String, Set<Id>>{
    'Account' => new Set<Id>(),
    'Contact' => new Set<Id>(),
    'Opportunity' => new Set<Id>()
};

// ═══════════════════════════════════════════════════════════════════════════════
// LIMIT TRACKING
// ═══════════════════════════════════════════════════════════════════════════════

Integer startQueries = Limits.getQueries();
Integer startDml = Limits.getDmlStatements();
Integer startDmlRows = Limits.getDmlRows();
Integer startCpu = Limits.getCpuTime();

System.debug('═══════════════════════════════════════════════════════════════');
System.debug('Starting Batch-Size Test: ' + accountCount + ' accounts');
System.debug('Expected total records: ~' + (accountCount + accountCount * contactsPerAccount + accountCount * oppsPerAccount));
System.debug('═══════════════════════════════════════════════════════════════');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 1: CREATE ACCOUNTS IN CHUNKS
// ═══════════════════════════════════════════════════════════════════════════════

List<Account> accounts = new List<Account>();
List<String> industries = new List<String>{
    'Technology', 'Healthcare', 'Finance', 'Manufacturing',
    'Retail', 'Education', 'Energy', 'Media', 'Government', 'Nonprofit'
};
List<String> types = new List<String>{'Prospect', 'Customer', 'Partner'};

for (Integer i = 0; i < accountCount; i++) {
    accounts.add(new Account(
        Name = namePrefix + '_Account_' + String.valueOf(i).leftPad(5, '0'),
        Industry = industries[Math.mod(i, industries.size())],
        Type = types[Math.mod(i, types.size())],
        AnnualRevenue = 100000 + (i * 25000),
        NumberOfEmployees = 25 + (i * 10),
        BillingCity = 'San Francisco',
        BillingState = 'CA',
        BillingCountry = 'USA',
        Description = 'Batch test account created at ' + testStartTime
    ));
}

insert accounts;
for (Account acc : accounts) {
    createdRecords.get('Account').add(acc.Id);
}
System.debug('✓ Created ' + accounts.size() + ' Accounts');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 2: CREATE CONTACTS IN CHUNKS (to stay under DML row limit)
// ═══════════════════════════════════════════════════════════════════════════════

List<Contact> allContacts = new List<Contact>();
Integer contactIndex = 0;
List<String> titles = new List<String>{
    'CEO', 'CFO', 'CTO', 'VP Sales', 'VP Marketing',
    'Director', 'Manager', 'Analyst', 'Developer', 'Consultant'
};

for (Account acc : accounts) {
    for (Integer i = 0; i < contactsPerAccount; i++) {
        String idx = String.valueOf(contactIndex++).leftPad(5, '0');
        allContacts.add(new Contact(
            FirstName = namePrefix,
            LastName = 'Contact_' + idx,
            AccountId = acc.Id,
            Email = namePrefix.toLowerCase() + '.contact' + idx + '@batchtest.example.com',
            Phone = '(555) 200-' + String.valueOf(1000 + Math.mod(contactIndex, 9000)),
            Title = titles[Math.mod(contactIndex, titles.size())],
            Department = 'Department ' + Math.mod(contactIndex, 5),
            MailingCity = 'San Francisco',
            MailingState = 'CA'
        ));
    }
}

// Insert contacts
insert allContacts;
for (Contact con : allContacts) {
    createdRecords.get('Contact').add(con.Id);
}
System.debug('✓ Created ' + allContacts.size() + ' Contacts');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 3: CREATE OPPORTUNITIES
// ═══════════════════════════════════════════════════════════════════════════════

List<Opportunity> allOpportunities = new List<Opportunity>();
Integer oppIndex = 0;
List<String> stages = new List<String>{
    'Prospecting', 'Qualification', 'Needs Analysis',
    'Value Proposition', 'Proposal/Price Quote', 'Negotiation/Review'
};
List<String> leadSources = new List<String>{
    'Web', 'Phone Inquiry', 'Partner Referral', 'Trade Show', 'Other'
};

for (Account acc : accounts) {
    for (Integer i = 0; i < oppsPerAccount; i++) {
        String idx = String.valueOf(oppIndex++).leftPad(5, '0');
        allOpportunities.add(new Opportunity(
            Name = namePrefix + '_Opportunity_' + idx,
            AccountId = acc.Id,
            StageName = stages[Math.mod(oppIndex, stages.size())],
            CloseDate = Date.today().addDays(15 + Math.mod(oppIndex, 90)),
            Amount = 5000 + (oppIndex * 500),
            Probability = 10 + Math.mod(oppIndex, 80),
            Type = 'New Customer',
            LeadSource = leadSources[Math.mod(oppIndex, leadSources.size())]
        ));
    }
}

insert allOpportunities;
for (Opportunity opp : allOpportunities) {
    createdRecords.get('Opportunity').add(opp.Id);
}
System.debug('✓ Created ' + allOpportunities.size() + ' Opportunities');

// ═══════════════════════════════════════════════════════════════════════════════
// REPORT RESULTS
// ═══════════════════════════════════════════════════════════════════════════════

Integer endQueries = Limits.getQueries();
Integer endDml = Limits.getDmlStatements();
Integer endDmlRows = Limits.getDmlRows();
Integer endCpu = Limits.getCpuTime();

Integer totalRecords = createdRecords.get('Account').size() +
                       createdRecords.get('Contact').size() +
                       createdRecords.get('Opportunity').size();

System.debug('');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('BATCH-SIZE TEST COMPLETE');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('');
System.debug('📊 RECORDS CREATED:');
System.debug('   Accounts:      ' + createdRecords.get('Account').size());
System.debug('   Contacts:      ' + createdRecords.get('Contact').size());
System.debug('   Opportunities: ' + createdRecords.get('Opportunity').size());
System.debug('   ────────────────────────────────');
System.debug('   TOTAL:         ' + totalRecords);
System.debug('');
System.debug('📈 GOVERNOR LIMITS USED:');
System.debug('   SOQL Queries:     ' + (endQueries - startQueries) + ' / 100 (' + ((endQueries - startQueries) * 100 / 100) + '%)');
System.debug('   DML Statements:   ' + (endDml - startDml) + ' / 150 (' + ((endDml - startDml) * 100 / 150) + '%)');
System.debug('   DML Rows:         ' + endDmlRows + ' / 10000 (' + (endDmlRows * 100 / 10000) + '%)');
System.debug('   CPU Time (ms):    ' + (endCpu - startCpu) + ' / 10000 (' + ((endCpu - startCpu) * 100 / 10000) + '%)');
System.debug('');
System.debug('🔄 BATCH RECOMMENDATIONS:');
System.debug('   Records can be processed in batches of 200 (default)');
System.debug('   This dataset would require ' + Math.ceil((Decimal)totalRecords / 200) + ' batch iterations');
System.debug('');
System.debug('═══════════════════════════════════════════════════════════════');

// ═══════════════════════════════════════════════════════════════════════════════
// CLEANUP SCRIPT
// ═══════════════════════════════════════════════════════════════════════════════
/*
CLEANUP - Run this after testing:

DELETE [SELECT Id FROM Opportunity WHERE Name LIKE 'BatchTest%'];
DELETE [SELECT Id FROM Contact WHERE LastName LIKE 'Contact_%' AND Email LIKE '%batchtest.example.com'];
DELETE [SELECT Id FROM Account WHERE Name LIKE 'BatchTest%'];

System.debug('Cleanup complete');
*/

// ═══════════════════════════════════════════════════════════════════════════════
// OUTPUT FOR CLEANUP VIA SF CLI
// ═══════════════════════════════════════════════════════════════════════════════

System.debug('');
System.debug('CLI Cleanup Commands:');
System.debug('sf data query --query "SELECT Id FROM Account WHERE Name LIKE \'BatchTest%\'" --target-org [alias] --result-format csv > cleanup-accounts.csv');
System.debug('sf data delete bulk --file cleanup-accounts.csv --sobject Account --target-org [alias] --wait 10');
