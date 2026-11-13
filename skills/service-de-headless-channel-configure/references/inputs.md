---
name: service-de-headless-channel-configure-inputs
description: "Load when you need the full input list for the headless channel setup orchestrator — the base MESSAGE_TYPE/ORG_ALIAS prompt plus the type-specific fields required for WhatsApp, LINE, AppleBusinessChat, Facebook, and Text (SMS). Covers exactly which fields are required vs optional per channel type and the prompt text shown when MESSAGE_TYPE is omitted. DO NOT load for Stage 0's preflight-key derivation logic, which lives inline in the parent skill."
metadata:
  version: "1.0"
  related-skills: service-de-headless-channel-configure
---

# Inputs (from user)

- `{MESSAGE_TYPE}` — one of `WhatsApp`, `Line`, `AppleBusinessChat`, `Facebook`, `Text` (`Text` is the enum value for SMS — there is no `SMS` type). If omitted, the orchestrator prompts:
  ```text
  Which channel type are you setting up?
    1) WhatsApp
    2) Line
    3) AppleBusinessChat
    4) Facebook
    5) Text (SMS)
  Pick [1-5]:
  ```
- `{ORG_ALIAS}` — optional. `sf` CLI target-org alias. Defaults to `sf config get target-org`.
- Plus the type-specific inputs, which are forwarded to the dispatcher:

## If `MESSAGE_TYPE=WhatsApp`
- `{WABA_ID}` — WhatsApp Business Account ID
- `{PHONE_NUMBER_ID}` — Meta phone number ID (not the display number)
- `{CHANNEL_NAME}` — optional
- `{ISO_COUNTRY_CODE}` — optional, default `US`

## If `MESSAGE_TYPE=Line`
- `{LINE_CHANNEL_ID}` — numeric LINE channel id
- `{LINE_CHANNEL_SECRET}`, `{LINE_ACCESS_TOKEN}`
- `{CHANNEL_NAME}` — optional

## If `MESSAGE_TYPE=AppleBusinessChat`
- `{APPLE_BC_ID}` — Apple Business Chat Account ID
- `{CHANNEL_NAME}` — required

## If `MESSAGE_TYPE=Facebook`
- `{PAGE_ID}` — optional. Facebook Page ID (numeric string). If not provided, the insertion skill runs OAuth, fetches available pages, and prompts for selection.
- `{CHANNEL_NAME}` — optional. If not provided, the insertion skill prompts for it.

## If `MESSAGE_TYPE=Text` (SMS)
- `{SMS_NUMBER}` — the phone number / short code / toll-free number the channel sends from, already provisioned to the org. It's the platform key. **Required.**
- `{SMS_PROVIDER}` — optional. The code provider for the number (e.g. `Sinch`). The insertion skill always sends the `smsProvider` key to satisfy the Connect request shape (omitting it trips a `400`), but the value is neither validated nor persisted — it leaves no observable trace on the record. If the caller doesn't supply one it defaults to `""`; pass a real value only when you have it, since nothing downstream reads it.
- `{CHANNEL_NAME}` — optional. Falls back to the number if omitted.
- `{ISO_COUNTRY_CODE}` — optional, default `US`. Pass the real country if the number is non-US.

The orchestrator validates type-specific inputs upfront; missing ones raise a prompt before we burn a Stage 0 SOQL.

## Optional, any type

- `{QUEUE}` — a routing queue the user named (label, DeveloperName, or `00G` Id). Forwarded to `service-de-channel-routing-configure`, which validates it instead of prompting.
- `{REQUESTED_SETTINGS}` — not a field the user fills in; extract it from the request in Stage 0. One item per thing asked for:

| User says (examples) | Item | Facet / leaf input |
| --- | --- | --- |
| "initial response: 'Thanks for reaching out…'" | `auto-response:InitialResponse` | `auto-responses`, `TextResponse` with that text |
| "when an agent engages: '…'" | `auto-response:AgentEngagedResponse` | `auto-responses` |
| "when the customer goes idle, after 10 minutes: '…'" | `auto-response:EndUserIdleResponse` | `auto-responses`, `responseTimeoutInMins=10` |
| "when the conversation ends / customer stopped responding: '…'" | `auto-response:AgentEndEngagementResponse` / `auto-response:EndUserInactiveResponse` | `auto-responses` |
| "implicit opt-in consent with STOP, END as opt-out keywords" (keywords given with a consent type) | none — these are consent inputs, not a separate item | Stage 3.5: forwarded as the language-keyword record's `OptOutKeywords` / `OptInKeywords` |
| "a Help keyword 'help'", "add OptOut keywords STOP, END" (no consent type) | `keywords:<Help\|OptOut\|OptIn>:<language>` | `keywords` |
| "session idle timeout 15 minutes", "end inactive sessions after 20" | `inactivity:endUserIdleTimeOut` / `inactivity:endInactiveSessionTimeOut` | `inactivity` (MIAW-only → `notApplicable` here) |
| "reset the timer when an agent replies" | `inactivity:isAgentMessageResetInactivityEnabled` | `inactivity` (Apple/Facebook only) |
| "use explicit / double opt-in" | `consent:<ConsentType>` | Stage 3.5, not Stage 4.5 |

Response text that references an existing messaging component by name (`ConversationMessageDefinition`) uses the `MessageDefinition` shape instead of `TextResponse` — the settings leaf handles both. Don't create messaging components from this orchestrator.
