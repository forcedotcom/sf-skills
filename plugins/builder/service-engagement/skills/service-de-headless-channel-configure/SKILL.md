---
name: service-de-headless-channel-configure
description: "Top-level orchestrator: given a messaging channel type and its inputs, produces an activated Enhanced `MessagingChannel` in the target org — without the Meta/LINE/Apple setup popups. Prompts for `{MESSAGE_TYPE}` if not supplied, then sequences insert → route → consent → activate → requested settings (auto-responses, keywords, session inactivity) via the type-agnostic dispatcher (`service-de-channel-create`) plus the shared routing/settings/activation leaves, and reports every requested setting as configured, not applicable, or failed. Resumes from partial state on re-run. Use to set up an Enhanced channel (WhatsApp, Facebook, LINE, Apple, SMS) end-to-end, bypassing in-org setup popups. Do not use for a single stage of an already-inserted channel — use the matching leaf skill (`service-de-channel-activate`, `service-de-channel-settings-configure`, `service-de-channel-routing-configure`) instead."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Service"]
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "service-de-channel-activate"
    - "service-de-channel-create"
    - "service-de-channel-routing-configure"
    - "service-de-channel-settings-configure"
    - "service-de-waba-integrate"
---

# Headless Channel Setup (type-agnostic)

## What this skill does

Takes a channel type (`WhatsApp` | `Line` | `AppleBusinessChat` | `Facebook` | `Text`) plus its type-specific inputs and drives it to an activated `MessagingChannel`. It first gates on the Enhanced Messaging Terms and Conditions, then runs four core steps plus an optional settings step:

0. **Accept Terms and Conditions** — renders the Enhanced Messaging disclaimer and requires the user to certify they have authority to bind their org, mirroring the in-org "Add a Channel" wizard. Blocking — a decline ends the run before any org work. *(Stage 0.5, in this skill)*
1. **Insert the channel** — invokes `service-de-channel-create`, which handles each type's third-party prereq (e.g. WhatsApp's `service-de-waba-integrate`). *(skill: `service-de-channel-create`)*
2. **Configure routing** — sets `SessionHandlerId` to an Omni-Channel Queue (pick existing or create new). Message-type-agnostic. *(skill: `service-de-channel-routing-configure`)*
3. **Configure consent** — ensures a valid `ConsentType` + matching `MsgChannelLanguageKeyword` record (often a **no-op**: the insert auto-seeds `ImplicitOptIn`). Activation's readiness check needs routing AND consent, so this runs before activation. *(skill: `service-de-channel-settings-configure`)*
4. **Activate** — PATCHes `MessagingChannelUsage.DeploymentStatus` to `Provisioning`; the save-hook runs synchronously and returns 204 once the channel is `IsActive=true`. Message-type-agnostic. *(skill: `service-de-channel-activate`)*
5. **Configure requested settings** — only if the request asked for auto-responses, keywords, or session inactivity. Runs **after** activation and is **non-blocking**: a failure is a warning, never a failed run, and every requested setting is reported as configured, not applicable, or failed. *(skill: `service-de-channel-settings-configure`, Stage 4.5)*

**Resume-by-default.** Each step is idempotent: a re-run detects existing state and skips steps that already succeeded.

**Prompt mid-flow.** A missing `{MESSAGE_TYPE}` is asked upfront; routing choices are prompted when step 2 runs.

## Reference File Index

| Reference file | Load when |
| --- | --- |
| `references/inputs.md` | You need the full input field list — MESSAGE_TYPE/ORG_ALIAS plus per-type fields for WhatsApp, LINE, AppleBusinessChat, Facebook, Text (SMS). |
| `references/terms-and-conditions.md` | Rendering the Stage 0.5 disclaimer and certification prompt — verbatim text and per-type label/third-party mappings. |
| `references/output-envelopes.md` | Wiring error handling or parsing the canonical success/failure/terms-declined JSON envelope shapes. |
| `references/partial-success.md` | The orchestrator fails mid-way and you need to render the partial-success/resume report. |
| `references/gotchas.md` | Debugging unexpected behavior — duplicate-key errors, resume/idempotency questions, preflight SOQL shape, unattended/CI usage, dropped settings, missing AuthProvider. |
| `references/requested-settings.md` | Running Stage 4.5 (auto-responses, keywords, inactivity) or rendering requested settings in the Stage 5 report. |
| `references/worked-examples.md` | You need a reference trace (fresh run, resume, Apple dispatch, unsupported type, requested settings) for exact envelope shapes. |

