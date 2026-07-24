# Authentication and CLI Compatibility

## Authentication Methods

### Web Login (Recommended for Initial Setup)

```bash
ORG="pipeline-mgmt-org"
BROWSER=/usr/bin/open sf org login web --instance-url https://login.salesforce.com --alias $ORG
```

### SFDX Auth URL (CI/CD and Automation)

```bash
# Export from authenticated org
sf org display --target-org $ORG --verbose --json 2>/dev/null | jq -r '.result.sfdxAuthUrl' > authurl.txt

# Import in another environment
sf org login sfdx-url --sfdx-url-file authurl.txt --alias $ORG
```

### JWT Bearer (Service Accounts)

```bash
sf org login jwt --client-id <connected-app-client-id> \
  --jwt-key-file server.key \
  --username admin@example.com \
  --instance-url https://login.salesforce.com \
  --alias $ORG
```

---

## Extracting Credentials

```bash
# Get instance URL (always works)
INSTANCE_URL=$(sf org display --target-org $ORG --json 2>/dev/null | jq -r '.result.instanceUrl')

# Get access token — newer CLI versions (2.108+) REDACT it in sf org display --json
ACCESS_TOKEN=$(sf org display --target-org $ORG --json 2>/dev/null | jq -r '.result.accessToken')

# Fallback for redacted token (CLI 2.108+)
if [[ -z "$ACCESS_TOKEN" || "$ACCESS_TOKEN" == "null" || "$ACCESS_TOKEN" == *"REDACTED"* ]]; then
  ACCESS_TOKEN=$(echo "y" | sf org auth show-access-token --target-org $ORG --no-prompt --json 2>/dev/null | jq -r '.result.accessToken // empty')
fi
```

**Why the fallback**: Starting with SF CLI ~2.108, `sf org display --json` returns `"[REDACTED] Use 'sf org auth show-access-token' to view"` instead of the actual token. The `sf org auth show-access-token --json` command always returns the real token. The `echo "y"` handles the interactive confirmation prompt in non-TTY environments.

**Why `2>/dev/null`**: The Salesforce CLI emits non-JSON warnings to stderr (plugin updates, deprecation notices). When piping to `jq`, these warnings get mixed with stdout on some CLI versions, causing parse failures. The `2>/dev/null` ensures only clean JSON reaches `jq`.

---

## CLI Compatibility Notes

### Version Requirements

| Feature | Minimum CLI Version | Notes |
|---------|-------------------|-------|
| `sf data query` | Any | Core command |
| `sf data create record` | Any | Core command |
| `sf org assign permset` | v2.20+ | Use Data API fallback for older versions |
| `sf org assign permsetgroup` | v2.130+ | Use Data API fallback for older versions |
| `sf project retrieve start` | v2.0+ | Core command |
| `sf project deploy start` | v2.0+ | Core command |
| `sf agent` commands | v2.50+ | Requires `@salesforce/plugin-agent`; creates Agent Script (AiAuthoringBundle) agents, NOT classic Bots |

### Permission Assignment Compatibility

```bash
# Modern CLI (v2.130+):
sf org assign permsetgroup --name SalesManagementUserPsg --on-behalf-of user@example.com --target-org $ORG --json 2>/dev/null

# Universal fallback (all CLI versions) — Data API approach:
PSG_ID=$(sf data query -q "SELECT Id FROM PermissionSetGroup WHERE DeveloperName = 'SalesManagementUserPsg'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
USER_ID=$(sf data query -q "SELECT Id FROM User WHERE Username = 'user@example.com'" --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id')
sf data create record --sobject PermissionSetAssignment --values "AssigneeId='${USER_ID}' PermissionSetGroupId='${PSG_ID}'" --target-org $ORG --json 2>/dev/null
# DUPLICATE_VALUE error = already assigned = success
```

### SOAP API vs CLI for Settings (Verified)

**Settings that REQUIRE SOAP API** (CLI cannot even retrieve them):
- `SalesDealAgentSettings` — CLI returns "Settings type is unknown"

**Settings that work with CLI** (verified — retrieve AND deploy both succeed):
- `EinsteinGptSettings` — CLI deploy works, no silent failure observed
- `EinsteinCopilotSettings` — CLI deploy works
- `OpportunitySettings` — CLI deploy works (may fail on specific fields that require additional config)
- `EnhancedNotesSettings` — CLI retrieve works
- `EmailAdministrationSettings` — CLI retrieve works

**Recommendation**: Use SOAP API for `SalesDealAgentSettings` (only option). For other settings, CLI is acceptable but SOAP provides a uniform approach. Always verify after deployment regardless of method.

### CLI Retrieve Returns Empty for Settings (Known Issue)

**Symptom**: `sf project retrieve start --metadata "Settings:EinsteinGptSettings"` succeeds but creates empty directories with no XML files, even when the setting is enabled in the org.

**Root cause**: The CLI retrieve for Settings metadata types has a known limitation where:
1. The type must be known to the CLI's internal metadata registry
2. Even known types may return empty if the org has no explicit customization (only default values)
3. Some settings types (like `SalesDealAgentSettings`) are not in the registry at all

**Workaround — Use SOAP `readMetadata` for verification**:
```bash
# Instead of retrieving via CLI, use SOAP readMetadata to CHECK settings state
curl -s "${INSTANCE_URL}/services/Soap/m/64.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: readMetadata" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:readMetadata><met:type>EinsteinGptSettings</met:type><met:fullNames>EinsteinGpt</met:fullNames></met:readMetadata></soapenv:Body>
</soapenv:Envelope>" | grep -o "<enableEinsteinGptPlatform>[^<]*"
```

**Workaround — Use SOAP `updateMetadata` for deployment**:
```bash
# For settings that CLI can't deploy, use SOAP updateMetadata
# (see scripts/setup-all.sh for full patterns)
```

**Rule**: Never trust `sf project retrieve start` for Settings verification. Always verify enablement via SOAP `readMetadata` or direct API queries after any deploy operation.

See `references/soap-api-enablement.md` for all SOAP API patterns.

---

## CLI Hardening Rules

1. **Always** use `2>/dev/null` on `sf ... --json` piped to jq
2. **Always** verify enablement after deploy (don't trust success response alone)
3. **Never** use `sf project deploy start` for `SalesDealAgentSettings` (not recognized by CLI)
4. **Never** use `--use-tooling-api` for `BotDefinition` queries (not supported — use standard SOQL)
5. **Prefer** Data API approach for permission assignments (universal compatibility)
6. **Check** `jq` output for `null` before using variables (prevents empty-string commands)

```bash
# Safe variable extraction pattern
VALUE=$(sf data query -q "..." --target-org $ORG --json 2>/dev/null | jq -r '.result.records[0].Id // empty')
if [[ -z "$VALUE" ]]; then
  echo "ERROR: Query returned no results"
  exit 1
fi
```
