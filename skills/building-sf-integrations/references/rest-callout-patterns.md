<!-- Parent: building-sf-integrations/SKILL.md -->
# REST Callout Patterns

## Overview

This guide covers patterns for making HTTP callouts from Salesforce Apex to external REST APIs.

## Synchronous vs Asynchronous

### When to Use Synchronous

- User needs immediate response
- Called from Visualforce, LWC, or Aura
- NOT triggered by DML operations
- Response required before next action

### When to Use Asynchronous

- Called from triggers (REQUIRED)
- Fire-and-forget operations
- Background processing
- Long-running operations

```
┌─────────────────────────────────────────────────────────────────┐
│  CALLOUT CONTEXT DECISION                                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Is this called from a trigger or after DML?                    │
│  ├── YES → Use Queueable with Database.AllowsCallouts          │
│  └── NO  → Synchronous OK                                       │
│                                                                 │
│  Does user need immediate response?                             │
│  ├── YES → Synchronous (if allowed)                            │
│  └── NO  → Consider async for better UX                         │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Basic Request Pattern

```apex
public class RestCallout {

    public static HttpResponse makeRequest(String method, String endpoint, String body) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:MyCredential' + endpoint);
        req.setMethod(method);
        req.setHeader('Content-Type', 'application/json');
        req.setHeader('Accept', 'application/json');
        req.setTimeout(120000); // 120 seconds max

        if (String.isNotBlank(body)) {
            req.setBody(body);
        }

        return new Http().send(req);
    }
}
```

## HTTP Methods

| Method | Use Case | Body |
|--------|----------|------|
| GET | Retrieve resource | No |
| POST | Create resource | Yes |
| PUT | Full update | Yes |
| PATCH | Partial update | Yes |
| DELETE | Remove resource | Usually No |

## Response Handling

### Status Code Categories

```apex
Integer statusCode = response.getStatusCode();

if (statusCode >= 200 && statusCode < 300) {
    // Success (2xx)
} else if (statusCode >= 400 && statusCode < 500) {
    // Client error (4xx) - don't retry
} else if (statusCode >= 500) {
    // Server error (5xx) - may retry
}
```

### Common Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | OK | Process response |
| 201 | Created | Resource created |
| 204 | No Content | Success, no body |
| 400 | Bad Request | Fix request |
| 401 | Unauthorized | Check credentials |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Resource doesn't exist |
| 429 | Too Many Requests | Rate limited, retry later |
| 500 | Server Error | Retry with backoff |
| 503 | Service Unavailable | Retry later |

## Error Handling Pattern

```apex
public class ApiClient {

    public static Map<String, Object> callApi(String endpoint) {
        try {
            HttpResponse res = makeRequest('GET', endpoint, null);

            if (res.getStatusCode() == 200) {
                return (Map<String, Object>) JSON.deserializeUntyped(res.getBody());
            }

            // Handle specific errors
            if (res.getStatusCode() == 404) {
                throw new NotFoundException('Resource not found: ' + endpoint);
            }

            if (res.getStatusCode() == 429) {
                String retryAfter = res.getHeader('Retry-After');
                throw new RateLimitedException('Rate limited. Retry after: ' + retryAfter);
            }

            throw new ApiException('API Error: ' + res.getStatusCode() + ' - ' + res.getBody());

        } catch (CalloutException e) {
            // Network error, timeout, SSL error
            throw new ApiException('Connection failed: ' + e.getMessage(), e);
        }
    }

    public class ApiException extends Exception {}
    public class NotFoundException extends Exception {}
    public class RateLimitedException extends Exception {}
}
```

## Retry Pattern

```apex
public class RetryableCallout {

    private static final Integer MAX_RETRIES = 3;
    private static final Set<Integer> RETRYABLE_CODES = new Set<Integer>{
        408, 429, 500, 502, 503, 504
    };

    public static HttpResponse callWithRetry(HttpRequest request) {
        Integer attempts = 0;

        while (attempts < MAX_RETRIES) {
            HttpResponse res = new Http().send(request);

            if (!RETRYABLE_CODES.contains(res.getStatusCode())) {
                return res;
            }

            attempts++;
            System.debug('Retry ' + attempts + ' for ' + res.getStatusCode());
        }

        throw new CalloutException('Max retries exceeded');
    }
}
```

## Queueable Pattern (Async)

```apex
public class AsyncCallout implements Queueable, Database.AllowsCallouts {

    private Id recordId;

    public AsyncCallout(Id recordId) {
        this.recordId = recordId;
    }

    public void execute(QueueableContext context) {
        // Query record
        Account acc = [SELECT Id, Name FROM Account WHERE Id = :recordId];

        // Make callout
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:MyAPI/accounts');
        req.setMethod('POST');
        req.setBody(JSON.serialize(new Map<String, Object>{
            'name' => acc.Name,
            'sfId' => acc.Id
        }));

        HttpResponse res = new Http().send(req);

        // Update record with result
        if (res.getStatusCode() == 201) {
            acc.External_Id__c = extractId(res.getBody());
            update acc;
        }
    }

    private String extractId(String body) {
        Map<String, Object> result = (Map<String, Object>) JSON.deserializeUntyped(body);
        return (String) result.get('id');
    }
}

// Usage from trigger:
// System.enqueueJob(new AsyncCallout(accountId));
```

## Pagination Pattern

```apex
public class PaginatedApiClient {

    public static List<Map<String, Object>> getAllRecords(String endpoint) {
        List<Map<String, Object>> allRecords = new List<Map<String, Object>>();
        String nextPageUrl = endpoint;

        while (String.isNotBlank(nextPageUrl)) {
            HttpResponse res = makeRequest('GET', nextPageUrl, null);
            Map<String, Object> response = (Map<String, Object>) JSON.deserializeUntyped(res.getBody());

            // Add records from this page
            List<Object> records = (List<Object>) response.get('data');
            for (Object rec : records) {
                allRecords.add((Map<String, Object>) rec);
            }

            // Get next page URL
            nextPageUrl = (String) response.get('nextPage');
        }

        return allRecords;
    }
}
```

## Governor Limits

| Limit | Value |
|-------|-------|
| Callouts per transaction | 100 |
| Maximum timeout | 120,000 ms (120 seconds) |
| Maximum request size | 6 MB |
| Maximum response size | 6 MB |
| Concurrent long-running requests | 10 |

## Testing Callouts

```apex
@isTest
private class ApiClientTest {

    @isTest
    static void testSuccessfulCallout() {
        // Set mock
        Test.setMock(HttpCalloutMock.class, new MockSuccess());

        Test.startTest();
        Map<String, Object> result = ApiClient.callApi('/endpoint');
        Test.stopTest();

        System.assertEquals('value', result.get('key'));
    }

    private class MockSuccess implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest req) {
            HttpResponse res = new HttpResponse();
            res.setStatusCode(200);
            res.setBody('{"key": "value"}');
            return res;
        }
    }
}
```

## Best Practices

1. **Always use Named Credentials** - Never hardcode endpoints or credentials
2. **Set appropriate timeouts** - Default may be too short for slow APIs
3. **Handle all error cases** - Don't assume success
4. **Log requests and responses** - Essential for debugging
5. **Use async for trigger contexts** - Queueable with AllowsCallouts
6. **Implement retry logic** - For transient failures
7. **Monitor governor limits** - Especially callout count
8. **Parse errors gracefully** - APIs return errors in various formats
