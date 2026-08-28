# Worked examples: `service-de-headless-channel-configure`

Four reference traces: a fresh WhatsApp run (the most common path), a resume after a mid-flow failure, an Apple Business Chat dispatch (to show type-agnostic flow), and an unsupported-type rejection. Read these when you need to see the exact envelope shapes the orchestrator emits at each outcome.

---

## Worked example: fresh WhatsApp channel on test1

Input (hypothetical, against `test1`):
- `MESSAGE_TYPE=WhatsApp`
- `WABA_ID=1558753535400324`
- `PHONE_NUMBER_ID=1005595132638768`
- `CHANNEL_NAME` = (omitted)

**Stage 0**: type known from input. `{PLATFORM_KEY} = PHONE_NUMBER_ID`. Required WhatsApp inputs (`WABA_ID`, `PHONE_NUMBER_ID`) both present — proceed.

**Stage 1**: preflight SOQL keyed off `MessagingPlatformKey=1005595132638768 AND MessageType='WhatsApp'` returns 0 records → `CURRENT_STATE=fresh`. First step: insert.

**Stage 2** (insert): `service-de-channel-create` runs (with `MESSAGE_TYPE=WhatsApp`):
  - Its Stage 1 preflight (same SOQL; still empty)
  - Its Stage 2 linking prereq (`service-de-waba-integrate`) — user confirms Meta partnership is in place
  - Its Stage 3 Connect API POST — inserts `MessagingChannel 0MjSG...` + MCU `0gLSG...`
  - Its Stage 4 verify — MCU subquery returns one row with `DeploymentType=Conversation`, `DeploymentStatus=Disabled`

Returns `{ok:true, channelId:"0MjSG...", mcuId:"0gLSG...", developerName:"WHATSAPP_US_...", isActive:false, messageType:"WhatsApp", path:"connect", created:true, durationMs:3210}` to the orchestrator. `STEPS_RUN=["insert"]`.

**Stage 3** (route): `service-de-channel-routing-configure` prompts user. User picks existing `Messaging_Queue` (`00GSG0000000LSf2AM`). PATCH lands. `STEPS_RUN=["insert","route"]`.

**Stage 3.5** (consent): `service-de-channel-consent-configure` runs. The insert auto-seeded `ConsentType=ImplicitOptIn` + a default opt-out `MsgChannelLanguageKeyword` (STOP-family + confirmation), so the leaf's Stage 1 finds the channel already activation-ready and returns `noop:true` — no write needed. (Had the user asked for ExplicitOptIn/DoubleOptIn or custom keywords, the leaf would upgrade it here.) `STEPS_RUN=["insert","route"]`, `STEPS_SKIPPED=["consent"]`.

**Stage 4** (activate): `service-de-channel-activate` PATCHes `MessagingChannelUsage.DeploymentStatus='Provisioning'` via REST. The PATCH blocks synchronously until the server-side observer chain finishes, then returns 204 with `DeploymentStatus=Active` → `channel.IsActive=true` in ~15-21s (Meta `/register` round-trip). `STEPS_RUN=["insert","route","activate"]`.

**Stage 5**: Emits:
```json
{"ok":true, "messageType":"WhatsApp", "channelId":"0MjSG...", "mcuId":"0gLSG...",
 "channelName":"+1 650-555-0199", "sessionHandlerId":"00GSG0000000LSf2AM",
 "queueName":"Messaging Queue", "isActive":true,
 "stepsRun":["insert","route","activate"], "stepsSkipped":["consent"], "totalDurationMs":8421}
```

User sees `Success — WhatsApp channel '+1 650-555-0199' is live on test1.` plus the detail lines.

---

## Worked example: resume after routing failure

Same inputs as above, but imagine Stage 3 failed the first time because the user's session lost permission to deploy Queue metadata.

