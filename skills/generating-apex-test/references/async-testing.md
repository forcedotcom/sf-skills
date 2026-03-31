# Async Testing Patterns

## Key Principle

`Test.stopTest()` forces all async operations to execute synchronously, allowing assertions on their results.

## Batch Apex Testing

### Basic Batch Test

**Critical:** In test context only one `execute()` invocation runs, so always set `batchSize >= testRecordCount` (e.g., `Database.executeBatch(batch, 200)` with 200 records). Never create more records than the batch size.

```apex
@isTest
static void shouldProcessAllRecords_WhenBatchExecutes() {
    List<Account> accounts = TestDataFactory.createAccounts(200, true);

    Test.startTest();
    MyBatchClass batch = new MyBatchClass();
    Id batchId = Database.executeBatch(batch, 200);
    Test.stopTest();

    List<Account> updated = [SELECT Id, Status__c FROM Account];
    for (Account acc : updated) {
        Assert.areEqual('Processed', acc.Status__c,
            'Batch should update all account statuses');
    }
}
```

### Batch with Failures

```apex
@isTest
static void shouldLogErrors_WhenRecordsFail() {
    List<Account> accounts = TestDataFactory.createAccounts(198, true);

    List<Account> invalidAccounts = new List<Account>();
    for (Integer i = 0; i < 2; i++) {
        invalidAccounts.add(new Account(
            Name = 'Invalid Account ' + i,
            Invalid_Field__c = 'triggers_validation_error'
        ));
    }
    insert invalidAccounts;

    Test.startTest();
    MyBatchClass batch = new MyBatchClass();
    Database.executeBatch(batch, 200);
    Test.stopTest();

    List<Error_Log__c> errors = [SELECT Id, Message__c FROM Error_Log__c];
    Assert.areEqual(2, errors.size(), 'Should log 2 failed records');
}
```

### Batch Chaining

Test `finish()` chaining in a **separate test method** — calling `Database.executeBatch()` inside `finish()` during a test can throw `UnexpectedException`. Verify the first batch independently, then test that `finish()` enqueues the next batch.

## Queueable Testing

### Basic Queueable Test

```apex
@isTest
static void shouldCompleteProcessing_WhenQueueableEnqueued() {
    Account acc = TestDataFactory.createAccount(true);

    Test.startTest();
    MyQueueableClass queueable = new MyQueueableClass(acc.Id);
    System.enqueueJob(queueable);
    Test.stopTest();

    Account updated = [SELECT Id, Status__c FROM Account WHERE Id = :acc.Id];
    Assert.areEqual('Processed', updated.Status__c,
        'Queueable should update account status');
}
```

### Queueable Chaining

Only the **first** chained queueable executes in tests. Design tests to verify:
1. First job completes correctly
2. Chain is properly enqueued (query `AsyncApexJob`)
3. Each job works independently in its own test method

```apex
@isTest
static void shouldChainNextJob_WhenMoreRecordsExist() {
    List<Account> accounts = TestDataFactory.createAccounts(500, true);

    Test.startTest();
    MyChainedQueueable queueable = new MyChainedQueueable(0, 100);
    System.enqueueJob(queueable);
    Test.stopTest();

    List<Account> processed = [SELECT Id FROM Account WHERE Processed__c = true];
    Assert.areEqual(100, processed.size(), 'First batch should process 100 records');

    List<AsyncApexJob> jobs = [
        SELECT Id, Status, JobType
        FROM AsyncApexJob
        WHERE ApexClass.Name = 'MyChainedQueueable'
    ];
    Assert.isTrue(jobs.size() >= 1, 'Chained job should be enqueued');
}
```

### Queueable with Callouts

Set the callout mock **before** `Test.startTest()`:

```apex
@isTest
static void shouldMakeCallout_WhenQueueableWithCallout() {
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse(200, '{"status":"ok"}'));
    Account acc = TestDataFactory.createAccount(true);

    Test.startTest();
    MyQueueableWithCallout queueable = new MyQueueableWithCallout(acc.Id);
    System.enqueueJob(queueable);
    Test.stopTest();

    Account updated = [SELECT Id, External_Status__c FROM Account WHERE Id = :acc.Id];
    Assert.areEqual('Synced', updated.External_Status__c,
        'Should update status after successful callout');
}
```

## Future Method Testing

```apex
@isTest
static void shouldExecuteFutureMethod() {
    Account acc = TestDataFactory.createAccount(true);

    Test.startTest();
    MyClass.processFuture(acc.Id);
    Test.stopTest();

    Account updated = [SELECT Id, Processed__c FROM Account WHERE Id = :acc.Id];
    Assert.isTrue(updated.Processed__c, 'Future should process record');
}
```

## Scheduled Apex Testing

### Direct Execution

```apex
@isTest
static void shouldExecuteScheduledJob() {
    List<Account> accounts = TestDataFactory.createAccounts(50, true);

    Test.startTest();
    MyScheduledClass scheduled = new MyScheduledClass();
    scheduled.execute(null);
    Test.stopTest();

    List<Account> processed = [SELECT Id FROM Account WHERE Processed__c = true];
    Assert.areEqual(50, processed.size(), 'Scheduled job should process records');
}
```

### CRON Registration

```apex
@isTest
static void shouldScheduleJob() {
    Test.startTest();
    String cronExp = '0 0 6 * * ?';
    String jobId = System.schedule('Daily Processing', cronExp, new MyScheduledClass());
    Test.stopTest();

    CronTrigger ct = [
        SELECT Id, CronExpression, State
        FROM CronTrigger
        WHERE Id = :jobId
    ];
    Assert.areEqual('0 0 6 * * ?', ct.CronExpression, 'CRON should match');
    Assert.areEqual('WAITING', ct.State, 'Job should be waiting');
}
```

## Common Pitfalls

| Pitfall | Impact |
|---|---|
| Missing `Test.stopTest()` | Async never executes, assertions fail silently |
| Expecting all chained queueables to run | Only the first runs; test each independently |
| Mock set after `Test.startTest()` | Callout mock must be set **before** `Test.startTest()` |
| Batch size < record count in tests | Only `batchSize` records processed; set `batchSize >= recordCount` |
