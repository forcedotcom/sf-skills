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
    - "service-digital-engagement-deployment-configure"
    - "service-omni-queue-deploy"
    - "service-omni-queue-routing-config-deploy"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
    - tool: ["python3"]
      semver: ">=3.8"
---

# Configuring Enhanced Chat Channel

Creates `MessagingChannel` metadata XML for Salesforce Messaging for In-App and Web (MIAW). This skill produces a fully configured enhanced chat channel with routing, user verification, pre-chat, and automated response settings ready for Metadata API deployment.

## Scope

- **In scope**: Creating `MessagingChannel` metadata with Omni-Channel Flow routing, Omni-Channel Queue routing, User routing, or Agentforce Service Agent (ASA) routing; enabling User Verification; configuring all channel settings (pre-chat forms, automated responses, consent keywords, file attachments, custom parameters)
- **Out of scope**: Creating the referenced Omni-Channel Flow/Queue definitions (use `automation-flow-generate`), creating the Embedded Service Deployment (separate metadata type — use `service-digital-engagement-deployment-configure`), creating permission sets for messaging (use `platform-permission-set-generate`), configuring the Embedded Service Code Snippet

---

## Entry points and transport

- **Delegated** (`context.calledFrom == "service-onboarding"`): use the approved `values` and ask nothing for changes the plan row describes; confirm drift on an existing channel with the user (step 3a). Return `failed` naming any missing required key. **Standalone** (no `context`): ask for the Inputs below.
- **Shell safety**: org alias and bot name must match `^[A-Za-z0-9_.@+-]+$` before use in a command; otherwise stop and ask (delegated: `failed`). Pass the channel label single-quoted, escaping any `'` as `'\''`.
- **Transport A** (primary): headless-360 MCP `dispatch` / `dispatch_readonly` on `/headless/metadata`. **Transport B**: the `sf` commands below, only where a probe shows Transport A unavailable.

Details: `references/onboarding_contract.md` (§1 entry points, §2 transport, §3 pre-scan, §5 result).

---

## Inputs

Standalone: ask for anything not already clear. Delegated: take `values`.

- **Channel name**: `masterLabel` and file name (`<Name>.messagingChannel-meta.xml`)
- **Routing type**: `Queue`, `Flow`, `User`, or `AgentforceServiceAgent`
- **Routing target**: developer name of the queue, flow, user, or ASA bot
- **Fallback queue** (Flow and ASA): developer name for escalation. **Routing config** (User): `QueueRoutingConfig` DeveloperName
- **User verification**: JWT-based identity verification (default `false`, so `authMode` `UnAuth`). `true` makes an `Auth` channel; a keyset name is optional (with one, also an `authIdentifier`, a free-form label defaulting to the file name). Creating keys is a separate setup
- **Pre-chat fields** (optional): which fields and types

Apply every other default from `references/channel_settings.md` unless the user specifies otherwise.

---

## Workflow

Run in order; step 3a may jump to step 15 or Phase 4. All SOQL below: Transport A `dispatch_readonly` first, `sf data query` as fallback.

### Phase 1 — Gather Context

1. **Verify org API version** — run `scripts/check-api-version.sh 67.0 '<org-alias>'` (skip it when Transport A is in use). Exit 1 = org below 67.0: stop and relay the script's next step (delegated: `failed`). Exit 2 = version could not be read: warn that it is unverified and continue; the deploy confirms it. Create `sfdx-project.json` in the output folder only if none exists, with `sourceApiVersion` set to the script's `ORG_API_VERSION` (67.0 if exit 2).

2. **Collect inputs** — standalone: ask for the Inputs. Delegated: from `values`. Then probe transport with a read-only `GET` of `MessagingChannel` (contract §2).

3. **Determine file name** — run `scripts/normalize-channel-name.sh '<LABEL>'` and surface any errors it returns.

