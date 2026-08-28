---
name: service-de-channel-activate
description: "Activate an Enhanced `MessagingChannel` (WhatsApp / Apple / Facebook / SMS / RCS) by PATCHing `MessagingChannelUsage.DeploymentStatus` from `Disabled` to `Provisioning` via the standard REST sobject endpoint. The UDD save-hook fires on the REST write, dispatches by `MessageType` for the external callout (`WHATS_APP` → Meta `/register`, `FACEBOOK` → `subscribeFacebookPage`, `TEXT` → `registerCsotSms`; Apple, LINE, and others need no external call), writes the terminal `Active` or `Error`, and flips `MessagingChannel.IsActive`. The chain is synchronous on the HTTP response — WhatsApp returns 204 only after Meta confirms registration (~15-21s); channels with no external callout are near-instant (~1s on Apple). No Aura RPC; no CSRF cookies. Use this skill when the user needs to activate an already-inserted Enhanced messaging channel headlessly via REST."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Service"]
  cliTools:
    - tool: ["jq"]
      semver: ">=1.6.0"
    - tool: ["node"]
      semver: ">=20.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "service-de-channel-consent-configure"
    - "service-de-channel-create"
    - "service-de-channel-routing-configure"
---

# Activating a Messaging Channel

## What this skill does

Given a `{CHANNEL_ID}`, reads the channel's `MessagingChannelUsage.Id`, then fires `PATCH /services/data/v{V}/sobjects/MessagingChannelUsage/{MCU_ID}` with body `{"DeploymentStatus":"Provisioning"}`. The server-side chain:

1. `MessagingChannelUsageFunctions.validateBeforeSave` runs `validateDeploymentStatus` → `validateChannelReadinessOnProvisioning`. For WhatsApp this confirms consent is configured. Rejected writes return HTTP 400 `FIELD_INTEGRITY_EXCEPTION`.
2. `MessagingChannelUsageFunctions.saveHook_PostStmtExecuteOnce` fires unconditionally after the UPDATE statement. It calls `MessagingChannelUsageFunctionsHelper.handlePostSave` which registers a post-commit `TransactionObserver`.
3. At commit, the observer calls `ConversationChannelUsageDeploymentStatusService.handleProvisioning` (inherited from `AbstractChannelUsageDeploymentStatusService`), which:
   - Calls `runProvisioning` — `switch`-dispatches by `MessageType` for the external callout:
     - `WHATS_APP` → `registerCsotWhatsAppNumber` → `LiveMessageSetupApi.registerWhatsAppNumber` → Meta `/register` + status verification. 15-21s wall-clock.
     - `FACEBOOK` → `metaGraphApiService.subscribeFacebookPage`.
     - `TEXT` → `registerCsotSms`.
     - `AppleBusinessChat`, `Line`, everything else → `default` branch, no external callout, no network wait.
   - On success: writes `DeploymentStatus = 'Active'` via PLSQL.
   - On failure: writes `DeploymentStatus = 'Error'` plus `ErrorReason` / `ErrorDetails`.
4. Inside the same observer, a second pass syncs `MessagingChannel.IsActive = true` once MCU reaches `Active` (the `isTransitioningStatus` flag skips the flip while status is still `Provisioning`).

All synchronous within the PATCH request — the 204 response only comes back after the full chain completes. WhatsApp: ~15-21s (Meta `/register` round-trip). Apple / Line: ~1s (no external call; just the local save-hook + observer + PLSQL write). Verified on wadtesting 2026-04-30.

## Reference File Index

| Reference file | Load when |
| --- | --- |
| `references/phone-verification.md` | Stage 3 comes back with `ErrorReason === "VERIFICATION_REQUIRED"` (WhatsApp only) — the phone-number OTP verification sub-flow. |
| `references/worked-examples.md` | You want a reference run of the WhatsApp happy-path, Apple activation, a readiness failure, or the already-active no-op. |
| `references/gotchas.md` | Troubleshooting an unexpected result, or before modifying this skill — the eleven known gotchas. |

## Why REST PATCH instead of Apex?

