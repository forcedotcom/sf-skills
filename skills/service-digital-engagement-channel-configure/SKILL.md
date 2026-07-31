---
name: service-digital-engagement-channel-configure
description: "Configures and deploys enhanced chat Messaging Channels for Messaging for In-App and Web (MIAW). Use when the user needs to create, deploy, and activate a messaging channel configured with Omni-Channel Flow, Omni-Channel Queue, User, or Agentforce Service Agent routing. Generates MessagingChannel metadata, deploys it to the target org, and activates the channel with User Verification, pre-chat forms, automated responses, consent settings, and all customizable channel options via Metadata API. TRIGGER when the user mentions messaging channel, MIAW, enhanced chat, in-app messaging, web messaging setup, or references a .messagingChannel-meta.xml file. DO NOT TRIGGER when the user is configuring legacy Live Agent chat, Embedded Service deployments without messaging, or standard Omni-Channel routing rules without a messaging channel."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  relatedSkills:
    - "automation-flow-generate"
    - "platform-permission-set-generate"
    - "service-digital-engagement-deployment-configure"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.10.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
---

# Configuring Enhanced Chat Channel

Creates `MessagingChannel` metadata XML for Salesforce Messaging for In-App and Web (MIAW). This skill produces a fully configured enhanced chat channel with routing, user verification, pre-chat, and automated response settings ready for Metadata API deployment.

## Scope

- **In scope**: Creating `MessagingChannel` metadata with Omni-Channel Flow routing, Omni-Channel Queue routing, or Agentforce Service Agent (ASA) routing; enabling User Verification; configuring all channel settings (pre-chat forms, automated responses, consent keywords, file attachments, custom parameters)
- **Out of scope**: Creating the referenced Omni-Channel Flow/Queue definitions (use `automation-flow-generate`), creating the Embedded Service Deployment (separate metadata type — use `service-digital-engagement-deployment-configure`), creating permission sets for messaging (use `platform-permission-set-generate`), configuring the Embedded Service Code Snippet

---

## Clarifying Questions

Before generating, ask the user if not already clear:

- What is the channel name / label? (used for `masterLabel` and file name)
- What routing type? (Omni-Channel Flow, Omni-Channel Queue, User, or Agentforce Service Agent)
- What is the routing target? (Flow API name, Queue developer name, User ID, or ASA bot name)
- For Flow, User, or ASA routing: What is the fallback queue name?
- Should User Verification be enabled? (defaults to `true` per this skill)
- Are there pre-chat form fields required? If so, which fields and types?

---

## Required Inputs

Gather or infer before proceeding:

- **Channel name**: Used for `masterLabel` and the file name (`<Name>.messagingChannel-meta.xml`)
- **Routing type**: One of `Queue`, `Flow`, `User`, or `AgentforceServiceAgent`
- **Routing target**: The developer name of the queue, flow, user, or ASA bot
- **Fallback queue** (Flow, User, and ASA): The developer name of the fallback queue for escalation
- **User verification**: Whether to require JWT-based identity verification (default: `true`)

Defaults unless specified:
- `messagingChannelType`: `EmbeddedMessaging`
- `authMode`: `Auth`
- `chatAbandonmentTimeout`: `5` (minutes)
- `endUserIdleTimeOut`: `5` (minutes)
- `isAttachmentUploadEnabled`: `true`
- `maxFileSize`: `5` (MB)
- `allowedFileTypes`: `bmp,csv,doc,docx,gif,jpg,pdf,png,tiff,txt,xls,xml`
- `anonymousUserJwtExpirationTime`: `360` (minutes, required for UnAuth, range 60-4320)
- `verifiedUserJwtExpirationTime`: `60` (minutes, required for Auth, range 60-240)
- `isAbandonedChatsEnabled`: `false`
- `isSaveTranscriptEnabled`: `false`
- `isFallbackMessageEnabled`: `false`
- `isEstimatedWaitTimeEnabled`: `false`
- `isFileAttachmentExtUnrestricted`: `false`
- `isQueuePositionEnabled`: `false`
- `isSynchronousChatEnabled`: `false`
- `isVoiceModeEnabled`: `false`

