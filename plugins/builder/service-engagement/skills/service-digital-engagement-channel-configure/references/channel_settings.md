# Messaging Channel Settings Reference

Complete reference for all configurable settings on a `MessagingChannel` metadata type for enhanced chat (MIAW).

---

## Core Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `masterLabel` | String | Yes | User-visible channel name (max 40 chars) |
| `messagingChannelType` | Enum | Yes | Always `EmbeddedMessaging` for enhanced chat |

The channel's API name (developer name) is determined by the **file name** (`<Name>.messagingChannel-meta.xml`), not a field in the XML body.

---

## Routing Configuration

Set `sessionHandlerType` and the corresponding handler field.

| `sessionHandlerType` | Handler Fields | Description |
|----------------------|----------------|-------------|
| `Queue` | `sessionHandlerQueue` | Routes to an Omni-Channel Queue |
| `Flow` | `sessionHandlerFlow` + `sessionHandlerQueue` | Routes via an Omni-Channel Flow with a fallback queue |
| `User` | `sessionHandlerUser` + `sessionHandlerQueue` | Routes directly to a specific user with a fallback queue |
| `AgentforceServiceAgent` | `sessionHandlerAsa` + `sessionHandlerQueue` | Routes to an ASA with a fallback queue |

### Routing Decision Matrix

| Scenario | Recommended Type | Rationale |
|----------|-----------------|-----------|
| Skills-based routing needed | `Flow` | Flow can evaluate agent skills and route dynamically |
| Simple round-robin distribution | `Queue` | Queue handles basic load balancing |
| Direct assignment to a specific agent | `User` | Routes all conversations to a named user |
| AI-first with human escalation | `AgentforceServiceAgent` | ASA handles initial interaction, escalates to fallback queue |
| Complex routing logic with data lookups | `Flow` | Flow supports record queries and branching |
| Single team, no skill differentiation | `Queue` | Simplest configuration for uniform teams |

### Flow Routing Requirements

When using `Flow` routing:
- `sessionHandlerFlow` — the Omni-Channel Flow's API name
- `sessionHandlerQueue` — **required** fallback queue for escalation
- Both fields must be populated

### User Routing Requirements

When using `User` routing:
- `sessionHandlerUser` — the user's ID
- `sessionHandlerQueue` — **required** fallback queue when user is unavailable
- Both fields must be populated

### ASA Routing Requirements

When using `AgentforceServiceAgent` routing:
- `sessionHandlerAsa` — the ASA bot's developer name
- `sessionHandlerQueue` — **required** fallback queue for escalation
- Both fields must be populated

### Queue Requirements

When using `Queue` routing, the referenced queue must:
- Exist as a `Queue` metadata record
- Include `MessagingSession` in its `queueSobject` types

---

## Embedded Configuration (`<embeddedConfig>`)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `allowedFileTypes` | String | See below | Comma-separated list of allowed file extensions |
| `anonymousUserJwtExpirationTime` | Integer | `360` | JWT expiration in minutes (required for UnAuth, range 60-4320) |
| `verifiedUserJwtExpirationTime` | Integer | `60` | JWT expiration in minutes (required for Auth, range 60-240) |
| `authMode` | Enum | `UnAuth` | `Auth` (JWT verified) or `UnAuth` (unauthenticated) |
| `chatAbandonmentTimeout` | Integer | `5` | Minutes before abandoned conversation cleanup |
| `isAbandonedChatsEnabled` | Boolean | `false` | Enable abandoned chat detection and cleanup |
| `isAttachmentUploadEnabled` | Boolean | `true` | Whether file uploads are allowed |
| `isEstimatedWaitTimeEnabled` | Boolean | `false` | Show estimated wait time in embedded config |
| `isFallbackMessageEnabled` | Boolean | `false` | Fallback message when agents unavailable |
| `isFileAttachmentExtUnrestricted` | Boolean | `false` | Allow any file extension (ignores `allowedFileTypes`) |
| `isSaveTranscriptEnabled` | Boolean | `false` | Save conversation transcripts |
| `maxFileSize` | Integer | `5` | Maximum file size in MB (range 1-5) |
| `isAgentAvlCheckEnabled` | Boolean | `false` | Enable chat button visibility based on agent availability |
| `queueLimitType` | Enum | — | Required if `isAgentAvlCheckEnabled` is `true`. `QueueLength` or `QueueLengthPerAgent` |
| `queueThreshold` | Integer | — | Required if `isAgentAvlCheckEnabled` is `true`. Threshold at which chat button becomes hidden |

