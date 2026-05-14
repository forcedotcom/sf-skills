<!-- Parent: building-sf-integrations/SKILL.md -->
# Named Credentials Guide

## Overview

Named Credentials provide secure storage of authentication credentials and endpoint URLs for external system integrations. They eliminate the need to hardcode credentials in Apex code.

## Architecture Evolution

### Legacy Named Credentials (Pre-API 61)

- Single principal per credential
- Authentication configured directly on Named Credential
- Simpler setup but less flexible

### External Credentials (API 61+)

- Separate External Credential and Named Credential
- Named Principal and Per-User Principal support
- Permission Set-based access control
- More secure and flexible

```
┌─────────────────────────────────────────────────────────────────┐
│  CREDENTIAL ARCHITECTURE (API 61+)                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  External Credential                                            │
│  ├── Authentication Protocol (OAuth, JWT, Custom)               │
│  ├── OAuth/JWT Parameters                                       │
│  └── Principals                                                 │
│      ├── Named Principal (shared service account)               │
│      └── Per-User Principal (individual auth)                   │
│                                                                 │
│  Named Credential                                               │
│  ├── Endpoint URL                                               │
│  └── References External Credential                             │
│                                                                 │
│  Permission Set                                                 │
│  └── External Credential Principal Access                       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Authentication Types

### 1. OAuth 2.0 Client Credentials

**Use Case**: Server-to-server integration without user context

```apex
// Apex usage - Named Credential handles auth automatically
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:MyOAuthCredential/api/resource');
req.setMethod('GET');
// Authorization header added automatically
```

**Setup**:
1. Create Auth Provider (optional, for complex OAuth)
2. Create Named Credential with OAuth protocol
3. Enter Client ID and Client Secret via UI

### 2. OAuth 2.0 JWT Bearer

**Use Case**: Certificate-based server-to-server auth

**Prerequisites**:
- Certificate in Setup → Certificate and Key Management
- Connected App configured for JWT Bearer
- External system configured to trust certificate

**Flow**:
1. Salesforce creates JWT with claims (iss, sub, aud, exp)
2. JWT signed with certificate private key
3. JWT exchanged for access token
4. Access token used for API calls

### 3. Certificate-Based (Mutual TLS)

**Use Case**: High-security integrations requiring client certificate

**Setup**:
1. Obtain client certificate from CA or external system
2. Import to Setup → Certificate and Key Management
3. Configure Named Credential with certificate
4. External system must trust Salesforce's certificate

### 4. Basic Auth / API Key

**Use Case**: Simple APIs, internal systems

**Pattern for API Key**:
```apex
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:MyCredential/api/resource');
req.setHeader('X-API-Key', '{!$Credential.Password}');
```

## Best Practices

### DO

- **Use Named Credentials** for ALL external callouts
- **Rotate credentials** regularly using Named Credential update
- **Use External Credentials** (API 61+) for new development
- **Limit OAuth scopes** to minimum required
- **Use Per-User Principal** when user context matters
- **Test credentials** before deployment

### DON'T

- **Never hardcode** credentials in Apex
- **Never commit** credentials to source control
- **Don't share** service account credentials across environments
- **Don't use** overly broad OAuth scopes

## Common Patterns

### Pattern 1: Service Integration

```apex
public class ExternalServiceCallout {
    public static HttpResponse callService(String endpoint, String body) {
        HttpRequest req = new HttpRequest();
        req.setEndpoint('callout:ServiceCredential' + endpoint);
        req.setMethod('POST');
        req.setHeader('Content-Type', 'application/json');
        req.setBody(body);
        return new Http().send(req);
    }
}
```

### Pattern 2: Multiple Environments

```
Named Credentials:
├── MyAPI_Dev     → https://api-dev.example.com
├── MyAPI_UAT     → https://api-uat.example.com
└── MyAPI_Prod    → https://api.example.com
```

Use Custom Metadata or Custom Settings to select credential by environment.

### Pattern 3: Per-User OAuth (API 61+)

For APIs requiring user-specific authentication:

1. Create External Credential with Per-User Principal
2. Create Named Credential referencing External Credential
3. Users authenticate individually via OAuth flow
4. Each user's callouts use their own token

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `Named credential not found` | Credential doesn't exist or wrong name | Verify credential name in Setup |
| `Authentication failed` | Invalid credentials | Update credentials via Setup UI |
| `Insufficient privileges` | User lacks permission | Assign Permission Set with External Credential Principal Access |
| `Connection refused` | Network/firewall issue | Check Remote Site Settings, firewall rules |
| `Certificate error` | SSL/TLS issue | Verify certificate chain, expiration |

## Migration: Legacy to External Credentials

1. **Create External Credential** with same auth parameters
2. **Create new Named Credential** referencing External Credential
3. **Create Permission Set** with External Credential Principal Access
4. **Assign Permission Set** to integration users
5. **Update Apex code** to use new Named Credential
6. **Test thoroughly** before decommissioning legacy credential
7. **Delete legacy** Named Credential after validation
