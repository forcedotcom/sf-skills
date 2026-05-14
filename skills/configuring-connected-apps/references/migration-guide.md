<!-- Parent: configuring-connected-apps/SKILL.md -->
# Migration Guide: Connected App → External Client App

Step-by-step guide for migrating from Connected Apps to External Client Apps (ECAs).

## Why Migrate?

| Feature | Connected App | External Client App |
|---------|--------------|---------------------|
| Metadata Compliance | Partial | Full |
| Secret in Sandboxes | Visible | Hidden |
| Key Rotation | Manual | Automated via API |
| Multi-Org Distribution | Manual recreation | Native 2GP packaging |
| Audit Logging | Limited | MFA + full audit |
| Security Model | Open by default | Closed by default |

**Migrate when**:
- Distributing to multiple orgs (ISV, enterprise)
- Compliance requires audit trails
- DevOps needs automated credential rotation
- Moving to 2GP packaging

---

## Migration Process

### Phase 1: Assessment

#### 1.1 Inventory Current Apps

```bash
# List all Connected Apps
sf org list metadata --metadata-type ConnectedApp --target-org <org>

# Retrieve for analysis
sf project retrieve start --metadata ConnectedApp --output-dir ./migration-review
```

#### 1.2 Document Configuration

For each Connected App, record:

| Setting | Value |
|---------|-------|
| App Name | |
| Consumer Key | |
| OAuth Scopes | |
| Callback URLs | |
| IP Restrictions | |
| Token Policy | |
| Certificate (if JWT) | |

#### 1.3 Identify Integrations

List all systems using each Connected App:
- External applications
- CI/CD pipelines
- Third-party tools
- Mobile applications

---

### Phase 2: Planning

#### 2.1 Choose Distribution Model

| Scenario | Distribution State |
|----------|-------------------|
| Single org only | `Local` |
| Multiple orgs, same company | `Local` per org or `Packageable` |
| ISV/AppExchange | `Packageable` |

#### 2.2 Plan Credential Rollover

```
Timeline Example:
Week 1: Create ECA, deploy to DevHub
Week 2: Update integration systems with new credentials
Week 3: Test in sandbox environments
Week 4: Production cutover
Week 5-8: Monitor, keep old app active as fallback
Week 9: Deactivate Connected App
Week 12: Delete Connected App
```

---

### Phase 3: Create External Client App

#### 3.1 Prepare Scratch Org (if needed)

```json
// config/project-scratch-def.json
{
  "orgName": "ECA Migration Dev",
  "edition": "Developer",
  "features": [
    "ExternalClientApps",
    "ExtlClntAppSecretExposeCtl"
  ]
}
```

#### 3.2 Create ECA Metadata Files

**File 1: Header** (`MyApp.eca-meta.xml`)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExternalClientApplication xmlns="http://soap.sforce.com/2006/04/metadata">
    <contactEmail>team@company.com</contactEmail>
    <description>Migrated from Connected App: MyConnectedApp</description>
    <distributionState>Local</distributionState>
    <isProtected>false</isProtected>
    <label>MyApp</label>
</ExternalClientApplication>
```

**File 2: Global OAuth** (`MyApp.ecaGlblOauth-meta.xml`)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExtlClntAppGlobalOauthSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <callbackUrl>https://app.example.com/oauth/callback</callbackUrl>
    <externalClientApplication>MyApp</externalClientApplication>
    <isConsumerSecretOptional>false</isConsumerSecretOptional>
    <isPkceRequired>true</isPkceRequired>
    <label>MyApp Global OAuth</label>
    <shouldRotateConsumerKey>true</shouldRotateConsumerKey>
    <shouldRotateConsumerSecret>true</shouldRotateConsumerSecret>
</ExtlClntAppGlobalOauthSettings>
```

**File 3: OAuth Settings** (`MyApp.ecaOauth-meta.xml`)
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExtlClntAppOauthSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <commaSeparatedOauthScopes>Api, RefreshToken</commaSeparatedOauthScopes>
    <externalClientApplication>MyApp</externalClientApplication>
    <label>MyApp OAuth Settings</label>
</ExtlClntAppOauthSettings>
```

**Optional companion metadata (retrieve-first):** `MyApp.ecaOauthSecurity-meta.xml`
- Use this when you need to source-control ECA OAuth security settings now supported by the CLI/SDR registry.
- Recommended workflow: retrieve from an org first, then commit the retrieved file under `extlClntAppOauthSecuritySettings/`.

#### 3.3 Deploy to DevHub/Org

```bash
sf project deploy start \
  --metadata ExternalClientApplication:MyApp \
  --metadata ExtlClntAppGlobalOauthSettings:MyApp \
  --metadata ExtlClntAppOauthSettings:MyApp \
  --target-org <target-org>