---

## Critical execution rule

**This orchestrator MUST run all stages (0-5) in a SINGLE response without stopping between stages.**

When you invoke a leaf skill (service-de-channel-create, service-de-channel-routing-configure, service-de-channel-settings-configure, service-de-channel-activate) and it returns via function_results:

- **DO:** Parse the return value immediately and run Stages 0.5 → 1 → 2 → 3 → 3.5 → 4 → 4.5 → 5 consecutively in ONE response
- **DO NOT:** Stop, report back, or wait for confirmation between stages, or treat each stage as a separate turn

**Why:** the user asked for an end-to-end activated channel; stopping mid-flow forces them to resume each stage by hand.

**Exception:** Only stop mid-flow if a leaf skill returns `ok: false` with a terminal error (not a recoverable prompt), or if the user declines the Stage 0.5 Terms and Conditions gate (emit `terms-not-accepted` and halt). The WhatsApp OTP prompts in `service-de-channel-activate` are also an allowed pause — wait for the user's input, then continue. Then report the failure immediately with context about which stage failed and what state was reached.

**Stage 0.5 is a required blocking prompt** — never auto-accepted. A decline ends the run; a `yes` continues to Stage 1 in the same response.

**Leaf skill prompts:** leaves like `service-de-waba-integrate` or `service-de-channel-routing-configure` may prompt mid-execution. Once a prompt is answered, CONTINUE to the next stage immediately.

---

## When NOT to use this skill

- **You only want one step, or manual control between stages.** Invoke the leaf skill directly (`service-de-channel-create`, `service-de-channel-routing-configure`, `service-de-channel-settings-configure`, `service-de-channel-activate`).
- **You want a message type outside `WhatsApp` / `Line` / `AppleBusinessChat` / `Facebook` / `Text`.** The dispatcher returns `unsupported-type`.
- **The prereq hasn't been met (WABA not shared, LINE channel not created, Apple account not registered, SMS number not provisioned).** The per-type insert skill surfaces this and returns. (SMS number provisioning isn't checked at insert — it surfaces later as an activation `provisioning-error`.)

## Inputs (from user)

`{MESSAGE_TYPE}` (prompted if omitted) and `{ORG_ALIAS}` (optional), plus type-specific fields for WhatsApp, LINE, AppleBusinessChat, Facebook, and Text (SMS) forwarded to the dispatcher. Optional: `{QUEUE}` (a queue the user named for routing) and `{REQUESTED_SETTINGS}` (auto-responses, keywords, inactivity, consent upgrade — extracted from the request). **Load `references/inputs.md` and follow it** for the full field list, the omitted-type prompt text, and how to extract `{REQUESTED_SETTINGS}`.

## Output (to user)

Three top-level outcomes: success, step-annotated failure, and terms-declined. **Load `references/output-envelopes.md` and follow it** for the exact JSON shapes.

---

## Stage 0: Resolve `{MESSAGE_TYPE}` and type-specific key

If `{MESSAGE_TYPE}` is omitted, prompt the user (see "Inputs" above). Refuse to proceed without one — there's no sensible default.

Once known, determine the **preflight key** used to detect existing state. It's always `MessagingPlatformKey`, but its value varies by type:

| `{MESSAGE_TYPE}` | Preflight key value `{PLATFORM_KEY}` | Notes |
| --- | --- | --- |
| `WhatsApp` | `{PHONE_NUMBER_ID}` | Required upfront |
| `Line` | `{LINE_CHANNEL_ID}` | Required upfront |
| `AppleBusinessChat` | `{APPLE_BC_ID}` | Required upfront |
| `Facebook` | `{PAGE_ID}` | Optional - OAuth → fetch pages → prompt if not provided |
| `Text` | `{SMS_NUMBER}` | Required upfront (the phone number / short code itself) |

