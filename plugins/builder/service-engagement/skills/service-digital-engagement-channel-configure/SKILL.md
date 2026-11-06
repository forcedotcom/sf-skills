---
name: service-digital-engagement-channel-configure
description: "Configures and deploys enhanced chat Messaging Channels for Messaging for In-App and Web (MIAW). Use when the user needs to create, deploy, and activate a messaging channel configured with Omni-Channel Flow, Omni-Channel Queue, User, or Agentforce Service Agent routing. Generates MessagingChannel metadata, deploys it to the target org, and activates the channel with User Verification, pre-chat forms, automated responses, consent settings, and all customizable channel options via Metadata API. TRIGGER when the user mentions messaging channel, MIAW, enhanced chat, in-app messaging, web messaging setup, or references a .messagingChannel-meta.xml file. DO NOT TRIGGER when the user is configuring legacy Live Agent chat, Embedded Service deployments without messaging, or standard Omni-Channel routing rules without a messaging channel."
metadata:
  version: "1.0"
  domains: ["Service"]
  minApiVersion: "67.0"
  relatedSkills:
    - "automation-flow-generate"
    - "platform-permission-set-generate"
    - "service-agentforce-channel-configure"
    - "service-digital-engagement-deployment-configure"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["python3"]
      semver: ">=3.8"
---

# Configuring Enhanced Chat Channel

Creates `MessagingChannel` metadata XML for Salesforce Messaging for In-App and Web (MIAW). This skill produces a fully configured enhanced chat channel with routing, user verification, pre-chat, and automated response settings ready for Metadata API deployment.

## Scope

- **In scope**: Creating `MessagingChannel` metadata with Omni-Channel Flow routing, Omni-Channel Queue routing, or Agentforce Service Agent (ASA) routing; enabling User Verification; configuring all channel settings (pre-chat forms, automated responses, consent keywords, file attachments, custom parameters)
- **Out of scope**: Creating the referenced Omni-Channel Flow/Queue definitions (use `automation-flow-generate`), creating the Embedded Service Deployment (separate metadata type — use `service-digital-engagement-deployment-configure`), creating permission sets for messaging (use `platform-permission-set-generate`), configuring the Embedded Service Code Snippet

---

## Entry points and transport

- **Delegated** (`context.calledFrom == "service-onboarding"`): use the approved `values`, ask nothing, and return `failed` naming any missing required key. **Standalone** (no `context`): ask for the Inputs below.
- **Shell safety**: org alias and bot name must match `^[A-Za-z0-9_.@+-]+$` before use in a command; otherwise stop and ask (delegated: `failed`). Pass the channel label single-quoted, escaping any `'` as `'\''`.
- **Transport A** (primary): headless-360 MCP `dispatch` / `dispatch_readonly` on `/headless/metadata`. **Transport B**: the `sf` commands below, only where a probe shows Transport A unavailable.

Details: `references/onboarding_contract.md` (§1 entry points, §2 transport, §3 pre-scan, §5 result).

---

## Inputs

Standalone: ask for anything not already clear. Delegated: take `values`.

- **Channel name**: `masterLabel` and file name (`<Name>.messagingChannel-meta.xml`)
- **Routing type**: `Queue`, `Flow`, `User`, or `AgentforceServiceAgent`
- **Routing target**: developer name of the queue, flow, user, or ASA bot
- **Fallback queue** (Flow, User, and ASA): developer name for escalation
- **User verification**: JWT-based identity verification (default `false`, so `authMode` `UnAuth`). `true` makes an `Auth` channel; a keyset name is optional (with one, also an `authIdentifier`, a free-form label defaulting to the file name). Creating keys is a separate setup
- **Pre-chat fields** (optional): which fields and types

Apply every other default from `references/channel_settings.md` unless the user specifies otherwise.

---

## Workflow

Run in order; step 3a may jump to step 15 or Phase 4. All SOQL below: Transport A `dispatch_readonly` first, `sf data query` as fallback.

### Phase 1 — Gather Context

1. **Verify org API version** — run `scripts/check-api-version.sh 67.0 '<org-alias>'` (skip it when Transport A is in use). Exit 1 = org below 67.0: stop (delegated: `failed`). Exit 2 = version unknown: say so and continue. Create `sfdx-project.json` with `"sourceApiVersion": "67.0"` in the output folder only if none exists.

2. **Collect inputs** — standalone: ask for the Inputs. Delegated: from `values`. Then probe transport with a read-only `GET` of `MessagingChannel` (contract §2).

