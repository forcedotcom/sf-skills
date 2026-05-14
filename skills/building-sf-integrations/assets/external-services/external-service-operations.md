# External Service Operations Guide

## Overview

External Services in Salesforce auto-generate Apex classes from OpenAPI specifications, providing type-safe API integrations without manual HTTP code.

## Generated Class Structure

When you register an External Service named `MyAPI`, Salesforce generates:

```
ExternalService.MyAPI                          - Main service class
ExternalService.MyAPI_operationName_Request    - Request wrapper for each operation
ExternalService.MyAPI_operationName_Response   - Response wrapper for each operation
ExternalService.MyAPI_SchemaName               - DTO for each schema in OpenAPI
```

## Basic Usage

### 1. Instantiate the Service

```apex
ExternalService.MyAPI api = new ExternalService.MyAPI();
```

### 2. Call GET Operation

```apex
// Simple GET with path parameter
ExternalService.MyAPI_getCustomer_Response response = api.getCustomer('cust_123');

// Access response data
String customerId = response.id;
String customerName = response.name;
```

### 3. Call POST Operation

```apex
// Create request object
ExternalService.MyAPI_createCustomer_Request request =
    new ExternalService.MyAPI_createCustomer_Request();
request.name = 'Acme Corp';
request.email = 'contact@acme.com';

// Make the call
ExternalService.MyAPI_createCustomer_Response response = api.createCustomer(request);

// Access created resource
String newCustomerId = response.id;
```

### 4. Call PUT/PATCH Operations

```apex
// Update request
ExternalService.MyAPI_updateCustomer_Request request =
    new ExternalService.MyAPI_updateCustomer_Request();
request.customerId = 'cust_123';  // Path parameter
request.name = 'Acme Corporation';  // Body field

ExternalService.MyAPI_updateCustomer_Response response = api.updateCustomer(request);
```

### 5. Call DELETE Operation

```apex
// DELETE usually returns void or simple confirmation
api.deleteCustomer('cust_123');
```

## Error Handling

```apex
try {
    ExternalService.MyAPI api = new ExternalService.MyAPI();
    ExternalService.MyAPI_getCustomer_Response response = api.getCustomer('invalid_id');

} catch (ExternalService.ExternalServiceException e) {
    // API returned error status code
    System.debug('API Error: ' + e.getMessage());
    System.debug('Status Code: ' + e.getStatusCode());
    System.debug('Response Body: ' + e.getBody());

} catch (CalloutException e) {
    // Network/connection error
    System.debug('Callout failed: ' + e.getMessage());
}
```

## Async Usage (Queueable)

External Service calls are still callouts, so use Queueable for trigger contexts:

```apex
public class CustomerSyncQueueable implements Queueable, Database.AllowsCallouts {

    private List<Account> accounts;

    public CustomerSyncQueueable(List<Account> accounts) {
        this.accounts = accounts;
    }

    public void execute(QueueableContext context) {
        ExternalService.MyAPI api = new ExternalService.MyAPI();

        for (Account acc : accounts) {
            try {
                ExternalService.MyAPI_createCustomer_Request req =
                    new ExternalService.MyAPI_createCustomer_Request();
                req.name = acc.Name;
                req.email = acc.Email__c;

                ExternalService.MyAPI_createCustomer_Response resp =
                    api.createCustomer(req);

                // Store external ID on Account
                acc.External_Customer_Id__c = resp.id;

            } catch (Exception e) {
                System.debug('Sync failed for ' + acc.Name + ': ' + e.getMessage());
            }
        }

        update accounts;
    }
}
```

## OpenAPI Schema Tips

### Required Properties

```json
{
  "components": {
    "schemas": {
      "Customer": {
        "type": "object",
        "required": ["name", "email"],
        "properties": {
          "name": { "type": "string" },
          "email": { "type": "string", "format": "email" }
        }
      }
    }
  }
}
```

### Nested Objects

```json
{
  "Customer": {
    "type": "object",
    "properties": {
      "address": {
        "$ref": "#/components/schemas/Address"
      }
    }
  },
  "Address": {
    "type": "object",
    "properties": {
      "street": { "type": "string" },
      "city": { "type": "string" }
    }
  }
}
```

### Arrays

```json
{
  "CustomerList": {
    "type": "object",
    "properties": {
      "customers": {
        "type": "array",
        "items": {
          "$ref": "#/components/schemas/Customer"
        }
      }
    }
  }
}
```

## Limitations

| Limitation | Workaround |
|------------|------------|
| 100 callouts per transaction | Use async (Queueable) with chaining |
| 120s max timeout | Use shorter timeout, implement retry |
| 6MB response size | Paginate responses, compress data |
| Some OpenAPI features not supported | Simplify schema, avoid oneOf/anyOf |

## Refreshing External Service

When the API schema changes:

1. Download updated OpenAPI spec
2. Go to Setup → External Services
3. Edit the service
4. Upload new schema
5. Review generated operations
6. Save and validate

Or via metadata deployment:
1. Update the `<schema>` content in the `.externalServiceRegistration-meta.xml`
2. Deploy with `sf project deploy start`

## Best Practices

1. **Version Your APIs**: Include version in Named Credential endpoint
2. **Handle All Errors**: Catch both `ExternalServiceException` and `CalloutException`
3. **Log Requests/Responses**: For debugging production issues
4. **Use Async**: Always use Queueable when called from DML contexts
5. **Test Thoroughly**: Mock External Service calls in test classes