### Default Allowed File Types

```text
bmp,csv,doc,docx,gif,jpg,pdf,png,tiff,txt,xls,xml
```

Comma-separated string, no spaces between extensions.

### JWT-Based User Verification

When user verification is enabled:
- Set `authMode` to `Auth`
- The customer's backend must issue a signed JWT containing user identity claims
- JWTs are verified only once a keyset (public key certificate set) whose key `kid` and issuer match them is attached via `messagingAuthorizations`; the channel itself deploys without one. Creating keys is a separate setup

---

## Messaging Authorizations (`<messagingAuthorizations>`)

Only applicable when `authMode` is `Auth`. Do not include when `authMode` is `UnAuth`.

Nested inside `<embeddedConfig>`. Configures verified user identity for the channel.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `authorizationType` | Enum | Yes | Always `PublicKeyCertificateSet` |
| `publicKeyCertificateSetName` | String | Yes | API name of an existing keyset used for public key verification |
| `enabled` | Boolean | Yes | Whether this authorization is active |
| `authIdentifier` | String | Yes | Free-form configuration name (default: the channel file name); not the JWT `sub` claim |

Do not emit `authProviderName`. With `Auth`, set `verifiedUserJwtExpirationTime` (60-240) and omit `anonymousUserJwtExpirationTime`.

```xml
<embeddedConfig>
    <authMode>Auth</authMode>
    <verifiedUserJwtExpirationTime>60</verifiedUserJwtExpirationTime>
    <messagingAuthorizations>
        <authIdentifier>Customer_Support_Chat</authIdentifier>
        <authorizationType>PublicKeyCertificateSet</authorizationType>
        <enabled>true</enabled>
        <publicKeyCertificateSetName>Support_Keyset</publicKeyCertificateSetName>
    </messagingAuthorizations>
</embeddedConfig>
```

---

## Session Settings (top-level)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `endUserIdleTimeOut` | Integer | `5` | Minutes of user inactivity before idle warning (range 5-30) |
| `endUserIdleAction` | Enum | — | Action taken when the idle timeout elapses: `Inactivate`, `End`, or `InactivateAndEnd` |
| `endInactiveSessionTimeOut` | Integer | — | Minutes after `endUserIdleAction` fires before the inactive session itself ends |
| `isAgentMessageResetInactivityEnabled` | Boolean | — | Restart the customer's inactivity timer when a rep sends a message (Setup label: "Rep messages reset customer's inactivity timer"). Only takes effect when `endUserIdleTimeOut` is set; it is forced to `false` otherwise |
| `isEstimatedWaitTimeEnabled` | Boolean | `false` | Show estimated wait time. Setup's **Notification** list (None / Estimated Wait Time / Queue Position) allows one choice, so never set this and `isQueuePositionEnabled` both `true` (deploy fails: "You can't enable Queue Position and Estimated Wait Time options at the same time") |
| `isQueuePositionEnabled` | Boolean | `false` | Show queue position to user. At most one of this and `isEstimatedWaitTimeEnabled` may be `true` |
| `isSynchronousChatEnabled` | Boolean | `false` | Enable real-time synchronous chat |
| `isVoiceModeEnabled` | Boolean | `false` | Enable voice mode capability |

Setup UI (Customer Inactivity card): `endUserIdleTimeOut` is "Minutes to Inactivate Session" / "Minutes to End Session" (5-30); `endUserIdleAction` is "Choose action when customer is idle" with values "Inactivate Session" (`Inactivate`), "End Session" (`End`), and "Inactivate & End Session" (`InactivateAndEnd`); `endInactiveSessionTimeOut` is "Minutes to End Session After Inactivation" (5-30, only meaningful with `InactivateAndEnd`).

