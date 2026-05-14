<!-- Parent: handling-sf-data/SKILL.md -->
# Cleanup and Rollback Examples

Strategies for test data isolation and proper cleanup.

## Method 1: Savepoint/Rollback

Best for synchronous operations in a single transaction.

### Basic Pattern
```apex
// Create savepoint BEFORE any DML
Savepoint sp = Database.setSavepoint();

try {
    // Create test data
    Account acc = new Account(Name = 'Test Account');
    insert acc;

    Contact con = new Contact(
        FirstName = 'Test',
        LastName = 'Contact',
        AccountId = acc.Id
    );
    insert con;

    // Perform operations
    MyClass.processAccount(acc);

    // Assert results
    acc = [SELECT Custom_Field__c FROM Account WHERE Id = :acc.Id];
    System.assert(acc.Custom_Field__c != null, 'Field should be populated');

} finally {
    // ALWAYS rollback - even on success
    Database.rollback(sp);
}

// Data is now completely removed
```

### In Unit Tests
```apex
@isTest
static void testWithRollback() {
    Savepoint sp = Database.setSavepoint();

    try {
        // Create 1000 test records
        List<Account> accounts = new List<Account>();
        for (Integer i = 0; i < 1000; i++) {
            accounts.add(new Account(Name = 'Rollback Test ' + i));
        }
        insert accounts;

        // Run business logic
        Test.startTest();
        BatchProcessor.process(accounts);
        Test.stopTest();

        // Assertions
        Integer count = [SELECT COUNT() FROM Account WHERE Name LIKE 'Rollback Test%'];
        System.assertEquals(1000, count);

    } finally {
        Database.rollback(sp);
    }

    // Verify cleanup
    Integer remaining = [SELECT COUNT() FROM Account WHERE Name LIKE 'Rollback Test%'];
    System.assertEquals(0, remaining, 'All records should be rolled back');
}
```

### Limitations
- **Does NOT rollback async operations** (future, queueable, batch)
- Maximum 5 savepoints per transaction
- Cannot rollback across transaction boundaries

## Method 2: Cleanup by Name Pattern

Best when savepoint isn't possible (async tests, multi-transaction).

### Single Object Cleanup
```apex
// Delete all test accounts
List<Account> toDelete = [
    SELECT Id FROM Account
    WHERE Name LIKE 'Test%'
    LIMIT 10000
];
delete toDelete;
```

### Multi-Object Cleanup (Correct Order)
```apex
// CRITICAL: Delete children before parents!
String testPattern = 'Test%';

// 1. Delete grandchildren first
delete [SELECT Id FROM Task WHERE What.Name LIKE :testPattern];
delete [SELECT Id FROM Event WHERE What.Name LIKE :testPattern];

// 2. Delete children
delete [SELECT Id FROM Opportunity WHERE Account.Name LIKE :testPattern];
delete [SELECT Id FROM Contact WHERE Account.Name LIKE :testPattern];
delete [SELECT Id FROM Case WHERE Account.Name LIKE :testPattern];

// 3. Delete parents last
delete [SELECT Id FROM Account WHERE Name LIKE :testPattern];

System.debug('Cleanup complete');
```

### sf CLI Cleanup
```bash
# Query records to delete
sf data query \
  --query "SELECT Id FROM Account WHERE Name LIKE 'Test%'" \
  --target-org dev \
  --result-format csv \
  > delete-accounts.csv

# Bulk delete
sf data delete bulk \
  --file delete-accounts.csv \
  --sobject Account \
  --target-org dev \
  --wait 30
```

## Method 3: Cleanup by Time Window

Best for cleaning up after a specific test run.

### By CreatedDate
```apex
// Clean up records created in the last hour
DateTime startTime = DateTime.now().addHours(-1);
String testPattern = 'Test%';

delete [
    SELECT Id FROM Account
    WHERE CreatedDate >= :startTime
    AND Name LIKE :testPattern
];
```

### With Timestamp Tracking
```apex
// At start of test - capture timestamp
DateTime testStartTime = DateTime.now();

// ... run tests ...

// Cleanup - only records created during this test
delete [
    SELECT Id FROM Account
    WHERE CreatedDate >= :testStartTime
    AND Name LIKE 'Test%'
];
```

## Method 4: ID-Based Cleanup

Most precise - track exactly what you created.

