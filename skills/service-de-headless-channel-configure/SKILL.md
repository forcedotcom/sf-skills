---
name: service-de-headless-channel-configure
description: "Top-level orchestrator: given a messaging channel type and its type-specific inputs, produces an activated Enhanced `MessagingChannel` in the target Salesforce org — without the Meta/LINE/Apple setup popups. Prompts for `{MESSAGE_TYPE}` if not supplied, then sequences insert → route → consent → activate via the type-agnostic dispatcher (`service-de-channel-create`) plus the shared routing/consent/activation leaves. Resumes from partial state on re-run. Use this skill when the user wants to set up an Enhanced messaging channel (WhatsApp, Facebook, LINE, Apple, or SMS/Text) end-to-end from the command line, bypassing the in-org setup popups."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Service"]
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "service-de-channel-activate"
    - "service-de-channel-consent-configure"
    - "service-de-channel-create"
    - "service-de-channel-routing-configure"
    - "service-de-waba-integrate"
---

# Headless Channel Setup (type-agnostic)

## What this skill does

Takes a channel type (`WhatsApp` | `Line` | `AppleBusinessChat` | `Facebook` | `Text`) plus its type-specific inputs and drives it to an activated `MessagingChannel`. It first gates on the Enhanced Messaging Terms and Conditions, then runs four steps:

