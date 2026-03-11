# Assertion Patterns

## Assertion Methods

The `System.Assert` class provides methods to assert various conditions in test methods. All methods support an optional message parameter for better error reporting.

| Method | Use Case |
|--------|----------|
| `System.Assert.areEqual(expected, actual, msg)` | Exact equality |
| `System.Assert.areNotEqual(notExpected, actual, msg)` | Value should differ |
| `System.Assert.isTrue(condition, msg)` | Boolean condition is true |
| `System.Assert.isFalse(condition, msg)` | Boolean condition is false |
| `System.Assert.isNull(value, msg)` | Value is null |
| `System.Assert.isNotNull(value, msg)` | Value is not null |
| `System.Assert.isInstanceOfType(instance, expectedType, msg)` | Instance is of specified type |
| `System.Assert.isNotInstanceOfType(instance, notExpectedType, msg)` | Instance is not of specified type |
| `System.Assert.fail(msg)` | Explicitly fail the test |

**Always include the message parameter** - Makes test failures meaningful and easier to debug.

**Note:** Assertion failures are fatal errors that halt code execution. You cannot catch assertion failures using try/catch blocks, even though they're logged as exceptions.


**Note:** Call `startTest()` and `stopTest()` only once per test method. Wrap only the code under test between these calls, not setup or verification code.

## Good vs Bad Assertions

### ❌ Bad: No message, tests coverage not behavior

```apex
System.Assert.areEqual(true, result);
System.Assert.isTrue(accounts.size() > 0);
```

### ✅ Good: Descriptive message, tests specific behavior

```apex
System.Assert.areEqual(true, result, 'Service should return true for valid input');
System.Assert.areEqual(200, accounts.size(), 'All 200 accounts should be processed');
```

## Common Assertion Patterns

### Collection Size

```apex
// Exact count
System.Assert.areEqual(200, results.size(), 'Should process all 200 records');

// Not empty
System.Assert.isFalse(results.isEmpty(), 'Results should not be empty');

// Empty
System.Assert.isTrue(results.isEmpty(), 'No results expected for invalid input');
```

### Field Values

```apex
// Single record
System.Assert.areEqual('Processed', acc.Status__c, 'Account status should be updated to Processed');

// All records in collection
for (Account acc : updatedAccounts) {
    System.Assert.areEqual('Active', acc.Status__c, 
        'Account ' + acc.Name + ' should have Active status');
}
```

### Exception Testing

```apex
@IsTest
private static void shouldThrowException_WhenInputInvalid() {
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
    
    System.Assert.isTrue(exceptionThrown, 'MyCustomException should be thrown for null input');
    System.Assert.isTrue(exceptionMessage.contains('cannot be null'), 
        'Exception message should mention null input');
}
```

### DML Results

```apex
// Insert success
Database.SaveResult[] results = Database.insert(accounts, false);
for (Database.SaveResult sr : results) {
    System.Assert.isTrue(sr.isSuccess(), 'Insert should succeed: ' + sr.getErrors());
}

// Expected failures
Database.SaveResult sr = Database.insert(invalidAccount, false);
System.Assert.isFalse(sr.isSuccess(), 'Insert should fail for invalid data');
System.Assert.isTrue(sr.getErrors()[0].getMessage().contains('REQUIRED_FIELD_MISSING'),
    'Error should indicate missing required field');
```

### Comparing Objects

```apex
// Compare specific fields, not entire objects
System.Assert.areEqual(expected.Name, actual.Name, 'Names should match');
System.Assert.areEqual(expected.Status__c, actual.Status__c, 'Status should match');

// Or use JSON for deep comparison (use sparingly)
System.Assert.areEqual(
    JSON.serialize(expected), 
    JSON.serialize(actual), 
    'Objects should be identical'
);
```

### Date/DateTime Assertions

```apex
// Exact date
System.Assert.areEqual(Date.today(), record.CreatedDate__c, 'Should be created today');

// Date within range
System.Assert.isTrue(record.DueDate__c >= Date.today(), 'Due date should be in the future');
System.Assert.isTrue(record.DueDate__c <= Date.today().addDays(30), 
    'Due date should be within 30 days');
```

### Null Checks

```apex
// Should be null
System.Assert.isNull(result.ErrorMessage__c, 'No error expected for valid input');

// Should not be null
System.Assert.isNotNull(result.Id, 'Record should have been inserted');
```

### Type Checking

```apex
// Verify instance is of expected type
Object result = MyService.processData();
System.Assert.isInstanceOfType(result, MyCustomClass.class, 
    'Result should be an instance of MyCustomClass');

// Verify instance is not of a specific type
Object handler = HandlerFactory.create('Account');
System.Assert.isNotInstanceOfType(handler, ContactHandler.class, 
    'Account handler should not be a ContactHandler');
```

### Explicit Test Failures

```apex
// Use Assert.fail() when an exception should have been thrown but wasn't
@IsTest
private static void shouldThrowException_WhenInputInvalid() {
    try {
        MyService.process(null);
        System.Assert.fail('Expected MyCustomException to be thrown for null input');
    } catch (MyCustomException e) {
        // Exception was thrown as expected, test passes
        System.Assert.isTrue(e.getMessage().contains('cannot be null'), 
            'Exception message should mention null input');
    }
}
```

## Anti-Patterns to Avoid

### ❌ Testing implementation, not behavior

```apex
// Bad: Testing that a specific method was called
System.Assert.isTrue(MyClass.methodWasCalled, 'Method should be called');

// Good: Testing the observable outcome
System.Assert.areEqual('Expected Value', record.Field__c, 'Field should be updated');
```

### ❌ Overly generic assertions

```apex
// Bad: Passes for any non-empty result
System.Assert.isTrue(results.size() > 0);

// Good: Verifies exact expected count
System.Assert.areEqual(200, results.size(), 'All 200 records should be returned');
```

### ❌ Missing negative test assertions

```apex
// Bad: Only tests that no exception occurred
MyService.process(data); // Test passes if no exception

// Good: Verifies the actual outcome
Result r = MyService.process(data);
System.Assert.areEqual('Success', r.status, 'Processing should succeed');
System.Assert.areEqual(0, r.errorCount, 'No errors should occur');
```