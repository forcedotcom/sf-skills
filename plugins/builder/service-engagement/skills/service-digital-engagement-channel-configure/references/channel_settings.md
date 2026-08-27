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
- Requires a configured connected app with certificate for JWT signature verification

---

## Messaging Authorizations (`<messagingAuthorizations>`)

Only applicable when `authMode` is `Auth`. Do not include when `authMode` is `UnAuth`.

Configures the authorization settings for verified user identity in the messaging channel.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `authorizationType` | Enum | Yes | Always `PublicKeyCertificateSet` |
| `authProviderName` | String | Yes | The name of the auth provider |
| `publicKeyCertificateSetName` | String | Yes | The certificate set used for public key verification |
| `enabled` | Boolean | Yes | Whether this authorization is active |
| `authIdentifier` | String | Yes | The identifier used to match the authenticated user |

```xml
<messagingAuthorizations>
    <authorizationType>PublicKeyCertificateSet</authorizationType>
    <authProviderName>MyAuthProvider</authProviderName>
    <publicKeyCertificateSetName>MyCertificateSet</publicKeyCertificateSetName>
    <enabled>true</enabled>
    <authIdentifier>Sub</authIdentifier>
</messagingAuthorizations>
```

---

## Session Settings (top-level)

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `endUserIdleTimeOut` | Integer | `5` | Minutes of user inactivity before idle warning |
| `isEstimatedWaitTimeEnabled` | Boolean | `false` | Show estimated wait time |
| `isQueuePositionEnabled` | Boolean | `false` | Show queue position to user |
| `isSynchronousChatEnabled` | Boolean | `false` | Enable real-time synchronous chat |
| `isVoiceModeEnabled` | Boolean | `false` | Enable voice mode capability |


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
| `parameterDataType` | Enum | Yes | `String`, `Number`, `Boolean` |
| `externalParameterName` | String | Yes | External mapping name for the parameter |
| `maxLength` | Integer | No | Max chars for Text type (default 255) |
| `actionParameterMappings` | Object | No | Maps this parameter to an Omni-Channel Flow action input variable |

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

---

## Automated Responses (`<automatedResponses>`)

Repeatable element — automated messages sent at specific events.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `autoResponseContentType` | Enum | Yes | `TextResponse` or `MessageDefinition` |
| `language` | String | Yes | Locale code (e.g., `en_US`) |
| `response` | String | Yes | The response message text (XML-escape special chars) |
| `type` | Enum | Yes | The event type — see table below |

### Response Types

| `type` Value | When Sent |
|-------------|-----------|
| `OptOutConfirmation` | When user opts out of receiving messages |
| `HelpResponse` | When user sends a help keyword |
| `InitialResponse` | Let a customer know that their initial message was received |
| `AgentEngagedResponse` | Let a customer know that their messaging session was accepted by a service rep |
| `AgentEndEngagementResponse` | Let a customer know that their messaging session ended, and optionally provide a post-chat URL. This auto-response is sent when the service rep or end user ends the session |
| `EndUserInactiveResponse` | Let a customer know that their messaging conversation has ended because they stopped responding |
| `EndUserIdleResponse` | When end user idle response |

### XML Escaping

Special characters in `response` must be XML-escaped:
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