3. **Determine file name** — run `scripts/normalize-channel-name.sh '<LABEL>'` and surface any errors it returns.

3a. **Pre-scan** — `GET` `MessagingChannel` by the step 3 name (contract §3): none → create; matches and active → no write, `already-configured`, skip to Phase 4; matches but inactive → activate only (step 15); differs → announce each change, then write the full document (standalone: ask first).

4. **Verify routing target exists** — skip when step 3a ended in `already-configured` or activate-only, so a re-run never creates a queue. Names must match `^[A-Za-z0-9_.@+-]+$` before they go into a query. Query the org to confirm the referenced routing target exists:
   - For Queue: `sf data query --query "SELECT Id, DeveloperName FROM Group WHERE Type='Queue' AND DeveloperName='<QUEUE_NAME>'" --target-org <org-alias>`
   - For Flow: `sf data query --query "SELECT Id, ApiName FROM FlowDefinitionView WHERE ApiName='<FLOW_NAME>' AND IsActive=true" --target-org <org-alias>`
   - For User: `sf data query --query "SELECT Id, Username FROM User WHERE Id='<USER_ID>' AND IsActive=true" --target-org <org-alias>`
   - For ASA: `sf data query --query "SELECT Id, DeveloperName FROM BotDefinition WHERE DeveloperName='<BOT_NAME>'" --target-org <org-alias>`
   - Also verify the fallback queue exists (required for Flow, User, and ASA routing)
   
   If any target is not found: standalone — inform the user and ask whether to create it. Delegated — return `failed` naming the missing target; never create it. If the standalone user confirms creating:
   - For Queue: generate a `.queue-meta.xml` with `MessagingSession` as the `queueSobject` type and deploy it before the channel. **A new queue needs a `QueueRoutingConfig`, or sessions fail with "Agents are not available. Try again later" even though the channel deploys and activates.** Right after the queue deploys, resolve or create one per `service-agentforce-channel-configure`'s `references/queue-resolution.md` Step 4 — do not defer it.
   - For Flow/User/ASA: inform the user that the flow, user, or bot must be created separately (out of scope for this skill)

5. **Read the channel settings reference** — load `references/channel_settings.md` to understand all available configuration options and their valid values.

### Phase 2 — Generate Metadata

6. **Read the metadata template** — new channel: load `assets/messaging_channel_template.xml` as the starting structure. Existing channel (3a): start from its current document (Transport A `GET` `xmlRep`; Transport B `sf project retrieve start -m MessagingChannel:<Name>`) and change only the targeted elements, so pre-chat, responses, and authorizations survive.

7. **Apply routing configuration** — set `sessionHandlerType` and the corresponding handler field:

   | Routing Type | `sessionHandlerType` | Required Fields |
   |-------------|---------------------|----------------|
   | Omni-Channel Queue | `Queue` | `sessionHandlerQueue` |
   | Omni-Channel Flow | `Flow` | `sessionHandlerFlow` + `sessionHandlerQueue` (fallback) |
   | User | `User` | `sessionHandlerUser` + `sessionHandlerQueue` (fallback) |
   | Agentforce Service Agent | `AgentforceServiceAgent` | `sessionHandlerQueue` (fallback) + `sessionHandlerAsa` (bot dev name — required, see v67 note below) |

   > **v67 note — `<sessionHandlerAsa>` is required** (omitting it fails with "Missing required Agentforce Service Agent"); the deploy then binds `SessionHandlerId`, no PATCH needed. The bot must be Active first: run `sf agent activate -o <org> --api-name <BotDevName>` and confirm `BotVersion.Status = Active`.

8. **Apply user verification** — not enabled: set `embeddedConfig.authMode` to `UnAuth` and omit `<messagingAuthorizations>`. Enabled: follow `references/user_verification.md` (add `<messagingAuthorizations>` only for a keyset name the user gave; never invent one, and without one still write `Auth`).

9. **Configure embedded settings** — populate `<embeddedConfig>` per `references/channel_settings.md`: `anonymousUserJwtExpirationTime` for UnAuth, `verifiedUserJwtExpirationTime` for Auth.

9a. **Configure session inactivity (optional)** — ask using the Setup labels and set the top-level fields per `references/channel_settings.md` → "Setup Prompts: Session Inactivity".

10. **Configure messaging keywords** — generate `<messagingKeywords>` elements:
    - `OptOut` type with individual `<keyword>` elements: cancel, end, quit, stop, stopall, unsubscribe
    - `Help` type with `<keyword>`: help

