/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * BULK UPSERT WITH EXTERNAL ID
 * For data synchronization and migration scenarios
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * PURPOSE:
 * Upsert (insert or update) records using an External ID field.
 * This is essential for:
 * • Data synchronization with external systems
 * • Data migration from legacy systems
 * • Ongoing integrations where records may or may not exist
 *
 * HOW IT WORKS:
 * • If External ID matches → UPDATE existing record
 * • If External ID not found → INSERT new record
 * • External ID field must be marked as "External ID" in Salesforce
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// APEX UPSERT EXAMPLE
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Example: Upsert Accounts using External_Id__c field
 *
 * Prerequisites:
 * 1. Create a custom field on Account: External_Id__c (Text, External ID, Unique)
 * 2. Ensure field is marked as "External ID" in field settings
 */

// Sample data simulating external system records
List<Map<String, Object>> externalData = new List<Map<String, Object>>{
    new Map<String, Object>{
        'externalId' => 'EXT-001',
        'name' => 'External Account One',
        'industry' => 'Technology',
        'revenue' => 1000000
    },
    new Map<String, Object>{
        'externalId' => 'EXT-002',
        'name' => 'External Account Two',
        'industry' => 'Healthcare',
        'revenue' => 2000000
    },
    new Map<String, Object>{
        'externalId' => 'EXT-003',
        'name' => 'External Account Three',
        'industry' => 'Finance',
        'revenue' => 3000000
    }
};

// Build Account records with External ID
List<Account> accountsToUpsert = new List<Account>();

for (Map<String, Object> data : externalData) {
    accountsToUpsert.add(new Account(
        External_Id__c = (String) data.get('externalId'),
        Name = (String) data.get('name'),
        Industry = (String) data.get('industry'),
        AnnualRevenue = (Decimal) data.get('revenue'),
        Type = 'Prospect',
        Description = 'Synced from external system'
    ));
}

// Upsert using External ID field
Schema.SObjectField externalIdField = Account.External_Id__c;
List<Database.UpsertResult> results = Database.upsert(accountsToUpsert, externalIdField, false);

// Process results
Integer insertedCount = 0;
Integer updatedCount = 0;
Integer errorCount = 0;

for (Integer i = 0; i < results.size(); i++) {
    Database.UpsertResult result = results[i];
    Account acc = accountsToUpsert[i];

    if (result.isSuccess()) {
        if (result.isCreated()) {
            insertedCount++;
            System.debug('✓ INSERTED: ' + acc.External_Id__c + ' -> ' + result.getId());
        } else {
            updatedCount++;
            System.debug('✓ UPDATED: ' + acc.External_Id__c + ' -> ' + result.getId());
        }
    } else {
        errorCount++;
        for (Database.Error err : result.getErrors()) {
            System.debug('✗ ERROR: ' + acc.External_Id__c + ' -> ' + err.getMessage());
        }
    }
}

System.debug('');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('UPSERT COMPLETE');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('Inserted: ' + insertedCount);
System.debug('Updated: ' + updatedCount);
System.debug('Errors: ' + errorCount);
System.debug('═══════════════════════════════════════════════════════════════');

// ═══════════════════════════════════════════════════════════════════════════════
// SF CLI BULK UPSERT
// ═══════════════════════════════════════════════════════════════════════════════

/*
STEP 1: Create CSV with External ID column

Example accounts-upsert.csv:
External_Id__c,Name,Industry,Type,AnnualRevenue,BillingCity,BillingState
EXT-001,External Account One,Technology,Prospect,1000000,San Francisco,CA
EXT-002,External Account Two,Healthcare,Customer,2000000,New York,NY
EXT-003,External Account Three,Finance,Partner,3000000,Chicago,IL

STEP 2: Run bulk upsert

sf data upsert bulk \
  --file accounts-upsert.csv \
  --sobject Account \
  --external-id External_Id__c \
  --target-org myorg \
  --wait 30

NOTES:
• The External_Id__c field must exist and be marked as External ID in Salesforce
• To use standard Id field as the external ID: --external-id Id
• CSV must include the external ID column
*/

// ═══════════════════════════════════════════════════════════════════════════════
// EXAMPLE: UPSERT CONTACTS WITH ACCOUNT RELATIONSHIP
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Upsert Contacts and establish Account relationship via External ID
 *
 * Prerequisites:
 * 1. Account.External_Id__c exists and has values
 * 2. Contact.External_Id__c exists
 */

/*
List<Contact> contactsToUpsert = new List<Contact>();

// Create Contacts referencing Accounts by External ID
for (Map<String, Object> data : externalContactData) {
    Contact con = new Contact(
        External_Id__c = (String) data.get('contactExternalId'),
        FirstName = (String) data.get('firstName'),
        LastName = (String) data.get('lastName'),
        Email = (String) data.get('email')
    );

    // Set Account relationship via External ID
    // This creates the relationship without querying for the Account first
    con.Account = new Account(
        External_Id__c = (String) data.get('accountExternalId')
    );

    contactsToUpsert.add(con);
}

// Upsert Contacts
Database.upsert(contactsToUpsert, Contact.External_Id__c, false);
*/

