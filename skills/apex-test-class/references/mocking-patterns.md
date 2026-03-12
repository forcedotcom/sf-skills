# Mocking Patterns

## HTTP Callout Mocking

Apex doesn't allow real HTTP callouts in tests. Use `HttpCalloutMock` interface.

### Basic Mock Implementation

```apex
@IsTest
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
@IsTest
private static void shouldProcessApiResponse_WhenCalloutSucceeds() {
    // Given
    String mockResponse = '{"status": "success", "data": [{"id": "123"}]}';
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse(200, mockResponse));
    
    // When
    Test.startTest();
    List<ExternalRecord> results = MyIntegrationService.fetchRecords();
    Test.stopTest();
    
    // Then
    System.Assert.areEqual(1, results.size(), 'Should parse one record from response');
    System.Assert.areEqual('123', results[0].externalId, 'Should extract correct ID');
}

@IsTest
private static void shouldHandleError_WhenCalloutFails() {
    // Given
    String errorResponse = '{"error": "Unauthorized"}';
    Test.setMock(HttpCalloutMock.class, new MockHttpResponse(401, errorResponse));
    
    // When
    Test.startTest();
    CalloutResult result = MyIntegrationService.fetchRecords();
    Test.stopTest();
    
    // Then
    System.Assert.areEqual(false, result.isSuccess, 'Should indicate failure');
    System.Assert.isTrue(result.errorMessage.contains('Unauthorized'), 'Should capture error');
}
```

### Multi-Request Mock

For services making multiple callouts:

```apex
@IsTest
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
        
        // Default 404 if no match
        HttpResponse res = new HttpResponse();
        res.setStatusCode(404);
        res.setBody('{"error": "Not found"}');
        return res;
    }
}

// Usage:
Map<String, HttpResponse> mocks = new Map<String, HttpResponse>();

HttpResponse authResponse = new HttpResponse();
authResponse.setStatusCode(200);
authResponse.setBody('{"token": "abc123"}');
mocks.put('/oauth/token', authResponse);

HttpResponse dataResponse = new HttpResponse();
dataResponse.setStatusCode(200);
dataResponse.setBody('{"records": []}');
mocks.put('/api/records', dataResponse);

Test.setMock(HttpCalloutMock.class, new MultiRequestMock(mocks));
```

## StaticResourceCalloutMock

For complex response bodies, store JSON in Static Resources:

```apex
@IsTest
private static void shouldParseComplexResponse() {
    StaticResourceCalloutMock mock = new StaticResourceCalloutMock();
    mock.setStaticResource('TestApiResponse'); // Static Resource name
    mock.setStatusCode(200);
    mock.setHeader('Content-Type', 'application/json');
    
    Test.setMock(HttpCalloutMock.class, mock);
    
    Test.startTest();
    Result r = MyService.callExternalApi();
    Test.stopTest();
    
    System.Assert.isNotNull(r, 'Should parse response');
}
```

## Stub API (Enterprise Pattern)

For mocking Apex class dependencies using `System.StubProvider`:

```apex
@IsTest
public class MyServiceMock implements System.StubProvider {
    
    public Object handleMethodCall(
        Object stubbedObject,
        String stubbedMethodName,
        Type returnType,
        List<Type> paramTypes,
        List<String> paramNames,
        List<Object> args
    ) {
        if (stubbedMethodName == 'getAccountData') {
            return new AccountData('Mock Account', 'Active');
        }
        return null;
    }
}

// Usage in test:
@IsTest
private static void shouldUseAccountData() {
    MyServiceMock mockProvider = new MyServiceMock();
    IMyService mockService = (IMyService)Test.createStub(IMyService.class, mockProvider);
    
    // Inject mock into class under test
    MyController controller = new MyController(mockService);
    
    Test.startTest();
    String result = controller.displayAccountInfo();
    Test.stopTest();
    
    System.Assert.isTrue(result.contains('Mock Account'), 'Should use mocked data');
}
```

## Email Mocking

Apex sends real emails by default. Use limits to verify:

```apex
@IsTest
private static void shouldSendEmail_WhenTriggered() {
    Integer emailsBefore = Limits.getEmailInvocations();
    
    Test.startTest();
    MyService.sendNotification(testContact);
    Test.stopTest();
    
    // Verify email was queued (not actually sent in tests)
    System.Assert.areEqual(
        emailsBefore + 1, 
        Limits.getEmailInvocations(), 
        'One email should be sent'
    );
}
```

## Platform Event Testing

```apex
@IsTest
private static void shouldPublishEvent_WhenRecordCreated() {
    Test.startTest();
    
    // Enable event delivery in test context
    Test.enableChangeDataCapture();
    
    Account acc = TestDataFactory.createAccount(true);
    
    // Deliver events
    Test.getEventBus().deliver();
    
    Test.stopTest();
    
    // Query platform event trigger results
    List<EventLog__c> logs = [SELECT Id FROM EventLog__c WHERE AccountId__c = :acc.Id];
    System.Assert.areEqual(1, logs.size(), 'Event handler should create log record');
}
```
