/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * DELETE RECORDS BY NAME PATTERN
 * Clean up test records matching a specific naming pattern
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * PURPOSE:
 * Delete test records that follow a naming convention.
 * Common patterns: 'Test%', 'BulkTest%', 'Demo%', etc.
 *
 * ⚠️  WARNING:
 * Always PREVIEW records before deleting!
 * Records go to Recycle Bin by default (soft delete)
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════════

String namePattern = 'Test%';  // LIKE pattern for Name field
Boolean previewOnly = true;    // Set to false to actually delete
Integer maxRecords = 10000;    // Safety limit

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 1: PREVIEW ACCOUNTS
// ═══════════════════════════════════════════════════════════════════════════════

System.debug('═══════════════════════════════════════════════════════════════');
System.debug('DELETE BY NAME PATTERN: ' + namePattern);
System.debug('Mode: ' + (previewOnly ? 'PREVIEW ONLY' : '⚠️  DELETE MODE'));
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('');

// Query Accounts
List<Account> accountsToDelete = [
    SELECT Id, Name, CreatedDate, CreatedBy.Name
    FROM Account
    WHERE Name LIKE :namePattern
    ORDER BY CreatedDate DESC
    LIMIT :maxRecords
];

System.debug('📋 ACCOUNTS matching "' + namePattern + '": ' + accountsToDelete.size());
if (!accountsToDelete.isEmpty()) {
    System.debug('   Sample records:');
    for (Integer i = 0; i < Math.min(10, accountsToDelete.size()); i++) {
        Account acc = accountsToDelete[i];
        System.debug('   - ' + acc.Name + ' (Created: ' + acc.CreatedDate.format() + ' by ' + acc.CreatedBy.Name + ')');
    }
    if (accountsToDelete.size() > 10) {
        System.debug('   ... and ' + (accountsToDelete.size() - 10) + ' more');
    }
}
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 2: PREVIEW CONTACTS
// ═══════════════════════════════════════════════════════════════════════════════

List<Contact> contactsToDelete = [
    SELECT Id, FirstName, LastName, Account.Name, CreatedDate
    FROM Contact
    WHERE LastName LIKE :namePattern
    OR Account.Name LIKE :namePattern
    ORDER BY CreatedDate DESC
    LIMIT :maxRecords
];

System.debug('📋 CONTACTS matching "' + namePattern + '": ' + contactsToDelete.size());
if (!contactsToDelete.isEmpty()) {
    System.debug('   Sample records:');
    for (Integer i = 0; i < Math.min(10, contactsToDelete.size()); i++) {
        Contact con = contactsToDelete[i];
        System.debug('   - ' + con.FirstName + ' ' + con.LastName + ' (' + con.Account?.Name + ')');
    }
}
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 3: PREVIEW OPPORTUNITIES
// ═══════════════════════════════════════════════════════════════════════════════

List<Opportunity> opportunitiesToDelete = [
    SELECT Id, Name, Account.Name, StageName, Amount, CreatedDate
    FROM Opportunity
    WHERE Name LIKE :namePattern
    OR Account.Name LIKE :namePattern
    ORDER BY CreatedDate DESC
    LIMIT :maxRecords
];

System.debug('📋 OPPORTUNITIES matching "' + namePattern + '": ' + opportunitiesToDelete.size());
if (!opportunitiesToDelete.isEmpty()) {
    System.debug('   Sample records:');
    for (Integer i = 0; i < Math.min(10, opportunitiesToDelete.size()); i++) {
        Opportunity opp = opportunitiesToDelete[i];
        System.debug('   - ' + opp.Name + ' (' + opp.StageName + ', $' + opp.Amount + ')');
    }
}
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 4: PREVIEW CASES
// ═══════════════════════════════════════════════════════════════════════════════

List<Case> casesToDelete = [
    SELECT Id, CaseNumber, Subject, Account.Name, Status, CreatedDate
    FROM Case
    WHERE Subject LIKE :namePattern
    OR Account.Name LIKE :namePattern
    ORDER BY CreatedDate DESC
    LIMIT :maxRecords
];

System.debug('📋 CASES matching "' + namePattern + '": ' + casesToDelete.size());
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 5: PREVIEW LEADS
// ═══════════════════════════════════════════════════════════════════════════════

