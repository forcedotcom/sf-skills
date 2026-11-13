# Metadata-API facets: automated responses, keywords, inactivity, parameters

Load this for facets 2–5. These settings live only in the channel's **metadata** — every Data/Connect/Tooling read of them returns `INVALID_TYPE`/"No such column" (verified live on sdb6, 2026-09). Configure them by retrieving the channel's `.messagingChannel-meta.xml`, editing it, and deploying it back.

## The retrieve → edit → deploy flow

You need the channel's **DeveloperName** (the metadata member name), not just its Id. Get it from the Stage 1 query (`DeveloperName`).

```bash
# 1. Scratch sfdx project (throwaway — do NOT create inside the skills repo)
mkdir -p /tmp/cs-meta/force-app/main/default && cd /tmp/cs-meta
cat > sfdx-project.json <<'EOF'
{ "packageDirectories": [{ "path": "force-app", "default": true }], "sourceApiVersion": "69.0" }
EOF

# 2. Retrieve the channel (use a package.xml manifest for >1 channel;
#    a comma-separated -m list is parsed as one member by some CLI versions)
sf project retrieve start --target-org '{ORG_ALIAS}' -m 'MessagingChannel:{DeveloperName}' --json

# 3. Edit force-app/main/default/messagingChannels/{DeveloperName}.messagingChannel-meta.xml
#    (add/replace the facet blocks below)

# 4. Deploy back
sf project deploy start --target-org '{ORG_ALIAS}' -m 'MessagingChannel:{DeveloperName}' --json
```

On deploy failure, read `result.details.componentFailures[].problem` and return it as `{ok:false, kind:"metadata-deploy-failed", message: ...}`. **sf calls on this org take 2–4 min each — slow is normal, not a hang.**

Edit rules: match/replace an existing block by its identity (`<type>` for auto-responses; `<keywordType>`+`<language>` for keywords), otherwise append a new one. Preserve all other elements. Keep the file well-formed.

---

## Facet 2 — Automated responses (`<automatedResponses>`)

Repeatable top-level element. Each block has a `<type>` (the event) and one of two content shapes.

**Content shapes:**
- `TextResponse` — inline text: `<autoResponseContentType>TextResponse</autoResponseContentType>`, `<response>…</response>`, and usually `<language>` (may be omitted on `OptInPrompt`).
- `MessageDefinition` — references a `ConversationMessageDefinition` by name: `<autoResponseContentType>MessageDefinition</autoResponseContentType>`, `<messageDefinitionName>…</messageDefinitionName>` (that definition must already exist in the org). Common on MIAW.

**The 12 `<type>` values** (superset across all Enhanced types):

| `type` | When sent |
| --- | --- |
| `InitialResponse` | Customer's first inbound message was received |
| `AgentEngagedResponse` | A service rep accepted the session |
| `AgentEndEngagementResponse` | Session ended (rep or end user); optional post-chat URL |
| `EndUserInactiveResponse` | Conversation ended because the end user stopped responding |
| `EndUserIdleResponse` | End user went idle; **adds `<responseTimeoutInMins>`** (minutes of idle before it fires) |
| `RerouteResponse` | Conversation was rerouted |
| `OptInPrompt` | Reply didn't match an opt-in keyword |
| `OptInConfirmation` | Successful opt-in |
| `DoubleOptInPrompt` | Reply didn't match a double-opt-in keyword |
| `OptOutConfirmation` | Successful opt-out |
| `HelpResponse` | End user sent a help keyword |
| `CustomResponse` | Custom keyword match |

**XML-escape** `<response>` text: `'`→`&apos;` `"`→`&quot;` `&`→`&amp;` `<`→`&lt;` `>`→`&gt;`.

```xml
<!-- TextResponse -->
<automatedResponses>
    <autoResponseContentType>TextResponse</autoResponseContentType>
    <language>en_US</language>
    <response>You&apos;ve opted out of receiving messages from us.</response>
    <type>OptOutConfirmation</type>
</automatedResponses>
<!-- MessageDefinition + idle timeout -->
<automatedResponses>
    <autoResponseContentType>MessageDefinition</autoResponseContentType>
    <messageDefinitionName>Customer_Idle_Message</messageDefinitionName>
    <responseTimeoutInMins>4</responseTimeoutInMins>
    <type>EndUserIdleResponse</type>
</automatedResponses>
```

