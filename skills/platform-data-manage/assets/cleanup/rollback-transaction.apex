/**
 * ═══════════════════════════════════════════════════════════════════════════════
 * TRANSACTION ROLLBACK PATTERN
 * Using Database.Savepoint for test isolation
 * ═══════════════════════════════════════════════════════════════════════════════
 *
 * PURPOSE:
 * Create test data, run tests, then roll back all changes.
 * This ensures complete test isolation without leaving orphan data.
 *
 * HOW IT WORKS:
 * 1. Create a savepoint BEFORE creating any test data
 * 2. Create your test data
 * 3. Run your test/validation logic
 * 4. Roll back to the savepoint (deletes all created records)
 *
 * USE CASES:
 * • Unit testing with data setup
 * • Integration testing without pollution
 * • Manual testing with automatic cleanup
 * • Validation runs that shouldn't persist
 *
 * LIMITATIONS:
 * • Cannot roll back asynchronous operations
 * • Savepoints don't persist across transactions
 * • Maximum 5 savepoints per transaction
 *
 * ═══════════════════════════════════════════════════════════════════════════════
 */

// ═══════════════════════════════════════════════════════════════════════════════
// BASIC SAVEPOINT/ROLLBACK PATTERN
// ═══════════════════════════════════════════════════════════════════════════════

System.debug('═══════════════════════════════════════════════════════════════');
System.debug('TRANSACTION ROLLBACK DEMONSTRATION');
System.debug('═══════════════════════════════════════════════════════════════');

// Step 1: Create savepoint BEFORE any DML
Savepoint sp = Database.setSavepoint();
System.debug('✓ Savepoint created');

// Track what we create for verification
Set<Id> createdAccountIds = new Set<Id>();
Set<Id> createdContactIds = new Set<Id>();

try {
    // ═══════════════════════════════════════════════════════════════════════
    // Step 2: Create test data
    // ═══════════════════════════════════════════════════════════════════════

    System.debug('');
    System.debug('Creating test data...');

    // Create Accounts
    List<Account> testAccounts = new List<Account>();
    for (Integer i = 0; i < 10; i++) {
        testAccounts.add(new Account(
            Name = 'Rollback Test Account ' + i,
            Industry = 'Technology',
            Description = 'This record will be rolled back'
        ));
    }
    insert testAccounts;
    for (Account acc : testAccounts) {
        createdAccountIds.add(acc.Id);
    }
    System.debug('  Created ' + testAccounts.size() + ' Accounts');

    // Create Contacts
    List<Contact> testContacts = new List<Contact>();
    for (Account acc : testAccounts) {
        testContacts.add(new Contact(
            FirstName = 'Test',
            LastName = 'Contact',
            AccountId = acc.Id,
            Email = 'test@rollback.example.com'
        ));
    }
    insert testContacts;
    for (Contact con : testContacts) {
        createdContactIds.add(con.Id);
    }
    System.debug('  Created ' + testContacts.size() + ' Contacts');

    // ═══════════════════════════════════════════════════════════════════════
    // Step 3: Verify data exists
    // ═══════════════════════════════════════════════════════════════════════

    System.debug('');
    System.debug('Verifying data exists...');

    Integer accountCount = [SELECT COUNT() FROM Account WHERE Id IN :createdAccountIds];
    Integer contactCount = [SELECT COUNT() FROM Contact WHERE Id IN :createdContactIds];

    System.debug('  Accounts in database: ' + accountCount);
    System.debug('  Contacts in database: ' + contactCount);

    // ═══════════════════════════════════════════════════════════════════════
    // Step 4: Run your test logic here
    // ═══════════════════════════════════════════════════════════════════════

    System.debug('');
    System.debug('Running test logic...');

    // Example: Verify trigger fired correctly
    // Example: Check field calculations
    // Example: Validate workflow results

    System.debug('  Test logic completed');

} finally {
    // ═══════════════════════════════════════════════════════════════════════
    // Step 5: Roll back ALL changes
    // ═══════════════════════════════════════════════════════════════════════

    System.debug('');
    System.debug('Rolling back transaction...');

    Database.rollback(sp);

    System.debug('✓ Rollback complete');
}

