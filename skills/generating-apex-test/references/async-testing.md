# Async Testing Patterns

## Key Principle

`Test.stopTest()` forces all async operations to execute synchronously, allowing assertions on their results.

## Batch Apex Testing

### Critical Constraint — Single Execute in Tests

In test context, Salesforce calls the batch `execute()` method **only once**, processing at most `batchSize` records. The `start()` and `finish()` methods still run normally, but only one chunk of data passes through `execute()`. This has three consequences:

1. **Match record count to batch size** — create `N` test records and call `Database.executeBatch(batch, N)` so all records are processed in the single invocation. If you create more records than the batch size, the excess records are silently skipped.
2. **One `executeBatch` call per test method** — calling `Database.executeBatch()` more than once between `Test.startTest()` and `Test.stopTest()` throws `System.UnexpectedException`. This includes chained batches triggered from the `finish()` method.
3. **`Database.Stateful` reflects one chunk** — stateful accumulators only capture values from the single `execute()` invocation.

### Basic Batch Test

```apex
@IsTest
private static void shouldProcessAllRecords_WhenBatchExecutes() {
    // Given — record count MUST equal batch size
    List<Account> accounts = TestDataFactory.createAccounts(200, true);
    
    // When — batch size matches record count so all records are processed
    Test.startTest();
    MyBatchClass batch = new MyBatchClass();
    Database.executeBatch(batch, 200);
    Test.stopTest();
    
    // Then
    List<Account> updated = [SELECT Id, Status__c FROM Account];
    Assert.areEqual(200, updated.size(), 'All 200 accounts should be processed');
    for (Account acc : updated) {
        Assert.areEqual('Processed', acc.Status__c, 
            'Batch should update all account statuses');
    }
}
```

### Testing Batch with Failures

```apex
@IsTest
private static void shouldLogErrors_WhenRecordsFail() {
    // Given — total records (valid + invalid) must fit within batch size
    List<Account> accounts = TestDataFactory.createAccounts(198, true);
    
    List<Account> invalidAccounts = new List<Account>();
    for (Integer i = 0; i < 2; i++) {
        invalidAccounts.add(new Account(
            Name = 'Invalid Account ' + i,
            Invalid_Field__c = 'triggers_validation_error'
        ));
    }
    insert invalidAccounts;
    
    // When — batch size = 200 to cover all 200 records in single execute()
    Test.startTest();
    MyBatchClass batch = new MyBatchClass();
    Database.executeBatch(batch, 200);
    Test.stopTest();
    
    // Then
    List<Error_Log__c> errors = [SELECT Id, Message__c FROM Error_Log__c];
    Assert.areEqual(2, errors.size(), 'Should log 2 failed records');
}
```

### Testing Database.Stateful Tracking

```apex
@IsTest
private static void shouldTrackProcessedCount_WhenStatefulBatch() {
    // Given — use a count that fits in one execute()
    List<Account> accounts = TestDataFactory.createAccounts(150, true);
    
    // When
    Test.startTest();
    MyStatefulBatch batch = new MyStatefulBatch();
    Database.executeBatch(batch, 150);
    Test.stopTest();
    
    // Then — query finish-method output or assert on batch instance
    // (stateful values reflect only the single execute() invocation)
    List<Batch_Log__c> logs = [SELECT Records_Processed__c FROM Batch_Log__c];
    Assert.areEqual(1, logs.size(), 'Finish should create a log record');
    Assert.areEqual(150, logs[0].Records_Processed__c,
        'Should track all 150 processed records');
}
```

### Testing Batch Chaining

A batch whose `finish()` method calls `Database.executeBatch()` will throw `System.UnexpectedException` in tests. Test each batch in the chain **independently** in separate test methods.

