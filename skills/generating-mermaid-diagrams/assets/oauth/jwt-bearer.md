# JWT Bearer Flow Template

OAuth 2.0 JWT Bearer assertion flow for server-to-server authentication without user interaction.

## When to Use
- Server-to-server integrations
- CI/CD pipelines
- Scheduled jobs and automation
- Background processes
- Any headless authentication scenario

## Prerequisites
1. X.509 Certificate uploaded to Salesforce Connected App
2. Pre-authorized user via Permission Set
3. Private key securely stored on server

## Mermaid Template

```mermaid
%%{init: {'theme': 'base', 'themeVariables': {
  'actorBkg': '#ddd6fe',
  'actorTextColor': '#1f2937',
  'actorBorder': '#6d28d9',
  'signalColor': '#334155',
  'signalTextColor': '#1f2937',
  'noteBkgColor': '#f8fafc',
  'noteTextColor': '#1f2937',
  'noteBorderColor': '#334155'
}}}%%
sequenceDiagram
    autonumber

    box rgba(221,214,254,0.3) SERVER ENVIRONMENT
        participant S as 🖥️ Server<br/>(CI/CD, Backend)
        participant K as 🔐 Key Store
    end

    box rgba(167,243,208,0.3) SALESFORCE
        participant SF as ☁️ Salesforce<br/>Authorization Server
    end

    Note over S,SF: JWT Bearer Flow (RFC 7523)

    S->>K: 1. Retrieve Private Key
    K->>S: 2. Return Private Key

    S->>S: 3. Create JWT Header
    Note over S: {<br/>  "alg": "RS256",<br/>  "typ": "JWT"<br/>}

    S->>S: 4. Create JWT Payload
    Note over S: {<br/>  "iss": "CONSUMER_KEY",<br/>  "sub": "user@company.com",<br/>  "aud": "https://login.salesforce.com",<br/>  "exp": CURRENT_TIME + 300<br/>}

    S->>S: 5. Sign JWT with Private Key
    Note over S: signature = RS256(header.payload, privateKey)<br/>jwt = header.payload.signature

    S->>SF: 6. POST /services/oauth2/token
    Note over S,SF: grant_type=urn:ietf:params:oauth:<br/>          grant-type:jwt-bearer<br/>assertion=SIGNED_JWT

    SF->>SF: 7. Decode JWT

    SF->>SF: 8. Validate Signature
    Note over SF: Verify using uploaded<br/>X.509 certificate

    SF->>SF: 9. Validate Claims
    Note over SF: • iss matches Consumer Key<br/>• sub is pre-authorized user<br/>• aud is correct endpoint<br/>• exp is not passed

    SF->>SF: 10. Check User Authorization
    Note over SF: User must be pre-authorized<br/>via Permission Set

    SF->>S: 11. Return Access Token
    Note over SF,S: {<br/>  "access_token": "...",<br/>  "instance_url": "https://...",<br/>  "token_type": "Bearer",<br/>  "issued_at": "...",<br/>  "scope": "api"<br/>}

    Note over S: ⚠️ No refresh_token returned

    S->>S: 12. Store Access Token

    S->>SF: 13. Make API Calls
    Note over S,SF: Authorization: Bearer ACCESS_TOKEN

    SF->>S: 14. API Response
```

## ASCII Fallback Template

```
┌───────────────────────┐     ┌────────────────────┐
│     Server/CI/CD      │     │     Salesforce     │
│    (Private Key)      │     │   (Certificate)    │
└───────────┬───────────┘     └─────────┬──────────┘
            │                           │
            │  1. Create JWT Claims     │
            │     iss: consumer_key     │
            │     sub: user@company.com │
            │     aud: login.sf.com     │
            │     exp: now + 5 min      │
            │                           │
            │  2. Sign JWT with         │
            │     Private Key (RS256)   │
            │                           │
            │  3. POST /token           │
            │     (grant_type=jwt-bearer)
            │     (assertion=signed_jwt)│
            │──────────────────────────>│
            │                           │
            │           4. Verify JWT   │
            │              signature    │
            │              with cert    │
            │                           │
            │           5. Validate     │
            │              claims       │
            │                           │
            │           6. Check user   │
            │              pre-auth     │
            │                           │
            │  7. Access Token          │
            │     (NO refresh token!)   │
            │<──────────────────────────│
            │                           │
            │  8. API Request           │
            │     (Bearer token)        │
            │──────────────────────────>│
            │                           │
            │  9. API Response          │
            │<──────────────────────────│
```