11. **Apply standard parameters** — if the user needs standard pre-chat fields, follow `references/prechat_params.md` → Standard parameters.

12. **Apply custom parameters** — if the user needs pre-chat data collection, follow `references/prechat_params.md` → Custom parameters (`parameterDataType` is always `String`).

13. **Generate the file** — produce the `.messagingChannel-meta.xml` file following the template structure. Place at the path the user specifies, or default to `<source-path>/messagingChannels/<ChannelName>.messagingChannel-meta.xml` under the project's metadata source path.

### Phase 3 — Deploy and Activate

14. **Write the channel** — Transport A: `POST` to create, `PUT` the **full** document to update (a minimal PUT drops `embeddedConfig`); check `results[].success`, then re-`GET`. Transport B:
    ```bash
    sf project deploy start --source-dir <path-to-messagingChannels-folder> --target-org <org-alias>
    ```

15. **Activate the channel** — after a successful write, activate the messaging channel (`IsActive` is not part of the metadata). Transport A: sObject update `{"IsActive": true}` through `dispatch`. Transport B:
    ```bash
    sf data update record --sobject MessagingChannel --where "DeveloperName='<CHANNEL_NAME>'" --values "IsActive=true" --target-org <org-alias>
    ```

15a. **ASA routing only — verify the bind landed** (skip for Queue, Flow, User):

    ```bash
    sf data query -o <org> --json \
      -q "SELECT SessionHandlerId, FallbackQueueId FROM MessagingChannel WHERE DeveloperName='<CHANNEL_DEV_NAME>'"
    ```

    Both must be non-null; if not, check both handler elements were in the XML and the bot was Active before the deploy.

### Phase 4 — Validate

16. **Verify against checklist** — confirm all items in the Verification Checklist below pass before presenting output.

17. **Report** — delegated: return the contract §5 result and stop. Standalone: continue.

18. **Present output** (standalone) — in a few lines: confirm the channel is created and its activation status, and list each setting the user asked for with its final value, whatever field it is. Say everything else uses the defaults, without listing them. Give transport details, file paths and record Ids only after a failure or if asked. Then offer next steps:
    - **Automated responses** — ask which messages the user wants using the Setup labels per `references/channel_settings.md` → "Setup Prompts: Automated Responses", then redeploy.
    - **reCAPTCHA** — not settable by this skill; say this skill does not set or check it and offer the admin handoff in `references/recaptcha_handoff.md`.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| File name serves as the channel API name | No `channelPlatformKey` field in the XML body |
| `sessionHandlerType` must match the handler fields present | Setting `Queue` but populating `sessionHandlerFlow` causes deployment error |
| Flow routing requires both `sessionHandlerFlow` and `sessionHandlerQueue` | Queue is the mandatory fallback for human escalation |
| User routing requires both `sessionHandlerUser` and `sessionHandlerQueue` | Queue is the mandatory fallback when user is unavailable |
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
| ASA routing: include both `sessionHandlerQueue` and `sessionHandlerAsa` in the XML | `sessionHandlerAsa` is required at v67 — the deploy fails with "Missing required Agentforce Service Agent" if omitted; the deploy itself binds `SessionHandlerId`, no PATCH needed |
| Bot must be Active before the metadata deploy that binds `SessionHandlerId` | API rejects with "Only active Agentforce Service Agents are supported" if the bot is inactive |
| Channel name conflicts with existing channel | Check org for existing channels; file name must be unique |
| Queue not found on deploy | Ensure the referenced queue exists and has `MessagingSession` as a `queueSobject` type |
| Channel deploys and activates fine, but widget shows "Agents are not available. Try again later." at session start | The queue has no `QueueRoutingConfig` — this is silent at deploy time. Check `SELECT QueueRoutingConfigId FROM Group WHERE Id='<QUEUE_ID>'`; if null, resolve/create one per `queue-resolution.md` Step 4 |
| Omni-Channel Flow not found on deploy | Ensure the referenced flow exists and is active before deploying the channel |
| ASA bot reference invalid | Bot must be published and active; use exact developer name from BotDefinition metadata |
| ASA channel deployed but `SessionHandlerId` is null after deploy | Bot was not Active at deploy time — run `sf agent activate`, confirm `BotVersion.Status = Active`, then redeploy |
| ASA channel deploy fails with "Missing required Agentforce Service Agent" | `<sessionHandlerAsa>{BotDevName}</sessionHandlerAsa>` is missing from the XML — it's required at v67, not optional |
| "Only active Agentforce Service Agents are supported" on deploy | Bot is inactive — run `sf agent activate` before deploying |
| Flow or ASA routing fails without fallback queue | `sessionHandlerQueue` is mandatory when `sessionHandlerType` is `Flow` or `AgentforceServiceAgent` |
| JWT verification not working | The keyset (`PublicKeyCertificateSet`) named in `messagingAuthorizations` must exist in the org and match the token's `kid` and issuer |
| Custom parameters not collected | `name` must be unique per channel |
| `<customParameters>` deploy fails: "bad value for restricted picklist field" | `parameterDataType` was set to something other than `String`. Channel custom parameters are always `String`; set the field's actual type (Number, Checkbox, dropdown) at the deployment level, not here |
| Removing a custom parameter: "can't be deleted as it is referenced elsewhere" | **Check before deploying, not after.** Every deployment on this channel whose pre-chat form uses the param must first drop that field and be published (user-approved); remove the param's `actionParameterMappings` in a separate deploy first. See `references/channel_settings.md` §Removing a Custom Parameter |
| Automated response / session-inactivity deploy fails | See `references/channel_settings.md` → "Automated Responses", "Session Settings" |
| Channel deployed but messages not routing | Channel must be activated after deployment — it defaults to inactive |
| "You can't enable Session-Based Chat for verified users" | Set `isSynchronousChatEnabled` to `false` for Auth channels — session-based chat is only valid for UnAuth |