```apex
@IsTest
private static void shouldCompleteFirstBatch_WhenChainedBatch() {
    // Given
    List<Account> accounts = TestDataFactory.createAccounts(100, true);
    
    // When — test only the first batch; suppress chaining in test context
    Test.startTest();
    MyChainedBatch batch = new MyChainedBatch();
    Database.executeBatch(batch, 100);
    Test.stopTest();
    
    // Then — verify first batch's work completed
    List<Account> processed = [SELECT Id FROM Account WHERE Processed__c = true];
    Assert.areEqual(100, processed.size(), 'First batch should process all records');
}

@IsTest
private static void shouldCompleteSecondBatch_WhenRunIndependently() {
    // Given — setup data as if first batch already ran
    List<Account> accounts = TestDataFactory.createAccounts(100, true);
    for (Account acc : accounts) {
        acc.Processed__c = true;
        acc.NeedsFollowUp__c = true;
    }
    update accounts;
    
    // When — test second batch in isolation
    Test.startTest();
    MyFollowUpBatch batch = new MyFollowUpBatch();
    Database.executeBatch(batch, 100);
    Test.stopTest();
    
    // Then
    List<Account> followedUp = [SELECT Id FROM Account WHERE FollowUpDone__c = true];
    Assert.areEqual(100, followedUp.size(), 'Second batch should process all records');
}
```

## Queueable Testing

### Basic Queueable Test

```apex
@IsTest
private static void shouldCompleteProcessing_WhenQueueableEnqueued() {
    // Given
    Account acc = TestDataFactory.createAccount(true);
    
    // When
    Test.startTest();
    MyQueueableClass queueable = new MyQueueableClass(acc.Id);
    System.enqueueJob(queueable);
    Test.stopTest(); // Forces queueable to complete
    
    // Then
    Account updated = [SELECT Id, Status__c FROM Account WHERE Id = :acc.Id];
    Assert.areEqual('Processed', updated.Status__c, 
        'Queueable should update account status');
}
```

### Testing Queueable Chaining

Chained queueables only execute the first job in tests:

```apex
@IsTest
private static void shouldChainNextJob_WhenMoreRecordsExist() {
    // Given: More records than one queueable can process
    List<Account> accounts = TestDataFactory.createAccounts(500, true);
    
    Test.startTest();
    // First queueable processes batch 1 and chains next
    MyChainedQueueable queueable = new MyChainedQueueable(0, 100);
    System.enqueueJob(queueable);
    Test.stopTest();
    
    // Verify first batch processed
    List<Account> processed = [SELECT Id FROM Account WHERE Processed__c = true];
    Assert.areEqual(100, processed.size(), 'First batch should process 100 records');
    
    // Verify chain was enqueued (check AsyncApexJob)
    List<AsyncApexJob> jobs = [
        SELECT Id, Status, JobType 
        FROM AsyncApexJob 
        WHERE ApexClass.Name = 'MyChainedQueueable'
    ];
    Assert.isTrue(jobs.size() >= 1, 'Chained job should be enqueued');
}
```

### Testing Queueable with Callouts

```apex
@IsTest
private static void shouldMakeCallout_WhenQueueableWithCallout() {
    // Given
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse(200, '{"status":"ok"}'));
    Account acc = TestDataFactory.createAccount(true);
    
    // When
    Test.startTest();
    MyQueueableWithCallout queueable = new MyQueueableWithCallout(acc.Id);
    System.enqueueJob(queueable);
    Test.stopTest();
    
    // Then
    Account updated = [SELECT Id, External_Status__c FROM Account WHERE Id = :acc.Id];
    Assert.areEqual('Synced', updated.External_Status__c, 
        'Should update status after successful callout');
}
```

## Future Method Testing

```apex
@IsTest
private static void shouldExecuteFutureMethod() {
    // Given
    Account acc = TestDataFactory.createAccount(true);
    
    // When
    Test.startTest();
    MyClass.processFuture(acc.Id); // @future method
    Test.stopTest(); // Forces future to complete
    
    // Then
    Account updated = [SELECT Id, Processed__c FROM Account WHERE Id = :acc.Id];
    Assert.areEqual(true, updated.Processed__c, 'Future should process record');
}
```