```

#### 3.4 Retrieve New Consumer Key

After deployment:
1. Go to Setup → External Client App Manager
2. Select your ECA
3. View Consumer Key (MFA required)
4. Securely store credentials

---

### Phase 4: Update Integrations

#### 4.1 Update External Systems

For each integrated system:

1. Update OAuth endpoint (if different environment)
2. Replace Consumer Key
3. Replace Consumer Secret
4. Test authentication flow
5. Verify API access

#### 4.2 Configuration Mapping

| Connected App Setting | ECA Equivalent |
|----------------------|----------------|
| Consumer Key | New Consumer Key (different) |
| Consumer Secret | New Consumer Secret (different) |
| Callback URL | Same (in `ecaGlblOauth`) |
| Scopes | Same (in `ecaOauth`) |
| IP Relaxation | In `ecaPlcy` (admin-managed) |
| Refresh Token Policy | In `ecaPlcy` (admin-managed) |
| OAuth security controls | In `ecaOauthSecurity` when source-controlled (retrieve-first) |

---

### Phase 5: Testing

#### 5.1 Test Checklist

- [ ] Authorization Code flow works
- [ ] Token refresh works
- [ ] API calls succeed
- [ ] Scopes are correct
- [ ] Error handling works
- [ ] Logout/revocation works

#### 5.2 Test Script

```bash
# Test Authorization Code Flow
curl "https://login.salesforce.com/services/oauth2/authorize?\
response_type=code&\
client_id=<NEW_CONSUMER_KEY>&\
redirect_uri=<CALLBACK_URL>&\
scope=api%20refresh_token"

# Test Token Exchange
curl -X POST https://login.salesforce.com/services/oauth2/token \
  -d "grant_type=authorization_code" \
  -d "code=<AUTH_CODE>" \
  -d "client_id=<NEW_CONSUMER_KEY>" \
  -d "client_secret=<NEW_CONSUMER_SECRET>" \
  -d "redirect_uri=<CALLBACK_URL>"
```

---

### Phase 6: Cutover

#### 6.1 Production Deployment

```bash
# Deploy ECA to production
sf project deploy start \
  --metadata ExternalClientApplication:MyApp \
  --metadata ExtlClntAppGlobalOauthSettings:MyApp \
  --metadata ExtlClntAppOauthSettings:MyApp \
  --target-org production
```

#### 6.2 Cutover Steps

1. Deploy ECA to production
2. Configure policies in Setup
3. Update production integrations
4. Monitor for errors
5. Keep Connected App active as fallback

---

### Phase 7: Decommission

#### 7.1 Deactivate Connected App

1. Go to Setup → Connected Apps → Manage Connected Apps
2. Select the old Connected App
3. Click "Edit Policies"
4. Set "Permitted Users" to "Admin approved users are pre-authorized"
5. Remove all user/profile assignments

#### 7.2 Monitor Period

- Monitor for 30 days minimum
- Check for authentication failures
- Investigate any traffic to old app

#### 7.3 Delete Connected App

After monitoring period:

```bash
# Remove from source control
rm force-app/main/default/connectedApps/OldApp.connectedApp-meta.xml

# Or delete via Setup UI
```

---

## Rollback Plan

If migration fails:

1. **Immediate**: Revert external systems to old Consumer Key
2. **Short-term**: Keep Connected App active during transition
3. **Long-term**: Document issues and retry migration

---

## Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| "Invalid consumer key" | Using old key | Update to new ECA key |
| "Callback URL mismatch" | URL not in ECA config | Add URL to `ecaGlblOauth` |
| "Scope not allowed" | Scope not in `ecaOauth` | Add required scope |
| "User not authorized" | No policy assignment | Assign user via Permission Set |
| "MFA required" | ECA security | Complete MFA challenge |

---

## Automation Script

```bash
#!/bin/bash
# migrate-connected-app.sh

APP_NAME=$1
TARGET_ORG=$2

echo "📦 Migrating Connected App: $APP_NAME"

# 1. Retrieve existing Connected App
sf project retrieve start \
  --metadata "ConnectedApp:$APP_NAME" \
  --target-org $TARGET_ORG \
  --output-dir ./migration

# 2. Create ECA source directories
mkdir -p force-app/main/default/externalClientApps
mkdir -p force-app/main/default/extlClntAppGlobalOauthSets
mkdir -p force-app/main/default/extlClntAppOauthSettings
# Optional when you source-control security settings:
mkdir -p force-app/main/default/extlClntAppOauthSecuritySettings

# 3. Deploy ECA (assumes files are created)
sf project deploy start \
  --source-dir force-app/main/default \
  --target-org $TARGET_ORG

echo "✅ ECA deployed. Retrieve new Consumer Key from Setup."
```
