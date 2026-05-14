<!-- Parent: configuring-connected-apps/SKILL.md -->
# OAuth Flows Reference for Connected Apps

Detailed OAuth flow patterns, configuration examples, and implementation guidance for the configuring-connected-apps skill.

---

## Flow Selection Decision Tree

```
START
│
├─ Do you have a backend server?
│  ├─ YES: Can it securely store secrets?
│  │  ├─ YES: Authorization Code Flow (Web Server)
│  │  └─ NO: Authorization Code + PKCE (SPA/Mobile)
│  │
│  └─ NO: Is this server-to-server?
│     ├─ YES: JWT Bearer Flow
│     └─ NO: Device Authorization Flow (CLI/IoT)
│
└─ Is this for a specific integration user?
   ├─ YES: JWT Bearer Flow
   └─ NO: Authorization Code Flow
```

---

## Authorization Code Flow (Web Server)

### When to Use
- Web applications with backend server
- Can securely store consumer secret
- User-interactive flow needed
- Examples: Portal, Integration Hub, Admin Console

### Connected App Configuration

**Minimal scopes for API access**:
```xml
<oauthConfig>
    <callbackUrl>https://app.example.com/oauth/callback</callbackUrl>
    <scopes>Api</scopes>
    <scopes>RefreshToken</scopes>
    <isConsumerSecretOptional>false</isConsumerSecretOptional>
</oauthConfig>
```

**With OpenID Connect**:
```xml
<oauthConfig>
    <callbackUrl>https://app.example.com/oauth/callback</callbackUrl>
    <scopes>Api</scopes>
    <scopes>RefreshToken</scopes>
    <scopes>OpenID</scopes>
    <isIdTokenEnabled>true</isIdTokenEnabled>
    <isConsumerSecretOptional>false</isConsumerSecretOptional>
</oauthConfig>
```

### Security Checklist
- [ ] HTTPS callback URL (no localhost in production)
- [ ] Consumer secret stored in environment variables (never in code)
- [ ] State parameter validated (CSRF protection)
- [ ] Authorization code used only once
- [ ] Refresh token rotation enabled
- [ ] IP restrictions configured (optional)

### Common Issues

**Problem**: "redirect_uri_mismatch" error
- **Cause**: Callback URL doesn't match exactly
- **Fix**: Ensure exact match including protocol, domain, path, and query parameters

**Problem**: "invalid_client_id" error
- **Cause**: Consumer key incorrect or app not deployed
- **Fix**: Verify consumer key from Setup > App Manager

---

## Authorization Code + PKCE (Public Clients)

### When to Use
- Single Page Applications (React, Vue, Angular)
- Mobile apps (iOS, Android)
- Desktop apps
- Any client that cannot securely store secrets

### Connected App Configuration

```xml
<oauthConfig>
    <callbackUrl>myapp://oauth/callback</callbackUrl>
    <scopes>Api</scopes>
    <scopes>RefreshToken</scopes>
    <isConsumerSecretOptional>true</isConsumerSecretOptional>
    <isPkceRequired>true</isPkceRequired>
</oauthConfig>

<oauthPolicy>
    <refreshTokenPolicy>infinite</refreshTokenPolicy>
    <isRefreshTokenRotationEnabled>true</isRefreshTokenRotationEnabled>
</oauthPolicy>
```

### External Client App Configuration

```xml
<!-- ecaGlblOauth-meta.xml -->
<ExtlClntAppGlobalOauthSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <callbackUrl>myapp://oauth/callback</callbackUrl>
    <externalClientApplication>MyMobileApp</externalClientApplication>
    <isConsumerSecretOptional>true</isConsumerSecretOptional>
    <isPkceRequired>true</isPkceRequired>
    <isSecretRequiredForRefreshToken>false</isSecretRequiredForRefreshToken>
    <label>Mobile App OAuth Settings</label>
</ExtlClntAppGlobalOauthSettings>
```

### Implementation Pattern (JavaScript)

