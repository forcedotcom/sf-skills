# Assertion Patterns

## Assertion Methods

| Method | Use Case |
|--------|----------|
| `Assert.areEqual(expected, actual, msg)` | Exact equality |
| `Assert.areNotEqual(expected, actual, msg)` | Value should differ |
| `Assert.isTrue(condition, msg)` | Boolean condition |
| `Assert.isFalse(condition, msg)` | Negated boolean condition |
| `Assert.fail(msg)` | Force failure (e.g., expected exception not thrown) |
| `Assert.isNotNull(value, msg)` | Non-null check |
| `Assert.isNull(value, msg)` | Null check |

**Always include the message parameter** — makes test failures actionable.

## Good vs Bad Assertions

### Bad: No message, tests coverage not behavior

```apex
Assert.isTrue(result); // no message
Assert.isTrue(accounts.size() > 0); // vague — use areEqual with exact count
```

### Good: Descriptive message, tests specific behavior

```apex
Assert.isTrue(result, 'Service should return true for valid input');
Assert.areEqual(200, accounts.size(), 'All 200 accounts should be processed');
```

## Common Assertion Patterns

### Collection Size

```apex
Assert.areEqual(200, results.size(), 'Should process all 200 records');
Assert.isTrue(results.isEmpty(), 'No results expected for invalid input');
Assert.isFalse(results.isEmpty(), 'Results should not be empty');
```

### Field Values

```apex
Assert.areEqual('Processed', acc.Status__c, 'Account status should be updated to Processed');

for (Account acc : updatedAccounts) {
    Assert.areEqual('Active', acc.Status__c,
        'Account ' + acc.Name + ' should have Active status');
}
```

### Exception Testing

```apex
@isTest
static void shouldThrowException_WhenInputInvalid() {
    Test.startTest();
    try {
        MyService.process(null);
        Assert.fail('Expected MyCustomException for null input');
    } catch (MyCustomException e) {
        Assert.isTrue(e.getMessage().contains('cannot be null'),
            'Exception message should mention null input');
    }
    Test.stopTest();
}
```

### DML Results

```apex
// Insert success
Database.SaveResult[] results = Database.insert(accounts, false);
for (Database.SaveResult sr : results) {
    Assert.isTrue(sr.isSuccess(), 'Insert should succeed: ' + sr.getErrors());
}

Database.SaveResult sr = Database.insert(invalidAccount, false);
Assert.isFalse(sr.isSuccess(), 'Insert should fail for invalid data');
Assert.isTrue(sr.getErrors()[0].getMessage().contains('REQUIRED_FIELD_MISSING'),
    'Error should indicate missing required field');
```

### Null Checks

```apex
Assert.isNull(result.ErrorMessage__c, 'No error expected for valid input');
Assert.isNotNull(result.Id, 'Record should have been inserted');
```

### Date/DateTime

```apex
Assert.areEqual(Date.today(), record.CreatedDate__c, 'Should be created today');
Assert.isTrue(record.DueDate__c >= Date.today(), 'Due date should be in the future');
```

## Anti-Patterns

| Anti-Pattern | Fix |
|---|---|
| `Assert.isTrue(results.size() > 0)` | Use `Assert.areEqual(expectedCount, results.size(), ...)` |
| `Assert.isTrue(results.size() >= expected)` | Compute exact expected count, use `Assert.areEqual` |
| Testing implementation not behavior | Assert on observable outcomes (field values, record counts) |
| Missing negative test assertions | Verify the actual outcome, not just that no exception occurred |
| `Assert.isTrue(count != 0)` | Use `Assert.areEqual` with deterministic value from test data |