## Scheduled Apex Testing

### Testing Scheduled Execution

```apex
@IsTest
private static void shouldExecuteScheduledJob() {
    // Given
    List<Account> accounts = TestDataFactory.createAccounts(50, true);
    
    // When
    Test.startTest();
    String cronExp = '0 0 0 1 1 ? 2099'; // Arbitrary future time
    String jobId = System.schedule('Test Job', cronExp, new MyScheduledClass());
    
    // Execute the scheduled job immediately
    MyScheduledClass scheduled = new MyScheduledClass();
    scheduled.execute(null); // Pass null SchedulableContext in tests
    Test.stopTest();
    
    // Then
    List<Account> processed = [SELECT Id FROM Account WHERE Processed__c = true];
    Assert.areEqual(50, processed.size(), 'Scheduled job should process records');
}
```

### Testing Schedule Registration

```apex
@IsTest
private static void shouldScheduleJob() {
    Test.startTest();
    String cronExp = '0 0 6 * * ?'; // Daily at 6 AM
    String jobId = System.schedule('Daily Processing', cronExp, new MyScheduledClass());
    Test.stopTest();
    
    // Verify job is scheduled
    CronTrigger ct = [
        SELECT Id, CronExpression, State 
        FROM CronTrigger 
        WHERE Id = :jobId
    ];
    Assert.areEqual('0 0 6 * * ?', ct.CronExpression, 'CRON should match');
    Assert.areEqual('WAITING', ct.State, 'Job should be waiting');
}
```

## Testing Async Limits

```apex
@IsTest
private static void shouldNotExceedQueueableLimits() {
    // Given: Setup that might enqueue multiple jobs
    List<Account> accounts = TestDataFactory.createAccounts(100, true);
    
    Test.startTest();
    Integer queueablesBefore = Limits.getQueueableJobs();
    
    MyService.processWithQueueables(accounts);
    
    Integer queueablesUsed = Limits.getQueueableJobs() - queueablesBefore;
    Test.stopTest();
    
    // Verify limit not exceeded (50 in synchronous context, 1 in queueable)
    Assert.isTrue(queueablesUsed <= 50, 
        'Should not exceed queueable limit. Used: ' + queueablesUsed);
}
```

## Common Pitfalls

### ❌ Forgetting Test.stopTest()

```apex
// Bad: Async never executes
Test.startTest();
System.enqueueJob(new MyQueueable());
// Missing Test.stopTest()!

List<Account> results = [SELECT Id FROM Account WHERE Processed__c = true];
Assert.areEqual(100, results.size()); // FAILS - queueable didn't run
```

### ❌ Testing chained jobs without understanding limits

```apex
// Only the FIRST chained queueable runs in tests
// Design tests to verify:
// 1. First job completes correctly
// 2. Chain is properly enqueued (check AsyncApexJob)
// 3. Each job works independently
```

### ❌ Not mocking callouts in async

```apex
// Async with callouts MUST have mock set BEFORE Test.startTest()
Test.setMock(HttpCalloutMock.class, new MockResponse()); // Before startTest!
Test.startTest();
System.enqueueJob(new QueueableWithCallout());
Test.stopTest();
```

### ❌ Duplicate Rule violations on bulk insert

```apex
// Bad: identical or near-identical field values trigger DUPLICATES_DETECTED at row 200+
List<Account> accounts = new List<Account>();
for (Integer i = 0; i < 251; i++) {
    accounts.add(new Account(Name = 'Test Account')); // same Name on all records
}
insert accounts; // FAILS: DUPLICATES_DETECTED

// Good: unique values per record via TestDataFactory
List<Account> accounts = TestDataFactory.createAccounts(251);
insert accounts;

// Good: bypass duplicate rules when fuzzy matching is active
Database.DMLOptions dml = new Database.DMLOptions();
dml.DuplicateRuleHeader.allowSave = true;
Database.insert(accounts, dml);
```