```javascript
// Generate PKCE verifier and challenge
function generatePKCE() {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  const codeVerifier = base64URLEncode(array);

  return crypto.subtle.digest('SHA-256', new TextEncoder().encode(codeVerifier))
    .then(buffer => ({
      codeVerifier,
      codeChallenge: base64URLEncode(new Uint8Array(buffer))
    }));
}

// Store verifier in sessionStorage (cleared on close)
const { codeVerifier, codeChallenge } = await generatePKCE();
sessionStorage.setItem('pkce_verifier', codeVerifier);

// Authorization URL
const authUrl = `https://login.salesforce.com/services/oauth2/authorize?` +
  `response_type=code` +
  `&client_id=${CLIENT_ID}` +
  `&redirect_uri=${REDIRECT_URI}` +
  `&scope=api%20refresh_token` +
  `&state=${STATE}` +
  `&code_challenge=${codeChallenge}` +
  `&code_challenge_method=S256`;
```

### Security Checklist
- [ ] PKCE required in Connected App config
- [ ] Consumer secret optional
- [ ] Refresh token rotation enabled
- [ ] Code verifier stored securely (sessionStorage, keychain)
- [ ] State parameter validated
- [ ] Deep link callback handled securely (mobile)

---

## JWT Bearer Flow (Server-to-Server)

### When to Use
- CI/CD pipelines (GitHub Actions, Jenkins)
- Backend integrations without user interaction
- Service accounts
- Scheduled jobs

### Prerequisites

**1. Generate X.509 Certificate**:
```bash
# Generate private key
openssl genrsa -out server.key 2048

# Generate certificate signing request
openssl req -new -key server.key -out server.csr

# Self-sign certificate (valid 1 year)
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt
```

**2. Upload to Salesforce**:
- Setup > Certificate and Key Management > Create Self-Signed Certificate
- Or use the certificate from step 1

### Connected App Configuration

```xml
<oauthConfig>
    <certificate>JWTAuthCertificate</certificate>
    <consumerKey>AUTO_GENERATED</consumerKey>
    <scopes>Api</scopes>
    <scopes>Web</scopes>
    <isAdminApproved>true</isAdminApproved>
</oauthConfig>

<oauthPolicy>
    <ipRelaxation>ENFORCE</ipRelaxation>
</oauthPolicy>
```

**Important**: No `callbackUrl` needed for JWT Bearer flow.

### Pre-Authorization

**Option 1: Permission Set**
```xml
<!-- permissionsets/IntegrationUser.permissionset-meta.xml -->
<PermissionSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>API Integration User</label>
    <connectedAppSettings>
        <connectedApp>MyJWTApp</connectedApp>
        <enabled>true</enabled>
    </connectedAppSettings>
    <hasActivationRequired>false</hasActivationRequired>
</PermissionSet>
```

Assign to integration user: Setup > Users > [User] > Permission Set Assignments

**Option 2: Profile**
Setup > Manage Connected Apps > [App] > Edit Policies > Permitted Users = "Admin approved users are pre-authorized"

### Implementation Pattern (Node.js)

```javascript
const jwt = require('jsonwebtoken');
const axios = require('axios');
const fs = require('fs');