3a. **Pre-scan** — `GET` `MessagingChannel` by the step 3 name (contract §3): none → create; matches and active → no write, `already-configured`, skip to Phase 4; matches but inactive → activate only (step 15); differs → announce each change, then write the full document. Standalone: ask first and end your turn; no record update or deploy until the user continues. Delegated: confirm the drift with the user first (contract §3). This applies to any change to an existing channel, however small, and naming the exact change in the request is not consent. If `sessionHandlerType` changes, also follow `references/routing_transitions.md`.

4. **Verify routing target exists** — skip when step 3a ended in `already-configured` or activate-only, so a re-run never creates a queue. Names must match `^[A-Za-z0-9_.@+-]+$` before they go into a query. Confirm the routing target exists with the lookup in `references/routing_transitions.md` → Target lookups (also the fallback queue for Flow and ASA, and the routing config for User).

   If a target is not found, never write its metadata here. Delegated — return `failed` naming the missing target. Standalone — tell the user which target is missing and ask whether to create it. A queue or routing config: on yes, hand off to the owning skill in Cross-Skill Integration with an explicit name, then resume at step 4; on no, stop. If that skill is unavailable or returns `blocked`, stop and tell the user what to create — never write the queue or routing config yourself. A flow, user or bot has no owning skill here: stop and tell the user to create it. **A new queue needs a `QueueRoutingConfig`, or sessions fail with "Agents are not available. Try again later" even though the channel deploys and activates.**

5. **Read the channel settings reference** — load `references/channel_settings.md` to understand all available configuration options and their valid values.

### Phase 2 — Generate Metadata

6. **Read the metadata template** — new channel: load `assets/messaging_channel_template.xml` as the starting structure. Existing channel (3a): start from its current document (Transport A `GET` `xmlRep`; Transport B `sf project retrieve start -m MessagingChannel:<Name>`) and change only the targeted elements, so pre-chat, responses, and authorizations survive.

7. **Apply routing configuration** — set `sessionHandlerType` and the corresponding handler field:

   | Routing Type | `sessionHandlerType` | Required Fields |
   |-------------|---------------------|----------------|
   | Omni-Channel Queue | `Queue` | `sessionHandlerQueue` |
   | Omni-Channel Flow | `Flow` | `sessionHandlerFlow` + `sessionHandlerQueue` (fallback) |
   | User | `User` | `sessionHandlerUser` (username) + `queueRoutingConfig`; no `sessionHandlerQueue` |
   | Agentforce Service Agent | `AgentforceServiceAgent` | `sessionHandlerQueue` (fallback) + `sessionHandlerAsa` (bot dev name — required, see v67 note below) |

   For ASA, `<sessionHandlerAsa>` is required and the bot must be Active; see `references/routing_transitions.md` → Agentforce Service Agent.

8. **Apply user verification** — not enabled: set `embeddedConfig.authMode` to `UnAuth` and omit `<messagingAuthorizations>`. Enabled: follow `references/user_verification.md` (add `<messagingAuthorizations>` only for a keyset name the user gave; never invent one, and without one still write `Auth`).

9. **Configure embedded settings** — populate `<embeddedConfig>` per `references/channel_settings.md`: `anonymousUserJwtExpirationTime` for UnAuth, `verifiedUserJwtExpirationTime` for Auth.

9a. **Configure session inactivity (optional)** — ask using the Setup labels and set the top-level fields per `references/channel_settings.md` → "Setup Prompts: Session Inactivity".

9b. **Write automated responses (only if requested)** — for every type except `OptOutConfirmation` and `HelpResponse`, write exactly `<autoResponseContentType>MessageDefinition</autoResponseContentType>`, `<messageDefinitionName>` (the CMD DeveloperName) and `<type>` directly under `<automatedResponses>`. There is no `<response>` wrapper and no `<conversationMessageDefinition>` element.

10. **Configure messaging keywords** — generate `<messagingKeywords>` elements (each has `<keyword>`s, `<keywordType>`, `<language>`; never `<type>`):
    - `OptOut` type with individual `<keyword>` elements: cancel, end, quit, stop, stopall, unsubscribe
    - `Help` type with `<keyword>`: help

11. **Apply standard parameters** — if the user needs standard pre-chat fields, follow `references/prechat_params.md` → Standard parameters.