`endUserIdleTimeOut`, `endUserIdleAction`, `endInactiveSessionTimeOut`, and `isAgentMessageResetInactivityEnabled` are **MIAW (EmbeddedMessaging) only** — not applicable to SMS/WhatsApp/LINE. These can be deployed together with `isAbandonedChatsEnabled`/`chatAbandonmentTimeout` with no conflict.

```xml
<endUserIdleTimeOut>5</endUserIdleTimeOut>
<endUserIdleAction>InactivateAndEnd</endUserIdleAction>
<endInactiveSessionTimeOut>10</endInactiveSessionTimeOut>
```

---

## Standard Parameters (`<standardParameters>`)

Repeatable element — one block per standard pre-chat field.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `parameterType` | Enum | Yes | `FirstName`, `LastName`, `Email`, `Subject` |
| `actionParameterMappings` | Object | No | Maps this parameter to an Omni-Channel Flow action input variable |

### Action Parameter Mappings

When the channel uses Flow-based routing, `actionParameterMappings` maps a standard parameter to a flow input variable so the value collected from the user is passed into the routing flow.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `actionParameterName` | String | Yes | The API name of the flow input variable to map this parameter to |

```xml
<standardParameters>
    <actionParameterMappings>
        <actionParameterName>fName</actionParameterName>
    </actionParameterMappings>
    <parameterType>FirstName</parameterType>
</standardParameters>
<standardParameters>
    <actionParameterMappings>
        <actionParameterName>lName</actionParameterName>
    </actionParameterMappings>
    <parameterType>LastName</parameterType>
</standardParameters>
<standardParameters>
    <actionParameterMappings>
        <actionParameterName>email</actionParameterName>
    </actionParameterMappings>
    <parameterType>Email</parameterType>
</standardParameters>
<standardParameters>
    <actionParameterMappings>
        <actionParameterName>subject</actionParameterName>
    </actionParameterMappings>
    <parameterType>Subject</parameterType>
</standardParameters>
```

---

## Custom Parameters (`<customParameters>`)

Repeatable element — one block per pre-chat field for data collection.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | Yes | Unique API name for the parameter |
| `masterLabel` | String | Yes | Display label shown to agent/user |
| `parameterDataType` | String | Yes | **Always `String`** — see note below |
| `externalParameterName` | String | Yes | External mapping name for the parameter |
| `maxLength` | Integer | No | Max chars (default 255) |
| `actionParameterMappings` | Object | No | Maps this parameter to an Omni-Channel Flow action input variable |

> **`parameterDataType` is always `String`.** Every channel custom parameter deploys as `String`, regardless of the field's logical type. The metadata field's declared type is the broad `FlowDataType` enum (`Apex`, `Boolean`, `Currency`, `Date`, `DateTime`, `Multipicklist`, `Number`, `Picklist`, `SObject`, `String`, `Time`), but `MessagingChannel` restricts it at deploy time to `String` only — any other value fails with *"bad value for restricted picklist field."* The parameter's actual data type (Number, Checkbox/Boolean, dropdown, etc.) is not set on the channel; it is chosen at the **deployment** level in the pre-chat New Custom Parameter screen — i.e. via the Embedded Service form field's `formFieldType` (see `service-digital-engagement-deployment-configure`).

### Action Parameter Mappings

When the channel uses Flow-based routing, `actionParameterMappings` maps a custom parameter to a flow input variable so the value collected from the user is passed into the routing flow.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `actionParameterName` | String | Yes | The API name of the flow input variable to map this parameter to |

```xml
<customParameters>
    <actionParameterMappings>
        <actionParameterName>city</actionParameterName>
    </actionParameterMappings>
    <externalParameterName>City</externalParameterName>
    <masterLabel>City</masterLabel>
    <maxLength>30</maxLength>
    <name>City</name>
    <parameterDataType>String</parameterDataType>
</customParameters>
```