### Track IDs During Creation
```apex
// Collection to track all created record IDs
Set<Id> createdAccountIds = new Set<Id>();
Set<Id> createdContactIds = new Set<Id>();
Set<Id> createdOppIds = new Set<Id>();

// Create and track
List<Account> accounts = TestDataFactory_Account.create(100);
createdAccountIds.addAll(new Map<Id, Account>(accounts).keySet());

List<Contact> contacts = TestDataFactory_Contact.createForAccounts(createdAccountIds, 3);
createdContactIds.addAll(new Map<Id, Contact>(contacts).keySet());

// ... run tests ...

// Cleanup exactly what we created
delete [SELECT Id FROM Contact WHERE Id IN :createdContactIds];
delete [SELECT Id FROM Account WHERE Id IN :createdAccountIds];
```

### Wrapper Class for Tracking
```apex
public class TestDataTracker {
    private Map<String, Set<Id>> trackedIds = new Map<String, Set<Id>>();

    public void track(SObject record) {
        String objType = record.getSObjectType().getDescribe().getName();
        if (!trackedIds.containsKey(objType)) {
            trackedIds.put(objType, new Set<Id>());
        }
        trackedIds.get(objType).add(record.Id);
    }

    public void trackAll(List<SObject> records) {
        for (SObject rec : records) {
            track(rec);
        }
    }

    public void cleanup() {
        // Delete in reverse dependency order
        List<String> deleteOrder = new List<String>{
            'Task', 'Event', 'Opportunity', 'Contact', 'Case', 'Account'
        };

        for (String objType : deleteOrder) {
            if (trackedIds.containsKey(objType)) {
                Set<Id> ids = trackedIds.get(objType);
                String query = 'SELECT Id FROM ' + objType + ' WHERE Id IN :ids';
                delete Database.query(query);
            }
        }
    }
}

// Usage
TestDataTracker tracker = new TestDataTracker();

List<Account> accounts = TestDataFactory_Account.create(100);
tracker.trackAll(accounts);

List<Contact> contacts = TestDataFactory_Contact.create(50);
tracker.trackAll(contacts);

// ... run tests ...

// Clean up everything tracked
tracker.cleanup();
```

## Method 5: @testSetup Isolation

Automatic rollback with @isTest annotation.

```apex
@isTest
public class MyTestClass {

    @testSetup
    static void setup() {
        // This data is automatically rolled back after ALL tests complete
        List<Account> accounts = TestDataFactory_Account.create(100);
    }

    @isTest
    static void testMethod1() {
        // Access setup data
        List<Account> accounts = [SELECT Id FROM Account];
        // Modify data - changes rolled back after this test
        delete accounts[0];
    }

    @isTest
    static void testMethod2() {
        // Fresh copy of @testSetup data - all 100 accounts available
        List<Account> accounts = [SELECT Id FROM Account];
        System.assertEquals(100, accounts.size());
    }
}
```

## Cleanup via sf CLI

### Generate Cleanup CSV
```bash
# Export IDs of test records
sf data query \
  --query "SELECT Id FROM Account WHERE Name LIKE 'Test%'" \
  --target-org dev \
  --result-format csv \
  > cleanup-accounts.csv

sf data query \
  --query "SELECT Id FROM Contact WHERE Account.Name LIKE 'Test%'" \
  --target-org dev \
  --result-format csv \
  > cleanup-contacts.csv
```

### Execute Bulk Delete
```bash
# Delete children first
sf data delete bulk \
  --file cleanup-contacts.csv \
  --sobject Contact \
  --target-org dev \
  --wait 30

# Then delete parents
sf data delete bulk \
  --file cleanup-accounts.csv \
  --sobject Account \
  --target-org dev \
  --wait 30
```

## Best Practices Summary

| Method | Best For | Limitations |
|--------|----------|-------------|
| Savepoint/Rollback | Synchronous tests | No async, max 5 savepoints |
| Name Pattern | Ad-hoc cleanup | May delete unintended records |
| Time Window | Post-test cleanup | Needs accurate timestamp |
| ID Tracking | Precise cleanup | Requires tracking discipline |
| @testSetup | Unit tests | Only in @isTest classes |
| sf CLI Bulk | Large volumes | External tool required |

## Golden Rules

1. **Always delete children before parents** - Respect relationships
2. **Use specific patterns** - 'Test%', 'BulkTest%' to avoid accidents
3. **Verify before delete** - Query first to see what will be deleted
4. **Test cleanup in sandbox** - Never run unverified cleanup in prod
5. **Track created IDs** - Most reliable cleanup method
