# SOAP API Enablement Patterns

This reference provides verified working SOAP API calls for enabling all Pipeline Management prerequisites and the feature itself.

## Why SOAP API Instead of CLI Metadata Deploy

**Problem:** CLI Metadata API deploy (`sf project deploy start`) has a **silent failure mode** with Settings metadata types:
- Deployment reports `success: true` and `changed: true`
- XML file shows intended values (e.g., `<enableDealAgent>true</enableDealAgent>`)
- But org silently reverts the setting to `false`
- Only discoverable via post-deployment verification queries

**Solution:** Use SOAP Metadata API `updateMetadata` operation directly. It bypasses the silent reversion issue.

**Evidence:** Tested in Enterprise Edition org with Agentforce for Sales add-on. All SOAP API calls succeeded; all CLI deploys silently failed.

---

## Pattern Template

All Settings metadata types follow this pattern:

```bash
ORG_ALIAS="your-org"
AUTH_INFO=$(sf org display --target-org $ORG_ALIAS --json 2>/dev/null)
ACCESS_TOKEN=$(echo "$AUTH_INFO" | jq -r '.result.accessToken')
INSTANCE_URL=$(echo "$AUTH_INFO" | jq -r '.result.instanceUrl')
API_VERSION="<version>"  # 62.0 for most, 64.0 for SalesDealAgent

curl -s "${INSTANCE_URL}/services/Soap/m/${API_VERSION}" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:<SettingsType>' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName><SettingsName></met:fullName>
        <met:<propertyName>><value></met:<propertyName>>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null
```

**Key points:**
- `xsi:type` must match the metadata type exactly (case-sensitive)
- `fullName` is the Settings API name (not always the same as the type name)
- Property names must match the metadata structure (check Metadata API docs or retrieve first)
- Use `xmllint --format -` to pretty-print the response
- Always pipe `sf ... --json` through `2>/dev/null` before jq

---

## 1. Einstein Generative AI Platform

**Metadata Type:** `EinsteinGptSettings`  
**API Version:** 62.0+  
**Verification:** SOAP `readMetadata` for `EinsteinGptSettings` → check `<enableEinsteinGptPlatform>true</enableEinsteinGptPlatform>`  
**Last resort UI:** Setup → Einstein → Einstein Generative AI → Einstein Setup → Turn on Einstein

```bash
ORG_ALIAS="pipeline-mgmt-org"
AUTH_INFO=$(sf org display --target-org $ORG_ALIAS --json 2>/dev/null)
ACCESS_TOKEN=$(echo "$AUTH_INFO" | jq -r '.result.accessToken')
INSTANCE_URL=$(echo "$AUTH_INFO" | jq -r '.result.instanceUrl')

echo "=== Enabling Einstein Generative AI Platform ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:EinsteinGptSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName>EinsteinGpt</met:fullName>
        <met:enableEinsteinGptPlatform>true</met:enableEinsteinGptPlatform>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|fullName|message)" | head -5

echo -e "\n=== Verifying enablement (SOAP readMetadata) ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:readMetadata>
      <met:type>EinsteinGptSettings</met:type>
      <met:fullNames>EinsteinGpt</met:fullNames>
    </met:readMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | grep -o "<enableEinsteinGptPlatform>[^<]*</enableEinsteinGptPlatform>"
# Expected: <enableEinsteinGptPlatform>true</enableEinsteinGptPlatform>
```

---

## 2. Agentforce Agent

**Metadata Type:** `EinsteinCopilotSettings`  
**API Version:** 62.0+  
**Depends On:** Einstein Generative AI must be enabled first  
**Verification:** SOAP `readMetadata` for `EinsteinCopilotSettings` → check `<enableEinsteinGptCopilot>true</enableEinsteinGptCopilot>`  
**Last resort UI:** Setup → Einstein → Einstein Generative AI → Agentforce Studio → Agentforce Agents → Enable Agentforce

```bash
echo "=== Enabling Agentforce Agent ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:EinsteinCopilotSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName>EinsteinCopilot</met:fullName>
        <met:enableEinsteinGptCopilot>true</met:enableEinsteinGptCopilot>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|fullName|message)" | head -5

echo -e "\n=== Verifying enablement ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:readMetadata>
      <met:type>EinsteinCopilotSettings</met:type>
      <met:fullNames>EinsteinCopilot</met:fullNames>
    </met:readMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | grep -o "<enableEinsteinGptCopilot>[^<]*</enableEinsteinGptCopilot>"
# Expected: <enableEinsteinGptCopilot>true</enableEinsteinGptCopilot>
```