---

## Workflow

All steps are sequential. Do not skip or reorder.

### Phase 1 — Gather Context

1. **Verify org API version** — run `scripts/check-api-version.sh 67.0 <org-alias>` and report any errors it returns. If the script fails, generate a `sfdx-project.json` in the metadata output folder with `"sourceApiVersion": "67.0"`.

2. **Collect inputs** — confirm the channel label, routing type, routing target, and verification settings from the user per Clarifying Questions above.

3. **Determine file name** — run `scripts/normalize-channel-name.sh "<LABEL>"` and surface any errors it returns.

4. **Verify routing target exists** — query the org to confirm the referenced routing target exists:
   - For Queue: `sf data query --query "SELECT Id, DeveloperName FROM Group WHERE Type='Queue' AND DeveloperName='<QUEUE_NAME>'" --target-org <org-alias>`
   - For Flow: `sf data query --query "SELECT Id, ApiName FROM FlowDefinitionView WHERE ApiName='<FLOW_NAME>' AND IsActive=true" --target-org <org-alias>`
   - For User: `sf data query --query "SELECT Id, Username FROM User WHERE Id='<USER_ID>' AND IsActive=true" --target-org <org-alias>`
   - For ASA: `sf data query --query "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName='<BOT_NAME>'" --target-org <org-alias>`
   - Also verify the fallback queue exists (required for Flow, User, and ASA routing)
   
   If any target is not found, inform the user and ask whether to create it. If the user confirms:
   - For Queue: generate a `.queue-meta.xml` with `MessagingSession` as the `queueSobject` type and deploy it before the channel
   - For Flow/User/ASA: inform the user that the flow, user, or bot must be created separately (out of scope for this skill)

5. **Read the channel settings reference** — load `references/channel_settings.md` to understand all available configuration options and their valid values.

### Phase 2 — Generate Metadata

6. **Read the metadata template** — load `assets/messaging_channel_template.xml` as the starting structure.

7. **Apply routing configuration** — set `sessionHandlerType` and the corresponding handler field:

   | Routing Type | `sessionHandlerType` | Required Fields |
   |-------------|---------------------|----------------|
   | Omni-Channel Queue | `Queue` | `sessionHandlerQueue` |
   | Omni-Channel Flow | `Flow` | `sessionHandlerFlow` + `sessionHandlerQueue` (fallback) |
   | User | `User` | `sessionHandlerUser` + `sessionHandlerQueue` (fallback) |
   | Agentforce Service Agent | `AgentforceServiceAgent` | `sessionHandlerAsa` + `sessionHandlerQueue` (fallback) |

8. **Apply user verification** — if enabled, set `embeddedConfig.authMode` to `Auth` and include `<messagingAuthorizations>`. If not enabled, set `embeddedConfig.authMode` to `UnAuth` and omit `<messagingAuthorizations>`.

9. **Configure embedded settings** — populate `<embeddedConfig>` with:
   - `allowedFileTypes` — comma-separated file extensions (no spaces)
   - `anonymousUserJwtExpirationTime` — JWT expiration in minutes (required for UnAuth)
   - `verifiedUserJwtExpirationTime` — JWT expiration in minutes (required for Auth)
   - `chatAbandonmentTimeout` — minutes before abandoned conversation cleanup
   - `isAbandonedChatsEnabled` — enable abandoned chat detection
   - `isAttachmentUploadEnabled` — file upload support
   - `isEstimatedWaitTimeEnabled` — show estimated wait time
   - `isFallbackMessageEnabled` — fallback when agents unavailable
   - `isFileAttachmentExtUnrestricted` — allow any file extension
   - `isSaveTranscriptEnabled` — save conversation transcripts
   - `maxFileSize` — maximum attachment size in MB