async function getAccessToken() {
  const privateKey = fs.readFileSync('server.key', 'utf8');

  const claims = {
    iss: process.env.CONSUMER_KEY,
    sub: 'integration@company.com', // Pre-authorized user
    aud: 'https://login.salesforce.com',
    exp: Math.floor(Date.now() / 1000) + 300 // 5 min
  };

  const assertion = jwt.sign(claims, privateKey, { algorithm: 'RS256' });

  const response = await axios.post('https://login.salesforce.com/services/oauth2/token',
    new URLSearchParams({
      grant_type: 'urn:ietf:params:oauth:grant-type:jwt-bearer',
      assertion: assertion
    })
  );

  return response.data.access_token;
}
```

### Security Checklist
- [ ] Private key stored securely (secrets manager, not in repo)
- [ ] Certificate uploaded to Salesforce
- [ ] User pre-authorized via Permission Set
- [ ] IP restrictions configured
- [ ] Token expiration set (exp claim)
- [ ] Audience (aud) set correctly (login vs test.salesforce.com)

### Common Issues

**Problem**: "user hasn't approved this consumer" error
- **Cause**: User not pre-authorized
- **Fix**: Assign Permission Set or configure admin pre-approval

**Problem**: "invalid_grant" error
- **Cause**: Certificate mismatch or expired token
- **Fix**: Verify certificate name matches `<certificate>` tag, check exp claim

---

## Device Authorization Flow

### When to Use
- CLI tools (sf CLI, custom CLIs)
- Smart TVs, Set-top boxes
- IoT devices without keyboard
- Any device with limited input capability

### Connected App Configuration

```xml
<oauthConfig>
    <callbackUrl>http://localhost:8080</callbackUrl>
    <scopes>Api</scopes>
    <scopes>RefreshToken</scopes>
    <isConsumerSecretOptional>true</isConsumerSecretOptional>
</oauthConfig>
```

### Implementation Pattern (Python)

```python
import requests
import time

CLIENT_ID = 'your_consumer_key'
DEVICE_CODE_URL = 'https://login.salesforce.com/services/oauth2/device/code'
TOKEN_URL = 'https://login.salesforce.com/services/oauth2/token'

# Step 1: Request device code
response = requests.post(DEVICE_CODE_URL, data={
    'client_id': CLIENT_ID,
    'scope': 'api refresh_token'
})
data = response.json()

# Step 2: Display user code
print(f"Visit: {data['verification_uri']}")
print(f"Enter code: {data['user_code']}")

# Step 3: Poll for token
device_code = data['device_code']
interval = data['interval']  # Polling interval in seconds

while True:
    time.sleep(interval)

    token_response = requests.post(TOKEN_URL, data={
        'grant_type': 'urn:ietf:params:oauth:grant-type:device_code',
        'client_id': CLIENT_ID,
        'code': device_code
    })

    if token_response.status_code == 200:
        tokens = token_response.json()
        print(f"Access Token: {tokens['access_token']}")
        break
    elif token_response.json().get('error') == 'authorization_pending':
        continue  # User hasn't authorized yet
    else:
        print(f"Error: {token_response.json()}")
        break
```

### Security Checklist
- [ ] Consumer secret optional
- [ ] Polling interval respected (don't spam)
- [ ] Device code expires after timeout
- [ ] Refresh token stored securely

---

## Client Credentials Flow (ECA Only)

### When to Use
- Service accounts (not tied to specific user)
- Background processes
- Microservices
- Requires External Client App (not available in Connected Apps)

### External Client App Configuration

```xml
<!-- extlClntAppOauthSettings/MyServiceApp.ecaOauth-meta.xml -->
<ExtlClntAppOauthSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <commaSeparatedOauthScopes>Api</commaSeparatedOauthScopes>
    <externalClientApplication>MyServiceApp</externalClientApplication>
    <label>Service OAuth Settings</label>
</ExtlClntAppOauthSettings>
```

**Source-control note:** if you also need to manage client-credentials security settings in source, retrieve `ExtlClntAppOauthSecuritySettings:MyServiceApp` from an org first and commit the retrieved `.ecaOauthSecurity-meta.xml` file as your starting point.

### Implementation Pattern

```bash
curl -X POST https://login.salesforce.com/services/oauth2/token \
  -d "grant_type=client_credentials" \
  -d "client_id=<CONSUMER_KEY>" \
  -d "client_secret=<CONSUMER_SECRET>"