**Note:** Do NOT enable `BotSettings` (`enableBots`) — that is for legacy messaging bots and is completely unrelated to Agentforce. It requires legal terms acceptance and will fail.

---

## 2b. Agentforce Studio (Agent Platform)

**Metadata Type:** `AgentPlatformSettings`  
**API Version:** 62.0+  
**Depends On:** Agentforce Agent (§2) must be enabled first  
**Gates:** the Sales Deal Agent — core's `DealAgentEnabledOrgPreference` validates the Agentforce Platform preference (`AgentPlatformEnabled`) and rejects `SalesDealAgentSettings.enableDealAgent` when it is off, so a missing step here surfaces later as an opaque Deal Agent activation failure.  
**Verification:** SOAP `readMetadata` for `AgentPlatformSettings` → check `<enableAgentPlatform>true</enableAgentPlatform>`  
**Last resort UI:** Setup → Einstein → Agentforce Studio → Enable

```bash
echo "=== Enabling Agentforce Studio (Agent Platform) ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:AgentPlatformSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName>AgentPlatform</met:fullName>
        <met:enableAgentPlatform>true</met:enableAgentPlatform>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|fullName|message)" | head -5

echo -e "\n=== Verifying enablement ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:readMetadata>
      <met:type>AgentPlatformSettings</met:type>
      <met:fullNames>AgentPlatform</met:fullNames>
    </met:readMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | grep -o "<enableAgentPlatform>[^<]*</enableAgentPlatform>"
# Expected: <enableAgentPlatform>true</enableAgentPlatform>
```

---

## 3. Enhanced Notes

**Metadata Type:** `EnhancedNotesSettings`  
**API Version:** 62.0+  
**Verification:** `SELECT count() FROM ContentNote` succeeds  
**Last resort UI:** Setup → Feature Settings → Sales → Notes Settings → Enable Notes

```bash
echo "=== Enabling Enhanced Notes ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:EnhancedNotesSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName>EnhancedNotes</met:fullName>
        <met:enableEnhancedNotes>true</met:enableEnhancedNotes>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|fullName|message)" | head -5

echo -e "\n=== Verifying enablement ==="
sf data query -q "SELECT count() FROM ContentNote" --target-org $ORG_ALIAS 2>/dev/null
# Expected: Total number of records (not "sObject type not supported")
```

---

## 4. Enhanced Email

**Metadata Type:** `EmailAdministrationSettings`  
**API Version:** 62.0+  
**Purpose:** Enables email body indexing for Pipeline Management data sources  
**Verification:** SOAP `readMetadata` for `EmailAdministrationSettings` → check `<enableEnhancedEmailEnabled>true</enableEnhancedEmailEnabled>`  
**Last resort UI:** Setup → Feature Settings → Sales → Email Administration → Enable Enhanced Email

```bash
echo "=== Enabling Enhanced Email ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:EmailAdministrationSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName>EmailAdministration</met:fullName>
        <met:enableEnhancedEmailEnabled>true</met:enableEnhancedEmailEnabled>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|fullName|message)" | head -5

echo -e "\n=== Verifying enablement ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:readMetadata>
      <met:type>EmailAdministrationSettings</met:type>
      <met:fullNames>EmailAdministration</met:fullNames>
    </met:readMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | grep -o "<enableEnhancedEmailEnabled>[^<]*</enableEnhancedEmailEnabled>"
# Expected: <enableEnhancedEmailEnabled>true</enableEnhancedEmailEnabled>
```

---

## 5. Opportunity Team Selling

**Metadata Type:** `OpportunitySettings`  
**API Version:** 62.0+  
**Prerequisite:** Opportunity Splitting must be disabled  
**Verification:** `SELECT count() FROM OpportunityTeamMember` succeeds  
**Last resort UI:** Setup → Feature Settings → Sales → Opportunities → Opportunity Team Settings → Enable Team Selling

```bash
echo "=== Enabling Opportunity Team Selling ==="
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:OpportunitySettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName>Opportunity</met:fullName>
        <met:enableOpportunityTeam>true</met:enableOpportunityTeam>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|fullName|message)" | head -5

echo -e "\n=== Verifying enablement ==="
sf data query -q "SELECT count() FROM OpportunityTeamMember" --target-org $ORG_ALIAS 2>/dev/null
# Expected: Total number of records (not "sObject type not supported")
```

**If error "Cannot enable both Opportunity Teams and Opportunity Splits":**
```bash
# Disable Opportunity Splitting first
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:OpportunitySettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName>Opportunity</met:fullName>
        <met:enableOpportunitySplit>false</met:enableOpportunitySplit>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|message)"

# Then retry enabling Opportunity Team Selling
```

