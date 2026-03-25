# Test Patterns by Component Type

Quick reference for choosing the right test pattern and asset template for each component type.

## Pattern Selection

| Component Under Test | Template | Key Scenarios |
|----------------------|----------|---------------|
| Service / Controller | [assets/basic-test.cls](../assets/basic-test.cls) | Valid input, null/invalid input, empty collection edge case |
| Trigger / Bulk DML | [assets/bulk-test.cls](../assets/bulk-test.cls) | 251-record insert/update/delete, governor limit verification |
| HTTP Callout | [assets/mock-callout-test.cls](../assets/mock-callout-test.cls) | Success response, error codes (400/401/500), timeout |
| DML-heavy service | [assets/dml-mock.cls](../assets/dml-mock.cls) | Fast unit tests via DML injection, no database |
| Interface mocking | [assets/stub-provider-example.cls](../assets/stub-provider-example.cls) | Dynamic behavior, method call tracking |
| Test data setup | [assets/test-data-factory.cls](../assets/test-data-factory.cls) | Consistent record creation across all tests |

## Naming Convention

Use the `should[ExpectedBehavior]_When[Condition]` pattern for all test methods:

```apex
@IsTest static void shouldCreateContact_WhenAccountIsActive() { }
@IsTest static void shouldThrowException_WhenEmailIsInvalid() { }
@IsTest static void shouldProcessAllRecords_WhenBulkInsert() { }
@IsTest static void shouldReturnError_WhenCalloutTimesOut() { }
```

## Test Structure (Given / When / Then)

Every test method follows this structure:

```apex
@IsTest
static void shouldUpdateStatus_WhenValidInput() {
    // Given
    List<Account> accounts = [SELECT Id FROM Account];

    // When
    Test.startTest();
    MyService.processAccounts(accounts);
    Test.stopTest();

    // Then
    List<Account> updated = [SELECT Status__c FROM Account];
    Assert.areEqual('Processed', updated[0].Status__c, 'Status should be updated');
}
```

## Component-Specific Guidance

### Triggers
- Always test at 251 records (crosses 200-record batch boundary)
- Test insert, update, and delete events separately
- Verify recursion guards and field-change detection
- Use `assertGovernorLimitsNotExceeded()` helper (see bulk-test.cls)
- **Duplicate Rules** — bulk inserts of 251+ records frequently trigger `DUPLICATES_DETECTED` when field values collide across records. Ensure `TestDataFactory` appends the loop index to all matchable fields (Name, Email, Phone, Company). If the org uses fuzzy matching rules, use `Database.insert()` with `DuplicateRuleHeader.allowSave = true`. See [test-data-factory.md](test-data-factory.md)

### Batch Apex
- **Single `execute()` in tests** — only one `execute()` invocation runs; set `batchSize >= testRecordCount` so all test data is processed
- Verify `start` query returns expected scope
- Test `finish` for cleanup and notifications
- Test batch chaining in **separate test methods** — `finish()` calling `Database.executeBatch()` throws `UnexpectedException` in tests
- For `Database.Stateful` batches, remember accumulators reflect only the single `execute()` invocation
- See [async-testing.md](async-testing.md) for constraints, examples, and pitfalls

### Queueable / Future
- `Test.stopTest()` forces synchronous execution
- Only the first chained queueable runs in tests
- Mock callouts before `Test.startTest()` if the job makes HTTP requests
- See [async-testing.md](async-testing.md) for chaining and callout patterns

### Callouts
- Salesforce requires `HttpCalloutMock` -- real HTTP is blocked in tests
- Test success, error codes, and timeout scenarios
- For complex response bodies, use `StaticResourceCalloutMock`
- See [mocking-patterns.md](mocking-patterns.md) for multi-endpoint and validation mocks

### Scheduled Apex
- Verify CRON registration with `CronTrigger` query
- Test execution by calling `execute(null)` directly
- See [async-testing.md](async-testing.md) for schedule testing patterns