// ═══════════════════════════════════════════════════════════════════════════════
// CSV FOR CONTACT UPSERT WITH ACCOUNT RELATIONSHIP
// ═══════════════════════════════════════════════════════════════════════════════

/*
Example contacts-upsert.csv:

External_Id__c,FirstName,LastName,Email,Account.External_Id__c
CON-001,John,Smith,john.smith@example.com,EXT-001
CON-002,Jane,Doe,jane.doe@example.com,EXT-001
CON-003,Bob,Johnson,bob.johnson@example.com,EXT-002

Note: Use "Account.External_Id__c" to reference parent by External ID

sf data upsert bulk \
  --file contacts-upsert.csv \
  --sobject Contact \
  --external-id External_Id__c \
  --target-org myorg \
  --wait 30
*/

// ═══════════════════════════════════════════════════════════════════════════════
// EXAMPLE: UPSERT WITH STANDARD ID (Update existing records)
// ═══════════════════════════════════════════════════════════════════════════════

/*
When you have Salesforce IDs (from export), use Id as the external ID:

Example updates.csv:
Id,Name,Industry,AnnualRevenue
001XXXXXXXXXXXX1,Updated Account One,Technology,1500000
001XXXXXXXXXXXX2,Updated Account Two,Healthcare,2500000

sf data upsert bulk \
  --file updates.csv \
  --sobject Account \
  --external-id Id \
  --target-org myorg \
  --wait 30
*/

// ═══════════════════════════════════════════════════════════════════════════════
// COMPLETE SYNC WORKFLOW EXAMPLE
// ═══════════════════════════════════════════════════════════════════════════════

/*
FULL SYNC WORKFLOW:

1. Export current data from Salesforce
   sf data query \
     --query "SELECT External_Id__c, Name, Industry FROM Account WHERE External_Id__c != null" \
     --target-org myorg \
     --result-format csv \
     > current-accounts.csv

2. Generate sync file from external system (your process)
   - Include External_Id__c for each record
   - Include all fields to update/insert

3. Upsert the sync file
   sf data upsert bulk \
     --file sync-accounts.csv \
     --sobject Account \
     --external-id External_Id__c \
     --target-org myorg \
     --wait 30

4. Check results
   sf data bulk results \
     --job-id [job-id-from-step-3] \
     --target-org myorg
*/

// ═══════════════════════════════════════════════════════════════════════════════
// BATCH APEX FOR COMPLEX UPSERT LOGIC
// ═══════════════════════════════════════════════════════════════════════════════

/**
 * Batch class for upserting with custom logic
 */
public class BulkUpsertProcessor implements Database.Batchable<SObject>, Database.Stateful {

    private String query;
    private Integer insertedCount = 0;
    private Integer updatedCount = 0;
    private Integer errorCount = 0;

    public BulkUpsertProcessor(String soqlQuery) {
        this.query = soqlQuery;
    }

    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator(query);
    }

    public void execute(Database.BatchableContext bc, List<SObject> records) {
        // Transform and prepare records for upsert
        List<Account> accountsToUpsert = new List<Account>();

        for (SObject record : records) {
            Account source = (Account) record;

            // Create upsert record
            Account target = new Account(
                External_Id__c = source.External_Id__c,
                Name = source.Name,
                Industry = source.Industry,
                AnnualRevenue = source.AnnualRevenue,
                LastModifiedDate = DateTime.now() // Will be auto-updated
            );

            // Apply transformation logic
            if (target.AnnualRevenue != null && target.AnnualRevenue > 1000000) {
                target.Type = 'Enterprise';
            }

            accountsToUpsert.add(target);
        }

        // Upsert with partial success
        List<Database.UpsertResult> results = Database.upsert(
            accountsToUpsert,
            Account.External_Id__c,
            false // Allow partial success
        );

        // Track results
        for (Database.UpsertResult result : results) {
            if (result.isSuccess()) {
                if (result.isCreated()) {
                    insertedCount++;
                } else {
                    updatedCount++;
                }
            } else {
                errorCount++;
            }
        }
    }

    public void finish(Database.BatchableContext bc) {
        System.debug('Batch Upsert Complete:');
        System.debug('  Inserted: ' + insertedCount);
        System.debug('  Updated: ' + updatedCount);
        System.debug('  Errors: ' + errorCount);
    }
}

// Execute with:
// String query = 'SELECT External_Id__c, Name, Industry, AnnualRevenue FROM Account WHERE External_Id__c != null';
// Database.executeBatch(new BulkUpsertProcessor(query), 200);
