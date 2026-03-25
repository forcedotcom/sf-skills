# Mocking Patterns in Apex Tests

This guide covers mocking and stubbing patterns that enable true unit testing in Apex. By replacing database operations and external services with mock implementations, you can write fast, isolated, reliable tests.

> **Sources**: [Beyond the Cloud](https://blog.beyondthecloud.dev/blog/salesforce-mock-in-apex-tests), [James Simone](https://www.jamessimone.net/blog/joys-of-apex/mocking-dml/), [Trailhead](https://trailhead.salesforce.com/content/learn/modules/unit-testing-on-the-lightning-platform/mock-stub-objects)

---

## Mocking vs Stubbing

Understanding the distinction is crucial for effective test design:

| Aspect | Mocking | Stubbing |
|--------|---------|----------|
| **Purpose** | Replace objects with fakes returning predefined values | Create fake implementations with dynamic logic |
| **Complexity** | Simple, static responses | Complex, behavioral simulation |
| **When to Use** | HTTP callouts, simple return values | Interface implementations, dynamic behavior |
| **Example** | `HttpCalloutMock` returns fixed response | `StubProvider` with conditional logic |

---

## Pattern 1: HttpCalloutMock (Required for HTTP Tests)

Salesforce **requires** mock callouts - you cannot make real HTTP requests in tests.

### Basic Implementation

```apex
/**
 * Simple HTTP mock returning a fixed response
 *
 * @see https://www.apexhours.com/testing-web-services-callouts-in-salesforce/
 */
@IsTest
public class MockHttpResponse implements HttpCalloutMock {

    private Integer statusCode;
    private String body;

    public MockHttpResponse(Integer statusCode, String body) {
        this.statusCode = statusCode;
        this.body = body;
    }

    public HttpResponse respond(HttpRequest req) {
        HttpResponse res = new HttpResponse();
        res.setStatusCode(this.statusCode);
        res.setHeader('Content-Type', 'application/json');
        res.setBody(this.body);
        return res;
    }
}

// Usage in test
@IsTest
static void testApiCall_Success() {
    String mockBody = '{"success": true, "data": {"id": "12345"}}';
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse(200, mockBody));

    Test.startTest();
    ApiResponse result = MyApiService.callExternalApi('endpoint');
    Test.stopTest();

    Assert.isTrue(result.success, 'API call should succeed');
}
```

### Multi-Endpoint Mock

```apex
/**
 * Mock that responds differently based on request endpoint
 */
@IsTest
public class MultiEndpointMock implements HttpCalloutMock {

    public HttpResponse respond(HttpRequest req) {
        HttpResponse res = new HttpResponse();
        res.setStatusCode(200);
        res.setHeader('Content-Type', 'application/json');

        String endpoint = req.getEndpoint();

        if (endpoint.contains('/users')) {
            res.setBody('{"users": [{"id": 1, "name": "John"}]}');
        } else if (endpoint.contains('/orders')) {
            res.setBody('{"orders": [{"id": 100, "total": 250.00}]}');
        } else {
            res.setStatusCode(404);
            res.setBody('{"error": "Not Found"}');
        }

        return res;
    }
}
```

### Error Scenario Mock

```apex
/**
 * Mock for testing error handling
 */
@IsTest
static void testApiCall_ServerError_HandlesGracefully() {
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse(500, '{"error": "Server Error"}'));

    Test.startTest();
    try {
        MyApiService.callExternalApi('endpoint');
        Assert.fail('Expected CalloutException was not thrown');
    } catch (CalloutException e) {
        Assert.isTrue(e.getMessage().contains('Server Error'), 'Should contain error message');
    }
    Test.stopTest();
}
```

---

## Pattern 2: DML Mocking (No Database Operations)

This pattern eliminates database operations from tests, achieving 35x faster execution.

### The DML Interface

```apex
/**
 * Interface for DML operations - enables mocking
 *
 * @see https://www.jamessimone.net/blog/joys-of-apex/mocking-dml/
 */
public interface IDML {
    void doInsert(SObject record);
    void doInsert(List<SObject> records);
    void doUpdate(SObject record);
    void doUpdate(List<SObject> records);
    void doUpsert(SObject record);
    void doUpsert(List<SObject> records);
    void doDelete(SObject record);
    void doDelete(List<SObject> records);
}
```

### Production Implementation

```apex
/**
 * Production DML implementation - performs actual database operations
 */
public class DML implements IDML {

    public void doInsert(SObject record) {
        insert record;
    }

    public void doInsert(List<SObject> records) {
        insert records;
    }

    public void doUpdate(SObject record) {
        update record;
    }

    public void doUpdate(List<SObject> records) {
        update records;
    }

    public void doUpsert(SObject record) {
        upsert record;
    }

    public void doUpsert(List<SObject> records) {
        upsert records;
    }

    public void doDelete(SObject record) {
        delete record;
    }

    public void doDelete(List<SObject> records) {
        delete records;
    }
}
```

### Mock Implementation

```apex
/**
 * Mock DML implementation - tracks operations without database
 */
@IsTest
public class DMLMock implements IDML {

    // Static lists to track operations
    public static List<SObject> InsertedRecords = new List<SObject>();
    public static List<SObject> UpdatedRecords = new List<SObject>();
    public static List<SObject> UpsertedRecords = new List<SObject>();
    public static List<SObject> DeletedRecords = new List<SObject>();

    // Counter for generating fake IDs
    private static Integer idCounter = 1;

    public void doInsert(SObject record) {
        doInsert(new List<SObject>{ record });
    }

    public void doInsert(List<SObject> records) {
        for (SObject record : records) {
            // Generate fake ID to simulate insert
            if (record.Id == null) {
                record.Id = generateFakeId(record.getSObjectType());
            }
            InsertedRecords.add(record);
        }
    }

    public void doUpdate(SObject record) {
        doUpdate(new List<SObject>{ record });
    }

    public void doUpdate(List<SObject> records) {
        UpdatedRecords.addAll(records);
    }

    public void doUpsert(SObject record) {
        doUpsert(new List<SObject>{ record });
    }

    public void doUpsert(List<SObject> records) {
        UpsertedRecords.addAll(records);
    }

    public void doDelete(SObject record) {
        doDelete(new List<SObject>{ record });
    }

    public void doDelete(List<SObject> records) {
        DeletedRecords.addAll(records);
    }

    /**
     * Generate a fake Salesforce ID for testing
     */
    private static Id generateFakeId(Schema.SObjectType sObjectType) {
        String keyPrefix = sObjectType.getDescribe().getKeyPrefix();
        String idBody = String.valueOf(idCounter++).leftPad(12, '0');
        return Id.valueOf(keyPrefix + idBody);
    }

    /**
     * Reset all tracked operations (call in @TestSetup or between tests)
     */
    public static void reset() {
        InsertedRecords.clear();
        UpdatedRecords.clear();
        UpsertedRecords.clear();
        DeletedRecords.clear();
        idCounter = 1;
    }

    /**
     * Get inserted records of a specific type
     */
    public static List<SObject> getInsertedOfType(Schema.SObjectType sObjectType) {
        List<SObject> result = new List<SObject>();
        for (SObject record : InsertedRecords) {
            if (record.getSObjectType() == sObjectType) {
                result.add(record);
            }
        }
        return result;
    }
}
```

### Using DML Mocking in Services

```apex
/**
 * Service class that accepts injected DML
 */
public class AccountService {

    private IDML dml;

    // Production constructor - uses real DML
    public AccountService() {
        this(new DML());
    }

    // Test constructor - accepts mock DML
    @TestVisible
    private AccountService(IDML dml) {
        this.dml = dml;
    }

    public Id createAccount(Account acc) {
        if (acc == null) {
            throw new IllegalArgumentException('Account cannot be null');
        }
        dml.doInsert(acc);
        return acc.Id;
    }
}

// Test using mock DML
@IsTest
static void testCreateAccount_NoDatabase() {
    // Arrange
    DMLMock.reset();
    AccountService service = new AccountService(new DMLMock());
    Account testAcc = new Account(Name = 'Test Account');

    // Act
    Test.startTest();
    Id accountId = service.createAccount(testAcc);
    Test.stopTest();

    // Assert
    Assert.isNotNull(accountId, 'Should have fake ID');
    Assert.areEqual(1, DMLMock.InsertedRecords.size(), 'Should have 1 inserted record');
    Account inserted = (Account) DMLMock.InsertedRecords[0];
    Assert.areEqual('Test Account', inserted.Name, 'Name should match');
}
```

---

## Pattern 3: StubProvider (Dynamic Behavior)

Use `StubProvider` when you need dynamic, conditional behavior in your mocks.

### Basic StubProvider Implementation

```apex
/**
 * StubProvider for dynamic service mocking
 *
 * @see https://developer.salesforce.com/docs/atlas.en-us.apexref.meta/apexref/apex_interface_System_StubProvider.htm
 */
@IsTest
public class AccountServiceStub implements System.StubProvider {

    private Map<String, Object> methodResponses = new Map<String, Object>();

    /**
     * Configure what a method should return
     */
    public AccountServiceStub withMethodReturn(String methodName, Object returnValue) {
        methodResponses.put(methodName, returnValue);
        return this;
    }

    public Object handleMethodCall(
        Object stubbedObject,
        String stubbedMethodName,
        Type returnType,
        List<Type> paramTypes,
        List<String> paramNames,
        List<Object> paramValues
    ) {
        // Return pre-configured response if available
        if (methodResponses.containsKey(stubbedMethodName)) {
            return methodResponses.get(stubbedMethodName);
        }

        // Default responses based on method name
        if (stubbedMethodName == 'getAccount') {
            return new Account(Id = generateFakeId(), Name = 'Stubbed Account');
        }
        if (stubbedMethodName == 'getAccounts') {
            return new List<Account>{
                new Account(Id = generateFakeId(), Name = 'Stubbed 1'),
                new Account(Id = generateFakeId(), Name = 'Stubbed 2')
            };
        }

        return null;
    }

    private static Integer idCounter = 1;
    private static Id generateFakeId() {
        String idBody = String.valueOf(idCounter++).leftPad(12, '0');
        return Id.valueOf('001' + idBody);
    }
}
```

### Using StubProvider

```apex
// Create stub with Test.createStub()
@IsTest
static void testWithStub() {
    // Create the stub
    AccountServiceStub stub = new AccountServiceStub()
        .withMethodReturn('getAccountCount', 42);

    IAccountService service = (IAccountService) Test.createStub(
        IAccountService.class,
        stub
    );

    // Use the stubbed service
    Test.startTest();
    Integer count = service.getAccountCount();
    Account acc = service.getAccount('001000000000001');
    Test.stopTest();

    // Verify
    Assert.areEqual(42, count, 'Should return configured value');
    Assert.areEqual('Stubbed Account', acc.Name, 'Should return stub default');
}
```

---

## Pattern 4: Selector Mocking (Query Results)

Mock SOQL query results without hitting the database.

```apex
/**
 * Mockable selector pattern
 */
public class AccountSelector {

    @TestVisible
    private static List<Account> mockResults;

    public static List<Account> getActiveAccounts() {
        if (Test.isRunningTest() && mockResults != null) {
            return mockResults;
        }
        return [
            SELECT Id, Name, Industry
            FROM Account
            WHERE IsActive__c = true
            WITH USER_MODE
        ];
    }

    @TestVisible
    private static void setMockResults(List<Account> accounts) {
        mockResults = accounts;
    }
}

// Usage in test
@IsTest
static void testWithMockedQuery() {
    // Arrange - no database insert needed!
    List<Account> mockAccounts = new List<Account>{
        new Account(Name = 'Mock 1', Industry = 'Tech'),
        new Account(Name = 'Mock 2', Industry = 'Finance')
    };
    AccountSelector.setMockResults(mockAccounts);

    // Act
    Test.startTest();
    List<Account> result = AccountSelector.getActiveAccounts();
    Test.stopTest();

    // Assert
    Assert.areEqual(2, result.size(), 'Should return mock data');
    Assert.areEqual('Mock 1', result[0].Name);
}
```

---

## Pattern 5: StaticResourceCalloutMock

For complex response bodies, store JSON in Static Resources instead of inline strings:

```apex
@IsTest
private static void shouldParseComplexResponse() {
    StaticResourceCalloutMock mock = new StaticResourceCalloutMock();
    mock.setStaticResource('TestApiResponse');
    mock.setStatusCode(200);
    mock.setHeader('Content-Type', 'application/json');

    Test.setMock(HttpCalloutMock.class, mock);

    Test.startTest();
    Result r = MyService.callExternalApi();
    Test.stopTest();

    Assert.isNotNull(r, 'Should parse response');
}
```

---

## Pattern 6: Email Mocking

Apex sends real emails by default. Use `Limits.getEmailInvocations()` to verify email dispatch without actually sending:

```apex
@IsTest
private static void shouldSendEmail_WhenTriggered() {
    Integer emailsBefore = Limits.getEmailInvocations();

    Test.startTest();
    MyService.sendNotification(testContact);
    Test.stopTest();

    Assert.areEqual(
        emailsBefore + 1,
        Limits.getEmailInvocations(),
        'One email should be sent'
    );
}
```

---

## Pattern 7: Platform Event Testing

```apex
@IsTest
private static void shouldPublishEvent_WhenRecordCreated() {
    Test.startTest();

    Test.enableChangeDataCapture();

    Account acc = TestDataFactory.createAndInsertAccounts(1)[0];

    Test.getEventBus().deliver();

    Test.stopTest();

    List<EventLog__c> logs = [SELECT Id FROM EventLog__c WHERE AccountId__c = :acc.Id];
    Assert.areEqual(1, logs.size(), 'Event handler should create log record');
}
```

---

## When to Use Each Pattern

| Scenario | Pattern | Why |
|----------|---------|-----|
| HTTP callouts | HttpCalloutMock | Required by Salesforce |
| Complex HTTP bodies | StaticResourceCalloutMock | Keeps test code clean |
| Fast unit tests | DML Mocking | Eliminates database overhead |
| Complex interfaces | StubProvider | Dynamic, conditional behavior |
| Query isolation | Selector Mocking | Test without data setup |
| Simple replacements | Direct mocking | Static @TestVisible fields |
| Email verification | Limits.getEmailInvocations | No real emails in tests |
| Platform events | Test.getEventBus().deliver() | Force event delivery in tests |

---

## Performance Comparison

| Approach | 10,000 Records | Notes |
|----------|----------------|-------|
| Actual DML | ~50 seconds | Database operations are slow |
| DML Mocking | <1 second | 35x faster |
| StubProvider | <1 second | No database at all |

---

## Best Practices

1. **Mock at the seams**: DML, callouts, and queries are natural mock points
2. **Use dependency injection**: Constructor injection enables easy test swapping
3. **Prefer interfaces**: `IDML` interface allows production/mock implementations
4. **Reset between tests**: Call `DMLMock.reset()` to prevent test pollution
5. **Verify mock behavior**: Assert on `DMLMock.InsertedRecords` to confirm operations
6. **Generate fake IDs**: Use key prefix + counter for realistic test IDs