10. **Configure messaging keywords** — generate `<messagingKeywords>` elements:
    - `OptOut` type with individual `<keyword>` elements: cancel, end, quit, stop, stopall, unsubscribe
    - `Help` type with `<keyword>`: help

11. **Apply standard parameters** — if the user needs standard pre-chat fields, generate `<standardParameters>` elements with `parameterType`. If the channel uses Flow-based routing and the user specifies flow variable mappings, include `<actionParameterMappings>` with `actionParameterName` to map each parameter to a flow input variable.

12. **Apply custom parameters** — if the user needs pre-chat data collection, generate `<customParameters>` elements with `name`, `masterLabel`, `parameterDataType`, `externalParameterName`, and `maxLength`. If the channel uses Flow-based routing and the user specifies flow variable mappings, include `<actionParameterMappings>` with `actionParameterName` to map each parameter to a flow input variable.

13. **Generate the file** — produce the `.messagingChannel-meta.xml` file following the template structure. Place at the path the user specifies, or default to the project's metadata source path under `messagingChannels/`.

### Phase 3 — Deploy and Activate

14. **Deploy the channel** — deploy the generated `.messagingChannel-meta.xml` file to the target org:
    ```bash
    sf project deploy start --source-dir <path-to-messagingChannels-folder> --target-org <org-alias>
    ```

15. **Activate the channel** — after successful deployment, activate the messaging channel:
    ```bash
    sf data update record --sobject MessagingChannel --where "DeveloperName='<CHANNEL_NAME>'" --values "IsActive=true" --target-org <org-alias>
    ```

### Phase 4 — Validate

16. **Verify against checklist** — confirm all items in the Verification Checklist below pass before presenting output.

17. **Present output** — show the generated file to the user with a summary of configured settings and confirm activation status. Offer next steps:
    - **Automated responses** — ask if the user wants to configure `<automatedResponses>` (OptOutConfirmation, HelpResponse). If yes, generate elements with `autoResponseContentType: TextResponse`, `language`, and XML-escaped `response` text, then redeploy.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| File name serves as the channel API name | No `channelPlatformKey` field in the XML body |
| `sessionHandlerType` must match the handler fields present | Setting `Queue` but populating `sessionHandlerFlow` causes deployment error |
| Flow routing requires both `sessionHandlerFlow` and `sessionHandlerQueue` | Queue is the mandatory fallback for human escalation |
| User routing requires both `sessionHandlerUser` and `sessionHandlerQueue` | Queue is the mandatory fallback when user is unavailable |
| ASA routing requires both `sessionHandlerAsa` and `sessionHandlerQueue` | Queue is the mandatory fallback for human escalation |
| `masterLabel` max 40 characters | Platform limit on channel labels |
| File name must match `^[a-zA-Z][a-zA-Z0-9_]*$` | API name format enforced by Metadata API |
| `allowedFileTypes` is a comma-separated string with no spaces | Not a nested list or array |
| `keyword` elements are individual — one per trigger word | Not a comma-separated list |
| `customParameters` need `name`, `masterLabel`, `parameterDataType`, and `externalParameterName` | Incomplete parameters fail silently |
| File extension is `.messagingChannel-meta.xml` | Metadata API uses this specific extension |
| Do not hardcode file paths — respect `sfdx-project.json` package directories | Customer orgs customize source paths |
| Channel must be activated after deployment | Channels are inactive by default — messages won't route until activated |
| `isSynchronousChatEnabled` defaults to `false`; can only be `true` for UnAuth channels upon user request | Platform rejects "You can't enable Session-Based Chat for verified users" for Auth channels |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Channel name conflicts with existing channel | Check org for existing channels; file name must be unique |
| Queue not found on deploy | Ensure the referenced queue exists and has `MessagingSession` as a `queueSobject` type |
| Omni-Channel Flow not found on deploy | Ensure the referenced flow exists and is active before deploying the channel |
| ASA bot reference invalid | Bot must be published and active; use exact developer name from BotDefinition metadata |
| Flow or ASA routing fails without fallback queue | `sessionHandlerQueue` is mandatory when `sessionHandlerType` is `Flow` or `AgentforceServiceAgent` |
| JWT verification not working | Connected app and certificate must be configured for the org |
| Custom parameters not collected | `name` must be unique per channel; `parameterDataType` defaults to `Text` |
| Automated responses not showing | Use exact `type` values (`OptOutConfirmation`, `HelpResponse`); XML-escape special characters |
| Channel deployed but messages not routing | Channel must be activated after deployment — it defaults to inactive |
| "You can't enable Session-Based Chat for verified users" | Set `isSynchronousChatEnabled` to `false` for Auth channels — session-based chat is only valid for UnAuth |