---

## Facet 3 — Messaging keywords (`<messagingKeywords>`)

Repeatable top-level element — one block per (keywordType, language). Each has one or more `<keyword>` children, a `<keywordType>` (`OptIn` | `OptOut` | `Help`), and a `<language>`. Type-agnostic; `OptIn` groups appear on types that support explicit opt-in (e.g. Apple, LINE).

```xml
<messagingKeywords>
    <keyword>cancel</keyword>
    <keyword>end</keyword>
    <keyword>stop</keyword>
    <keyword>unsubscribe</keyword>
    <keywordType>OptOut</keywordType>
    <language>en_US</language>
</messagingKeywords>
<messagingKeywords>
    <keyword>help</keyword>
    <keywordType>Help</keywordType>
    <language>en_US</language>
</messagingKeywords>
```

> Consent keyword *records* (`MsgChannelLanguageKeyword`, facet 1) and metadata `<messagingKeywords>` are distinct surfaces. Facet 1 (Data API) drives the activation-readiness check; `<messagingKeywords>` is the channel's metadata representation. Configure consent via facet 1 for activation; use `<messagingKeywords>` when editing the channel's metadata directly.

---

## Facet 4 — Session inactivity (top-level, scoped)

Four fields, **siblings of `<embeddedConfig>`** (top-level, NOT nested inside it):

| Field | Type | Notes |
| --- | --- | --- |
| `endUserIdleTimeOut` | int (5–30) | minutes idle before the idle action |
| `endUserIdleAction` | enum | `Inactivate` \| `End` \| `InactivateAndEnd` |
| `endInactiveSessionTimeOut` | int | minutes before an inactive session ends |
| `isAgentMessageResetInactivityEnabled` | bool | agent message resets the idle timer |

```xml
<endInactiveSessionTimeOut>5</endInactiveSessionTimeOut>
<endUserIdleAction>InactivateAndEnd</endUserIdleAction>
<endUserIdleTimeOut>5</endUserIdleTimeOut>
```

**Per-type scope (verified live):** all four → **MIAW (EmbeddedMessaging) only**. `isAgentMessageResetInactivityEnabled` alone also appears on **Apple** and **Facebook**. **SMS/WhatsApp/LINE carry no inactivity fields** — emit `facet-not-applicable`. On 262-line pods only `endUserIdleTimeOut` deploys (`endInactiveSessionTimeOut`/`endUserIdleAction` land at 264+) — see `gotchas.md`.

---

## Facet 5 — Pre-chat parameters (MIAW pre-chat only, rare)

`<customParameters>` / `<standardParameters>` are pre-chat-form fields. A live scan found **0 occurrences across all sampled channels including MIAW** — they exist only on MIAW channels that explicitly enable pre-chat. Skip unless the caller is configuring pre-chat.

```xml
<customParameters>
    <externalParameterName>City</externalParameterName>
    <masterLabel>City</masterLabel>
    <maxLength>30</maxLength>
    <name>City</name>
    <parameterDataType>String</parameterDataType>
</customParameters>
```

`parameterDataType` is `String` (not `Text`). **Never emit `<actionParameterMappings>`** — 0 occurrences across a 191-channel scan; it's a Tooling-only entity, mapped in the UI post-deploy. `<standardParameters>` (`parameterType` = `FirstName`|`LastName`|`Email`|`Subject`) is likewise MIAW-pre-chat-only.

---

## Per-type applicability matrix (verified live, sdb6 2026-09)

| Facet | MIAW | Apple | Facebook | LINE | SMS | WhatsApp |
| --- | :-: | :-: | :-: | :-: | :-: | :-: |
| Auto-responses (2) | yes | yes | yes | yes | yes | yes |
| Messaging keywords (3) | yes | yes | yes | yes | yes | yes |
| Inactivity — 3 timeout fields (4) | yes | no | no | no | no | no |
| Inactivity — reset flag (4) | yes | yes | yes | no | no | no |
| Pre-chat parameters (5) | pre-chat only | no | no | no | no | no |

Derived from a Metadata-API retrieve of real channels of each type. Don't deploy a facet a type doesn't support — the deploy will either fail or silently drop the element.