```

### Security Checklist
- [ ] Execution user configured
- [ ] Consumer secret rotated regularly
- [ ] Scopes minimal (least privilege)
- [ ] IP restrictions enabled

---

## Refresh Token Patterns

### Standard Refresh

```javascript
async function refreshAccessToken(refreshToken) {
  const response = await axios.post('https://login.salesforce.com/services/oauth2/token',
    new URLSearchParams({
      grant_type: 'refresh_token',
      client_id: CLIENT_ID,
      client_secret: CLIENT_SECRET,
      refresh_token: refreshToken
    })
  );

  return response.data;
}
```

### With Token Rotation (Recommended)

When `isRefreshTokenRotationEnabled=true`, each refresh returns a NEW refresh token:

```javascript
async function refreshWithRotation(refreshToken) {
  const response = await refreshAccessToken(refreshToken);

  // Store NEW refresh token (old one is now invalid)
  await secureStorage.set('refresh_token', response.refresh_token);
  await secureStorage.set('access_token', response.access_token);

  return response;
}
```

### Refresh Token Policies

| Policy | Description | Use Case |
|--------|-------------|----------|
| `infinite` | Never expires | Trusted integrations |
| `immediately` | Expires on use | Maximum security |
| `zero` | Not issued | Access token only |

**Configuration**:
```xml
<oauthPolicy>
    <refreshTokenPolicy>infinite</refreshTokenPolicy>
    <isRefreshTokenRotationEnabled>true</isRefreshTokenRotationEnabled>
</oauthPolicy>
```

---

## Named Credentials Integration

### Why Use Named Credentials
- Secrets managed by Salesforce (not in code)
- Automatic token refresh
- Per-user or per-org authentication
- Audit trail in Setup Audit Trail

### Create Named Credential for JWT Flow

```xml
<!-- namedCredentials/SalesforceAPI.namedCredential-meta.xml -->
<NamedCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>Salesforce API</label>
    <endpoint>https://yourinstance.salesforce.com</endpoint>
    <protocol>NoAuthentication</protocol>
    <principalType>NamedUser</principalType>
    <oauthConfig>
        <certificate>JWTAuthCertificate</certificate>
        <consumerKey>YOUR_CONSUMER_KEY</consumerKey>
        <oauthFlows>JwtBearer</oauthFlows>
        <username>integration@company.com</username>
    </oauthConfig>
</NamedCredential>
```

### Use in Apex

```apex
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:SalesforceAPI/services/data/v66.0/query?q=SELECT+Id+FROM+Account');
req.setMethod('GET');

Http http = new Http();
HttpResponse res = http.send(req);
```

---

## Token Introspection

**Use**: Validate token status and metadata

```bash
curl -X POST https://login.salesforce.com/services/oauth2/introspect \
  -d "token=<ACCESS_TOKEN>" \
  -d "client_id=<CONSUMER_KEY>" \
  -d "client_secret=<CONSUMER_SECRET>" \
  -d "token_type_hint=access_token"
```

---

## Token Revocation

**Use**: Invalidate tokens on logout

```bash
curl -X POST https://login.salesforce.com/services/oauth2/revoke \
  -d "token=<TOKEN>"
