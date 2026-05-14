/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * DELETE TEST DATA - COMPREHENSIVE CLEANUP
 * Remove all test data matching common test data patterns
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * PURPOSE:
 * Clean up test data created by TestDataFactory classes.
 * Targets common test data naming patterns across multiple objects.
 *
 * PATTERNS MATCHED:
 * • 'Test%' - Standard test prefix
 * • 'BulkTest%' - Bulk testing data
 * • 'BatchTest%' - Batch Apex testing data
 * • 'BulkData%' - Large volume test data
 * • 'BulkImport%' - Import testing data
 * • 'Hierarchy%' - Hierarchy testing data
 * • '%@testfactory.example.com' - Test email domain
 * • '%@bulktest.example.com' - Bulk test email domain
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

Boolean previewOnly = true;     // Set to false to actually delete
Integer maxRecordsPerObject = 10000;

// Patterns to match (add your custom test patterns here)
List<String> namePatterns = new List<String>{
    'Test%',
    'BulkTest%',
    'BatchTest%',
    'BulkData%',
    'BulkImport%',
    'Hierarchy%'
};

List<String> emailPatterns = new List<String>{
    '%@testfactory.example.com',
    '%@bulktest.example.com',
    '%@batchtest.example.com'
};

// ═══════════════════════════════════════════════════════════════════════════════
// TRACKING
// ═══════════════════════════════════════════════════════════════════════════════

Map<String, Integer> recordCounts = new Map<String, Integer>();

System.debug('═══════════════════════════════════════════════════════════════');
System.debug('COMPREHENSIVE TEST DATA CLEANUP');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('Mode: ' + (previewOnly ? 'PREVIEW ONLY' : '⚠️  DELETE MODE'));
System.debug('Patterns: ' + namePatterns);
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 1: FIND TASKS (delete first - activity records)
// ═══════════════════════════════════════════════════════════════════════════════

List<Task> tasksToDelete = [
    SELECT Id, Subject, WhoId, WhatId
    FROM Task
    WHERE Subject LIKE 'Test%'
    OR Subject LIKE 'BulkTest%'
    OR Subject LIKE 'Hierarchy%'
    LIMIT :maxRecordsPerObject
];
recordCounts.put('Task', tasksToDelete.size());
System.debug('📋 Tasks found: ' + tasksToDelete.size());

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 2: FIND EVENTS
// ═══════════════════════════════════════════════════════════════════════════════

List<Event> eventsToDelete = [
    SELECT Id, Subject, WhoId, WhatId
    FROM Event
    WHERE Subject LIKE 'Test%'
    OR Subject LIKE 'All Day Event%'
    OR Subject LIKE 'Recurring Event%'
    OR Subject LIKE 'Calendar Event%'
    LIMIT :maxRecordsPerObject
];
recordCounts.put('Event', eventsToDelete.size());
System.debug('📋 Events found: ' + eventsToDelete.size());

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 3: FIND CASES
// ═══════════════════════════════════════════════════════════════════════════════

List<Case> casesToDelete = [
    SELECT Id, Subject, AccountId
    FROM Case
    WHERE Subject LIKE 'Test%'
    OR Subject LIKE 'Hierarchy Case%'
    LIMIT :maxRecordsPerObject
];
recordCounts.put('Case', casesToDelete.size());
System.debug('📋 Cases found: ' + casesToDelete.size());

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 4: FIND OPPORTUNITIES
// ═══════════════════════════════════════════════════════════════════════════════

List<Opportunity> opportunitiesToDelete = [
    SELECT Id, Name, AccountId
    FROM Opportunity
    WHERE Name LIKE 'Test%'
    OR Name LIKE 'BulkTest%'
    OR Name LIKE 'BatchTest%'
    OR Name LIKE 'Hierarchy%'
    LIMIT :maxRecordsPerObject
];
recordCounts.put('Opportunity', opportunitiesToDelete.size());
System.debug('📋 Opportunities found: ' + opportunitiesToDelete.size());

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 5: FIND CONTACTS
// ═══════════════════════════════════════════════════════════════════════════════

List<Contact> contactsToDelete = [
    SELECT Id, FirstName, LastName, Email, AccountId
    FROM Contact
    WHERE LastName LIKE 'Contact_%'
    OR LastName LIKE 'Hierarchy%'
    OR LastName LIKE 'Test%'
    OR Email LIKE '%@testfactory.example.com'
    OR Email LIKE '%@bulktest.example.com'
    OR Email LIKE '%@batchtest.example.com'
    LIMIT :maxRecordsPerObject
];
recordCounts.put('Contact', contactsToDelete.size());
System.debug('📋 Contacts found: ' + contactsToDelete.size());

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 6: FIND LEADS
// ═══════════════════════════════════════════════════════════════════════════════

List<Lead> leadsToDelete = [
    SELECT Id, FirstName, LastName, Company
    FROM Lead
    WHERE LastName LIKE 'Lead%'
    OR LastName LIKE 'Test%'
    OR Company LIKE 'Test Company%'
    OR Email LIKE '%@testlead.example.com'
    LIMIT :maxRecordsPerObject
];
recordCounts.put('Lead', leadsToDelete.size());
System.debug('📋 Leads found: ' + leadsToDelete.size());

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 7: FIND ACCOUNTS (delete last - parent records)
// ═══════════════════════════════════════════════════════════════════════════════

