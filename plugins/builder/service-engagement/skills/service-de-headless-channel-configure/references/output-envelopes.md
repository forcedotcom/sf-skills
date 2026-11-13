---
name: service-de-headless-channel-configure-output-envelopes
description: "Load when you need the canonical JSON envelope shapes this orchestrator emits — success, step-annotated failure, and terms-declined — before wiring error handling or parsing a leaf skill's response. Covers the exact field names (channelId, mcuId, stepsRun, failedStep, resumeHint, etc.) for each of the three top-level outcomes. DO NOT load for the per-stage envelope-handling tables in Stage 2-4, which already reference these shapes."
metadata:
  version: "1.0"
  related-skills: service-de-headless-channel-configure
---

# Output (to user)

**Success:**
```json
{"ok": true, "messageType": "{MESSAGE_TYPE}", "channelId": "0Mj...",
 "mcuId": "0gL...", "channelName": "...", "sessionHandlerId": "00G...",
 "queueName": "...", "isActive": true,
 "stepsRun": ["insert","route","activate"], "stepsSkipped": ["consent"],
 "totalDurationMs": 12345}
```

On a typical fresh run `consent` lands in `stepsSkipped`, not `stepsRun`: the Connect insert
auto-seeds `ConsentType=ImplicitOptIn` + a default opt-out keyword, so the consent leaf no-ops
(`noop: true`) and the orchestrator appends `"consent"` to `stepsSkipped`. It appears in `stepsRun`
only when the caller asked for an upgrade (ExplicitOptIn/DoubleOptIn) or custom keywords, which
triggers a real write.

**Failure** (with step annotation):
```json
{"ok": false, "failedStep": "route", "failedStepIndex": 2, "failedStepTotal": 4,
 "leafEnvelope": { ...whatever the failing leaf skill returned... },
 "stateSoFar": { "channelId": "0Mj...", "mcuId": "0gL...", "isActive": false,
   "stepsRun": ["insert"], "stepsSkipped": [] },
 "resumeHint": "fix the routing issue above, then re-run this skill — step 1 will be skipped automatically"}
```

`stateSoFar` carries only what landed *before* the failure — the failed step itself is NOT in
`stepsRun`, and that step's output fields are absent. In this `failedStep: "route"` example routing
never completed, so `stepsRun` is `["insert"]` and there is no `sessionHandlerId`/`queueName` (Stage 3
records those and appends `"route"` only on a successful routing envelope). `stateSoFar` **always
includes both `stepsRun` and `stepsSkipped`** (each an array, possibly empty) so the renderer can read
either without a guard; here `stepsSkipped` is `[]` because the failure happened before Stage 3.5.
`stepsRun` (the ordered list of *completed* steps) is what the partial-success renderer reads to
report each step's status.
**Consent is the exception:** there is no separate `consentConfigured` flag, but because the insert
auto-seeds `ImplicitOptIn`, a consent-ready channel usually lands `"consent"` in `stepsSkipped`
(no-op), not `stepsRun`. So to answer "is consent configured?", treat *either* list — a `"consent"`
in `stepsRun` OR `stepsSkipped` means consent is activation-ready; only its total absence (a failure
before Stage 3.5) means unconfigured.

**Terms declined** (Stage 0.5 gate — returned before any org work):
```json
{"ok": false, "kind": "terms-not-accepted",
 "hint": "user did not accept the Enhanced Messaging Terms and Conditions — channel setup cannot proceed. Re-run when ready to accept."}
```
