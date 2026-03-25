# Async Testing Patterns

## Key Principle

`Test.stopTest()` forces all async operations to execute synchronously, allowing assertions on their results.

## Batch Apex Testing

### Basic Batch Test

```apex
@isTest
static void shouldProcessAllRecords_WhenBatchExecutes() {
    // Given: Create test data
    List<Account> accounts = TestDataFactory.createAccounts(200, true);
    
    // When: Execute batch
    Test.startTest();
    MyBatchClass batch = new MyBatchClass();
    Id batchId = Database.executeBatch(batch, 200);
    Test.stopTest(); // Forces batch to complete
    
    // Then: Verify results
    List<Account> updated = [SELECT Id, Status__c FROM Account];
    for (Account acc : updated) {
        System.assertEquals('Processed', acc.Status__c, 
            'Batch should update all account statuses');
    }
}
```

### Testing Batch with Failures

```apex
@isTest
static void shouldLogErrors_WhenRecordsFail() {
    // Given: Create mix of valid and invalid records
    List<Account> accounts = TestDataFactory.createAccounts(198, true);
    
    // Create 2 accounts that will fail processing
    List<Account> invalidAccounts = new List<Account>();
    for (Integer i = 0; i < 2; i++) {
        invalidAccounts.add(new Account(
            Name = 'Invalid Account ' + i,
            Invalid_Field__c = 'triggers_validation_error'
        ));
    }
    insert invalidAccounts;
    
    // When
    Test.startTest();
    MyBatchClass batch = new MyBatchClass();
    Database.executeBatch(batch, 50);
    Test.stopTest();
    
    // Then
    List<Error_Log__c> errors = [SELECT Id, Message__c FROM Error_Log__c];
    System.assertEquals(2, errors.size(), 'Should log 2 failed records');
}
```

### Testing Batch Scope

```apex
@isTest
static void shouldRespectBatchSize() {
    // Given
    List<Account> accounts = TestDataFactory.createAccounts(250, true);
    
    Test.startTest();
    MyBatchClass batch = new MyBatchClass();
    Database.executeBatch(batch, 50); // 5 batches of 50
    Test.stopTest();
    
    // Note: In tests, all batches execute but you can verify total processing
    List<Account> processed = [SELECT Id FROM Account WHERE Processed__c = true];
    System.assertEquals(250, processed.size(), 'All records should be processed');
}
```

## Queueable Testing

### Basic Queueable Test

```apex
@isTest
static void shouldCompleteProcessing_WhenQueueableEnqueued() {
    // Given
    Account acc = TestDataFactory.createAccount(true);
    
    // When
    Test.startTest();
    MyQueueableClass queueable = new MyQueueableClass(acc.Id);
    System.enqueueJob(queueable);
    Test.stopTest(); // Forces queueable to complete
    
    // Then
    Account updated = [SELECT Id, Status__c FROM Account WHERE Id = :acc.Id];
    System.assertEquals('Processed', updated.Status__c, 
        'Queueable should update account status');
}
```

### Testing Queueable Chaining

Chained queueables only execute the first job in tests:

```apex
@isTest
static void shouldChainNextJob_WhenMoreRecordsExist() {
    // Given: More records than one queueable can process
    List<Account> accounts = TestDataFactory.createAccounts(500, true);
    
    Test.startTest();
    // First queueable processes batch 1 and chains next
    MyChainedQueueable queueable = new MyChainedQueueable(0, 100);
    System.enqueueJob(queueable);
    Test.stopTest();
    
    // Verify first batch processed
    List<Account> processed = [SELECT Id FROM Account WHERE Processed__c = true];
    System.assertEquals(100, processed.size(), 'First batch should process 100 records');
    
    // Verify chain was enqueued (check AsyncApexJob)
    List<AsyncApexJob> jobs = [
        SELECT Id, Status, JobType 
        FROM AsyncApexJob 
        WHERE ApexClass.Name = 'MyChainedQueueable'
    ];
    System.assert(jobs.size() >= 1, 'Chained job should be enqueued');
}
```

### Testing Queueable with Callouts

```apex
@isTest
static void shouldMakeCallout_WhenQueueableWithCallout() {
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
    System.assertEquals('Synced', updated.External_Status__c, 
        'Should update status after successful callout');
}
```

## Future Method Testing

```apex
@isTest
static void shouldExecuteFutureMethod() {
    // Given
    Account acc = TestDataFactory.createAccount(true);
    
    // When
    Test.startTest();
    MyClass.processFuture(acc.Id); // @future method
    Test.stopTest(); // Forces future to complete
    
    // Then
    Account updated = [SELECT Id, Processed__c FROM Account WHERE Id = :acc.Id];
    System.assertEquals(true, updated.Processed__c, 'Future should process record');
}
```

## Scheduled Apex Testing

### Testing Scheduled Execution

```apex
@isTest
static void shouldExecuteScheduledJob() {
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
    System.assertEquals(50, processed.size(), 'Scheduled job should process records');
}
```

### Testing Schedule Registration

```apex
@isTest
static void shouldScheduleJob() {
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
    System.assertEquals('0 0 6 * * ?', ct.CronExpression, 'CRON should match');
    System.assertEquals('WAITING', ct.State, 'Job should be waiting');
}
```

## Testing Async Limits

```apex
@isTest
static void shouldNotExceedQueueableLimits() {
    // Given: Setup that might enqueue multiple jobs
    List<Account> accounts = TestDataFactory.createAccounts(100, true);
    
    Test.startTest();
    Integer queueablesBefore = Limits.getQueueableJobs();
    
    MyService.processWithQueueables(accounts);
    
    Integer queueablesUsed = Limits.getQueueableJobs() - queueablesBefore;
    Test.stopTest();
    
    // Verify limit not exceeded (50 in synchronous context, 1 in queueable)
    System.assert(queueablesUsed <= 50, 
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
System.assertEquals(100, results.size()); // FAILS - queueable didn't run
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