### Removing a Custom Parameter

A parameter still used by a pre-chat form can't be deleted ("can't be deleted as it is referenced elsewhere"). Several deployments can share one channel, so **check every deployment before writing**: retrieve all `EmbeddedServiceConfig` and find each one whose `<messagingChannel>` is this channel and whose form has `<formField>` = the param `name`. Don't use a failed channel deploy to find them.

1. If another deployment the user didn't mention still uses the param, stop and ask; changing it is outside the request.
2. Each referencing deployment: remove the field (via `service-digital-engagement-deployment-configure`) and publish it after the user approves.
3. If the param has `actionParameterMappings`, deploy the channel with the mapping removed first.
4. Deploy the channel without that parameter's `<customParameters>` block; keep every other parameter.

---

## Automated Responses (`<automatedResponses>`)

Repeatable element — automated messages sent at specific events. There are two mutually exclusive content shapes, and **which shape applies depends on the `type`** (EmbeddedMessaging channel).

### Shape 1 — `TextResponse` (inline text)

Applies only to `OptOutConfirmation` and `HelpResponse`.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `autoResponseContentType` | Enum | Yes | `TextResponse` |
| `language` | String | Yes | Locale code (e.g., `en_US`) |
| `response` | String | Yes | The response message text (XML-escape special chars) |
| `type` | Enum | Yes | `OptOutConfirmation` or `HelpResponse` |

### Shape 2 — `MessageDefinition` (reference to a Messaging Component)

Applies to `InitialResponse`, `AgentEngagedResponse`, `AgentEndEngagementResponse`, `EndUserInactiveResponse`, `EndUserIdleResponse`, `RerouteResponse`, and `RoutingUnavailableResponse` — the "Conversation Acknowledgement," "Start Conversation," "End Conversation," "Inactive Conversation," "Warning Message," "Reroute Conversation," and "Routing Unavailable" fields in the Setup UI, all backed by a "Messaging Components" (`ConversationMessageDefinition`) picker.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `autoResponseContentType` | Enum | Yes | `MessageDefinition` |
| `messageDefinitionName` | String | Yes | `DeveloperName` of an existing `ConversationMessageDefinition`. Must already exist in the org — build it with the `conversation-message-definition-builder` skill before deploying this reference (see Cross-Skill Integration in SKILL.md) |
| `type` | Enum | Yes | `InitialResponse`, `AgentEngagedResponse`, `AgentEndEngagementResponse`, `EndUserInactiveResponse`, `EndUserIdleResponse`, `RerouteResponse`, or `RoutingUnavailableResponse` |
| `responseTimeoutInMins` | Integer | No | **Only** on `EndUserIdleResponse` and `EndUserInactiveResponse` (range 4-30). Minutes before the idle action fires at which the message is shown (Setup label "Minutes to Show Warning"; Help: "select 4 to show the message 4 minutes before the session inactivates"). On `EndUserIdleResponse` it must be less than `endUserIdleTimeOut` (Setup caps it at `endUserIdleTimeOut` - 1). Rejected on every other type and on `TextResponse` |

**Do not include `<language>` or `<response>` on a `MessageDefinition`-shaped block.** The language comes from the referenced CMD's own `<language>` field. Including `<language>` here causes the deploy to fail — with `"unexpected metadata"` for `InitialResponse`/`AgentEngagedResponse`/`AgentEndEngagementResponse`, and with an internal server error for `EndUserInactiveResponse`. Omitting it is the fix, not a schema quirk to work around another way.

