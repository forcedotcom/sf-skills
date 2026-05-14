<!-- Parent: configuring-connected-apps/SKILL.md -->
# configuring-connected-apps Examples

Real-world examples of using the configuring-connected-apps skill.

## Example 1: Create a Basic API Integration Connected App

**Request**:
```
Use the configuring-connected-apps skill to create a Connected App named "DataSyncIntegration"
for syncing data with our external ERP system. It needs API access and refresh tokens.
Contact email: admin@company.com
```

**Generated Output**:
- `force-app/main/default/connectedApps/DataSyncIntegration.connectedApp-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ConnectedApp xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>DataSyncIntegration</label>
    <contactEmail>admin@company.com</contactEmail>
    <description>Data synchronization with external ERP system</description>
    <oauthConfig>
        <callbackUrl>https://erp.company.com/oauth/callback</callbackUrl>
        <isAdminApproved>true</isAdminApproved>
        <isConsumerSecretOptional>false</isConsumerSecretOptional>
        <scopes>Api</scopes>
        <scopes>RefreshToken</scopes>
    </oauthConfig>
    <oauthPolicy>
        <ipRelaxation>ENFORCE</ipRelaxation>
        <refreshTokenPolicy>infinite</refreshTokenPolicy>
    </oauthPolicy>
</ConnectedApp>
```

**Score**: 95/120 ⭐⭐⭐⭐

---

## Example 2: Create a JWT Bearer App for CI/CD

**Request**:
```
Create a Connected App for our CI/CD pipeline using JWT Bearer flow.
Name it "GitHubActionsDeployment" and use certificate "GH_Actions_Cert".
```

**Generated Output**:
- `force-app/main/default/connectedApps/GitHubActionsDeployment.connectedApp-meta.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<ConnectedApp xmlns="http://soap.sforce.com/2006/04/metadata">
    <label>GitHubActionsDeployment</label>
    <contactEmail>devops@company.com</contactEmail>
    <description>CI/CD deployment via GitHub Actions - JWT Bearer flow</description>
    <oauthConfig>
        <callbackUrl>https://localhost/oauth/callback</callbackUrl>
        <certificate>GH_Actions_Cert</certificate>
        <isAdminApproved>true</isAdminApproved>
        <isConsumerSecretOptional>true</isConsumerSecretOptional>
        <scopes>Api</scopes>
    </oauthConfig>
    <oauthPolicy>
        <ipRelaxation>ENFORCE</ipRelaxation>
        <refreshTokenPolicy>zero</refreshTokenPolicy>
    </oauthPolicy>
</ConnectedApp>
```

**Score**: 108/120 ⭐⭐⭐⭐⭐

---

## Example 3: Create a Mobile App with External Client App

**Request**:
```
Create an External Client App for our mobile app "FieldServiceMobile".
It needs PKCE enabled, refresh tokens, and should be packageable for distribution.
```

**Generated Files**:

### 1. Header File: `FieldServiceMobile.eca-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExternalClientApplication xmlns="http://soap.sforce.com/2006/04/metadata">
    <contactEmail>mobile-team@company.com</contactEmail>
    <description>Field Service mobile application for technicians</description>
    <distributionState>Packageable</distributionState>
    <isProtected>false</isProtected>
    <label>FieldServiceMobile</label>
</ExternalClientApplication>
```

### 2. Global OAuth: `FieldServiceMobile.ecaGlblOauth-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExtlClntAppGlobalOauthSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <callbackUrl>fieldservicemobile://oauth/callback</callbackUrl>
    <externalClientApplication>FieldServiceMobile</externalClientApplication>
    <isConsumerSecretOptional>true</isConsumerSecretOptional>
    <isPkceRequired>true</isPkceRequired>
    <label>Field Service Mobile Global OAuth</label>
    <shouldRotateConsumerKey>true</shouldRotateConsumerKey>
    <shouldRotateConsumerSecret>true</shouldRotateConsumerSecret>
</ExtlClntAppGlobalOauthSettings>
```

### 3. OAuth Settings: `FieldServiceMobile.ecaOauth-meta.xml`
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExtlClntAppOauthSettings xmlns="http://soap.sforce.com/2006/04/metadata">
    <commaSeparatedOauthScopes>Api, RefreshToken, OpenID</commaSeparatedOauthScopes>
    <externalClientApplication>FieldServiceMobile</externalClientApplication>
    <label>Field Service Mobile OAuth Settings</label>
</ExtlClntAppOauthSettings>
```

