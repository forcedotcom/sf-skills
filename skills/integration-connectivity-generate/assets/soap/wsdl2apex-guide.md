# WSDL to Apex Generation Guide

## Overview

Salesforce can automatically generate Apex classes from WSDL (Web Services Description Language) files, enabling integration with SOAP-based web services.

## Step-by-Step Process

### 1. Obtain the WSDL File

Get the WSDL from your external system. Common sources:
- API documentation portal
- Endpoint URL with `?wsdl` suffix (e.g., `https://api.example.com/service?wsdl`)
- Direct download from vendor

### 2. Review WSDL for Compatibility

Salesforce WSDL2Apex has limitations. Check for:

**Supported:**
- Document/literal and RPC/encoded styles
- Simple types (string, integer, boolean, date, etc.)
- Complex types (objects with properties)
- Arrays and lists
- Basic SOAP headers

**Not Supported / Problematic:**
- Very large WSDLs (may hit Apex class size limits)
- Certain complex inheritance patterns
- Some advanced XSD features
- WS-Security (requires manual implementation)

### 3. Generate Apex Classes

1. Navigate to **Setup → Apex Classes**
2. Click **Generate from WSDL**
3. Click **Choose File** and upload the WSDL
4. Review the parse results
5. Modify class names if needed (keep them short to avoid limits)
6. Click **Generate Apex code**

### 4. Generated Class Structure

For a WSDL defining `CustomerService` with operation `getCustomer`:

```
AsyncCustomerService.cls         - Async version of service
CustomerService.cls              - Main stub class with methods
GetCustomerRequest.cls           - Request wrapper
GetCustomerResponse.cls          - Response wrapper
Customer.cls                     - Data type from schema
Address.cls                      - Nested data type
```

### 5. Configure Endpoint Access

**Option A: Named Credential (Recommended)**

1. Create Named Credential in Setup
2. Set endpoint to SOAP service URL
3. Configure authentication (Basic, Certificate, OAuth)
4. In Apex: `stub.endpoint_x = 'callout:MyNamedCredential';`

**Option B: Remote Site Setting**

1. Create Remote Site Setting with domain
2. In Apex: `stub.endpoint_x = 'https://api.example.com/service';`

### 6. Basic Usage Example

```apex
public class CustomerServiceCaller {

    public static Customer getCustomer(String customerId) {
        // Instantiate the generated stub
        CustomerService.CustomerServicePort stub = new CustomerService.CustomerServicePort();

        // Configure endpoint (Named Credential)
        stub.endpoint_x = 'callout:CustomerServiceNC';

        // Set timeout (max 120 seconds)
        stub.timeout_x = 120000;

        // Create request
        GetCustomerRequest request = new GetCustomerRequest();
        request.customerId = customerId;

        // Make the call
        GetCustomerResponse response = stub.getCustomer(request);

        return response.customer;
    }
}
```

### 7. Error Handling

```apex
try {
    GetCustomerResponse response = stub.getCustomer(request);
    // Process response

} catch (CalloutException e) {
    // Network error, timeout, SSL issues
    System.debug('Callout failed: ' + e.getMessage());

} catch (Exception e) {
    // SOAP fault (error from service)
    // The exception message contains SOAP fault details
    System.debug('SOAP error: ' + e.getMessage());
}
```

### 8. Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| `Web service callout failed` | Network/SSL issue | Check Remote Site Setting, verify endpoint |
| `Read timed out` | Service slow to respond | Increase `timeout_x` (max 120000ms) |
| `Apex class size limit` | WSDL too large | Split WSDL, use fewer operations |
| `Unable to parse callout response` | Response doesn't match WSDL | Check service version, update WSDL |
| `Methods defined as Webservice` | Conflict with reserved keywords | Rename operations in WSDL or generated class |

### 9. Testing SOAP Callouts

Use `Test.setMock()` with `WebServiceMock`:

```apex
@isTest
public class CustomerServiceTest {

    @isTest
    static void testGetCustomer() {
        // Set mock
        Test.setMock(WebServiceMock.class, new CustomerServiceMock());

        // Call service
        Test.startTest();
        Customer result = CustomerServiceCaller.getCustomer('CUST001');
        Test.stopTest();

        // Assert
        System.assertEquals('Test Customer', result.name);
    }

    // Mock implementation
    public class CustomerServiceMock implements WebServiceMock {
        public void doInvoke(
            Object stub,
            Object request,
            Map<String, Object> response,
            String endpoint,
            String soapAction,
            String requestName,
            String responseNS,
            String responseName,
            String responseType
        ) {
            // Create mock response
            GetCustomerResponse mockResponse = new GetCustomerResponse();
            mockResponse.customer = new Customer();
            mockResponse.customer.name = 'Test Customer';

            response.put('response_x', mockResponse);
        }
    }
}
```

### 10. Async SOAP Calls

For calls from triggers or after DML:

```apex
public class CustomerSyncQueueable implements Queueable, Database.AllowsCallouts {

    private String customerId;

    public CustomerSyncQueueable(String customerId) {
        this.customerId = customerId;
    }

    public void execute(QueueableContext context) {
        try {
            Customer customer = CustomerServiceCaller.getCustomer(customerId);
            // Process result
        } catch (Exception e) {
            // Log error
        }
    }
}

// Usage in trigger:
System.enqueueJob(new CustomerSyncQueueable(accountId));
```

## Best Practices

1. **Always use Named Credentials** for authentication instead of hardcoding credentials
2. **Set appropriate timeouts** - default may be too short
3. **Implement error handling** - SOAP services can fail in many ways
4. **Log requests and responses** for debugging
5. **Use async patterns** when calling from DML contexts
6. **Test with mocks** - don't call real services in tests
7. **Monitor governor limits** - especially for large responses

## Limitations

- Maximum 100 callouts per transaction
- Maximum 120 second timeout per callout
- Response body limit: 6MB
- Apex code size limits may prevent large WSDL imports
- Some WSDL features not supported (WS-Security, MTOM, etc.)
