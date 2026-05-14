<!-- Parent: building-sf-integrations/SKILL.md -->
# Callout Patterns Reference

This document provides detailed implementation patterns for REST and SOAP callouts in Salesforce integrations.

> **Parent Document**: [building-sf-integrations/SKILL.md](../SKILL.md)
> **Related**: [event-patterns.md](./event-patterns.md)

---

## Table of Contents

- [REST Callout Patterns](#rest-callout-patterns)
  - [Synchronous REST Callout](#synchronous-rest-callout)
  - [Asynchronous REST Callout (Queueable)](#asynchronous-rest-callout-queueable)
  - [Retry Handler with Exponential Backoff](#retry-handler-with-exponential-backoff)
- [SOAP Callout Patterns](#soap-callout-patterns)
  - [WSDL2Apex Process](#wsdl2apex-process)
  - [SOAP Service Implementation](#soap-service-implementation)

---

## REST Callout Patterns

### Synchronous REST Callout

**Use Case**: Need immediate response, NOT triggered from DML

**Template**: `assets/callouts/rest-sync-callout.cls`

**When to Use**:
- User-initiated actions requiring immediate feedback
- API calls from Lightning Web Components
- Scheduled batch jobs needing sequential processing
- Any non-trigger context where response is needed

**When NOT to Use**:
- Triggered from DML operations (triggers, Process Builder, flows)
- Long-running operations (>10 seconds expected)
- High-volume batch operations

#### Implementation

```apex
public with sharing class {{ServiceName}}Callout {

    private static final String NAMED_CREDENTIAL = 'callout:{{NamedCredentialName}}';

    public static HttpResponse makeRequest(String method, String endpoint, String body) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint(NAMED_CREDENTIAL + endpoint);
        req.setMethod(method);
        req.setHeader('Content-Type', 'application/json');
        req.setTimeout(120000); // 120 seconds max

        if (String.isNotBlank(body)) {
            req.setBody(body);
        }

        Http http = new Http();
        return http.send(req);
    }

    public static Map<String, Object> get(String endpoint) {
        HttpResponse res = makeRequest('GET', endpoint, null);
        return handleResponse(res);
    }

    public static Map<String, Object> post(String endpoint, Map<String, Object> payload) {
        HttpResponse res = makeRequest('POST', endpoint, JSON.serialize(payload));
        return handleResponse(res);
    }

    public static Map<String, Object> put(String endpoint, Map<String, Object> payload) {
        HttpResponse res = makeRequest('PUT', endpoint, JSON.serialize(payload));
        return handleResponse(res);
    }

    public static Map<String, Object> patch(String endpoint, Map<String, Object> payload) {
        HttpResponse res = makeRequest('PATCH', endpoint, JSON.serialize(payload));
        return handleResponse(res);
    }

    public static void deleteRequest(String endpoint) {
        makeRequest('DELETE', endpoint, null);
    }

    private static Map<String, Object> handleResponse(HttpResponse res) {
        Integer statusCode = res.getStatusCode();

        if (statusCode >= 200 && statusCode < 300) {
            return (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
        } else if (statusCode >= 400 && statusCode < 500) {
            throw new CalloutException('Client Error: ' + statusCode + ' - ' + res.getBody());
        } else if (statusCode >= 500) {
            throw new CalloutException('Server Error: ' + statusCode + ' - ' + res.getBody());
        }

        return null;
    }
}
```

#### Key Features

- **Named Credential Integration**: Uses `callout:` syntax for secure authentication
- **Timeout Management**: 120-second max timeout (governor limit)
- **HTTP Method Support**: GET, POST, PUT, PATCH, DELETE
- **Status Code Handling**: Differentiates between client (4xx) and server (5xx) errors
- **JSON Serialization**: Automatic JSON handling for request/response bodies

#### Usage Example

```apex
// GET request
try {
    Map<String, Object> data = StripeCallout.get('/v1/customers/cus_123');
    String email = (String) data.get('email');
} catch (CalloutException e) {
    // Handle error
    System.debug(LoggingLevel.ERROR, 'Callout failed: ' + e.getMessage());
}

// POST request
Map<String, Object> payload = new Map<String, Object>{
    'email' => 'customer@example.com',
    'name' => 'John Doe'
};
Map<String, Object> response = StripeCallout.post('/v1/customers', payload);
```

---

### Asynchronous REST Callout (Queueable)

**Use Case**: Callouts triggered from DML (triggers, Process Builder)

**Template**: `assets/callouts/rest-queueable-callout.cls`

**When to Use**:
- Callouts from triggers (REQUIRED - sync callouts fail in triggers)
- Fire-and-forget operations (no immediate response needed)
- Bulk operations processing multiple records
- Long-running API calls (>10 seconds)

**Governor Limit Considerations**:
- Max 50 queueable jobs per transaction
- Queueable can chain to another queueable (max depth varies by org)
- Callout timeout: 120 seconds

#### Implementation

```apex
public with sharing class {{ServiceName}}QueueableCallout implements Queueable, Database.AllowsCallouts {

    private List<Id> recordIds;
    private String operation;

    public {{ServiceName}}QueueableCallout(List<Id> recordIds, String operation) {
        this.recordIds = recordIds;
        this.operation = operation;
    }

    public void execute(QueueableContext context) {
        if (recordIds == null || recordIds.isEmpty()) {
            return;
        }

        try {
            // Query records
            List<{{ObjectName}}> records = [
                SELECT Id, Name, {{FieldsToSend}}
                FROM {{ObjectName}}
                WHERE Id IN :recordIds
                WITH USER_MODE
            ];

            // Make callout for each record (consider batching)
            for ({{ObjectName}} record : records) {
                makeCallout(record);
            }

        } catch (CalloutException e) {
            // Log callout errors
            System.debug(LoggingLevel.ERROR, 'Callout failed: ' + e.getMessage());
            // Consider: Create error log record, retry logic, notification
        } catch (Exception e) {
            System.debug(LoggingLevel.ERROR, 'Error: ' + e.getMessage());
        }
    }

    private void makeCallout({{ObjectName}} record) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:{{NamedCredentialName}}/{{Endpoint}}');
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setTimeout(120000);

        Map<String, Object> payload = new Map<String, Object>{
            'id' => record.Id,
            'name' => record.Name
            // Add more fields
        };
        req.setBody(JSON.serialize(payload));

        Http http = new Http();
        HttpResponse res = http.send(req);

        if (res.getStatusCode() >= 200 && res.getStatusCode() < 300) {
            // Success - update record status if needed
        } else {
            // Handle error
            throw new CalloutException('API Error: ' + res.getStatusCode());
        }
    }
}
```

#### Trigger Integration

```apex
trigger OpportunityTrigger on Opportunity (after insert, after update) {
    List<Id> opportunityIds = new List<Id>();

    for (Opportunity opp : Trigger.new) {
        // Only sync closed-won opportunities
        if (opp.StageName == 'Closed Won') {
            opportunityIds.add(opp.Id);
        }
    }

    if (!opportunityIds.isEmpty()) {
        // Enqueue async callout
        System.enqueueJob(new SalesforceQueueableCallout(opportunityIds, 'SYNC'));
    }
}
```

#### Bulkification Pattern

For high-volume scenarios, batch multiple callouts:

```apex
private void makeCallouts(List<{{ObjectName}}> records) {
    // Batch up to 10 records per callout
    Integer BATCH_SIZE = 10;
    List<Map<String, Object>> batch = new List<Map<String, Object>>();

    for (Integer i = 0; i < records.size(); i++) {
        batch.add(buildPayload(records[i]));

        if (batch.size() == BATCH_SIZE || i == records.size() - 1) {
            // Make single callout with batch
            sendBatch(batch);
            batch.clear();
        }
    }
}

private void sendBatch(List<Map<String, Object>> batch) {
    HttpRequest req = new HttpRequest();
    req.setEndpoint('callout:{{NamedCredentialName}}/batch');
    req.setMethod('POST');
    req.setHeader('Content-Type', 'application/json');
    req.setTimeout(120000);
    req.setBody(JSON.serialize(new Map<String, Object>{'records' => batch}));

    Http http = new Http();
    HttpResponse res = http.send(req);
    // Handle response
}
```

---

### Retry Handler with Exponential Backoff

**Use Case**: Handle transient failures with intelligent retry logic

**Template**: `assets/callouts/callout-retry-handler.cls`

**Retry Strategy**:
- **Max Retries**: 3 attempts
- **Backoff**: Exponential (1s, 2s, 4s)
- **Retry on**: 5xx server errors, network timeouts
- **Don't Retry**: 4xx client errors (bad request, auth failure)

#### Implementation

```apex
public with sharing class CalloutRetryHandler {

    private static final Integer MAX_RETRIES = 3;
    private static final Integer BASE_DELAY_MS = 1000; // 1 second

    public static HttpResponse executeWithRetry(HttpRequest request) {
        Integer retryCount = 0;
        HttpResponse response;

        while (retryCount < MAX_RETRIES) {
            try {
                Http http = new Http();
                response = http.send(request);

                // Success or client error (4xx) - don't retry
                if (response.getStatusCode() < 500) {
                    return response;
                }

                // Server error (5xx) - retry with backoff
                retryCount++;
                if (retryCount < MAX_RETRIES) {
                    // Exponential backoff: 1s, 2s, 4s
                    Integer delayMs = BASE_DELAY_MS * (Integer) Math.pow(2, retryCount - 1);
                    // Note: Apex doesn't have sleep(), so we schedule retry via Queueable
                    throw new RetryableException('Server error, retry ' + retryCount);
                }

            } catch (CalloutException e) {
                retryCount++;
                if (retryCount >= MAX_RETRIES) {
                    throw e;
                }
            }
        }

        return response;
    }

    public class RetryableException extends Exception {}
}
```

#### Queueable Retry Pattern

Since Apex doesn't support `Thread.sleep()`, implement retry delays using Queueable chaining:

```apex
public with sharing class CalloutWithRetryQueueable implements Queueable, Database.AllowsCallouts {

    private HttpRequest request;
    private Integer retryCount;
    private static final Integer MAX_RETRIES = 3;

    public CalloutWithRetryQueueable(HttpRequest req) {
        this(req, 0);
    }

    private CalloutWithRetryQueueable(HttpRequest req, Integer retries) {
        this.request = req;
        this.retryCount = retries;
    }

    public void execute(QueueableContext context) {
        try {
            Http http = new Http();
            HttpResponse res = http.send(request);

            if (res.getStatusCode() >= 500 && retryCount < MAX_RETRIES) {
                // Server error - retry
                System.debug(LoggingLevel.WARN, 'Retry ' + (retryCount + 1) + ' for ' + request.getEndpoint());
                System.enqueueJob(new CalloutWithRetryQueueable(request, retryCount + 1));
            } else if (res.getStatusCode() >= 200 && res.getStatusCode() < 300) {
                // Success
                handleSuccess(res);
            } else {
                // Client error - don't retry
                handleError(res);
            }

        } catch (CalloutException e) {
            if (retryCount < MAX_RETRIES) {
                System.enqueueJob(new CalloutWithRetryQueueable(request, retryCount + 1));
            } else {
                throw e;
            }
        }
    }

    private void handleSuccess(HttpResponse res) {
        // Process successful response
        System.debug('Callout succeeded: ' + res.getBody());
    }

    private void handleError(HttpResponse res) {
        // Log error
        System.debug(LoggingLevel.ERROR, 'Callout error: ' + res.getStatusCode() + ' - ' + res.getBody());
    }
}
```

#### Idempotency Considerations

When implementing retries, ensure API operations are idempotent:

```apex
// BAD: Non-idempotent (creates new record on each retry)
POST /api/orders { "item": "Widget", "quantity": 1 }

// GOOD: Idempotent (uses idempotency key)
POST /api/orders
Headers: Idempotency-Key: {{recordId}}-{{timestamp}}
{ "item": "Widget", "quantity": 1 }
```

---

## SOAP Callout Patterns

### WSDL2Apex Process

SOAP integrations in Salesforce use WSDL2Apex to auto-generate Apex classes from WSDL files.

#### Step-by-Step Process

**Step 1: Generate Apex from WSDL**

1. Navigate to **Setup** → **Apex Classes** → **Generate from WSDL**
2. Upload WSDL file or provide URL
3. Salesforce parses WSDL and generates:
   - Stub class (contains service endpoint and operations)
   - Request/Response classes (for each operation)
   - Type classes (for complex data types)

**Step 2: Configure Named Credential**

Create a Named Credential for the SOAP endpoint:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<NamedCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>{{ServiceName}} SOAP</label>
    <endpoint>https://api.example.com/soap/v1</endpoint>
    <principalType>NamedUser</principalType>
    <protocol>Password</protocol>
    <username>{{Username}}</username>
    <password>{{Password}}</password>
</NamedCredential>
```

**Step 3: Use Generated Classes**

Generated classes follow this naming pattern:
- **Stub Class**: `{{WsdlNamespace}}.{{ServiceName}}`
- **Port Type**: `{{WsdlNamespace}}.{{PortTypeName}}`
- **Operations**: Methods on the port type class

---

### SOAP Service Implementation

**Template**: `assets/soap/soap-callout-service.cls`

#### Basic SOAP Callout

```apex
public with sharing class {{ServiceName}}SoapService {

    public static {{ResponseType}} callService({{RequestType}} request) {
        try {
            // Generated stub class
            {{WsdlGeneratedClass}}.{{PortType}} stub = new {{WsdlGeneratedClass}}.{{PortType}}();

            // Set endpoint (use Named Credential if possible)
            stub.endpoint_x = 'callout:{{NamedCredentialName}}';

            // Set timeout
            stub.timeout_x = 120000;

            // Make the call
            return stub.{{OperationName}}(request);

        } catch (Exception e) {
            System.debug(LoggingLevel.ERROR, 'SOAP Callout Error: ' + e.getMessage());
            throw new CalloutException('SOAP service error: ' + e.getMessage());
        }
    }
}
```

#### Example: Weather Service SOAP Callout

**WSDL**: `https://your-external-system.com/service?wsdl` *(replace with your actual WSDL endpoint)*

**Generated Classes** (example based on a weather service WSDL):
- `GlobalWeatherSoap`
- `GetWeatherRequest`
- `GetWeatherResponse`

**Service Implementation**:

```apex
public with sharing class WeatherService {

    public static String getWeather(String city, String country) {
        try {
            // Initialize SOAP stub
            GlobalWeatherSoap.GlobalWeatherSoap stub =
                new GlobalWeatherSoap.GlobalWeatherSoap();

            // Configure endpoint and timeout
            stub.endpoint_x = 'callout:GlobalWeather_NC';
            stub.timeout_x = 120000;

            // Build request
            GlobalWeatherSoap.GetWeatherRequest req =
                new GlobalWeatherSoap.GetWeatherRequest();
            req.CityName = city;
            req.CountryName = country;

            // Make callout
            GlobalWeatherSoap.GetWeatherResponse res = stub.GetWeather(req);

            return res.GetWeatherResult;

        } catch (System.CalloutException e) {
            System.debug(LoggingLevel.ERROR, 'Weather API callout failed: ' + e.getMessage());
            return null;
        }
    }
}
```

#### SOAP Headers and Authentication

For SOAP services requiring custom headers (e.g., WS-Security):

```apex
public with sharing class SecureSoapService {

    public static void callServiceWithAuth(String username, String password) {
        // Generated stub
        MyService.MyServiceSoap stub = new MyService.MyServiceSoap();

        // Set endpoint
        stub.endpoint_x = 'callout:MyService_NC';
        stub.timeout_x = 120000;

        // Set SOAP headers for authentication
        stub.inputHttpHeaders_x = new Map<String, String>{
            'SOAPAction' => 'http://tempuri.org/IMyService/MyOperation',
            'Authorization' => 'Basic ' + EncodingUtil.base64Encode(
                Blob.valueOf(username + ':' + password)
            )
        };

        // Make request
        MyService.MyRequest req = new MyService.MyRequest();
        MyService.MyResponse res = stub.MyOperation(req);
    }
}
```

#### SOAP Fault Handling

```apex
public with sharing class RobustSoapService {

    public static Object callWithFaultHandling() {
        try {
            MyService.MyServiceSoap stub = new MyService.MyServiceSoap();
            stub.endpoint_x = 'callout:MyService_NC';
            stub.timeout_x = 120000;

            MyService.MyRequest req = new MyService.MyRequest();
            return stub.MyOperation(req);

        } catch (System.CalloutException e) {
            // Parse SOAP fault
            String errorMessage = e.getMessage();

            if (errorMessage.contains('faultcode')) {
                // SOAP Fault occurred
                System.debug(LoggingLevel.ERROR, 'SOAP Fault: ' + errorMessage);
                // Extract fault details using XML parsing if needed
            } else {
                // Network/HTTP error
                System.debug(LoggingLevel.ERROR, 'Callout error: ' + errorMessage);
            }

            throw e;
        }
    }
}
```

#### Async SOAP Callout (Queueable)

For SOAP callouts triggered from DML:

```apex
public with sharing class SoapQueueableCallout implements Queueable, Database.AllowsCallouts {

    private List<Id> recordIds;

    public SoapQueueableCallout(List<Id> recordIds) {
        this.recordIds = recordIds;
    }

    public void execute(QueueableContext context) {
        try {
            // Query records
            List<Account> accounts = [
                SELECT Id, Name, BillingCity, BillingCountry
                FROM Account
                WHERE Id IN :recordIds
                WITH USER_MODE
            ];

            // Initialize SOAP stub
            GlobalWeatherSoap.GlobalWeatherSoap stub =
                new GlobalWeatherSoap.GlobalWeatherSoap();
            stub.endpoint_x = 'callout:GlobalWeather_NC';
            stub.timeout_x = 120000;

            // Process each record
            for (Account acc : accounts) {
                GlobalWeatherSoap.GetWeatherRequest req =
                    new GlobalWeatherSoap.GetWeatherRequest();
                req.CityName = acc.BillingCity;
                req.CountryName = acc.BillingCountry;

                GlobalWeatherSoap.GetWeatherResponse res = stub.GetWeather(req);

                // Update account with weather data
                acc.Weather_Data__c = res.GetWeatherResult;
            }

            // Update records
            update as user accounts;

        } catch (Exception e) {
            System.debug(LoggingLevel.ERROR, 'SOAP Queueable error: ' + e.getMessage());
        }
    }
}
```

---

## Best Practices

### Callout Governor Limits

| Limit | Value | Notes |
|-------|-------|-------|
| Max callouts per transaction | 100 | Batch multiple requests if possible |
| Max timeout per callout | 120 seconds | Set explicitly with `setTimeout()` |
| Max total timeout per transaction | 120 seconds | All callouts combined |
| Max heap size | 6 MB (sync) / 12 MB (async) | Large responses consume heap |

### Security Checklist

- Use Named Credentials for authentication (NEVER hardcode credentials)
- Minimize OAuth scopes to least privilege
- Use Certificate-based auth for high-security integrations
- Validate SSL certificates (don't disable SSL verification)
- Sanitize user input before including in callout payloads
- Log callout errors without exposing sensitive data

### Error Handling Patterns

```apex
try {
    HttpResponse res = makeCallout();
    handleResponse(res);
} catch (System.CalloutException e) {
    // Network error, timeout, SSL error
    logError('Callout failed', e);
} catch (JSONException e) {
    // Malformed JSON response
    logError('JSON parsing failed', e);
} catch (Exception e) {
    // Unexpected error
    logError('Unexpected error', e);
}
```

### Testing Callouts

Use `Test.setMock()` to mock HTTP responses:

```apex
@isTest
private class MyCalloutTest {

    @isTest
    static void testSuccessfulCallout() {
        // Set mock response
        Test.setMock(HttpCalloutMock.class, new MockHttpResponseGenerator());

        Test.startTest();
        Map<String, Object> result = MyService.get('/customers/123');
        Test.stopTest();

        System.assertEquals('customer@example.com', result.get('email'));
    }

    // Mock class
    private class MockHttpResponseGenerator implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setHeader('Content-Type', 'application/json');
            res.setBody('{"email":"customer@example.com"}');
            res.setStatusCode(200);
            return res;
        }
    }
}
```

---

## Related Resources

- [Event Patterns](./event-patterns.md) - Platform Events and Change Data Capture
- [Main Skill Documentation](../SKILL.md) - building-sf-integrations overview
- [Named Credentials Templates](../assets/named-credentials/) - Authentication templates
- [Callout Templates](../assets/callouts/) - Ready-to-use callout patterns