```xml
<!-- TextResponse shape -->
<automatedResponses>
    <autoResponseContentType>TextResponse</autoResponseContentType>
    <language>en_US</language>
    <response>Text STOP to opt out of further messages.</response>
    <type>HelpResponse</type>
</automatedResponses>

<!-- MessageDefinition shape -->
<automatedResponses>
    <autoResponseContentType>MessageDefinition</autoResponseContentType>
    <messageDefinitionName>Customer_Inactive_Message</messageDefinitionName>
    <type>EndUserInactiveResponse</type>
</automatedResponses>

<!-- Idle warning with responseTimeoutInMins (only valid on EndUserIdleResponse / EndUserInactiveResponse) -->
<automatedResponses>
    <autoResponseContentType>MessageDefinition</autoResponseContentType>
    <messageDefinitionName>Idle_Warning_Message</messageDefinitionName>
    <responseTimeoutInMins>4</responseTimeoutInMins>
    <type>EndUserIdleResponse</type>
</automatedResponses>
```

### Response Types

| `type` Value | Content Shape | When Sent |
|-------------|---------------|-----------|
| `OptOutConfirmation` | `TextResponse` | When user opts out of receiving messages |
| `HelpResponse` | `TextResponse` | When user sends a help keyword |
| `InitialResponse` | `MessageDefinition` | Let a customer know that their initial message was received |
| `AgentEngagedResponse` | `MessageDefinition` | Let a customer know that their messaging session was accepted by a service rep |
| `AgentEndEngagementResponse` | `MessageDefinition` | Let a customer know that their messaging session ended, and optionally provide a post-chat URL. Sent when the service rep or end user ends the session |
| `EndUserInactiveResponse` | `MessageDefinition` | Let a customer know that their messaging conversation has ended because they stopped responding |
| `EndUserIdleResponse` | `MessageDefinition` | Warn a customer that their conversation will be inactivated or ended because they are idle. Set in the Customer Inactivity card ("Warning Message"); `responseTimeoutInMins` is how many minutes before the idle action it is shown |
| `RerouteResponse` | `MessageDefinition` | Sent when a conversation is rerouted to a different queue or agent ("Reroute Conversation") |
| `RoutingUnavailableResponse` | `MessageDefinition` | Sent when no routing target is available ("Routing Unavailable") |

Only `OptOutConfirmation` and `HelpResponse` use the `TextResponse` shape; every other type is `MessageDefinition`-only. `OptIn*` and `CustomResponse` types are not used for EmbeddedMessaging channels.

### XML Escaping

Special characters in a `TextResponse` block's `response` must be XML-escaped:
- `'` → `&apos;`
- `"` → `&quot;`
- `&` → `&amp;`
- `<` → `&lt;`
- `>` → `&gt;`

---

## Messaging Keywords (`<messagingKeywords>`)

Repeatable element — keyword groups that trigger automated responses. Each keyword block contains:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `keyword` | String (repeatable) | Yes | Individual trigger word (one `<keyword>` element per word) |
| `keywordType` | Enum | Yes | `OptOut` or `Help` |
| `language` | String | Yes | Locale code (e.g., `en_US`) |

### Default OptOut Keywords

```xml
<messagingKeywords>
    <keyword>cancel</keyword>
    <keyword>end</keyword>
    <keyword>quit</keyword>
    <keyword>stop</keyword>
    <keyword>stopall</keyword>
    <keyword>unsubscribe</keyword>
    <keywordType>OptOut</keywordType>
    <language>en_US</language>
</messagingKeywords>
```

### Default Help Keywords

```xml
<messagingKeywords>
    <keyword>help</keyword>
    <keywordType>Help</keywordType>
    <language>en_US</language>
</messagingKeywords>
```

---

## Setup Prompts: Session Inactivity

Ask using the Setup labels (Customer Inactivity card), with the field in parentheses:

- "Inactivate or end a session after a period of customer inactivity?" If yes, "Minutes to Inactivate Session / End Session?" (`endUserIdleTimeOut`, 5-30).
- "Choose action when customer is idle": **Inactivate Session** (`Inactivate`), **End Session** (`End`), or **Inactivate & End Session** (`InactivateAndEnd`) (`endUserIdleAction` — no other values). **Validate before editing or deploying:** if the user names any other value (e.g. `EndChatSession`, "close", "terminate"), do not write it; say it is not an option, list the three, and ask which one. Never deploy to see whether it is accepted. For Inactivate & End Session also ask "Minutes to End Session After Inactivation?" (`endInactiveSessionTimeOut`, 5-30).
- "Should rep messages reset the customer's inactivity timer?" (`isAgentMessageResetInactivityEnabled`; needs `endUserIdleTimeOut`).
- Optional idle warning: the **Warning Message** prompt under Automated Responses below.