List<Account> accountsToDelete = [
    SELECT Id, Name
    FROM Account
    WHERE Name LIKE 'Test%'
    OR Name LIKE 'BulkTest%'
    OR Name LIKE 'BatchTest%'
    OR Name LIKE 'BulkData%'
    OR Name LIKE 'BulkImport%'
    OR Name LIKE 'Hierarchy%'
    OR Name LIKE 'Root Account%'
    OR Name LIKE 'Level%'
    LIMIT :maxRecordsPerObject
];
recordCounts.put('Account', accountsToDelete.size());
System.debug('📋 Accounts found: ' + accountsToDelete.size());

// ═══════════════════════════════════════════════════════════════════════════════
// SUMMARY
// ═══════════════════════════════════════════════════════════════════════════════

Integer totalRecords = 0;
for (String objName : recordCounts.keySet()) {
    totalRecords += recordCounts.get(objName);
}

System.debug('');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('CLEANUP SUMMARY');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('  Tasks:         ' + recordCounts.get('Task'));
System.debug('  Events:        ' + recordCounts.get('Event'));
System.debug('  Cases:         ' + recordCounts.get('Case'));
System.debug('  Opportunities: ' + recordCounts.get('Opportunity'));
System.debug('  Contacts:      ' + recordCounts.get('Contact'));
System.debug('  Leads:         ' + recordCounts.get('Lead'));
System.debug('  Accounts:      ' + recordCounts.get('Account'));
System.debug('  ─────────────────────────────────');
System.debug('  TOTAL:         ' + totalRecords);
System.debug('═══════════════════════════════════════════════════════════════');

// ═══════════════════════════════════════════════════════════════════════════════
// EXECUTE DELETE
// ═══════════════════════════════════════════════════════════════════════════════

if (!previewOnly && totalRecords > 0) {
    System.debug('');
    System.debug('⚠️  DELETING RECORDS...');
    System.debug('   Deleting in dependency order (children before parents)');
    System.debug('');

    Integer deletedCount = 0;

    // Delete in order: Activities → Children → Parents
    try {
        if (!tasksToDelete.isEmpty()) {
            delete tasksToDelete;
            deletedCount += tasksToDelete.size();
            System.debug('  ✓ Deleted ' + tasksToDelete.size() + ' Tasks');
        }

        if (!eventsToDelete.isEmpty()) {
            delete eventsToDelete;
            deletedCount += eventsToDelete.size();
            System.debug('  ✓ Deleted ' + eventsToDelete.size() + ' Events');
        }

        if (!casesToDelete.isEmpty()) {
            delete casesToDelete;
            deletedCount += casesToDelete.size();
            System.debug('  ✓ Deleted ' + casesToDelete.size() + ' Cases');
        }

        if (!opportunitiesToDelete.isEmpty()) {
            delete opportunitiesToDelete;
            deletedCount += opportunitiesToDelete.size();
            System.debug('  ✓ Deleted ' + opportunitiesToDelete.size() + ' Opportunities');
        }

        if (!contactsToDelete.isEmpty()) {
            delete contactsToDelete;
            deletedCount += contactsToDelete.size();
            System.debug('  ✓ Deleted ' + contactsToDelete.size() + ' Contacts');
        }

        if (!leadsToDelete.isEmpty()) {
            delete leadsToDelete;
            deletedCount += leadsToDelete.size();
            System.debug('  ✓ Deleted ' + leadsToDelete.size() + ' Leads');
        }

        if (!accountsToDelete.isEmpty()) {
            delete accountsToDelete;
            deletedCount += accountsToDelete.size();
            System.debug('  ✓ Deleted ' + accountsToDelete.size() + ' Accounts');
        }

        System.debug('');
        System.debug('═══════════════════════════════════════════════════════════════');
        System.debug('✅ CLEANUP COMPLETE');
        System.debug('   Deleted: ' + deletedCount + ' records');
        System.debug('   Status: Moved to Recycle Bin');
        System.debug('═══════════════════════════════════════════════════════════════');

    } catch (DmlException e) {
        System.debug('');
        System.debug('❌ DELETE ERROR: ' + e.getMessage());
        System.debug('   Some records may have dependencies preventing deletion.');
        System.debug('   Try running again after resolving dependencies.');
    }
} else if (previewOnly) {
    System.debug('');
    System.debug('ℹ️  PREVIEW MODE - No records deleted');
    System.debug('   To delete, set previewOnly = false and run again');
    System.debug('');
    System.debug('   ⚠️  Please review the counts above before deleting!');
}

// ═══════════════════════════════════════════════════════════════════════════════
// BATCH APEX VERSION (For very large datasets)
// ═══════════════════════════════════════════════════════════════════════════════

/*
For datasets larger than 10,000 records, use batch Apex:

public class TestDataCleanupBatch implements Database.Batchable<SObject> {
    private String objectName;
    private String query;

    public TestDataCleanupBatch(String objName, String soqlQuery) {
        this.objectName = objName;
        this.query = soqlQuery;
    }

    public Database.QueryLocator start(Database.BatchableContext bc) {
        return Database.getQueryLocator(query);
    }

    public void execute(Database.BatchableContext bc, List<SObject> records) {
        delete records;
    }

    public void finish(Database.BatchableContext bc) {
        System.debug('Cleanup complete for ' + objectName);
    }
}

// Execute for each object (in order):
Database.executeBatch(new TestDataCleanupBatch('Task',
    'SELECT Id FROM Task WHERE Subject LIKE \'Test%\''), 200);
Database.executeBatch(new TestDataCleanupBatch('Account',
    'SELECT Id FROM Account WHERE Name LIKE \'Test%\''), 200);
*/
