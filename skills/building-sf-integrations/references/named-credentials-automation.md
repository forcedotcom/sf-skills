<!-- Parent: building-sf-integrations/SKILL.md -->
# Named Credentials Automation Guide

This guide explains how to automate Named Credential configuration using the building-sf-integrations helper scripts.

> **Key Insight:** Enhanced Named Credentials (API 60+) can be configured programmatically using `ConnectApi.NamedCredentials` - no UI required!

---

## Overview

Enhanced Named Credentials = **External Credential** + **Named Credential** + **Endpoint Security**

```
External Credential (stores the API key securely)
         ↓
Named Credential (references the External Credential)
         ↓
Your HTTP Callout (uses callout:NamedCredentialName)
```

### Why Enhanced Named Credentials?

| Benefit | Description |
|---------|-------------|
| **Security** | AES-256 encryption by Salesforce platform |
| **Flexibility** | Supports Custom, Basic, OAuth, JWT protocols |
| **Portability** | Easier to manage across multiple orgs |
| **Automation** | Configurable via ConnectApi (no UI required) |
| **Compliance** | Passes PCI-DSS, SOC 2 audits |

---

## Deployment Order

**CRITICAL:** Deploy components in this exact order:

```bash
# 1. Deploy External Credential (defines the credential structure)
sf project deploy start \
  --source-dir force-app/main/default/externalCredentials/YourAPI.externalCredential-meta.xml \
  --target-org YourOrg

# 2. Deploy Named Credential (references the External Credential)
sf project deploy start \
  --source-dir force-app/main/default/namedCredentials/YourAPI.namedCredential-meta.xml \
  --target-org YourOrg

# 3. Deploy endpoint security (allows outbound HTTP calls)
sf project deploy start \
  --source-dir force-app/main/default/cspTrustedSites/YourAPI.cspTrustedSite-meta.xml \
  --target-org YourOrg

# 4. Set the API key using our automation script
./scripts/configure-named-credential.sh YourOrg
```

---

## Automation Scripts

### `configure-named-credential.sh`

**Purpose:** Sets API keys for Enhanced Named Credentials using ConnectApi

**Usage:**
```bash
./scripts/configure-named-credential.sh <org-alias>
```

**What it does:**
1. Validates org connection via `sf org display`
2. Checks External Credential exists via SOQL
3. Prompts for API key securely (input hidden)
4. Generates Apex using `ConnectApi.NamedCredentials.createCredential()`
5. Handles create vs. patch automatically

**Under the hood:**
```apex
ConnectApi.CredentialInput creds = new ConnectApi.CredentialInput();
creds.externalCredential = 'YourExternalCredential';
creds.principalName = 'yourPrincipalName';
creds.authenticationProtocol = ConnectApi.CredentialAuthenticationProtocol.Custom;

Map<String, ConnectApi.CredentialValueInput> params = new Map<String, ConnectApi.CredentialValueInput>();
ConnectApi.CredentialValueInput apiKey = new ConnectApi.CredentialValueInput();
apiKey.encrypted = true;
apiKey.value = 'YOUR_API_KEY';
params.put('apiKey', apiKey);

creds.credentials = params;
ConnectApi.NamedCredentials.createCredential(creds);
```

### `set-api-credential.sh`

**Purpose:** Stores API keys in Custom Settings (legacy/dev approach)

**Usage:**
```bash
# Secure input (recommended)
./scripts/set-api-credential.sh <setting-name> - <org-alias>

# Direct input
./scripts/set-api-credential.sh <setting-name> <api-key> <org-alias>
```

**When to use:**
- Dev/test environments
- CI/CD pipelines (no Apex execution)
- Simple API key auth via query parameters

**Not recommended for production** - use Enhanced Named Credentials instead.

---

## Complete Example: Weather API

### Step 1: Create Metadata

**External Credential:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ExternalCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <authenticationProtocol>Custom</authenticationProtocol>
    <externalCredentialParameters>
        <parameterGroup>weatherAPIKey</parameterGroup>
        <parameterName>weatherAPIKey</parameterName>
        <parameterType>NamedPrincipal</parameterType>
        <sequenceNumber>1</sequenceNumber>
    </externalCredentialParameters>
    <label>Weather API</label>
</ExternalCredential>
```

**Named Credential:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<NamedCredential xmlns="http://soap.sforce.com/2006/04/metadata">
    <allowMergeFieldsInBody>false</allowMergeFieldsInBody>
    <allowMergeFieldsInHeader>true</allowMergeFieldsInHeader>
    <calloutStatus>Enabled</calloutStatus>
    <label>Weather API</label>
    <namedCredentialParameters>
        <parameterName>Url</parameterName>
        <parameterType>Url</parameterType>
        <parameterValue>https://api.weather.com</parameterValue>
    </namedCredentialParameters>
    <namedCredentialParameters>
        <externalCredential>WeatherAPI</externalCredential>
        <parameterName>ExternalCredential</parameterName>
        <parameterType>Authentication</parameterType>
    </namedCredentialParameters>
    <namedCredentialType>SecuredEndpoint</namedCredentialType>
</NamedCredential>
```

### Step 2: Deploy and Configure

```bash
# Deploy all metadata
sf project deploy start --metadata ExternalCredential:WeatherAPI \
  --metadata NamedCredential:WeatherAPI \
  --metadata CspTrustedSite:WeatherAPI \
  --target-org MyOrg

# Configure API key
./scripts/configure-named-credential.sh MyOrg
```

### Step 3: Use in Apex

```apex
HttpRequest req = new HttpRequest();
req.setEndpoint('callout:WeatherAPI/forecast?city=London');
req.setMethod('GET');

HttpResponse res = new Http().send(req);
System.debug(res.getBody());
```

The API key is automatically included - no manual credential handling!

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| "External Credential not found" | Not deployed or wrong name | Deploy first, check spelling |
| "Named Credential not found" | Not deployed | Deploy after External Credential |
| "No existing credentials to update" | Using patch instead of create | Script handles automatically |
| "Unable to connect" | Missing endpoint security | Deploy CSP Trusted Site |

---

## Related Documentation

- [named-credentials-guide.md](./named-credentials-guide.md) - Template reference
- [external-services-guide.md](./external-services-guide.md) - OpenAPI integration
- [security-best-practices.md](./security-best-practices.md) - Security patterns