## JWT Structure

### Header
```json
{
  "alg": "RS256",
  "typ": "JWT"
}
```

### Payload (Claims)
```json
{
  "iss": "3MVG9...",          // Consumer Key from Connected App
  "sub": "user@company.com",   // Pre-authorized username
  "aud": "https://login.salesforce.com",  // Or test.salesforce.com for sandbox
  "exp": 1702123456            // Expiration (current time + 5 min max)
}
```

### Signature
```
RS256(
  base64URLEncode(header) + "." + base64URLEncode(payload),
  privateKey
)
```

## Token Request

```bash
curl -X POST https://login.salesforce.com/services/oauth2/token \
  -d "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" \
  -d "assertion=eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiIzTVZHOS4uLiIsInN1YiI6InVzZXJAY29tcGFueS5jb20iLCJhdWQiOiJodHRwczovL2xvZ2luLnNhbGVzZm9yY2UuY29tIiwiZXhwIjoxNzAyMTIzNDU2fQ.SIGNATURE"
```

## Code Examples

### Python
```python
import jwt
import time
import requests

private_key = open('server.key').read()

claim_set = {
    'iss': 'YOUR_CONSUMER_KEY',
    'sub': 'user@company.com',
    'aud': 'https://login.salesforce.com',
    'exp': int(time.time()) + 300  # 5 minutes
}

assertion = jwt.encode(claim_set, private_key, algorithm='RS256')

response = requests.post(
    'https://login.salesforce.com/services/oauth2/token',
    data={
        'grant_type': 'urn:ietf:params:oauth:grant-type:jwt-bearer',
        'assertion': assertion
    }
)

access_token = response.json()['access_token']
instance_url = response.json()['instance_url']
```

### Node.js
```javascript
const jwt = require('jsonwebtoken');
const axios = require('axios');
const fs = require('fs');

const privateKey = fs.readFileSync('server.key');

const token = jwt.sign(
  {
    iss: 'YOUR_CONSUMER_KEY',
    sub: 'user@company.com',
    aud: 'https://login.salesforce.com',
    exp: Math.floor(Date.now() / 1000) + 300
  },
  privateKey,
  { algorithm: 'RS256' }
);

const response = await axios.post(
  'https://login.salesforce.com/services/oauth2/token',
  new URLSearchParams({
    grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
    assertion: token
  })
);

const { access_token, instance_url } = response.data;
```

## Key Characteristics

| Aspect | Value |
|--------|-------|
| User Interaction | None required |
| Refresh Token | **Not returned** - re-authenticate with new JWT |
| Token Lifetime | Default ~2 hours (configurable) |
| Security Model | Certificate-based (asymmetric) |
| Audience | `login.salesforce.com` or `test.salesforce.com` |

## Security Considerations

1. **Protect private key** - Use secrets manager, HSM, or secure vault
2. **Rotate certificates** before expiration
3. **Short JWT expiration** - Maximum 5 minutes recommended
4. **Limit user permissions** - Use dedicated integration user
5. **Monitor token usage** - Set up login history alerts

## Troubleshooting

| Error | Cause | Solution |
|-------|-------|----------|
| `invalid_grant` | JWT expired or invalid | Check exp claim, verify signature |
| `invalid_client` | Consumer key mismatch | Verify iss matches Connected App |
| `user_not_authorized` | User not pre-approved | Assign Permission Set to user |
| `invalid_assertion` | Signature verification failed | Verify certificate upload |

## Customization Points

Replace these placeholders:
- `CONSUMER_KEY` → Your Connected App's Consumer Key
- `user@company.com` → Pre-authorized Salesforce username
- `login.salesforce.com` → Or `test.salesforce.com` for sandbox
