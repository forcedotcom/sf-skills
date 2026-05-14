<!-- Parent: handling-sf-data/SKILL.md -->
# Cleanup and Rollback Guide

Strategies for test data isolation and cleanup.

## Savepoint/Rollback Pattern

Best for synchronous test isolation.

```apex
// Create savepoint BEFORE any DML
Savepoint sp = Database.setSavepoint();

try {
    // Create test data
    List<Account> accounts = TestDataFactory_Account.create(100);

    // Run your tests
    Test.startTest();
    MyClass.processAccounts(accounts);
    Test.stopTest();

    // Assert results
    System.assertEquals(expected, actual);

} finally {
    // Always rollback
    Database.rollback(sp);
}
```

**Limitations:**
- Does not roll back async operations
- Maximum 5 savepoints per transaction

## Cleanup by Name Pattern

```apex
String pattern = 'Test%';

DELETE [SELECT Id FROM Opportunity WHERE Name LIKE :pattern];
DELETE [SELECT Id FROM Contact WHERE LastName LIKE :pattern];
DELETE [SELECT Id FROM Account WHERE Name LIKE :pattern];
```

**Order matters:** Delete children before parents.

## Cleanup by Date

```apex
DateTime startTime = DateTime.now().addHours(-1);

DELETE [
    SELECT Id FROM Account
    WHERE CreatedDate >= :startTime
    AND Name LIKE 'Test%'
];
```

## Cleanup via sf CLI

```bash
# Export IDs to delete
sf data query \
  --query "SELECT Id FROM Account WHERE Name LIKE 'Test%'" \
  --target-org myorg \
  --result-format csv \
  > delete.csv

# Bulk delete
sf data delete bulk \
  --file delete.csv \
  --sobject Account \
  --target-org myorg \
  --wait 30
```

## Best Practices

1. **Track created IDs** - Store in Set<Id>
2. **Delete in order** - Children first, parents last
3. **Use test prefixes** - 'Test', 'BulkTest'
4. **Preview before delete** - Verify records first
5. **Use @isTest** - Auto-rollback in tests