A direct REST PATCH produces the identical save-hook chain as the old `activateChannelUsage` Apex method, with substantially less machinery — no CSRF cookie acquisition, no bootstrap fetch, no Aura response parsing, no double-wrapped `returnValue`. REST semantics are honest: 204 means the transition succeeded; 4xx means it didn't.

Code proof: `MessagingChannelUsageFunctions.saveHook_PostStmtExecuteOnce` fires on any DML path (REST, SOAP, Apex, Metadata API) — there is no Apex-specific gate. The entity XML (`MessagingChannelUsage.entity.xml`) marks `DeploymentStatus` as `editAccess="always"` with no `<readonly>` attribute. The transition validator (`getValidAPIStatusTransitions`) allows `Disabled → Provisioning` (and `New → Provisioning`, and `Error → Provisioning | Deprovisioning`, and `Active → Deprovisioning`). The DB-only transitions `Provisioning → Active | Error` are reserved for the observer's PLSQL call — that's why we write `Provisioning` and let the server pick the terminal state.

## When NOT to use this skill

- **The channel is already `IsActive=true`.** Re-firing is blocked by the API transition validator (`Active → Provisioning` is not in `getValidAPIStatusTransitions()`) — the PATCH would return 400. The Stage 1 precondition check catches this and emits `noop:true`.
- **Routing isn't configured.** `activateChannelUsage` used to fail with `LiveMessageSetupException` / `nullQueueId` at the Apex entry point. With the REST path the same guard lives in `validateChannelReadinessOnProvisioning` — write with `SessionHandlerId=null && FallbackQueueId=null` → 400 `FIELD_INTEGRITY_EXCEPTION`. Run `service-de-channel-routing-configure` first. The Stage 1 check still runs defensively.
- **The MCU doesn't exist.** Can't PATCH a row that's missing. Run the insertion skill first — it always creates the MCU as a side-effect of `addChannel`.

## Inputs (from caller)

- `{CHANNEL_ID}` — a 15- or 18-char `MessagingChannel.Id` (prefix `0Mj`). The channel must already exist with a non-null `SessionHandlerId` or `FallbackQueueId`.
- `{ORG_ALIAS}` — optional; the `sf` CLI target-org alias. Default: whatever `sf config get target-org` returns. Used for OAuth and SOQL reads.
- `{API_VERSION}` — optional; REST API version. Default: `68.0`. Any version where `MessagingChannelUsage` is addressable as a standard sobject is fine (v50+ should work; not exhaustively tested).

Unlike the old Aura-based version of this skill, there are no `{POLL_TIMEOUT_S}` / `{POLL_INTERVAL_S}` inputs — the PATCH is synchronous end-to-end.

## Output (to caller)

**Success — channel is live:**
```json
{"ok": true, "channelId": "0Mj...", "mcuId": "0gL...", "deploymentStatus": "Active", "isActive": true, "messageType": "WhatsApp", "durationMs": 20934}
```

**Success — no-op (already active):**
```json
{"ok": true, "noop": true, "channelId": "0Mj...", "message": "Channel already active"}
```

**Failure — precondition not met:**
```json
{"ok": false, "kind": "no-routing",     "hint": "run service-de-channel-routing-configure first"}
{"ok": false, "kind": "no-mcu",         "hint": "no MessagingChannelUsage row for this channel — run the insertion skill first"}
{"ok": false, "kind": "channel-missing","hint": "MessagingChannel id not found"}
```

**Failure — validator or server-side provisioning error:**
```json
{"ok": false, "kind": "readiness-failed", "errorCode": "FIELD_INTEGRITY_EXCEPTION",
 "message": "...", "hint": "validateChannelReadinessOnProvisioning rejected the write — most commonly missing consent; run service-de-channel-consent-configure first"}
{"ok": false, "kind": "provisioning-error", "mcuId": "0gL...", "errorReason": "MetaRegistrationFailed", "errorDetails": "..."}
{"ok": false, "kind": "verification-failed", "hint": "WhatsApp phone number verification failed or was declined by user"}
{"ok": false, "kind": "verification-request-failed", "errorCode": "...", "message": "...", "hint": "Could not request verification code from Meta"}
```

