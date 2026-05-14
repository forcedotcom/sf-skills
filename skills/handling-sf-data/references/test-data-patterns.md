<!-- Parent: handling-sf-data/SKILL.md -->
# Test Data Patterns Guide

Best practices for creating realistic and effective test data.

## Factory Pattern

### Standard Implementation

```apex
public class TestDataFactory_Account {

    public static List<Account> create(Integer count) {
        return create(count, true);
    }

    public static List<Account> create(Integer count, Boolean doInsert) {
        List<Account> records = new List<Account>();
        for (Integer i = 0; i < count; i++) {
            records.add(buildRecord(i));
        }
        if (doInsert) {
            insert records;
        }
        return records;
    }

    private static Account buildRecord(Integer index) {
        return new Account(
            Name = 'Test Account ' + index,
            Industry = 'Technology'
        );
    }
}
```

### Key Principles

1. **Always create in lists** - Support bulk operations
2. **Provide doInsert parameter** - Caller controls insertion
3. **Track IDs for cleanup** - Return inserted records
4. **Use realistic data** - Valid picklist values

## Record Count Recommendations

| Test Scenario | Record Count | Why |
|---------------|--------------|-----|
| Basic unit test | 1-10 | Quick validation |
| Trigger testing | 201 | Batch boundary |
| Flow testing | 200 | Single transaction |
| Batch Apex | 500+ | Multiple batches |
| Performance | 1000+ | Stress testing |

## Edge Cases to Test

### Null Values
```apex
account.Industry = null;  // Test null handling
```

### Boundary Values
```apex
account.Name = 'A';  // Min length
account.Name = String.valueOf('X').repeat(255);  // Max length
```

### Special Characters
```apex
account.Name = 'Test & "Special" <Characters>';
```

### Date Boundaries
```apex
opp.CloseDate = Date.today();  // Today
opp.CloseDate = Date.today().addDays(-1);  // Yesterday
opp.CloseDate = Date.newInstance(2000, 1, 1);  // Old date
```

## Relationship Testing

### Create Hierarchy
```apex
// Create parent first
List<Account> accounts = TestDataFactory_Account.create(10);

// Create children with parent references
List<Contact> contacts = TestDataFactory_Contact.createForAccounts(
    new List<Id>(new Map<Id, Account>(accounts).keySet()),
    5  // 5 contacts per account
);
```

## Best Practices

1. **Avoid hardcoded IDs** - Use dynamic references
2. **Create all required fields** - Prevent validation errors
3. **Use unique values** - Prevent duplicate errors
4. **Document patterns** - Explain test scenarios
