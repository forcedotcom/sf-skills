# Data Sources Decision Table

Pipeline Management uses data sources to generate field update suggestions. The quality and relevance of suggestions directly depends on which data sources are enabled and have recent activity.

---

## Data Source Matrix

| Data Source | What It Provides | Required Setting | Automation Level |
|-------------|------------------|------------------|-----------------|
| **Notes** (ContentNote) | Meeting notes, deal notes attached to opportunities | `EnhancedNotesSettings.enableEnhancedNotes` | ✅ SOAP API |
| **Enhanced Email** | Email body text indexing for deeper analysis | `EmailAdministrationSettings.enableEnhancedEmailEnabled` | ✅ SOAP API |
| **Einstein Activity Capture** (EAC) | Auto-captured emails + calendar events | Separate product provisioning | ❌ UI setup required |
| **Einstein Conversation Insights** (ECI) | Voice/video call transcripts | Separate product provisioning | ❌ UI setup required |

---

## Decision Flow

```text
Does the org have Notes (ContentNote) with recent activity?
├── Yes → Enable Enhanced Notes ✅ (baseline data source)
└── No → Create sample notes on open opportunities for testing

Does the org use email-to-opportunity logging?
├── Yes → Enable Enhanced Email ✅ (enables email body indexing)
│         → Check if Einstein Activity Capture is provisioned
│           ├── Yes → Verify EAC is capturing emails (Setup → EAC Configuration)
│           └── No → Email logging via manual BCC or Salesforce Inbox
└── No → Skip email data source

Does the org use call recording/transcription?
├── Yes → Check if Einstein Conversation Insights is provisioned
│         ├── Yes → Verify transcripts exist: SELECT COUNT() FROM VoiceCall
│         └── No → Cannot enable without ECI license
└── No → Skip call transcript data source
```

---

## Minimum Viable Data Sources

For Pipeline Management to produce useful suggestions, at minimum:

1. **Notes** — must be enabled (lowest barrier)
2. **Recent opportunity activity** — at least some open opportunities must have activity in the last 7 days

Without any data sources with recent content, the flow will run daily but produce no suggestions.

---

## Verifying Data Source Activity

```bash
ORG="pipeline-mgmt-org"

echo "=== Notes (primary data source) ==="
sf data query -q "SELECT COUNT() FROM ContentNote WHERE CreatedDate = LAST_N_DAYS:30" --target-org $ORG 2>/dev/null

echo "=== Emails (if Enhanced Email enabled) ==="
sf data query -q "SELECT COUNT() FROM EmailMessage WHERE CreatedDate = LAST_N_DAYS:30 AND RelatedToId != null" --target-org $ORG 2>/dev/null

echo "=== Recent opportunity activity ==="
sf data query -q "SELECT COUNT() FROM Opportunity WHERE LastActivityDate = LAST_N_DAYS:7 AND IsClosed = false" --target-org $ORG 2>/dev/null

echo "=== Voice calls (if ECI enabled) ==="
sf data query -q "SELECT COUNT() FROM VoiceCall WHERE CreatedDate = LAST_N_DAYS:30" --target-org $ORG 2>/dev/null
```

**Expected**: Total > 0 for at least Notes and recent opportunity activity.

---

## Enabling Data Sources via API

### Notes (SOAP API)

```bash
# See references/soap-api-enablement.md Section 3
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>
    <met:metadata xsi:type='met:EnhancedNotesSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
      <met:fullName>EnhancedNotes</met:fullName>
      <met:enableEnhancedNotes>true</met:enableEnhancedNotes>
    </met:metadata>
  </met:updateMetadata></soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|message)" | head -5
```

### Enhanced Email (SOAP API)

```bash
# See references/soap-api-enablement.md Section 4
curl -s "${INSTANCE_URL}/services/Soap/m/62.0" \
  -H "Content-Type: text/xml; charset=UTF-8" \
  -H "SOAPAction: update" \
  -d "<?xml version='1.0' encoding='utf-8'?>
<soapenv:Envelope xmlns:soapenv='http://schemas.xmlsoap.org/soap/envelope/' xmlns:met='http://soap.sforce.com/2006/04/metadata'>
  <soapenv:Header><met:SessionHeader><met:sessionId>${ACCESS_TOKEN}</met:sessionId></met:SessionHeader></soapenv:Header>
  <soapenv:Body><met:updateMetadata>
    <met:metadata xsi:type='met:EmailAdministrationSettings' xmlns:xsi='http://www.w3.org/2001/XMLSchema-instance'>
      <met:fullName>EmailAdministration</met:fullName>
      <met:enableEnhancedEmailEnabled>true</met:enableEnhancedEmailEnabled>
    </met:metadata>
  </met:updateMetadata></soapenv:Body>
</soapenv:Envelope>" | xmllint --format - 2>/dev/null | grep -E "(success|message)" | head -5
```

### Einstein Activity Capture (UI-Only)

EAC requires separate product provisioning and cannot be fully automated:

1. Setup → Einstein Activity Capture → Settings
2. Enable for target users or profiles
3. Configure sync settings (which emails/events to capture)
4. Wait 24-48 hours for initial sync

### Einstein Conversation Insights (UI-Only)

ECI requires a separate license and provisioning:

1. Setup → Einstein Conversation Insights → Settings
2. Connect recording provider (Zoom, Teams, etc.)
3. Enable for target users
4. Wait for transcripts to populate

---

## Data Source Impact on Suggestions

| Data Source | Suggestion Quality Impact |
|-------------|--------------------------|
| Notes only | Basic — relies on manually written notes |
| Notes + Email | Better — captures communication context automatically |
| Notes + Email + EAC | Good — full email + calendar activity captured |
| Notes + Email + EAC + ECI | Best — includes call transcript insights |

**Recommendation**: Enable Notes + Enhanced Email as the baseline (both automatable). Add EAC and ECI if the org has those licenses.

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| No suggestions generated despite active flow | No recent data in any source | Create notes on open opportunities, wait 24h |
| Suggestions low quality | Only notes enabled, notes are sparse | Enable Enhanced Email, add more detailed notes |
| "VoiceCall not supported" error | ECI not provisioned | Skip ECI-related queries if not licensed |
| Emails not appearing in suggestions | Enhanced Email not enabled | Enable via SOAP API (see above) |
| EAC enabled but no emails captured | Sync delay or configuration issue | Check EAC settings, wait 24-48h |
