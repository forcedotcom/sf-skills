# Assertion Patterns

## Assertion Methods

| Method | Use Case |
|--------|----------|
| `System.assertEquals(expected, actual, msg)` | Exact equality |
| `System.assertNotEquals(expected, actual, msg)` | Value should differ |
| `System.assert(condition, msg)` | Boolean condition |

**Always include the third parameter (message)** - Makes test failures meaningful.

## Good vs Bad Assertions

### ❌ Bad: No message, tests coverage not behavior

```apex
System.assertEquals(true, result);
System.assert(accounts.size() > 0);
```

### ✅ Good: Descriptive message, tests specific behavior

```apex
System.assertEquals(true, result, 'Service should return true for valid input');
System.assertEquals(200, accounts.size(), 'All 200 accounts should be processed');
```

## Common Assertion Patterns

### Collection Size

```apex
// Exact count
System.assertEquals(200, results.size(), 'Should process all 200 records');

// Not empty
System.assert(!results.isEmpty(), 'Results should not be empty');

// Empty
System.assert(results.isEmpty(), 'No results expected for invalid input');
```

### Field Values

```apex
// Single record
System.assertEquals('Processed', acc.Status__c, 'Account status should be updated to Processed');

// All records in collection
for (Account acc : updatedAccounts) {
    System.assertEquals('Active', acc.Status__c, 
        'Account ' + acc.Name + ' should have Active status');
}
```

### Exception Testing

```apex
@isTest
static void shouldThrowException_WhenInputInvalid() {
    Boolean exceptionThrown = false;
    String exceptionMessage = '';
    
    Test.startTest();
    try {
        MyService.process(null);
    } catch (MyCustomException e) {
        exceptionThrown = true;
        exceptionMessage = e.getMessage();
    }
    Test.stopTest();
    
    System.assert(exceptionThrown, 'MyCustomException should be thrown for null input');
    System.assert(exceptionMessage.contains('cannot be null'), 
        'Exception message should mention null input');
}
```

### DML Results

```apex
// Insert success
Database.SaveResult[] results = Database.insert(accounts, false);
for (Database.SaveResult sr : results) {
    System.assert(sr.isSuccess(), 'Insert should succeed: ' + sr.getErrors());
}

// Expected failures
Database.SaveResult sr = Database.insert(invalidAccount, false);
System.assert(!sr.isSuccess(), 'Insert should fail for invalid data');
System.assert(sr.getErrors()[0].getMessage().contains('REQUIRED_FIELD_MISSING'),
    'Error should indicate missing required field');
```

### Comparing Objects

```apex
// Compare specific fields, not entire objects
System.assertEquals(expected.Name, actual.Name, 'Names should match');
System.assertEquals(expected.Status__c, actual.Status__c, 'Status should match');

// Or use JSON for deep comparison (use sparingly)
System.assertEquals(
    JSON.serialize(expected), 
    JSON.serialize(actual), 
    'Objects should be identical'
);
```

### Date/DateTime Assertions

```apex
// Exact date
System.assertEquals(Date.today(), record.CreatedDate__c, 'Should be created today');

// Date within range
System.assert(record.DueDate__c >= Date.today(), 'Due date should be in the future');
System.assert(record.DueDate__c <= Date.today().addDays(30), 
    'Due date should be within 30 days');
```

### Null Checks

```apex
// Should be null
System.assertEquals(null, result.ErrorMessage__c, 'No error expected for valid input');

// Should not be null
System.assertNotEquals(null, result.Id, 'Record should have been inserted');
```

## Anti-Patterns to Avoid

### ❌ Testing implementation, not behavior

```apex
// Bad: Testing that a specific method was called
System.assert(MyClass.methodWasCalled, 'Method should be called');

// Good: Testing the observable outcome
System.assertEquals('Expected Value', record.Field__c, 'Field should be updated');
```

### ❌ Overly generic assertions

```apex
// Bad: Passes for any non-empty result
System.assert(results.size() > 0);

// Good: Verifies exact expected count
System.assertEquals(200, results.size(), 'All 200 records should be returned');
```

### ❌ Missing negative test assertions

```apex
// Bad: Only tests that no exception occurred
MyService.process(data); // Test passes if no exception

// Good: Verifies the actual outcome
Result r = MyService.process(data);
System.assertEquals('Success', r.status, 'Processing should succeed');
System.assertEquals(0, r.errorCount, 'No errors should occur');
```
