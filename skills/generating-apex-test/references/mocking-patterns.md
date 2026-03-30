# Mocking Patterns

## HTTP Callout Mocking

Apex doesn't allow real HTTP callouts in tests. Use `HttpCalloutMock` interface.

### Basic Mock

```apex
@isTest
public class MockHttpResponse implements HttpCalloutMock {
    
    private Integer statusCode;
    private String body;
    
    public MockHttpResponse(Integer statusCode, String body) {
        this.statusCode = statusCode;
        this.body = body;
    }
    
    public HTTPResponse respond(HTTPRequest req) {
        HttpResponse res = new HttpResponse();
        res.setStatusCode(statusCode);
        res.setBody(body);
        res.setHeader('Content-Type', 'application/json');
        return res;
    }
}
```

### Using the Mock

```apex
@isTest
static void shouldProcessApiResponse_WhenCalloutSucceeds() {
    String mockResponse = '{"status": "success", "data": [{"id": "123"}]}';
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse(200, mockResponse));

    Test.startTest();
    List<ExternalRecord> results = MyIntegrationService.fetchRecords();
    Test.stopTest();

    Assert.areEqual(1, results.size(), 'Should parse one record from response');
    Assert.areEqual('123', results[0].externalId, 'Should extract correct ID');
}

@isTest
static void shouldHandleError_WhenCalloutFails() {
    String errorResponse = '{"error": "Unauthorized"}';
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse(401, errorResponse));

    Test.startTest();
    CalloutResult result = MyIntegrationService.fetchRecords();
    Test.stopTest();

    Assert.areEqual(false, result.isSuccess, 'Should indicate failure');
    Assert.isTrue(result.errorMessage.contains('Unauthorized'), 'Should capture error');
}
```

### Multi-Request Mock

For services making multiple callouts:

```apex
@isTest
public class MultiRequestMock implements HttpCalloutMock {

    private Map<String, HttpResponse> endpointResponses;

    public MultiRequestMock(Map<String, HttpResponse> responses) {
        this.endpointResponses = responses;
    }

    public HTTPResponse respond(HTTPRequest req) {
        String endpoint = req.getEndpoint();
        for (String key : endpointResponses.keySet()) {
            if (endpoint.contains(key)) {
                return endpointResponses.get(key);
            }
        }
        HttpResponse res = new HttpResponse();
        res.setStatusCode(404);
        res.setBody('{"error": "Not found"}');
        return res;
    }
}
```

### StaticResourceCalloutMock

Use when response JSON is large or complex:

```apex
@isTest
static void shouldParseComplexResponse() {
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

## SOSL Mocking

SOSL returns empty results in tests by default. Call `Test.setFixedSearchResults(List<Id>)` before the search:

```apex
@isTest
static void shouldReturnSearchResults() {
    Account acc = TestDataFactory.createAccount(true);
    Test.setFixedSearchResults(new List<Id>{ acc.Id });

    Test.startTest();
    List<Account> results = MyService.searchAccounts('Test');
    Test.stopTest();

    Assert.areEqual(1, results.size(), 'Should return mocked search result');
}
```

## DML Mocking (Constructor Injection)

Design for testability — use a public constructor for production and a `@TestVisible private` constructor that accepts mock interfaces:

```apex
public class MyService {
    private IDML dmlHandler;

    public MyService() {
        this.dmlHandler = new DMLHandler();
    }

    @TestVisible
    private MyService(IDML dmlHandler) {
        this.dmlHandler = dmlHandler;
    }

    public void createRecords(List<Account> accounts) {
        dmlHandler.doInsert(accounts);
    }
}
```

## Stub API (System.StubProvider)

For mocking Apex class dependencies:

```apex
@isTest
public class MyServiceMock implements System.StubProvider {

    public Object handleMethodCall(
        Object stubbedObject, String stubbedMethodName, Type returnType,
        List<Type> paramTypes, List<String> paramNames, List<Object> args
    ) {
        if (stubbedMethodName == 'getAccountData') {
            return new AccountData('Mock Account', 'Active');
        }
        return null;
    }
}

@isTest
static void shouldUseAccountData() {
    MyServiceMock mockProvider = new MyServiceMock();
    IMyService mockService = (IMyService) Test.createStub(IMyService.class, mockProvider);

    MyController controller = new MyController(mockService);

    Test.startTest();
    String result = controller.displayAccountInfo();
    Test.stopTest();

    Assert.isTrue(result.contains('Mock Account'), 'Should use mocked data');
}
```

## Email Testing

Apex doesn't actually send emails in tests. Use limits to verify:

```apex
@isTest
static void shouldSendEmail_WhenTriggered() {
    Integer emailsBefore = Limits.getEmailInvocations();

    Test.startTest();
    MyService.sendNotification(testContact);
    Test.stopTest();

    Assert.areEqual(emailsBefore + 1, Limits.getEmailInvocations(),
        'One email should be sent');
}
```

## Platform Event Testing

```apex
@isTest
static void shouldPublishEvent_WhenRecordCreated() {
    Test.startTest();
    Test.enableChangeDataCapture();

    Account acc = TestDataFactory.createAccount(true);
    Test.getEventBus().deliver();
    Test.stopTest();
    
    // Query platform event trigger results
    List<EventLog__c> logs = [SELECT Id FROM EventLog__c WHERE AccountId__c = :acc.Id];
    Assert.areEqual(1, logs.size(), 'Event handler should create log record');
}
```