---

## Verification Checklist

### Universal Checks
- [ ] Does the file name match `^[a-zA-Z][a-zA-Z0-9_]*$`?
- [ ] Is `masterLabel` 40 characters or fewer?
- [ ] Is `messagingChannelType` set to `EmbeddedMessaging`?

### Routing Checks
- [ ] Is exactly one `sessionHandlerType` value set (`Queue`, `Flow`, `User`, or `AgentforceServiceAgent`)?
- [ ] Is the corresponding handler field populated (`sessionHandlerQueue`, `sessionHandlerFlow`, `sessionHandlerUser`, or `sessionHandlerAsa`)?
- [ ] For Flow, User, or ASA routing, is `sessionHandlerQueue` also populated (fallback)?
- [ ] Does the routing target reference an existing entity in the org?

### User Verification Checks
- [ ] If verification is enabled, is `embeddedConfig.authMode` set to `Auth`?
- [ ] If verification is disabled, is `embeddedConfig.authMode` set to `UnAuth`?

### Embedded Config Checks
- [ ] Is `chatAbandonmentTimeout` a positive integer (minutes)?
- [ ] Is `allowedFileTypes` a comma-separated string with no spaces?
- [ ] Is `maxFileSize` a value between 1-5 MB?
- [ ] If UnAuth, is `anonymousUserJwtExpirationTime` set (default 360, range 60-4320)?
- [ ] If Auth, is `verifiedUserJwtExpirationTime` set (default 60, range 60-240)?

### Automated Response Checks (only if user requested)
- [ ] Do all `type` values use valid IDs (`OptOutConfirmation`, `HelpResponse`)?
- [ ] Are special characters XML-escaped in `response` text?

### Keyword Checks
- [ ] Is there at least an `OptOut` keyword type defined?
- [ ] Are keywords individual `<keyword>` elements (not comma-separated)?
- [ ] Is `language` set on each keyword block?

### Activation Checks
- [ ] Was the channel deployed successfully?
- [ ] Was the channel activated after deployment (`IsActive=true`)?

---

## Output Expectations

Deliverables:
- **Messaging Channel metadata**: `<source-path>/messagingChannels/<ChannelName>.messagingChannel-meta.xml`

File structure follows the template in `assets/messaging_channel_template.xml`.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Creating the Omni-Channel Flow for routing | `automation-flow-generate` skill |
| Creating permission sets for messaging agents | `platform-permission-set-generate` skill |
| Creating the Embedded Service Deployment | `service-digital-engagement-deployment-configure` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `assets/messaging_channel_template.xml` | Before generating — use as the starting structure |
| `references/channel_settings.md` | When configuring channel options beyond defaults |
| `scripts/check-api-version.sh` | Phase 1 — verify org API version meets the passed minimum (67.0) |
| `scripts/normalize-channel-name.sh` | Phase 1 — derive file API name from channel label |
| `examples/omni_flow_channel.xml` | To verify output for Omni-Channel Flow routing |
| `examples/omni_queue_channel.xml` | To verify output for Omni-Channel Queue routing |
| `examples/asa_agent_channel.xml` | To verify output for Agentforce Service Agent routing |