For non-Facebook types, validate the required type-specific inputs now; if missing, prompt or halt rather than letting the dispatcher return `missing-input`.

**Capture `{REQUESTED_SETTINGS}` now:** each auto-response, keyword group, inactivity timeout, or consent upgrade in the request is a separate item (mapping in `references/inputs.md`). Also record `{QUEUE}` if the user named one. Every item must be accounted for in the Stage 5 report — none may be silently dropped.

---

## Stage 0.5: Enhanced Messaging Terms and Conditions (blocking gate)

**Run this before any org query or channel work.** Do not skip it or accept on the user's behalf. It runs once per invocation, after `{MESSAGE_TYPE}` is known (the disclaimer names the channel).

**Render the disclaimer and certification prompt from `references/terms-and-conditions.md` (verbatim, substituting the channel label) — load it and follow it for the exact wording and per-type label/third-party mappings.**

**Gate behavior:**

- If the user answers **yes** (affirmative acceptance), record `{TC_ACCEPTED} = true` and continue to Stage 1.
- If the user answers **no**, declines, or does not affirmatively accept, **halt immediately** — do not run Stage 1 or any subsequent stage. Emit:
  ```json
  {"ok": false, "kind": "terms-not-accepted",
   "hint": "user did not accept the Enhanced Messaging Terms and Conditions — channel setup cannot proceed. Re-run when ready to accept."}
  ```
- Acceptance is required on **every** invocation, including resume runs — it isn't persisted.

---

## Stage 1: Pre-flight state detection (resume support)

**Skip this stage entirely if `MESSAGE_TYPE=Facebook` and `{PAGE_ID}` was not provided** — the page isn't known until OAuth, and `service-de-channel-create` runs its own preflight after page selection.

For all other cases, query the org to see how far a prior run got. This enables skip-ahead on resume. **Two queries, not a subquery** — the `MessagingChannelUsages` child relationship is unnameable on some orgs (gotcha #9).

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
| Record exists, `IsActive=true` | `already-active` | If `{REQUESTED_SETTINGS}` is empty: emit the no-op success envelope and return. Otherwise skip insert, route, and activate (add them to `STEPS_SKIPPED`). Run Stage 3.5 if a consent upgrade is requested, else add `consent` to `STEPS_SKIPPED`. Then run Stage 4.5. **Never return a no-op success while requested settings are outstanding.** |

Record the existing `{CHANNEL_ID}` and `{MCU_ID}` if present. Initialize `{STEPS_RUN} = []`, `{STEPS_SKIPPED} = []`, `{T0} = Date.now()` before applying the row above.

**AuthProvider preflight (fresh channels, every type except `Text`).** When `CURRENT_STATE=fresh` (or Stage 1 was skipped for Facebook), confirm the org-global `LiveMessageSetup` AuthProvider exists before starting the insert — every non-Text insert needs it, and so does WhatsApp's WABA-manage call:

```bash
sf data query --target-org '{ORG_ALIAS}' \
  --query "SELECT Id FROM AuthProvider WHERE DeveloperName = 'LiveMessageSetup'" \
  --json > /tmp/hcs-authprovider.json
```

Zero rows → halt with `failedStep: "insert"`, `failedStepIndex: 1`, `kind: "missing-authprovider"`, and render the missing-AuthProvider message from `references/output-envelopes.md`. It's a known manual prerequisite (gotcha #11); catching it here avoids a wasted OAuth round trip or WABA prompt.

---

## Stage 2: Insert the channel (step 1 of 4)

Skip this stage if `CURRENT_STATE` ∈ `{inserted-no-routing, routed-not-active, already-active}` — the channel already exists. Append `"insert"` to `STEPS_SKIPPED` in that case.

Otherwise invoke `service-de-channel-create` with:

- `{MESSAGE_TYPE}` = (from Stage 0)
- All type-specific inputs (forwarded verbatim — dispatcher routes to the right leaf)
- `{ORG_ALIAS}`

`service-de-channel-create` owns the per-type prereqs (WABA linking, LINE token verification, Apple registration).

Handle the envelope:

| Leaf envelope | Orchestrator action |
| --- | --- |
| `{ok: true, channelId, mcuId, ...}` | Record `{CHANNEL_ID}` and `{MCU_ID}`. Append `"insert"` to `STEPS_RUN`. Continue. |
| `{ok: false, kind: "partnership-blocked" \| "user-declined" \| "apple-registration-pending" \| "line-prereq-missing"}` | These come from the per-type prereq stage. Pass through as `failedStep: "insert"`, `failedStepIndex: 1`. Return. |
| `{ok: false, kind: "unified-messaging-required"}` | WhatsApp on a DE Unlimited Access org, which only allows Unified Messaging WhatsApp. Pass through the leaf's `hint` as `failedStep: "insert"` (re-running won't fix it). Return. |
| `{ok: false, kind: "missing-input" \| "unsupported-type"}` | Should have been caught in Stage 0 — emit failure with `failedStep: "insert"` and a note that the caller's inputs were incomplete. |
| `{ok: false, kind: <anything else>}` | Emit failure envelope with `failedStep: "insert"`, `failedStepIndex: 1`. Return. |

