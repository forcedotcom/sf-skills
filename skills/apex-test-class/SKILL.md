---
name: apex-test-class
description: Apex test class generation with TestDataFactory patterns, bulk testing (200+ records), mocking strategies for callouts and async operations, and assertion best practices. Use when creating new Apex test classes, improving test coverage, refactoring existing tests, or implementing proper testing patterns for triggers, services, controllers, batch jobs, queueables, and integrations.
---

# Apex Test Class Skill

## Core Principles

1. **Bulkify tests** - Always test with 200+ records to catch governor limit issues
2. **Isolate test data** - Use `@TestSetup` and TestDataFactory; never rely on org data
3. **Assert meaningfully** - Test behavior, not just coverage; include failure messages
4. **Mock external dependencies** - Use `HttpCalloutMock`, `Test.setMock()` for integrations
5. **Test negative paths** - Validate error handling, not just happy paths

## Test Class Structure

```apex
@IsTest
private class MyServiceTest {

    @TestSetup
    static void setupTestData() {
        // Create shared test data using TestDataFactory
        List<Account> accounts = TestDataFactory.createAccounts(200, true);
    }

    @IsTest
    static void shouldPerformExpectedBehavior_WhenValidInput() {
        // Given: Setup specific test state
        List<Account> accounts = [SELECT Id, Name FROM Account];
        
        // When: Execute the code under test
        Test.startTest();
        MyService.processAccounts(accounts);
        Test.stopTest();
        
        // Then: Assert expected outcomes
        List<Account> updated = [SELECT Id, Status__c FROM Account];
        System.Assert.areEqual(200, updated.size(), 'All accounts should be processed');
        for (Account acc : updated) {
            System.Assert.areEqual('Processed', acc.Status__c, 'Status should be updated');
        }
    }

    @IsTest
    static void shouldThrowException_WhenInvalidInput() {
        // Given
        List<Account> emptyList = new List<Account>();
        
        // When/Then
        Test.startTest();
        try {
            MyService.processAccounts(emptyList);
            System.Assert.fail('Expected MyCustomException to be thrown');
        } catch (MyCustomException e) {
            System.Assert.isTrue(e.getMessage().contains('cannot be empty'), 
                'Exception message should indicate empty input');
        }
        Test.stopTest();
    }
}
```

## Naming Convention

Use descriptive method names: `should[ExpectedBehavior]_When[Condition]`

Examples:
- `shouldCreateContact_WhenAccountIsActive`
- `shouldThrowException_WhenEmailIsInvalid`
- `shouldSendNotification_WhenOpportunityClosedWon`
- `shouldBypassTrigger_WhenRunningAsBatch`

## Test.startTest() / Test.stopTest()

Always wrap the code under test:
- Resets governor limits for accurate limit testing
- Executes async operations synchronously (queueables, batch, future)
- Fires scheduled jobs immediately

## Reference Files

Detailed patterns for specific scenarios:

- **[references/test-data-factory.md](references/test-data-factory.md)** - TestDataFactory class patterns and field defaults
- **[references/assertion-patterns.md](references/assertion-patterns.md)** - Assertion best practices and common pitfalls
- **[references/mocking-patterns.md](references/mocking-patterns.md)** - HttpCalloutMock, Test.setMock(), stubbing
- **[references/async-testing.md](references/async-testing.md)** - Batch, Queueable, Future, Scheduled job testing

## Quick Reference: What to Test

| Component | Key Test Scenarios |
|-----------|-------------------|
| Trigger | Bulk insert/update/delete, recursion, field changes |
| Service | Valid/invalid inputs, bulk operations, exceptions |
| Controller | Page load, action methods, view state |
| Batch | Start/execute/finish, chunking, error records |
| Queueable | Chaining, bulkification, error handling |
| Callout | Success response, error response, timeout |
| Scheduled | Execution, CRON validation |