12. **Apply custom parameters** — if the user needs pre-chat data collection, follow `references/prechat_params.md` → Custom parameters (`parameterDataType` is always `String`).

13. **Generate the file** — produce the `.messagingChannel-meta.xml` file following the template structure. Place at the path the user specifies, or default to `<source-path>/messagingChannels/<ChannelName>.messagingChannel-meta.xml` under the project's metadata source path.

### Phase 3 — Deploy and Activate

14. **Write the channel** — if 3a found a routing-type change, first run `references/routing_transitions.md` Procedure steps 1–3; if the write fails, run its step 4 restore. Transport A: `POST` to create, `PUT` the **full** document to update (a minimal PUT drops `embeddedConfig`); check `results[].success`, then re-`GET`. Transport B:
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
| User routing requires `sessionHandlerUser` and `queueRoutingConfig`, and no `sessionHandlerQueue` | The platform rejects a fallback queue on User routing |
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
| Routing-type change fails with a fallback-queue or "Only a Queue or Flow Routing Method…" error | The old type's fields are still set; see `references/routing_transitions.md` |
| Channel name conflicts with existing channel | Check org for existing channels; file name must be unique |
| Queue not found on deploy | Ensure the referenced queue exists and has `MessagingSession` as a `queueSobject` type |
| Channel deploys and activates fine, but widget shows "Agents are not available. Try again later." at session start | The queue has no `QueueRoutingConfig` — this is silent at deploy time. Check `SELECT QueueRoutingConfigId FROM Group WHERE Id='<QUEUE_ID>'`; if null, create one with `service-omni-queue-routing-config-deploy` |
| Omni-Channel Flow not found on deploy | Ensure the referenced flow exists and is active before deploying the channel |
| ASA bot reference invalid | Bot must be published and active; use exact developer name from BotDefinition metadata |
| ASA channel deployed but `SessionHandlerId` is null after deploy | Bot was not Active at deploy time — run `sf agent activate`, confirm `BotVersion.Status = Active`, then redeploy |
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
- [ ] Exactly one `sessionHandlerType` value is set (`Queue`, `Flow`, `User`, or `AgentforceServiceAgent`)?
- [ ] Queue: `sessionHandlerQueue` in the XML? Flow: `sessionHandlerFlow` plus `sessionHandlerQueue` as fallback? User: `sessionHandlerUser` plus `queueRoutingConfig`, no `sessionHandlerQueue`? ASA: both `sessionHandlerQueue` and `sessionHandlerAsa`?
- [ ] ASA: step 15a run, with `SessionHandlerId` and `FallbackQueueId` non-null after the deploy?
- [ ] The routing target references an existing entity in the org?

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
| Creating the routing or fallback queue | `service-omni-queue-deploy` skill |
| Creating the `QueueRoutingConfig` a queue or User routing needs | `service-omni-queue-routing-config-deploy` skill |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/onboarding_contract.md` | Delegated mode (`context.calledFrom == "service-onboarding"`), org writes (transport), module registration |
| `assets/messaging_channel_template.xml` | Before generating — use as the starting structure |
| `references/channel_settings.md` | When configuring channel options beyond defaults |
| `references/routing_transitions.md` | Changing a channel's routing type, or looking up routing targets |
| `references/user_verification.md` | The user turns user verification (Auth mode) on |
| `references/prechat_params.md` | The user needs standard or custom pre-chat parameters |
| `references/recaptcha_handoff.md` | The user asks about reCAPTCHA / captcha, or at the end of standalone output |
| `scripts/check-api-version.sh` | Phase 1 — verify org API version meets the passed minimum (67.0) |
| `scripts/normalize-channel-name.sh` | Phase 1 — derive file API name from channel label |
| `examples/omni_flow_channel.xml`, `omni_queue_channel.xml`, `user_channel.xml`, `asa_agent_channel.xml`, `auth_queue_channel.xml` (Auth with keyset) | To verify output for Flow, Queue, User, or Agentforce Service Agent routing |