Set all of these as **top-level fields, siblings of `<embeddedConfig>`** (not nested inside it). MIAW (EmbeddedMessaging) only.

Checks:
- [ ] `endUserIdleAction`/`endInactiveSessionTimeOut` are top-level siblings of `<embeddedConfig>`, not nested inside it.
- [ ] `endUserIdleAction` is one of `Inactivate`, `End`, `InactivateAndEnd`, checked before the file is edited (free text such as `EndChatSession` fails with "not a valid value for the enum").
- [ ] `endUserIdleTimeOut` is in range 5-30.

## Setup Prompts: Automated Responses

Ask which messages the user wants, using the Setup labels (Automated Responses card), with the `type` in parentheses. Two content shapes, chosen by `type`:

- Consent text — **Opt-Out Confirmation** (`OptOutConfirmation`) and **Help Response** (`HelpResponse`): `TextResponse` shape; generate elements with `autoResponseContentType: TextResponse`, `language`, and XML-escaped `response` text.
- Messaging Components — `MessageDefinition` shape; the referenced `ConversationMessageDefinition` must exist first. If it doesn't, delegate to `conversation-message-definition-builder` to create it, then generate the element with `autoResponseContentType: MessageDefinition` and `messageDefinitionName` (no `language`, no `response`):
  - **Conversation Acknowledgement** (`InitialResponse`), **Start Conversation** (`AgentEngagedResponse`), **End Conversation** (`AgentEndEngagementResponse`), **Inactive Conversation** (`EndUserInactiveResponse`), **Reroute Conversation** (`RerouteResponse`), **Routing Unavailable** (`RoutingUnavailableResponse`).
  - **Warning Message** (`EndUserIdleResponse`) — the idle warning; ask "How many minutes before the session inactivates/ends should the warning show?" (Setup: "Minutes to Show Warning"; `responseTimeoutInMins`, 4-30, less than `endUserIdleTimeOut`). `responseTimeoutInMins` is allowed only on `EndUserIdleResponse` and `EndUserInactiveResponse`.

Offer **every** type above (nine in all), never a subset. A question tool that allows only four options means asking in several rounds; do not merge types into buckets or drop any. If the user says only "automated responses", ask round by round until each type is accepted or declined. Ask for the `TextResponse` wording (Opt-Out, Help) instead of inventing it. Create any missing component by **invoking the `conversation-message-definition-builder` skill** (Skill tool) and deploying what it produces. Never write, copy, or adapt a `ConversationMessageDefinition` by hand, including by copying the shape of an existing one: the builder owns the required layout, `AutoResponse` type, and `Title` constant. If the builder skill is not available, stop and tell the user; do not fall back to hand-writing.

When adding to an existing channel, retrieve it first and keep **one** `automatedResponses` block per `type`. A second block of the same type fails the deploy with `duplicate value found: MessagingChannelId`; the cause is the duplicate block, not the component.

Checks:
- [ ] Every type was offered, and each answer (accepted or declined) was recorded.
- [ ] `OptOutConfirmation`/`HelpResponse`: `TextResponse` shape with `language` + `response`, special characters XML-escaped.
- [ ] Every other type: `MessageDefinition` shape with `messageDefinitionName` set and `language`/`response` both absent.
- [ ] `messageDefinitionName` references a `ConversationMessageDefinition` that already exists in the org (otherwise: "reference not found" — build it with `conversation-message-definition-builder` first).
- [ ] `responseTimeoutInMins` (4-30) appears only on `EndUserIdleResponse`/`EndUserInactiveResponse`, and on `EndUserIdleResponse` is less than `endUserIdleTimeOut`.
