# Autonomous Updates in Pipeline Management

Pipeline Management generates opportunity field update suggestions by default, but requires manual approval. **Autonomous updates** allow the agent to apply approved suggestions automatically without user intervention.

---

## Safety Default: Suggestion-Only Mode

By default, Pipeline Management operates in **suggestion-only mode**:
- Agent generates `AiGenActionItem` records (`Type = 'FIELD_UPDATE'`) with suggested field updates
- Suggestions appear in Sales Console under "Pipeline Management" component
- Users manually review and approve/reject each suggestion
- No automatic writes to opportunity fields

This is the **safest mode** for initial deployment and testing.

---

## Global Autonomous Toggle

### Setting: `enableDealAgentAutoApproveAllTasks`

Located in `SalesDealAgentSettings` (SOAP API only — CLI deploy silently fails).

**When enabled**:
- Agent automatically applies **all** field update suggestions without user approval
- Suggestions are still logged as `AiGenActionItem` records but are immediately applied
- Users see updates in Opportunity field history
- No review workflow

**When disabled** (default):
- Suggestion-only mode (manual approval required)

---

## Enabling Global Autonomous Updates

### Via SOAP API v64.0

```bash
ORG="pipeline-mgmt-org"
AUTH_INFO=$(sf org display --target-org $ORG --json 2>/dev/null)
ACCESS_TOKEN=$(echo "$AUTH_INFO" | jq -r '.result.accessToken')
INSTANCE_URL=$(echo "$AUTH_INFO" | jq -r '.result.instanceUrl')

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
        <met:enableDealAgentAutoApproveAllTasks>true</met:enableDealAgentAutoApproveAllTasks>
      </met:metadata>
    </met:updateMetadata>
  </soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null
```

### Verification

```bash
sf data query -q "SELECT enableDealAgent, enableDealAgentAutoApproveAllTasks FROM SalesDealAgentSettings" --target-org $ORG --json 2>/dev/null
```

**Expected output**:
```json
{
  "enableDealAgent": true,
  "enableDealAgentAutoApproveAllTasks": true
}
```

---

## Per-Field Autonomous Updates

**Status**: Not yet available in current Pipeline Management release (as of API v67.0).

**Future capability**: Salesforce plans to support per-field autonomous toggles, allowing fine-grained control:
- Enable autonomous updates for `Stage` (high confidence field)
- Require manual approval for `Amount` (high impact field)
- Enable autonomous updates for `NextStep` (low risk field)

**Current workaround**: Use global toggle only. If per-field control is required, implement custom Apex trigger to block autonomous updates on specific fields based on business logic.

---

## Daily LLM Request Limits

Pipeline Management has **daily LLM request limits** to prevent quota exhaustion:

| Limit | Value |
|-------|-------|
| Max LLM requests per day | 8,000 |
| Approximate opportunities processed | ~4,000 (2 requests per opportunity: grounding + suggestion) |

The 8,000/day figure was observed live: the suggestion flow's debug log emits `{enqueuedStatus=Successful, currentLLMUsage=N, dailyLLMLimit=8000}`. Confirm the current value for your org/edition — `dailyLLMLimit` in that log line is the source of truth.

**What happens when limit is reached**:
- Agent stops generating new suggestions until next day (UTC reset)
- Existing suggestions remain visible and actionable
- No error messages shown to users

**Monitoring usage**:
```bash
# Query suggestion records created today
sf data query -q "SELECT COUNT() FROM AiGenActionItem WHERE Type = 'FIELD_UPDATE' AND CreatedDate = TODAY" --target-org $ORG --json 2>/dev/null

# Each AiGenActionItem represents 1 field-update suggestion
# Grounding + suggestion together consume ~2 LLM requests per opportunity
```

**Recommendations**:
- Start with suggestion-only mode to gauge usage patterns
- Enable autonomous updates only after confirming daily volume stays under 4,000 opportunities
- Monitor `AiGenActionItem` record creation rate
- Consider stage-based filtering (only generate suggestions for opportunities in specific stages)

---

## Risk Matrix: When to Enable Autonomous Updates

| Scenario | Autonomous Mode | Rationale |
|----------|-----------------|-----------|
| Initial deployment | ❌ Disabled | Validate suggestion quality first |
| Sandbox testing | ✅ Enabled | Test end-to-end flow with real data |
| Production pilot (< 50 users) | ⚠️ Optional | Depends on confidence in suggestion accuracy |
| Production rollout (> 50 users) | ❌ Disabled initially | Start with manual approval, enable after 2 weeks |
| High-value opportunities (> $1M) | ❌ Disabled | Manual approval for high-stakes updates |
| Standard opportunities (< $100K) | ✅ Enabled | Low risk for autonomous updates |

---

## Disabling Autonomous Updates

To revert to suggestion-only mode:

```bash
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
</soapenv:Envelope>" | xmllint --format - 2>/dev/null
```

---

## Troubleshooting

### Autonomous updates enabled but suggestions still require approval

**Symptom**: `enableDealAgentAutoApproveAllTasks = true` but suggestions appear in UI for manual approval

**Causes**:
1. **Setting not propagated** — Wait up to 5 minutes after SOAP API call
2. **User permission mismatch** — Autonomous updates may require specific permission set (verify with Salesforce support)
3. **Opportunity-level override** — Some orgs have custom validation rules or process builders blocking automatic updates

**Diagnosis**:
```bash
# Check setting value
sf data query -q "SELECT enableDealAgentAutoApproveAllTasks FROM SalesDealAgentSettings" --target-org $ORG --json 2>/dev/null

# Check suggestion status (Subject = the field API name, ParentId = the Opportunity Id)
sf data query -q "SELECT Id, Subject, Status, ParentId FROM AiGenActionItem WHERE Type = 'FIELD_UPDATE' AND CreatedDate = TODAY LIMIT 10" --target-org $ORG --json 2>/dev/null
```

### Autonomous updates apply wrong values

**Symptom**: Agent autonomously updates fields but values are incorrect

**Causes**:
1. **Insufficient grounding data** — Agent lacks recent notes, emails, or call transcripts
2. **Stage descriptions missing or outdated** — See `references/opportunity-stages.md`
3. **Prompt template misconfiguration** — Custom prompt templates may override default logic

**Fix**:
1. Disable autonomous updates immediately
2. Review `AiGenActionItem` records for patterns (which fields have high error rates — group by `Subject`)
3. Add or update stage descriptions for frequently misidentified stages
4. Re-enable autonomous updates after validation

---

## Notes

- Always test autonomous updates in sandbox before production enablement
- Use suggestion-only mode for at least 2 weeks in production to validate accuracy
- Monitor field history on opportunities to detect autonomous update patterns
- Consider custom Apex triggers for org-specific autonomous update rules (e.g., block updates on closed opportunities)
- SOAP API v64.0+ required for `SalesDealAgentSettings` (CLI deploy silently fails)