### 4. Optional OAuth Security Settings (retrieve-first)
```bash
sf project retrieve start \
  --metadata ExtlClntAppOauthSecuritySettings:FieldServiceMobile \
  --target-org my-devhub
```

**Score**: 115/120 ⭐⭐⭐⭐⭐

---

## Example 4: Review Existing Connected Apps

**Request**:
```
Review and score my existing Connected Apps for security best practices.
```

**Process**:
1. Scan: `Glob: **/*.connectedApp-meta.xml`
2. Read each file
3. Validate against scoring criteria
4. Generate report

**Sample Report**:
```
📊 CONNECTED APP SECURITY REVIEW
════════════════════════════════════════════════════════════════

🔍 Apps Scanned: 3
📅 Review Date: 2025-01-15

┌────────────────────────────┬────────┬────────┬──────────────────┐
│ App Name                   │ Score  │ Rating │ Critical Issues  │
├────────────────────────────┼────────┼────────┼──────────────────┤
│ LegacyERPConnector         │ 45/120 │ ⭐     │ 3                │
│ MobileAppV2                │ 82/120 │ ⭐⭐⭐  │ 0                │
│ DataSyncIntegration        │ 95/120 │ ⭐⭐⭐⭐│ 0                │
└────────────────────────────┴────────┴────────┴──────────────────┘

🚨 CRITICAL ISSUES

LegacyERPConnector:
  ❌ Wildcard callback URL detected (https://*)
  ❌ Full scope granted (overly permissive)
  ❌ No IP restrictions configured
  ⚠️ Recommend: Migrate to External Client App

✅ RECOMMENDATIONS

1. LegacyERPConnector: URGENT - Fix security issues or migrate to ECA
2. MobileAppV2: Enable PKCE for mobile security
3. DataSyncIntegration: Consider enabling token rotation
```

---

## Example 5: Migrate Connected App to External Client App

**Request**:
```
Migrate our "SalesPortal" Connected App to an External Client App for better security.
```

**Process**:
1. Read existing Connected App configuration
2. Map OAuth settings to ECA structure
3. Generate all required ECA files
4. Provide migration checklist

**Output**:
```
📦 MIGRATION PLAN: SalesPortal → External Client App
════════════════════════════════════════════════════════════════

📋 Source Configuration
   Type: Connected App
   OAuth Flow: Authorization Code
   Scopes: Api, RefreshToken, OpenID
   IP Policy: ENFORCE

📄 Files to Generate:
   1. SalesPortalECA.eca-meta.xml
   2. SalesPortalECA.ecaGlblOauth-meta.xml
   3. SalesPortalECA.ecaOauth-meta.xml
   4. (Optional) SalesPortalECA.ecaOauthSecurity-meta.xml after retrieve-first validation

🔄 Migration Steps:
   1. ✓ Generate ECA metadata files
   2. □ Deploy ECA to DevHub
   3. □ Generate new Consumer Key/Secret
   4. □ Update external application with new credentials
   5. □ Test OAuth flow
   6. □ Configure policies in subscriber orgs
   7. □ Deactivate old Connected App
   8. □ Monitor for 30 days before deletion

⚠️ Breaking Change: New Consumer Key/Secret required
```

---

## Deployment Commands

### Deploy Connected App
```bash
sf project deploy start \
  --source-dir force-app/main/default/connectedApps \
  --target-org my-org
```

### Deploy External Client App
```bash
sf project deploy start \
  --metadata ExternalClientApplication:MyECAName \
  --metadata ExtlClntAppGlobalOauthSettings:MyECAName \
  --metadata ExtlClntAppOauthSettings:MyECAName \
  --target-org my-devhub
```

### Retrieve Existing Apps
```bash
# Connected Apps
sf project retrieve start \
  --metadata ConnectedApp:MyAppName \
  --target-org my-org

# External Client Apps (header + companions)
sf project retrieve start \
  --metadata ExternalClientApplication:MyECAName \
  --metadata ExtlClntAppGlobalOauthSettings:MyECAName \
  --metadata ExtlClntAppOauthSettings:MyECAName \
  --target-org my-org
```