**Failure — auth / transport:**
```json
{"ok": false, "kind": "auth",      "hint": "OAuth token invalid / expired — run 'sf org login web'"}
{"ok": false, "kind": "transport", "status": 500, "message": "..."}
```

---

## Stage 1: Precondition checks

Read the channel, then its MCU, as two separate SOQL calls. A combined subquery would be cheaper but fails on orgs where the child relationship is unnameable (see gotcha #4).

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, MessageType, IsActive, SessionHandlerId, FallbackQueueId, MessagingPlatformKey FROM MessagingChannel WHERE Id = '{CHANNEL_ID}'" \
  --json > /tmp/amc-precheck-channel.json

sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeploymentStatus, DeploymentType, ErrorReason, ErrorDetails FROM MessagingChannelUsage WHERE MessagingChannelId = '{CHANNEL_ID}'" \
  --json > /tmp/amc-precheck-mcu.json
```

Let `channel = /tmp/amc-precheck-channel.json records[0]` and `mcu = /tmp/amc-precheck-mcu.json records[0]`:

| Condition | Envelope |
| --- | --- |
| Channel query returned 0 records | `{ok:false, kind:"channel-missing", hint:"MessagingChannel id not found"}` |
| `channel.IsActive === true` | `{ok:true, noop:true, channelId, message:"Channel already active"}` — return |
| `channel.SessionHandlerId == null && channel.FallbackQueueId == null` | `{ok:false, kind:"no-routing", hint:"run service-de-channel-routing-configure first"}` |
| MCU query returned 0 records | `{ok:false, kind:"no-mcu", hint:"no MessagingChannelUsage row for this channel — run the insertion skill first"}` |
| Otherwise | Record `{MCU_ID} = mcu.Id`, `{MESSAGE_TYPE} = channel.MessageType`, `{MESSAGING_PLATFORM_KEY} = channel.MessagingPlatformKey`, `{INITIAL_MCU_STATUS} = mcu.DeploymentStatus` and continue to Stage 2. |

Also record `{T0}` (epoch ms at start of Stage 2) so the final envelope can report `durationMs`.

### Stage 1.1: Fast path for already-provisioning MCU

If `{INITIAL_MCU_STATUS} === "Provisioning"` — the MCU is already mid-flight from a prior call in this transaction window. Skip Stage 2 (firing the PATCH) entirely and jump to Stage 3 (verification). This is a rare race guard: the observer is synchronous with the PATCH, so by the time the caller sees the 204 the status is already terminal (`Active` or `Error`) — `Provisioning` should be invisible from outside. If we do see it in the precheck, something wrote `Provisioning` in a separate DML and the observer is still mid-flight — don't fire a second PATCH.

---

## Stage 2: PATCH `MessagingChannelUsage.DeploymentStatus = "Provisioning"`

Use `sf api request rest` so authentication stays inside the CLI's transport — no OAuth token is ever extracted into shell state.

Fire the PATCH. **This call can take 15-30 seconds for WhatsApp** — the observer runs synchronously, including Meta's `/register` round trip. `sf api request rest` has no separate client-side timeout to raise; it waits on the underlying HTTP call.

```bash
sf api request rest \
  "/services/data/v{API_VERSION}/sobjects/MessagingChannelUsage/{MCU_ID}" \
  --method PATCH \
  --target-org '{ORG_ALIAS}' \
  --header 'Content-Type: application/json' \
  --body '{"DeploymentStatus":"Provisioning"}' \
  --include \
  > /tmp/amc-patch-response.txt 2>&1
HTTP_CODE=$(head -1 /tmp/amc-patch-response.txt | grep -oE '[0-9]{3}')
```

`--include` prints the HTTP status/headers block ahead of the (typically empty, on 204) body — read the status line from that block rather than a `-w`-style trailing marker.

Classify by HTTP status:

| Status | Body | Handling |
| --- | --- | --- |
| 204 | empty | Success. The observer ran to completion; MCU is `Active` or `Error`. Continue to Stage 3 to read the terminal state. |
| 400 | `[{errorCode:"FIELD_INTEGRITY_EXCEPTION", message:"..."}]` | Validator rejection. See table below. |
| 400 | `[{errorCode:"INVALID_FIELD_FOR_INSERT_UPDATE" or "MALFORMED_ID", ...}]` | Skill bug — the MCU_ID from Stage 1 was wrong, or the body shape is off. Emit `{ok:false, kind:"transport", status:400, message}`. |
| 401 | (usually empty) | Bearer token invalid. Emit `{ok:false, kind:"auth", hint:"OAuth token invalid / expired — run 'sf org login web'"}`. |
| 403 | `[{errorCode:"INSUFFICIENT_ACCESS"}]` | User lacks perm to write `DeploymentStatus`. Emit `{ok:false, kind:"business", errorCode:"INSUFFICIENT_ACCESS", message}`. |
| 5xx | varies | Transport. The observer may have partially committed — Stage 3's SOQL is the source of truth. Read MCU state; if it's `Active`, report success with a warning; if `Error` or still `Disabled`, classify as `{ok:false, kind:"transport", status, message}`. |

**Known 400 `FIELD_INTEGRITY_EXCEPTION` messages:**

| Message fragment | Meaning | Envelope |
| --- | --- | --- |
| "invalid deployment status transition" | The current status doesn't allow `→ Provisioning` (e.g. MCU is already `Active` — Stage 1 should have caught this, but there's a race window). | Re-read MCU; if now `Active`, emit success-noop. If `Provisioning`, Stage 3 poll. Otherwise emit `{ok:false, kind:"readiness-failed", ...}`. |
| "consent" / "keyword" / mentions of STOP/HELP | `validateChannelReadinessOnProvisioning` rejected — channel doesn't have required consent configured. | `{ok:false, kind:"readiness-failed", errorCode:"FIELD_INTEGRITY_EXCEPTION", message, hint:"channel requires a ConsentType and a matching MsgChannelLanguageKeyword record (opt-out keyword + confirmation) before activation — run service-de-channel-consent-configure"}`. |
| "routing" / "queue" / "SessionHandler" | Routing precondition (Stage 1 should have caught, but the validator re-checks). | `{ok:false, kind:"no-routing", message, hint:"run service-de-channel-routing-configure first"}`. |
| other | Unrecognized validator error. | `{ok:false, kind:"readiness-failed", errorCode, message}`. |

---

## Stage 3: Read the terminal MCU state

The PATCH is synchronous, so by the time we're here the MCU is `Active` or `Error` — no polling. Read once:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeploymentStatus, ErrorReason, ErrorDetails FROM MessagingChannelUsage WHERE Id = '{MCU_ID}'" \
  --json > /tmp/amc-poststate-mcu.json
```

| Status | Handling |
| --- | --- |
| `Active` | Continue to Stage 4. |
| `Error` with `ErrorReason === "VERIFICATION_REQUIRED"` | For WhatsApp channels only: phone number needs OTP verification. Continue to Stage 3.2 (WhatsApp verification flow). |
| `Error` (other) | Emit `{ok:false, kind:"provisioning-error", mcuId, errorReason, errorDetails}`. |
| `Provisioning` | Unexpected — the observer was supposed to terminate before the PATCH returned 204. Fall through to a defensive poll (see Stage 3.1). |
| `Disabled` | The PATCH returned 204 but the write didn't take? Emit `{ok:false, kind:"transport", message:"PATCH returned 204 but MCU is still Disabled — observer didn't commit"}`. |

### Stage 3.2: WhatsApp phone number verification (only if ErrorReason === "VERIFICATION_REQUIRED")

This sub-flow only runs for WhatsApp channels when activation fails with `ErrorReason === "VERIFICATION_REQUIRED"` — the phone number needs OTP verification with Meta before it can be registered. **If the MCU comes back with `ErrorReason === "VERIFICATION_REQUIRED"` (WhatsApp only), load `references/phone-verification.md` and follow it** to drive the phone-number verification sub-flow (request code → prompt user → validate code → retry activation once).

### Stage 3.1: Defensive poll (only if Stage 3 saw `Provisioning`)

The observer's external-callout block (WhatsApp/Facebook/SMS) runs synchronously inside the PATCH request — there's no async queue indirection in `runProvisioning` for any message type (verified against the switch/case in `ConversationChannelUsageDeploymentStatusService`). So a `Provisioning` status at Stage 3 should not happen in steady state. Possible causes if it does: an exception thrown *after* the external call succeeded but before the PLSQL terminal-write ran; unusual instance config with async observer execution; or a future MessageType whose dispatch behavior we haven't accounted for. If Stage 3 returned `Provisioning`, loop:

```bash
for i in 1 2 3 4 5 6 7 8 9 10; do
  sleep 3
  STATUS=$(sf data query --target-org '{ORG_ALIAS}' \
    --query "SELECT DeploymentStatus FROM MessagingChannelUsage WHERE Id='{MCU_ID}'" --json \
    | node -e 'console.log(JSON.parse(require("fs").readFileSync(0,"utf8")).result.records[0].DeploymentStatus)')
  case "$STATUS" in
    Provisioning) continue ;;
    Active|Error) break ;;
  esac
done
```

Max wait: 30s. If still `Provisioning` after the loop: emit `{ok:false, kind:"timeout", mcuId, lastStatus:"Provisioning", elapsedS:30}`. Verified on WhatsApp/wadtesting 2026-04-30: this loop should never actually iterate.

---

## Stage 4: Verify `MessagingChannel.IsActive`

The observer flips `IsActive` inside the same callback as the status terminal write. In principle this is set by the time the PATCH returns. Confirm:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, IsActive FROM MessagingChannel WHERE Id = '{CHANNEL_ID}'" --json > /tmp/amc-verify-channel.json
```

If `IsActive === true`: compute `durationMs = Date.now() - T0` and emit success. If `IsActive !== true` despite MCU `Active`: the `IsActive` sync pass skipped (e.g. `isTransitioningStatus` was true when the observer ran, which shouldn't happen post-terminal). Emit:

```json
{"ok": false, "kind": "provisioning-error", "mcuId": "...", "errorReason": "mcu-active-but-channel-inactive",
 "errorDetails": "MCU DeploymentStatus=Active but MessagingChannel.IsActive=false — observer's IsActive sync pass didn't run. Inspect MessagingChannelUsageFunctionsHelper.handlePostSave."}
```

---

## Stage 5: Report to caller

Build the success envelope:

```json
{"ok": true, "channelId": "{CHANNEL_ID}", "mcuId": "{MCU_ID}", "deploymentStatus": "Active",
 "isActive": true, "messageType": "{MESSAGE_TYPE}", "durationMs": 20934}
```

If this skill is the leaf (user invoked it directly), render:

- `Success — Activated — MessagingChannel {CHANNEL_ID} ({messageType}) is now live. MCU DeploymentStatus=Active, IsActive=true. (~{durationMs/1000}s)`
- `Info: Already active — MessagingChannel {CHANNEL_ID} is IsActive=true. No changes.` (no-op path)
- `Error: Routing not configured — run 'service-de-channel-routing-configure' skill first.` (no-routing)
- `Error: No MessagingChannelUsage row — run the insertion skill first.` (no-mcu)
- `Error: Readiness check failed: {message} — if it mentions consent/keywords, run 'service-de-channel-consent-configure' first.` (readiness-failed)
- `Error: Activation failed: {errorReason} — {errorDetails}` (provisioning-error)
- `Error: WhatsApp phone number verification failed: {hint}` (verification-failed)
- `Error: Could not request verification code: {message}` (verification-request-failed)
- `Timeout: Activation timed out after {elapsedS}s with MCU.DeploymentStatus={lastStatus}. Defensive-poll limit hit; this is unusual. Check MCU {mcuId} in Setup.` (timeout)

---

## Worked examples

For end-to-end activation traces (WhatsApp happy-path, Apple activation, a readiness-validator failure, and the already-active no-op), see `references/worked-examples.md`.

---

## Gotchas

Eleven known gotchas — synchronous PATCH timing for WhatsApp, valid API status transitions, the `IsActive` sync pass, relationship-name variance across orgs, consent preconditions, `DeploymentStatus` picklist casing, the REST-vs-Apex equivalence, `ErrorReason` values, `VERIFICATION_REQUIRED` handling, OAuth token extraction, and the Status-code-409 Admin API conflict. Before troubleshooting an unexpected result or modifying this skill, load `references/gotchas.md` and follow it.