```

---

## Error Handling Patterns

### OAuth Error Response Structure

```json
{
  "error": "invalid_grant",
  "error_description": "authentication failure"
}
```

### Common Errors

| Error Code | Meaning | Resolution |
|------------|---------|------------|
| `invalid_client_id` | Consumer key invalid | Verify key from Setup |
| `invalid_client` | Secret incorrect | Check consumer secret |
| `redirect_uri_mismatch` | Callback URL mismatch | Match exactly with config |
| `invalid_grant` | Auth code expired/used | Request new authorization |
| `unsupported_grant_type` | Flow not enabled | Enable in Connected App |
| `invalid_scope` | Scope not allowed | Check available scopes |
| `access_denied` | User declined | User must approve |

### Retry Logic Example

```javascript
async function callSalesforceAPI(accessToken, retries = 1) {
  try {
    return await axios.get('https://instance.salesforce.com/services/data/v66.0/query', {
      headers: { 'Authorization': `Bearer ${accessToken}` }
    });
  } catch (error) {
    if (error.response?.status === 401 && retries > 0) {
      // Token expired, refresh and retry
      const newToken = await refreshAccessToken();
      return callSalesforceAPI(newToken, retries - 1);
    }
    throw error;
  }
}
```

---

## Scoring Impact by Flow

| Flow | Security Score Impact | Best Practices Score |
|------|----------------------|---------------------|
| Authorization Code + PKCE | +10 (PKCE enabled) | +10 (modern flow) |
| JWT Bearer | +5 (certificate) | +15 (server-to-server best practice) |
| Device Authorization | +5 (secret optional) | +10 (appropriate for CLI) |
| Username-Password | -10 (deprecated) | -10 (anti-pattern) |

**Recommendation**: JWT Bearer or Authorization Code + PKCE score highest (90-100/120).

---

## Testing OAuth Flows

### Postman Collection Variables

```json
{
  "login_url": "https://login.salesforce.com",
  "client_id": "{{CONSUMER_KEY}}",
  "client_secret": "{{CONSUMER_SECRET}}",
  "redirect_uri": "https://localhost/oauth/callback",
  "username": "test@company.com",
  "password": "password123"
}
```

### Quick Test: JWT Bearer

```bash
# Generate JWT (requires jq)
JWT=$(python3 -c "
import jwt, time, os
claims = {
    'iss': os.getenv('CONSUMER_KEY'),
    'sub': 'integration@company.com',
    'aud': 'https://login.salesforce.com',
    'exp': int(time.time()) + 300
}
with open('server.key') as f:
    print(jwt.encode(claims, f.read(), algorithm='RS256'))
")

# Get token
curl -X POST https://login.salesforce.com/services/oauth2/token \
  -d "grant_type=urn:ietf:params:oauth:grant-type:jwt-bearer" \
  -d "assertion=$JWT" | jq
```

---

## Migration Strategies

### Connected App → External Client App

**Step 1**: Create equivalent ECA
```bash
# Read existing Connected App
Grep: pattern="<oauthConfig>" path="force-app/main/default/connectedApps/"

# Create new ECA with same scopes
# Use templates: external-client-app.xml, eca-global-oauth.xml
```

**Step 2**: Parallel operation
- Deploy ECA alongside Connected App
- Update one integration at a time
- Monitor both apps

**Step 3**: Cutover
- Update all integrations to use new Consumer Key
- Disable old Connected App
- Archive after 30 days

**Scoring benefit**: ECA typically scores 15-20 points higher due to modern security model.

---

## Quick Reference

### Template Selection by Flow

| Flow | Template File |
|------|---------------|
| Authorization Code (basic) | `connected-app-oauth.xml` |
| JWT Bearer | `connected-app-jwt.xml` |
| Mobile/SPA (PKCE) | `external-client-app.xml` + `eca-global-oauth.xml` |
| Device Authorization | `connected-app-basic.xml` (secret optional) |
| Client Credentials | `eca-oauth-settings.xml` + optional retrieve-first `ecaOauthSecurity` metadata (ECA only) |

### Salesforce OAuth Endpoints

| Environment | Base URL |
|-------------|----------|
| Production | `https://login.salesforce.com` |
| Sandbox | `https://test.salesforce.com` |
| Custom Domain | `https://yourdomain.my.salesforce.com` |

### Key Endpoints
- Authorize: `/services/oauth2/authorize`
- Token: `/services/oauth2/token`
- Revoke: `/services/oauth2/revoke`
- Introspect: `/services/oauth2/introspect`
- Device Code: `/services/oauth2/device/code`
- UserInfo (OpenID): `/services/oauth2/userinfo`

---

## Related Resources

- **Flow Diagrams**: Included above (Authorization Code, JWT Bearer, Device Authorization)
- **Security Checklist**: [references/security-checklist.md](../references/security-checklist.md)
- **Migration Guide**: [references/migration-guide.md](../references/migration-guide.md)
- **Main Skill**: [SKILL.md](../SKILL.md)
