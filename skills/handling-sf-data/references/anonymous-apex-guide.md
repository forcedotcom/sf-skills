<!-- Parent: handling-sf-data/SKILL.md -->
# Anonymous Apex Guide

Using anonymous Apex for complex data operations.

## When to Use Anonymous Apex

- Complex data setup requiring Apex logic
- Testing triggers with specific data patterns
- One-time data migrations
- Debugging and troubleshooting

## sf CLI Execution

### From File
```bash
sf apex run --file setup-data.apex --target-org myorg
```

### Interactive
```bash
sf apex run --target-org myorg
# Then type Apex code and press Ctrl+D
```

## Common Patterns

### Bulk Data Creation
```apex
List<Account> accounts = new List<Account>();
for (Integer i = 0; i < 500; i++) {
    accounts.add(new Account(
        Name = 'Test Account ' + i,
        Industry = 'Technology'
    ));
}
insert accounts;
System.debug('Created ' + accounts.size() + ' accounts');
```

### Data Transformation
```apex
List<Account> accounts = [
    SELECT Id, Name, Industry
    FROM Account
    WHERE Name LIKE 'Old%'
];

for (Account acc : accounts) {
    acc.Name = acc.Name.replace('Old', 'New');
}

update accounts;
```

### Testing Trigger Logic
```apex
// Setup test data
Account acc = new Account(Name = 'Trigger Test');
insert acc;

// Force trigger to fire
acc.Industry = 'Technology';
update acc;

// Verify results
acc = [SELECT Id, Field__c FROM Account WHERE Id = :acc.Id];
System.debug('Result: ' + acc.Field__c);
```

## Error Handling

```apex
try {
    insert accounts;
} catch (DmlException e) {
    System.debug('Error: ' + e.getMessage());
    for (Integer i = 0; i < e.getNumDml(); i++) {
        System.debug('Row ' + e.getDmlIndex(i) + ': ' + e.getDmlMessage(i));
    }
}
```

## Limits in Anonymous Apex

| Limit | Value |
|-------|-------|
| SOQL Queries | 100 |
| DML Rows | 10,000 |
| CPU Time | 10,000 ms |
| Heap Size | 6 MB |

## Best Practices

1. **Test in sandbox first** - Validate before production
2. **Add debug statements** - Track progress
3. **Handle errors gracefully** - Use try/catch
4. **Keep scripts idempotent** - Safe to re-run
