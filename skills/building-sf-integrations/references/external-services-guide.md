<!-- Parent: building-sf-integrations/SKILL.md -->
# External Services Guide

## Overview

External Services in Salesforce automatically generate Apex classes from OpenAPI (Swagger) specifications, enabling type-safe REST API integrations without writing HTTP code.

## How It Works

```
┌─────────────────────────────────────────────────────────────────┐
│  EXTERNAL SERVICE FLOW                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  1. OpenAPI Spec (JSON/YAML)                                    │
│     ↓                                                           │
│  2. External Service Registration (Metadata)                    │
│     ↓                                                           │
│  3. Auto-generated Apex Classes                                 │
│     ↓                                                           │
│  4. Type-safe API calls from Apex                              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Prerequisites

1. **Named Credential** configured for authentication
2. **OpenAPI Specification** (2.0 or 3.0) for the API
3. **API Version 48.0+** (Winter '20)

## Creating External Service

### Via Setup UI

1. Go to **Setup → External Services**
2. Click **New External Service**
3. Provide name and description
4. Select **Named Credential**
5. Upload or paste OpenAPI spec
6. Review operations
7. Save

### Via Metadata API

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExternalServiceRegistration xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Stripe API</label>
    <description>Stripe payment processing API</description>
    <namedCredential>Stripe_API</namedCredential>
    <schemaType>OpenApi3</schemaType>
    <schema>
{
  "openapi": "3.0.0",
  "info": { "title": "Stripe API", "version": "1.0" },
  "paths": { ... }
}
    </schema>
    <status>Complete</status>
</ExternalServiceRegistration>
```

## Generated Classes

For an External Service named "StripeAPI":

| Class | Purpose |
|-------|---------|
| `ExternalService.StripeAPI` | Main service class with operation methods |
| `ExternalService.StripeAPI_createCustomer_Request` | Request wrapper |
| `ExternalService.StripeAPI_createCustomer_Response` | Response wrapper |
| `ExternalService.StripeAPI_Customer` | DTO matching schema |

## Usage Patterns

### Basic GET Request

```apex
// Instantiate service
ExternalService.StripeAPI stripe = new ExternalService.StripeAPI();

// Call GET operation
ExternalService.StripeAPI_getCustomer_Response response =
    stripe.getCustomer('cus_ABC123');

// Access response data
String email = response.email;
```

### POST with Request Body

```apex
// Create request object
ExternalService.StripeAPI_createCustomer_Request request =
    new ExternalService.StripeAPI_createCustomer_Request();
request.email = 'customer@example.com';
request.name = 'John Doe';

// Make call
ExternalService.StripeAPI_createCustomer_Response response =
    stripe.createCustomer(request);

// Get created resource ID
String customerId = response.id;
```

### Handling Nested Objects

```apex
// Access nested data
ExternalService.StripeAPI_Address address = response.address;
String city = address.city;
String postalCode = address.postalCode;
```

## Error Handling

```apex
try {
    ExternalService.StripeAPI stripe = new ExternalService.StripeAPI();
    response = stripe.getCustomer('invalid_id');

} catch (ExternalService.ExternalServiceException e) {
    // API returned error response
    System.debug('Status Code: ' + e.getStatusCode());
    System.debug('Error Body: ' + e.getBody());
    System.debug('Error Message: ' + e.getMessage());

} catch (CalloutException e) {
    // Network/connection error
    System.debug('Connection failed: ' + e.getMessage());
}
```

## Async Calls (Queueable)

Use Queueable for calls from triggers:

```apex
public class StripeCustomerSync implements Queueable, Database.AllowsCallouts {

    private Account account;

    public StripeCustomerSync(Account account) {
        this.account = account;
    }

    public void execute(QueueableContext context) {
        ExternalService.StripeAPI stripe = new ExternalService.StripeAPI();

        ExternalService.StripeAPI_createCustomer_Request req =
            new ExternalService.StripeAPI_createCustomer_Request();
        req.email = account.Email__c;
        req.name = account.Name;

        try {
            ExternalService.StripeAPI_createCustomer_Response resp =
                stripe.createCustomer(req);

            account.Stripe_Customer_Id__c = resp.id;
            update account;
        } catch (Exception e) {
            System.debug('Sync failed: ' + e.getMessage());
        }
    }
}
```

## OpenAPI Schema Tips

### Supported Features

- GET, POST, PUT, PATCH, DELETE methods
- Path and query parameters
- Request and response bodies
- JSON schema types (string, number, boolean, object, array)
- References ($ref)
- Basic authentication headers

### Limitations

- **No file uploads** (multipart/form-data limited)
- **No WebSockets** (HTTP only)
- **No streaming responses**
- **Some complex schemas** may not parse
- **Maximum schema size** limited

### Schema Best Practices

```json
{
  "openapi": "3.0.0",
  "info": {
    "title": "My API",
    "version": "1.0.0"
  },
  "paths": {
    "/customers/{id}": {
      "get": {
        "operationId": "getCustomer",
        "parameters": [
          {
            "name": "id",
            "in": "path",
            "required": true,
            "schema": { "type": "string" }
          }
        ],
        "responses": {
          "200": {
            "description": "Success",
            "content": {
              "application/json": {
                "schema": { "$ref": "#/components/schemas/Customer" }
              }
            }
          }
        }
      }
    }
  },
  "components": {
    "schemas": {
      "Customer": {
        "type": "object",
        "properties": {
          "id": { "type": "string" },
          "email": { "type": "string" }
        }
      }
    }
  }
}
```

## Updating External Service

When API changes:

1. Get updated OpenAPI spec
2. Go to Setup → External Services
3. Edit service
4. Upload new schema
5. Review changes to operations
6. Save and validate
7. Update calling code if signatures changed

## Testing

```apex
@isTest
private class StripeIntegrationTest {

    @isTest
    static void testCreateCustomer() {
        // Set mock
        Test.setMock(HttpCalloutMock.class, new StripeMock());

        Test.startTest();

        ExternalService.StripeAPI stripe = new ExternalService.StripeAPI();
        ExternalService.StripeAPI_createCustomer_Request req =
            new ExternalService.StripeAPI_createCustomer_Request();
        req.email = 'test@example.com';

        ExternalService.StripeAPI_createCustomer_Response resp =
            stripe.createCustomer(req);

        Test.stopTest();

        System.assertEquals('cus_test123', resp.id);
    }

    private class StripeMock implements HttpCalloutMock {
        public HttpResponse respond(HttpRequest request) {
            HttpResponse response = new HttpResponse();
            response.setStatusCode(201);
            response.setBody('{"id": "cus_test123", "email": "test@example.com"}');
            return response;
        }
    }
}
```

## Use with Agentforce

External Services are ideal for Agent Actions:

1. Create External Service from API spec
2. Create Flow that calls External Service
3. Reference Flow in Agent Script action

```agentscript
actions:
    lookup_customer:
        description: "Looks up customer in payment system"
        inputs:
            customer_email: string
        outputs:
            customer_id: string
        target: "flow://Lookup_Stripe_Customer"
```