---

## Verification Checklist

### Universal, Verification, Config, and Keyword Checks
- [ ] File name matches `^[a-zA-Z][a-zA-Z0-9_]*$`, `masterLabel` is 40 characters or fewer, `messagingChannelType` is `EmbeddedMessaging`?
- [ ] `embeddedConfig.authMode` is `Auth` when verification is enabled, `UnAuth` when not, with the matching JWT expiration set in range (`references/channel_settings.md`)?
- [ ] `chatAbandonmentTimeout` is a positive integer, `allowedFileTypes` is comma-separated with no spaces, `maxFileSize` is 1-5 MB?
- [ ] An `OptOut` keyword is defined, keywords are individual `<keyword>` elements, and `language` is set on each keyword block?
- [ ] Session inactivity / automated responses (only if requested) checked against `references/channel_settings.md`?

### Routing Checks
- [ ] Is exactly one `sessionHandlerType` value set (`Queue`, `Flow`, `User`, or `AgentforceServiceAgent`)?
- [ ] For Queue routing: is `sessionHandlerQueue` in the XML?
- [ ] For Flow routing: is `sessionHandlerFlow` in the XML, plus `sessionHandlerQueue` as fallback?
- [ ] For User routing: is `sessionHandlerUser` in the XML, plus `sessionHandlerQueue` as fallback?
- [ ] For ASA routing: are both `sessionHandlerQueue` and `sessionHandlerAsa` in the XML?
- [ ] For ASA routing: was step 15a run? Are `SessionHandlerId` and `FallbackQueueId` non-null after the deploy?
- [ ] Does the routing target reference an existing entity in the org?

### Activation Checks
- [ ] Was the channel deployed successfully?
- [ ] Was the channel activated after deployment (`IsActive=true`)?

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Creating the Omni-Channel Flow for routing | `automation-flow-generate` skill |
| Creating permission sets for messaging agents | `platform-permission-set-generate` skill |
| Creating the Embedded Service Deployment | `service-digital-engagement-deployment-configure` skill |
| Creating the `ConversationMessageDefinition` an automated response references | `conversation-message-definition-builder` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/onboarding_contract.md` | Delegated mode (`context.calledFrom == "service-onboarding"`), org writes (transport), module registration |
| `assets/messaging_channel_template.xml` | Before generating — use as the starting structure |
| `references/channel_settings.md` | When configuring channel options beyond defaults |
| `references/user_verification.md` | The user turns user verification (Auth mode) on |
| `references/prechat_params.md` | The user needs standard or custom pre-chat parameters |
| `references/recaptcha_handoff.md` | The user asks about reCAPTCHA / captcha, or at the end of standalone output |
| `scripts/check-api-version.sh` | Phase 1 — verify org API version meets the passed minimum (67.0) |
| `scripts/normalize-channel-name.sh` | Phase 1 — derive file API name from channel label |
| `examples/omni_flow_channel.xml`, `omni_queue_channel.xml`, `asa_agent_channel.xml`, `auth_queue_channel.xml` (Auth with keyset) | To verify output for Flow, Queue, or Agentforce Service Agent routing |