List<Lead> leadsToDelete = [
    SELECT Id, FirstName, LastName, Company, Status, CreatedDate
    FROM Lead
    WHERE LastName LIKE :namePattern
    OR Company LIKE :namePattern
    ORDER BY CreatedDate DESC
    LIMIT :maxRecords
];

System.debug('📋 LEADS matching "' + namePattern + '": ' + leadsToDelete.size());
System.debug('');

// ═══════════════════════════════════════════════════════════════════════════════
// SUMMARY
// ═══════════════════════════════════════════════════════════════════════════════

Integer totalRecords = accountsToDelete.size() + contactsToDelete.size() +
                       opportunitiesToDelete.size() + casesToDelete.size() +
                       leadsToDelete.size();

System.debug('═══════════════════════════════════════════════════════════════');
System.debug('SUMMARY - Records matching "' + namePattern + '"');
System.debug('═══════════════════════════════════════════════════════════════');
System.debug('  Accounts:      ' + accountsToDelete.size());
System.debug('  Contacts:      ' + contactsToDelete.size());
System.debug('  Opportunities: ' + opportunitiesToDelete.size());
System.debug('  Cases:         ' + casesToDelete.size());
System.debug('  Leads:         ' + leadsToDelete.size());
System.debug('  ─────────────────────────────────');
System.debug('  TOTAL:         ' + totalRecords);
System.debug('═══════════════════════════════════════════════════════════════');

// ═══════════════════════════════════════════════════════════════════════════════
// STEP 6: DELETE (if not preview mode)
// ═══════════════════════════════════════════════════════════════════════════════

if (!previewOnly && totalRecords > 0) {
    System.debug('');
    System.debug('⚠️  DELETING RECORDS...');

    // Delete in correct order (children before parents)
    Integer deletedCount = 0;

    // Delete Cases
    if (!casesToDelete.isEmpty()) {
        delete casesToDelete;
        deletedCount += casesToDelete.size();
        System.debug('  ✓ Deleted ' + casesToDelete.size() + ' Cases');
    }

    // Delete Opportunities
    if (!opportunitiesToDelete.isEmpty()) {
        delete opportunitiesToDelete;
        deletedCount += opportunitiesToDelete.size();
        System.debug('  ✓ Deleted ' + opportunitiesToDelete.size() + ' Opportunities');
    }

    // Delete Contacts
    if (!contactsToDelete.isEmpty()) {
        delete contactsToDelete;
        deletedCount += contactsToDelete.size();
        System.debug('  ✓ Deleted ' + contactsToDelete.size() + ' Contacts');
    }

    // Delete Leads
    if (!leadsToDelete.isEmpty()) {
        delete leadsToDelete;
        deletedCount += leadsToDelete.size();
        System.debug('  ✓ Deleted ' + leadsToDelete.size() + ' Leads');
    }

    // Delete Accounts (last - they're parents)
    if (!accountsToDelete.isEmpty()) {
        delete accountsToDelete;
        deletedCount += accountsToDelete.size();
        System.debug('  ✓ Deleted ' + accountsToDelete.size() + ' Accounts');
    }

    System.debug('');
    System.debug('═══════════════════════════════════════════════════════════════');
    System.debug('DELETE COMPLETE: ' + deletedCount + ' records moved to Recycle Bin');
    System.debug('═══════════════════════════════════════════════════════════════');
} else if (previewOnly) {
    System.debug('');
    System.debug('ℹ️  PREVIEW MODE - No records deleted');
    System.debug('   To delete, set previewOnly = false and run again');
}

// ═══════════════════════════════════════════════════════════════════════════════
// SF CLI ALTERNATIVE
// ═══════════════════════════════════════════════════════════════════════════════

/*
For large datasets, use sf CLI Bulk API:

# Step 1: Query and export IDs
sf data query \
  --query "SELECT Id FROM Account WHERE Name LIKE 'Test%'" \
  --target-org myorg \
  --result-format csv \
  > delete-accounts.csv

# Step 2: Bulk delete
sf data delete bulk \
  --file delete-accounts.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30

# For permanent delete (hard delete):
sf data delete bulk \
  --file delete-accounts.csv \
  --sobject Account \
  --target-org myorg \
  --hard-delete \
  --wait 30
*/