---

## 6. Pipeline Management

**Metadata Type:** `SalesDealAgentSettings`  
**API Version:** 64.0+ (v62.0 returns "Property 'enableDealAgent' not valid")  
**Verification:** SOAP `readMetadata` for `SalesDealAgentSettings` → check `<enableDealAgent>true</enableDealAgent>`  
**Last resort UI:** Setup → Agentforce for Sales → Pipeline Management toggle

```bash
echo "=== Enabling Pipeline Management ==="
curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:SalesDealAgentSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName>SalesDealAgent</met:fullName>
        <met:enableDealAgent>true</met:enableDealAgent>
        <met:enableDealAgentAutoApproveAllTasks>false</met:enableDealAgentAutoApproveAllTasks>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|fullName|message)" | head -5

echo -e "\n=== Verifying enablement ==="
curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:readMetadata>
      <met:type>SalesDealAgentSettings</met:type>
      <met:fullNames>SalesDealAgent</met:fullNames>
    </met:readMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | grep -o "<enableDealAgent>[^<]*</enableDealAgent>"
# Expected: <enableDealAgent>true</enableDealAgent>
```

---

## 7. Pipeline Inspection

**Metadata Type:** `OpportunitySettings`  
**API Version:** 64.0+  
**Purpose:** Provides UI for sales reps to review and accept/dismiss agent suggestions  
**Verification:** SOAP `readMetadata` for `OpportunitySettings` → check `<enablePipelineInspection>true</enablePipelineInspection>`  
**Last resort UI:** Setup → Feature Settings → Sales → Opportunities → Pipeline Inspection

```bash
echo "=== Enabling Pipeline Inspection ==="
curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:updateMetadata>
      <met:metadata xsi:type='met:OpportunitySettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
        <met:fullName>Opportunity</met:fullName>
        <met:enablePipelineInspection>true</met:enablePipelineInspection>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|fullName|message)" | head -5

echo -e "\n=== Verifying enablement ==="
curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header>
    <met:SessionHeader>
      <met:sessionId>${ACCESS_TOKEN}</met:sessionId>
    </met:SessionHeader>
  </soapenv:Header>
  <soapenv:Body>
    <met:readMetadata>
      <met:type>OpportunitySettings</met:type>
      <met:fullNames>Opportunity</met:fullNames>
    </met:readMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | grep -o "<enablePipelineInspection>[^<]*</enablePipelineInspection>"
# Expected: <enablePipelineInspection>true</enablePipelineInspection>
```

---

## Troubleshooting

### SOAP API login disabled

If you see "SOAP API login() is disabled", use CLI metadata retrieve instead of raw SOAP calls:

```bash
# Retrieve settings to check current values
sf project retrieve start --metadata "Settings:EinsteinGpt" --target-org $ORG_ALIAS 2>/dev/null
sf project retrieve start --metadata "Settings:EinsteinCopilot" --target-org $ORG_ALIAS 2>/dev/null
sf project retrieve start --metadata "Settings:EnhancedNotes" --target-org $ORG_ALIAS 2>/dev/null
sf project retrieve start --metadata "Settings:EmailAdministration" --target-org $ORG_ALIAS 2>/dev/null
sf project retrieve start --metadata "Settings:Opportunity" --target-org $ORG_ALIAS 2>/dev/null

# Check retrieved XML for <enable*>true</enable*> values
grep -r "enableEinsteinGptPlatform" force-app/
```

The `sf` CLI uses its own OAuth mechanism internally, so it works even when SOAP API login is disabled.

### Silent failure mode

If CLI deploy reports success but verification shows the setting is still disabled:
1. Confirm you're using SOAP API `updateMetadata` (NOT `sf project deploy start`)
2. Check API version (v64.0 for SalesDealAgent, v62.0 for others)
3. Verify `xsi:type` matches the metadata type exactly
4. Check for dependency violations (e.g., Agentforce Agent requires Einstein GenAI first)

### Success but no change

If SOAP API returns `<success>true</success>` but setting doesn't change:
1. Check for missing prerequisites (e.g., license, edition)
2. Verify user has correct permissions
3. Check for conflicting settings (e.g., Opportunity Splitting vs Team Selling)
4. Look for error messages in SOAP response beyond `<success>` tag

---

## Notes

- Always pipe `sf ... --json` through `2>/dev/null` before jq (strips CLI warnings)
- Use `xmllint --format -` to pretty-print SOAP responses
- SOAP API is the ONLY reliable way to enable DealAgent settings
- CLI Metadata deploy WILL report success even when it fails
- Verify every enablement with a post-call check (SOAP readMetadata or SOQL)
