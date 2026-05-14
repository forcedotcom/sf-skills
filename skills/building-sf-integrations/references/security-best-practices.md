<!-- Parent: building-sf-integrations/SKILL.md -->
# Integration Security Best Practices

## Overview

Security is critical for integrations. This guide covers best practices for securing Salesforce integrations with external systems.

## Credential Management

### DO: Use Named Credentials

```apex
// ✅ CORRECT - Named Credential handles auth
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:MySecureAPI/resource');
```

### DON'T: Hardcode Credentials

```apex
// ❌ WRONG - Never hardcode credentials
req.setHeader('Authorization', 'Bearer sk_live_abc123...');
req.setEndpoint('https://api.example.com');
```

### Credential Storage Rules

| Item | Storage Location | Never Store In |
|------|------------------|----------------|
| API Keys | Named Credential | Apex code, Custom Settings |
| Client Secrets | Named Credential / External Credential | Source control |
| Certificates | Certificate & Key Management | Static Resources |
| Passwords | Named Credential | Custom Metadata |

## OAuth Best Practices

### Scope Minimization

Request only necessary scopes:

```
✅ read:orders write:orders
❌ admin:* read:* write:*
```

### Token Handling

- Never log access tokens
- Don't expose tokens in error messages
- Use short-lived tokens when possible
- Implement token refresh handling

### PKCE for Public Clients

For mobile or SPA clients:

```
Use Authorization Code with PKCE, not Implicit flow
```

## Network Security

### Remote Site Settings

- Only allow necessary domains
- Don't use wildcard domains
- Review and audit regularly

### Certificate Validation

- Use trusted CA certificates
- Don't disable SSL/TLS verification
- Monitor certificate expiration

### IP Restrictions

For Connected Apps:
- Configure IP relaxation carefully
- Use "Enforce IP restrictions" when possible

## Input Validation

### Validate External Data

```apex
// Validate before processing
public static void processExternalData(String externalId) {
    // Validate format
    if (!Pattern.matches('[A-Za-z0-9]{10,20}', externalId)) {
        throw new ValidationException('Invalid external ID format');
    }

    // Sanitize for SOQL
    String safeId = String.escapeSingleQuotes(externalId);
}
```

### Output Encoding

```apex
// Encode data sent to external systems
String encodedData = EncodingUtil.urlEncode(userData, 'UTF-8');
```

## Error Handling Security

### Don't Expose Internal Details

```apex
// ❌ WRONG - Exposes internal structure
throw new CalloutException('Failed: ' + response.getBody());

// ✅ CORRECT - User-friendly, log details separately
System.debug(LoggingLevel.ERROR, 'API Error: ' + response.getBody());
throw new CalloutException('Unable to complete request. Contact support.');
```

### Log Securely

```apex
// ❌ WRONG - Logs sensitive data
System.debug('Request: ' + JSON.serialize(request)); // May contain PII

// ✅ CORRECT - Redact sensitive fields
System.debug('Request to: ' + endpoint + ', Status: ' + statusCode);
```

## API Security Patterns

### Rate Limiting Awareness

```apex
if (response.getStatusCode() == 429) {
    String retryAfter = response.getHeader('Retry-After');
    // Implement backoff, don't hammer the API
}
```

### Idempotency Keys

For POST requests that shouldn't duplicate:

```apex
req.setHeader('Idempotency-Key', generateUniqueKey());
```

### Request Signing

For APIs requiring signature:

```apex
String signature = generateHmacSignature(payload, secretKey);
req.setHeader('X-Signature', signature);
```

## User Context Security

### Per-User vs Named Principal

| Scenario | Use |
|----------|-----|
| User-specific data access | Per-User Principal |
| Background/batch jobs | Named Principal |
| Service integrations | Named Principal |
| User-initiated with audit | Per-User Principal |

### Audit Logging

```apex
public static void logIntegrationActivity(String operation, Id userId, String externalSystem) {
    Integration_Log__c log = new Integration_Log__c(
        Operation__c = operation,
        User__c = userId,
        External_System__c = externalSystem,
        Timestamp__c = Datetime.now()
    );
    insert log;
}
```

## Platform Event Security

### Sensitive Data in Events

- Don't include PII in event payloads when avoidable
- Use record IDs and query for details
- Consider encryption for sensitive fields

### Event Consumer Validation

```apex
trigger SecureEventHandler on My_Event__e (after insert) {
    for (My_Event__e event : Trigger.new) {
        // Validate event source/origin if possible
        if (!isValidEventSource(event)) {
            System.debug(LoggingLevel.WARN, 'Suspicious event: ' + event.ReplayId);
            continue;
        }
        processEvent(event);
    }
}
```

## Security Checklist

### Before Deployment

- [ ] Named Credentials used for all external calls
- [ ] No hardcoded credentials in code
- [ ] OAuth scopes minimized
- [ ] Remote Site Settings restricted
- [ ] Error messages don't expose internals
- [ ] Sensitive data not logged
- [ ] Input validation implemented
- [ ] Rate limiting handled
- [ ] Certificate expiration monitored

### Regular Review

- [ ] Audit Named Credential usage
- [ ] Review integration user permissions
- [ ] Check for unused credentials
- [ ] Monitor integration error logs
- [ ] Validate certificate validity
- [ ] Review OAuth app authorizations

## Compliance Considerations

### GDPR / Data Privacy

- Minimize data transferred
- Document data flows
- Implement data deletion for integrated records
- Encrypt PII in transit and at rest

### SOC 2 / Security Audits

- Maintain integration documentation
- Log all external access
- Implement change management
- Regular security assessments

### HIPAA (Healthcare)

- Business Associate Agreements
- Encryption requirements
- Access logging
- Minimum necessary standard