**First run** — orchestrator gets through stages 0-2, stage 3 fails:
```json
{"ok":false, "failedStep":"route", "failedStepIndex":2, "failedStepTotal":4,
 "leafEnvelope":{"ok":false,"kind":"metadata-deploy-failed","message":"INSUFFICIENT_ACCESS_OR_READONLY"},
 "stateSoFar":{"channelId":"0MjSG...", "mcuId":"0gLSG...",
               "sessionHandlerId":null, "isActive":false,
               "stepsRun":["insert"], "stepsSkipped":[]},
 "resumeHint":"fix the routing issue above, then re-run this skill — step 1 will be skipped automatically"}
```

User fixes the permission, re-runs with the same inputs.

**Second run**:
- **Stage 0** type known (user provided `WhatsApp` again). Inputs validated.
- **Stage 1** preflight now returns 1 record: `{channelId, IsActive:false, SessionHandlerId:null, FallbackQueueId:null, ...}` → `CURRENT_STATE=inserted-no-routing`. First step: route.
- **Stage 2** (insert): skipped. `STEPS_SKIPPED=["insert"]`. The dispatcher + all per-type prereqs (including the WABA linking prompt) are skipped entirely, which is the whole point of preflight short-circuiting.
- **Stage 3** (route): runs fresh, succeeds this time. `STEPS_RUN=["route"]`.
- **Stage 3.5** (consent): the channel was inserted on the *first* run, so its consent was auto-seeded then (`ConsentType=ImplicitOptIn` + default opt-out keyword). The leaf's Stage 1 finds it already activation-ready and returns `noop:true` — no write. `STEPS_SKIPPED=["consent"]`. (Only an explicit Explicit/DoubleOptIn or custom-keyword request would make this a real write.)
- **Stage 4** (activate): runs. `STEPS_RUN=["route","activate"]`.
- **Stage 5**: success, with `stepsRun: ["route","activate"]` and `stepsSkipped: ["insert","consent"]` visible in the report.

The user sees that resume happened, and the total time reflects only what was re-done.

---

## Worked example: Apple Business Chat dispatch

Shows the type-agnostic flow — same orchestrator, different leaf via the dispatcher.

Input:
- `MESSAGE_TYPE=AppleBusinessChat`
- `APPLE_BC_ID=abc123-def456-...` (GUID)
- `CHANNEL_NAME="Acme Apple Support"`

**Stage 0**: type known. `{PLATFORM_KEY} = APPLE_BC_ID`. Apple-required inputs (`APPLE_BC_ID`, `CHANNEL_NAME`) present — proceed.

**Stage 1**: preflight SOQL keyed off `MessagingPlatformKey='abc123-...' AND MessageType='AppleBusinessChat'` returns 0 records → `CURRENT_STATE=fresh`.

**Stage 2** (insert): `service-de-channel-create` runs with `MESSAGE_TYPE=AppleBusinessChat`. The user supplies the Apple BC Account ID (obtained on the Apple Business Register side beforehand), and the skill inserts the channel. Returns with `messageType:"AppleBusinessChat"`.

**Stages 3-5**: routing and activation are identical to the WhatsApp path — they operate on `MessagingChannel.Id` + `MessagingChannelUsage.Id`, which don't care about message type.

Final envelope identical shape to the WhatsApp run but with `messageType: "AppleBusinessChat"`.

---

## Worked example: unsupported type rejection

User invokes without specifying a type, gets the prompt, then types `wechat`.

**Stage 0**: prompt shows `1) WhatsApp / 2) Line / 3) AppleBusinessChat / 4) Facebook / 5) Text (SMS)`. Input `wechat` doesn't match any — orchestrator re-prompts or halts with:
```json
{"ok":false, "kind":"unsupported-type", "messageType":"wechat",
 "supportedTypes":["WhatsApp","Line","AppleBusinessChat","Facebook","Text"],
 "hint":"WeChat needs its own insertion leaf, not yet built — supported types are WhatsApp, Line, AppleBusinessChat, Facebook, Text"}
```

Alternatively, if the orchestrator forwards `WeChat` directly to the dispatcher without validating upfront, the dispatcher (`service-de-channel-create`) emits the same `unsupported-type` envelope and the orchestrator passes it through with `failedStep: "insert"`.

Either way the user gets a clear "this type isn't supported" message rather than a confusing mid-flow error.