**→ Continue immediately to Stage 3 in this same response. DO NOT STOP.**

---

## Stage 3: Configure routing (step 2 of 4)

Skip this stage if `CURRENT_STATE === "routed-not-active"` — routing is already set. Append `"route"` to `STEPS_SKIPPED`.

Otherwise invoke `service-de-channel-routing-configure`:

- `{CHANNEL_ID}` = recorded above
- `{QUEUE}` = the queue the user named, if any (the leaf validates it and only prompts if it's ineligible)
- `{ORG_ALIAS}`

Without a `{QUEUE}`, this step **prompts the user** for queue choice. Don't pre-empt the prompts — forward the answers as-is.

Handle the envelope:

| Leaf envelope | Orchestrator action |
| --- | --- |
| `{ok: true, sessionHandlerId, queueName, ...}` (including `noop: true`) | Record `{SESSION_HANDLER_ID}` and `{QUEUE_NAME}`. Append `"route"` to `STEPS_RUN`. Continue. |
| `{ok: false, kind: "unsupported-routing-type", ...}` | User chose flow/user/asa/aea. Emit partial-success with `failedStep: "route"` and a resume hint pointing at the UI. Return. |
| `{ok: false, kind: "metadata-deploy-failed" \| "patch-failed" \| "verify-failed"}` | Emit failure envelope with `failedStep: "route"`. Return. |

**→ Continue immediately to Stage 3.5 in this same response. DO NOT STOP.**

---

## Stage 3.5: Configure consent (before activation)

Skip if `already-active` with no consent upgrade requested (Stage 1 logged it skipped). A requested upgrade on a live channel runs here — Stage 4.5 never applies consent.

Activation's readiness check requires **consent AND routing** — a fully-routed channel still fails to activate if consent isn't configured. Invoke `service-de-channel-settings-configure`:

- `{CHANNEL_ID}` = recorded above
- `{CONSENT_TYPE}`, `{LANGUAGE}`, and the keyword/prompt values — forward whatever the user supplied; omit what they didn't
- `{ORG_ALIAS}`

Pass **only the `consent` facet** here — consent upgrades and keywords given with a consent type are resolved in this stage; the metadata facets (auto-responses, keywords, inactivity) wait for Stage 4.5 so a metadata-deploy failure can't block activation.

The insert auto-seeds `ImplicitOptIn` plus a default opt-out keyword, so `noop: true` is normal on a fresh channel. The leaf writes only to upgrade (ExplicitOptIn/DoubleOptIn) or override the seeded keywords/prompts, and prompts for missing values.

Handle the envelope:

| Leaf envelope | Orchestrator action |
| --- | --- |
| `{ok: true, ...}` (including `noop: true`) | Append `"consent"` to `STEPS_RUN` (or `STEPS_SKIPPED` if `noop`). Continue. |
| `{ok: false, ...}` (`missing-consent-input`, `not-enhanced`, `channel-patch-failed`, `keyword-record-failed`, `verify-failed`, or anything else) | Emit failure with `failedStep: "consent"`, passing through the leaf's `kind`, message, and `hint` verbatim. Return. |

**→ Continue immediately to Stage 4 in this same response. DO NOT STOP.**

---

## Stage 4: Activate (step 4 of 4)

Skip if `CURRENT_STATE === "already-active"` (Stage 1 already added `"activate"` to `STEPS_SKIPPED`).

Invoke `service-de-channel-activate`:

- `{CHANNEL_ID}` = recorded above
- `{ORG_ALIAS}`

Handle the envelope:

| Leaf envelope | Orchestrator action |
| --- | --- |
| `{ok: true, isActive: true, ...}` (including `noop: true`) | Record results. Append `"activate"` to `STEPS_RUN`. Continue to Stage 4.5. |
| `{ok: false, kind: "no-routing" \| "no-mcu" \| "channel-missing"}` | Unexpected after Stages 2–3 (race or permissions). Emit failure with the leaf's envelope. Return. |
| `{ok: false, kind: "readiness-failed", errorMessage}` | Missing consent (STOP/HELP keyword record) — Stage 3.5 should have caught it. Emit failure; resume hint: re-run `service-de-channel-settings-configure`. Return. |
| `{ok: false, kind: "provisioning-error", errorReason, errorDetails}` | Third-party side rejected (Meta `/register` failed, etc.). MCU is now in `Error`. Emit failure and pass through `errorReason`/`errorDetails`. Return. |
| `{ok: false, kind: "verification-declined" \| "verification-request-failed" \| "verification-failed"}` | WhatsApp OTP verification didn't complete. Emit failure, pass through `errorDetails`/`message`; resume hint: re-run to retry verification. Return. |
| `{ok: false, kind: "auth" \| "transport"}` | REST call failed at the HTTP layer (401 from `sf` auth, 5xx from the instance). Pass through. Return. |

**→ Continue immediately to Stage 4.5 in this same response. DO NOT STOP.**

---

## Stage 4.5: Configure requested settings (non-blocking)

Skip if `{REQUESTED_SETTINGS}` has no auto-response, keyword, or inactivity items. Otherwise invoke `service-de-channel-settings-configure` once with the requested facets and the user's values, then classify each item as `configured`, `notApplicable`, or `failed`. **Never fail the run here** — the channel is already live, so failures become Stage 5 warnings. **Load `references/requested-settings.md` and follow it** for what to forward, per-type applicability, the classification table, and the Facebook metadata defect.

**→ Continue immediately to Stage 5 in this same response. DO NOT STOP.**

---

## Stage 5: Final report

Build the success envelope (`ok`, `messageType`, `channelId`, `mcuId`, `channelName`, `sessionHandlerId`, `queueName`, `isActive`, `stepsRun`, `stepsSkipped`, `settings`, `totalDurationMs = Date.now() - T0`; exact shape in `references/output-envelopes.md`).

Include `settings` only when `{REQUESTED_SETTINGS}` was non-empty. Render to the user as:

```text
Success — {MESSAGE_TYPE} channel '{CHANNEL_NAME}' is live on {ORG_ALIAS}.
   Channel ID: {CHANNEL_ID}
   Routed to: {queueName} ({SESSION_HANDLER_ID})
   Steps: ran {STEPS_RUN.join(", ")}{, skipped " + STEPS_SKIPPED.join(", ") if any}
   Total time: {formatted from durationMs}
```

If any step was skipped due to resume, the report should make that visible. With requested settings, add the "Requested settings" block and the failure warning from `references/requested-settings.md` — every Stage 0 item must land in exactly one bucket.

---

## Partial-success and resume reporting

If the orchestrator fails mid-way, the envelope always includes `stateSoFar` describing what landed. **`stateSoFar` must always carry both `stepsRun` and `stepsSkipped`** (each an array, empty if nothing landed/skipped yet) alongside the fields that landed — the partial-success renderer reads both. **When rendering a failure, load `references/partial-success.md` and follow it** — it has the exact template for showing which steps already landed and how to retry.

---

## Gotchas

Eleven known gotchas (resume semantics, preflight shape, error classification, dropped settings, the `LiveMessageSetup` prerequisite, and more). **When debugging unexpected behavior, load `references/gotchas.md` and follow it.** For reference traces, see `references/worked-examples.md`.