// ═══════════════════════════════════════════════════════════════════════════════
// Step 6: Verify rollback worked
// ═══════════════════════════════════════════════════════════════════════════════

System.debug('');
System.debug('Verifying rollback...');

Integer accountCountAfter = [SELECT COUNT() FROM Account WHERE Id IN :createdAccountIds];
Integer contactCountAfter = [SELECT COUNT() FROM Contact WHERE Id IN :createdContactIds];

System.debug('  Accounts remaining: ' + accountCountAfter + ' (expected: 0)');
System.debug('  Contacts remaining: ' + contactCountAfter + ' (expected: 0)');

if (accountCountAfter == 0 && contactCountAfter == 0) {
    System.debug('');
    System.debug('═══════════════════════════════════════════════════════════════');
    System.debug('✅ ROLLBACK SUCCESSFUL - All test data removed');
    System.debug('═══════════════════════════════════════════════════════════════');
} else {
    System.debug('');
    System.debug('⚠️  WARNING: Some records were not rolled back');
}

// ═══════════════════════════════════════════════════════════════════════════════
// PATTERN: TEST METHOD WITH SAVEPOINT
// ═══════════════════════════════════════════════════════════════════════════════

/*
@isTest
public class MyTestClass {

    @isTest
    static void testWithRollback() {
        // In test methods, DML is automatically rolled back
        // This example shows explicit savepoint usage

        Savepoint sp = Database.setSavepoint();

        try {
            // Create test data
            Account testAccount = new Account(Name = 'Test');
            insert testAccount;

            // Run the test
            Test.startTest();
            MyClass.processAccount(testAccount.Id);
            Test.stopTest();

            // Assert results
            Account result = [SELECT Field__c FROM Account WHERE Id = :testAccount.Id];
            System.assertEquals('Expected', result.Field__c);

        } finally {
            // Optional explicit rollback (tests auto-rollback anyway)
            Database.rollback(sp);
        }
    }
}
*/

// ═══════════════════════════════════════════════════════════════════════════════
// PATTERN: NESTED SAVEPOINTS
// ═══════════════════════════════════════════════════════════════════════════════

/*
// You can have up to 5 savepoints

Savepoint sp1 = Database.setSavepoint();

// Create data set 1
insert accounts;

Savepoint sp2 = Database.setSavepoint();

// Create data set 2
insert contacts;

// Rollback to sp2 (removes contacts, keeps accounts)
Database.rollback(sp2);

// Rollback to sp1 (removes everything)
Database.rollback(sp1);
*/

// ═══════════════════════════════════════════════════════════════════════════════
// PATTERN: CONDITIONAL ROLLBACK
// ═══════════════════════════════════════════════════════════════════════════════

/*
Savepoint sp = Database.setSavepoint();
Boolean shouldCommit = true;

try {
    // Create data
    insert records;

    // Validate
    if (!isValid(records)) {
        shouldCommit = false;
    }

} finally {
    if (!shouldCommit) {
        Database.rollback(sp);
        System.debug('Changes rolled back due to validation failure');
    } else {
        System.debug('Changes committed');
    }
}
*/

// ═══════════════════════════════════════════════════════════════════════════════
// IMPORTANT NOTES
// ═══════════════════════════════════════════════════════════════════════════════

/*
1. SAVEPOINT LIMITATIONS:
   • Max 5 savepoints per transaction
   • Cannot cross transaction boundaries
   • Does not roll back @future, Queueable, or Batch operations
   • Does not roll back platform events
   • Does not roll back email sends

2. WHAT GETS ROLLED BACK:
   ✓ All DML operations (insert, update, delete, undelete)
   ✓ Workflow field updates triggered by DML
   ✓ Process Builder / Flow changes triggered by DML

3. WHAT DOES NOT GET ROLLED BACK:
   ✗ Asynchronous operations (@future, Queueable, Batch, Scheduled)
   ✗ Platform events
   ✗ Outbound messages
   ✗ Email sends
   ✗ Callouts (HTTP requests)
   ✗ Debug logs

4. BEST PRACTICES:
   • Create savepoint as early as possible
   • Always use try-finally to ensure rollback
   • Verify rollback worked by querying records
   • Don't rely on savepoints for async operations
*/