0. **Accept Terms and Conditions** — renders the Enhanced Messaging disclaimer and requires the user to certify they have authority to bind their org, mirroring the in-org "Add a Channel" wizard. Blocking — a decline ends the run before any org work. *(Stage 0.5, in this skill)*
1. **Insert the channel** — invokes `service-de-channel-create`, which handles the per-type third-party prereq internally (e.g. WhatsApp's `service-de-waba-integrate` runs inside `service-de-channel-create`). *(skill: `service-de-channel-create`)*
2. **Configure routing** — sets `SessionHandlerId` to an Omni-Channel Queue (pick existing or create new). Message-type-agnostic. *(skill: `service-de-channel-routing-configure`)*
3. **Configure consent** — ensures a valid `ConsentType` + matching `MsgChannelLanguageKeyword` record. The Connect insert auto-seeds a default `ConsentType=ImplicitOptIn` + opt-out keyword, so on a fresh channel this step is frequently a **no-op** — or an *upgrade* if the caller wants ExplicitOptIn/DoubleOptIn. Activation's readiness check requires both routing AND consent, so this runs before activation. *(skill: `service-de-channel-consent-configure`)*
4. **Activate** — PATCHes `MessagingChannelUsage.DeploymentStatus` to `Provisioning` via REST; the server-side save-hook drives the full observer chain synchronously and returns 204 once the MCU reaches `Active` and `MessagingChannel.IsActive=true`. Message-type-agnostic. *(skill: `service-de-channel-activate`)*

**Resume-by-default.** Each step is idempotent — if you re-run after a failure, the orchestrator detects existing state and skips steps that already succeeded.

**Prompt mid-flow.** If `{MESSAGE_TYPE}` isn't in the initial request, the orchestrator asks upfront. Routing choices (pick queue / create new) are prompted when step 2 runs, not upfront — keeps leaf skills self-contained.

## Reference File Index

| Reference file | Load when |
| --- | --- |
| `references/inputs.md` | You need the full input field list — MESSAGE_TYPE/ORG_ALIAS plus per-type fields for WhatsApp, LINE, AppleBusinessChat, Facebook, Text (SMS). |
| `references/terms-and-conditions.md` | Rendering the Stage 0.5 disclaimer and certification prompt — verbatim text and per-type label/third-party mappings. |
| `references/output-envelopes.md` | Wiring error handling or parsing the canonical success/failure/terms-declined JSON envelope shapes. |
| `references/partial-success.md` | The orchestrator fails mid-way and you need to render the partial-success/resume report. |
| `references/gotchas.md` | Debugging unexpected behavior — duplicate-key errors, resume/idempotency questions, preflight SOQL shape, unattended/CI usage. |
| `references/worked-examples.md` | You need a reference trace (fresh WhatsApp run, resume after failure, Apple dispatch, unsupported-type rejection) for exact envelope shapes. |

---

## Critical execution rule

**This orchestrator MUST run all stages (0-5) in a SINGLE response without stopping between stages.**

When you invoke a leaf skill (service-de-channel-create, service-de-channel-routing-configure, service-de-channel-consent-configure, service-de-channel-activate) and it returns via function_results:

- **DO:** Immediately parse the function_results return value and continue to the next stage
- **DO:** Run Stage 0.5 → Stage 1 → Stage 2 → Stage 3 → Stage 3.5 → Stage 4 → Stage 5 consecutively in ONE response
- **DO NOT:** Stop and report back to the user between stages
- **DO NOT:** Wait for user confirmation between stages
- **DO NOT:** Treat each stage as a separate turn in the conversation

**Why this matters:** The user invoked THIS orchestrator skill to get an end-to-end activated channel. They did NOT invoke the individual leaf skills. Your job is to run the entire pipeline autonomously and report the final result. Stopping mid-flow breaks the orchestrator pattern and forces the user to manually resume each stage.

**Exception:** Only stop mid-flow if a leaf skill returns `ok: false` with a terminal error (not a recoverable prompt), or if the user declines the Stage 0.5 Terms and Conditions gate (emit `terms-not-accepted` and halt). Then report the failure immediately with context about which stage failed and what state was reached.

**Stage 0.5 is a required blocking prompt.** The Terms and Conditions gate is the one prompt that must be answered affirmatively before any org work. It is not optional and must not be auto-accepted. A `no`/decline ends the run per the exception above; a `yes` continues to Stage 1 in the same response.

**Leaf skill prompts:** Some leaf skills (like `service-de-waba-integrate` or `service-de-channel-routing-configure`) may prompt the user for input mid-execution. That's fine — answer those prompts as they come up, but then CONTINUE to the next stage immediately after the prompt is answered. Don't stop just because a prompt was involved.

---

## When NOT to use this skill

- **You only want one step.** Invoke the leaf skill directly (`service-de-channel-create`, `service-de-channel-routing-configure`, `service-de-channel-activate`). This orchestrator is for the full automated path from nothing → activated channel.
- **You want to run stages independently in separate conversation turns.** This orchestrator runs all stages consecutively in one response. If you need manual control between stages, invoke the leaf skills individually.
- **You want a message type outside `WhatsApp` / `Line` / `AppleBusinessChat` / `Facebook` / `Text`.** The dispatcher will return `unsupported-type`. WeChat / MsCopilot / Alexa would need their own leaves + a dispatcher update.
- **The prereq hasn't been met (WABA not shared, LINE channel not created, Apple account not registered, SMS number not provisioned).** The per-type insert skill's Stage 2-equivalent surfaces this clearly and returns; no orchestration fixes it. (For SMS/Text the number-provisioning prereq isn't checked at insert — an unprovisioned number surfaces later as an activation-time `provisioning-error`.)

## Inputs (from user)

`{MESSAGE_TYPE}` (prompted if omitted) and `{ORG_ALIAS}` (optional), plus type-specific fields for WhatsApp, LINE, AppleBusinessChat, Facebook, and Text (SMS) forwarded to the dispatcher. **Load `references/inputs.md` and follow it** for the full field list and the omitted-type prompt text.

## Output (to user)

Three top-level outcomes: success, step-annotated failure, and terms-declined. **Load `references/output-envelopes.md` and follow it** for the exact JSON shapes.

---

## Stage 0: Resolve `{MESSAGE_TYPE}` and type-specific key

If `{MESSAGE_TYPE}` is omitted, prompt the user (see "Inputs" above). Refuse to proceed without one — there's no sensible default.

Once known, determine the **preflight key** — the field we'll filter the `MessagingChannel` SOQL on to detect existing state. It's always `MessagingPlatformKey`, but what that value *is* varies by type:

| `{MESSAGE_TYPE}` | Preflight key value `{PLATFORM_KEY}` | Notes |
| --- | --- | --- |
| `WhatsApp` | `{PHONE_NUMBER_ID}` | Required upfront |
| `Line` | `{LINE_CHANNEL_ID}` | Required upfront |
| `AppleBusinessChat` | `{APPLE_BC_ID}` | Required upfront |
| `Facebook` | `{PAGE_ID}` | Optional - OAuth → fetch pages → prompt if not provided |
| `Text` | `{SMS_NUMBER}` | Required upfront (the phone number / short code itself) |

**Facebook is unique:** If `{PAGE_ID}` is not provided, the orchestrator cannot run its own Stage 1 preflight. Instead, skip Stage 1 and let `service-de-channel-create` handle the full OAuth → page selection → preflight → creation flow. The insertion skill has its own Stage 1 preflight that runs after page selection.

For non-Facebook types, validate that the caller provided the required type-specific inputs for `{MESSAGE_TYPE}` (see Inputs above). If missing, prompt or halt — don't call the dispatcher, it will re-validate and return `missing-input`, wasting a round trip.

---

## Stage 0.5: Enhanced Messaging Terms and Conditions (blocking gate)

**Run this before any org query or channel work.** The in-org "Add a Channel" wizard requires the admin to accept the Enhanced Messaging Terms and Conditions before it will let them proceed to channel setup. The headless flow must enforce the same gate — do not skip it, do not accept on the user's behalf. This runs once per orchestrator invocation, after `{MESSAGE_TYPE}` is known (the disclaimer names the channel) and before Stage 1.

**Render the disclaimer and certification prompt from `references/terms-and-conditions.md` (verbatim, substituting the channel label) — load it and follow it for the exact wording and per-type label/third-party mappings.**

**Gate behavior:**

- If the user answers **yes** (affirmative acceptance), record `{TC_ACCEPTED} = true` and continue to Stage 1.
- If the user answers **no**, declines, or does not affirmatively accept, **halt immediately** — do not run Stage 1 or any subsequent stage. Emit:
  ```json
  {"ok": false, "kind": "terms-not-accepted",
   "hint": "user did not accept the Enhanced Messaging Terms and Conditions — channel setup cannot proceed. Re-run when ready to accept."}
  ```
- Acceptance is required on **every** orchestrator invocation, including resume runs. It is a per-session gate, not persisted — we don't have a place to durably record it, and the cost of re-confirming is one prompt.

---

## Stage 1: Pre-flight state detection (resume support)

**Skip this stage entirely if `MESSAGE_TYPE=Facebook` and `{PAGE_ID}` was not provided.** The Facebook insertion skill needs to run OAuth first before we know which PAGE_ID to check for. Let the insertion skill handle its own preflight in Stage 1 after page selection.

For all other cases, query the org to see how far a prior run got. This enables skip-ahead on resume. **Two queries, not a subquery** — the `(SELECT ... FROM MessagingChannelUsages)` subquery fails on some orgs where the child relationship is unnameable. Use FK-keyed second query instead (see gotcha #9).

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeveloperName, MessageType, IsActive, SessionHandlerId, FallbackQueueId FROM MessagingChannel WHERE MessagingPlatformKey = '{PLATFORM_KEY}' AND MessageType = '{MESSAGE_TYPE}'" \
  --json > /tmp/hcs-preflight.json
```

If the channel query returns a row, fire a second query to resolve its MCU:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id, DeploymentStatus FROM MessagingChannelUsage WHERE MessagingChannelId = '{CHANNEL_ID}'" \
  --json > /tmp/hcs-preflight-mcu.json
```

Parse the combined result to figure out `{CURRENT_STATE}`:

| Preflight result | `CURRENT_STATE` | First step to run |
| --- | --- | --- |
| No records | `fresh` | Step 1 (insert) |
| Record exists, `IsActive=false`, `SessionHandlerId=null` and `FallbackQueueId=null` | `inserted-no-routing` | Step 2 (configure routing) |
| Record exists, `IsActive=false`, routing set | `routed-not-active` | Step 3 (configure consent), then Step 4 (activate) |
| Record exists, `IsActive=true` | `already-active` | Emit no-op success envelope; return. |

Record the existing `{CHANNEL_ID}` and `{MCU_ID}` if present — downstream steps need them.

Initialize `{STEPS_RUN} = []`, `{STEPS_SKIPPED} = []`, `{T0} = Date.now()`.

---

## Stage 2: Insert the channel (step 1 of 4)

Skip this stage if `CURRENT_STATE` ∈ `{inserted-no-routing, routed-not-active, already-active}` — the channel already exists. Append `"insert"` to `STEPS_SKIPPED` in that case.

Otherwise invoke `service-de-channel-create` with:

- `{MESSAGE_TYPE}` = (from Stage 0)
- All type-specific inputs (forwarded verbatim — dispatcher routes to the right leaf)
- `{ORG_ALIAS}`

The insertion skill handles per-type prereqs internally (e.g., for WhatsApp, `service-de-channel-create` invokes `service-de-waba-integrate` as its Stage 2). This orchestrator doesn't need to know about WABA linking, LINE token verification, or Apple registration — `service-de-channel-create` owns the prereq semantics for whichever type it's running.

Handle the envelope:

| Leaf envelope | Orchestrator action |
| --- | --- |
| `{ok: true, channelId, mcuId, ...}` | Record `{CHANNEL_ID}` and `{MCU_ID}`. Append `"insert"` to `STEPS_RUN`. Continue. |
| `{ok: false, kind: "partnership-blocked" \| "user-declined" \| "apple-registration-pending" \| "line-prereq-missing"}` | These come from the per-type prereq stage. Pass through as `failedStep: "insert"`, `failedStepIndex: 1`. Return. |
| `{ok: false, kind: "missing-input" \| "unsupported-type"}` | Should have been caught in Stage 0 — emit failure with `failedStep: "insert"` and a note that the caller's inputs were incomplete. |
| `{ok: false, kind: <anything else>}` | Emit failure envelope with `failedStep: "insert"`, `failedStepIndex: 1`. Return. |

At this point we have `{CHANNEL_ID}` and `{MCU_ID}` regardless of whether step 1 ran or was skipped.

**→ Continue immediately to Stage 3 in this same response. DO NOT STOP.**

---

## Stage 3: Configure routing (step 2 of 4)

Skip this stage if `CURRENT_STATE === "routed-not-active"` — routing is already set. Append `"route"` to `STEPS_SKIPPED`.

Otherwise invoke `service-de-channel-routing-configure`:

- `{CHANNEL_ID}` = recorded above
- `{ORG_ALIAS}`

This is the step that **prompts the user** for queue choice (pick existing / create new / escape hatch). Don't try to pre-empt the prompts — forward the user's answers as-is.

Handle the envelope:

| Leaf envelope | Orchestrator action |
| --- | --- |
| `{ok: true, sessionHandlerId, queueName, ...}` (including `noop: true`) | Record `{SESSION_HANDLER_ID}` and `{QUEUE_NAME}`. Append `"route"` to `STEPS_RUN`. Continue. |
| `{ok: false, kind: "unsupported-routing-type", ...}` | User chose flow/user/asa/aea. Emit partial-success with `failedStep: "route"` and a resume hint pointing at the UI. Return. |
| `{ok: false, kind: "metadata-deploy-failed" \| "patch-failed" \| "verify-failed"}` | Emit failure envelope with `failedStep: "route"`. Return. |

**→ Continue immediately to Stage 3.5 in this same response. DO NOT STOP.**

---

## Stage 3.5: Configure consent (before activation)

Activation's readiness check requires **consent AND routing** — a fully-routed channel still fails to activate if consent isn't configured. Invoke `service-de-channel-consent-configure`:

- `{CHANNEL_ID}` = recorded above
- `{CONSENT_TYPE}`, `{LANGUAGE}`, and the keyword/prompt values — forward whatever the user supplied; omit what they didn't
- `{ORG_ALIAS}`

This stage **ensures consent is activation-ready** — it doesn't always write. The Connect insert **auto-seeds** `ConsentType=ImplicitOptIn` plus a default opt-out `MsgChannelLanguageKeyword`, which already satisfies the readiness check. So the leaf's Stage 1 will frequently find the channel *already* ready and return `noop: true` — the expected outcome on a fresh `ImplicitOptIn` channel, not a bug. It performs a **real write only** to upgrade (ExplicitOptIn/DoubleOptIn) or override the seeded keywords/prompts. When the user pre-supplied inputs asking for an upgrade, expect a write and let the leaf prompt for missing values — don't suppress those prompts.

Handle the envelope:

| Leaf envelope | Orchestrator action |
| --- | --- |
| `{ok: true, ...}` (including `noop: true`) | Append `"consent"` to `STEPS_RUN` (or `STEPS_SKIPPED` if `noop`). Continue. |
| `{ok: false, kind: "not-enhanced"}` | Shouldn't happen — these skills only create Enhanced channels. Emit failure with `failedStep: "consent"`. Return. |
| `{ok: false, kind: "missing-consent-input", hint}` | The user didn't supply a required keyword/prompt for the chosen ConsentType. Emit failure with `failedStep: "consent"` and pass through the `hint`. Return. |
| `{ok: false, ...}` (any other kind — `channel-patch-failed`, `keyword-record-failed`, `verify-failed`, or an unrecognized envelope) | Emit failure with `failedStep: "consent"` and pass through the leaf's `kind` and message verbatim. Return. |

**→ Continue immediately to Stage 4 in this same response. DO NOT STOP.**

---

## Stage 4: Activate (step 4 of 4)

Always run (unless `CURRENT_STATE === "already-active"`, in which case Stage 1 returned early).

Invoke `service-de-channel-activate`:

- `{CHANNEL_ID}` = recorded above
- `{ORG_ALIAS}`

No timeout knobs — activation is a single synchronous PATCH. The leaf does a defensive poll if the server ever returns mid-transition, but the expected path is one round-trip.

Handle the envelope:

| Leaf envelope | Orchestrator action |
| --- | --- |
| `{ok: true, isActive: true, ...}` (including `noop: true`) | Record results. Append `"activate"` to `STEPS_RUN`. Continue to Stage 5. |
| `{ok: false, kind: "no-routing"}` | Unusual (we just set it) — probably a race or permission issue. Emit failure with a hint about the permissions check. Return. |
| `{ok: false, kind: "no-mcu" \| "channel-missing"}` | Shouldn't happen after successful insert. Emit failure with the leaf's envelope. Return. |
| `{ok: false, kind: "readiness-failed", errorMessage}` | `validateChannelReadinessOnProvisioning` rejected the PATCH — missing consent (STOP/HELP keyword record). Stage 3.5 should have caught this; if it re-appears, re-run `service-de-channel-consent-configure` for the channel. Emit failure and pass through the resume hint. Return. |
| `{ok: false, kind: "provisioning-error", errorReason, errorDetails}` | Third-party side rejected (Meta `/register` failed, etc.). MCU is now in `Error`. Emit failure and pass through `errorReason`/`errorDetails`. Return. |
| `{ok: false, kind: "auth" \| "transport"}` | REST call failed at the HTTP layer (401 from `sf` auth, 5xx from the instance). Pass through. Return. |

---

## Stage 5: Final report

Build the success envelope:

```json
{
  "ok": true,
  "messageType": "{MESSAGE_TYPE}",
  "channelId": "{CHANNEL_ID}",
  "mcuId": "{MCU_ID}",
  "channelName": "{CHANNEL_NAME or inferred}",
  "sessionHandlerId": "{SESSION_HANDLER_ID}",
  "queueName": "{QUEUE_NAME}",
  "isActive": true,
  "stepsRun": [...],
  "stepsSkipped": [...],
  "totalDurationMs": Date.now() - T0
}
```

Render to the user as:

```text
Success — {MESSAGE_TYPE} channel '{CHANNEL_NAME}' is live on {ORG_ALIAS}.
   Channel ID: {CHANNEL_ID}
   Routed to: {queueName} ({SESSION_HANDLER_ID})
   Steps: ran {STEPS_RUN.join(", ")}{, skipped " + STEPS_SKIPPED.join(", ") if any}
   Total time: {formatted from durationMs}
```

If any step was skipped due to resume, the report should make that visible.

---

## Partial-success and resume reporting

If the orchestrator fails mid-way, the envelope always includes `stateSoFar` describing what landed. **`stateSoFar` must always carry both `stepsRun` and `stepsSkipped`** (each an array, empty if nothing landed/skipped yet) alongside the fields that landed — the partial-success renderer reads both. **When rendering a failure, load `references/partial-success.md` and follow it** — it has the exact template for showing which steps already landed and how to retry.

---

## Worked examples

For reference traces (fresh WhatsApp run, resume after routing failure, Apple dispatch, unsupported-type rejection), see `references/worked-examples.md`.

---

## Gotchas

Nine known gotchas covering prereq ownership, `MessagingPlatformKey` uniqueness, resume semantics, CSOT-only support, error-classification boundaries, prompt placement, platform-key mapping, wall-clock duration, and the two-query preflight workaround. **When debugging unexpected behavior, load `references/gotchas.md` and follow it.**
