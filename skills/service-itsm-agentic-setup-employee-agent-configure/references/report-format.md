# Report Format — Employee Agent Create & Activate

The report layout is generated deterministically by `scripts/render-report.mjs` — the single source of report text for both the chat-turn response and the harness's `${outputDir}/report.md` file, so the two never diverge. Never hand-compose the layout, field placement, stage rows, or next-step wording in prose (authoring standard A9); always shell out to the helper.

## Rendered shape

The helper reads a phase-state JSON and emits a report in this exact shape:

```text
# Employee Agent — Create & Activate

IT Service Employee Agent Creation (via service-itsm-agentic-setup-employee-agent-configure)

Org:      <org-alias> (API v67.0)
Template: <resolvedMasterLabel> (id=<resolvedId>) — <broad umbrella|specialized>
Source:   <resolvedId> Agent Script
Agent:    <developerName> ("<label>") — NGA-native bundle

  Preflight  ......................... Studio hasAccess=<true|false|cannot-confirm>; template agentScript present=<yes|no>
  Enumerate  ......................... target agent exists before write=<yes|no>; latest version status=<Active|Inactive|n/a>
  Confirm-to-write ................... user-confirmed=<true|false|pending>
  Create bundle ...................... <bundleVersionId=... | ALREADY-CREATED | skipped (reactivation path) | pending confirmation | FAILED>
  Publish ............................ <publishedBotId=... | skipped | pending confirmation | FAILED>
  Activate ........................... <succeeded (created) | succeeded (reactivated existing) | skipped | pending confirmation | FAILED>
  Verify ............................. <BotDefinition present: yes|no; latest version Active: yes|no | skipped>

Verdict: CREATED | ALREADY-CREATED | ACTIVATED | PENDING CONFIRMATION | DECLINED | FAILED
Reason:  <plain-language explanation naming the atomicity constraint, the idempotency decision, and any decline/skip reasoning — the caller populates this before invoking the helper, so it can be as rubric-facing as the situation warrants without repeating raw API calls>

Next steps:
  - <helper-emitted next-step line for the emitted verdict>
```

## Report-state JSON schema (input to `render-report.mjs`)

The caller writes `${SCRATCH_DIR}/report-state.json` and passes it as the first arg:

```json
{
  "org": "<alias>",
  "template": {"masterLabel": "...", "id": "...", "kind": "broad umbrella"|"specialized"},
  "developerName": "...",
  "label": "...",
  "preflight": {"studioHasAccess": true|false|"cannot-confirm", "templateAgentScriptPresent": true|false},
  "enumerate": {"existsBeforeWrite": true|false, "latestVersionStatus": "Active"|"Inactive"|"n/a"},
  "confirmToWrite": "true"|"false"|"pending",
  "verdict": "CREATED"|"ALREADY-CREATED"|"ACTIVATED"|"PENDING CONFIRMATION"|"DECLINED"|"FAILED",
  "reason": "..."
}
```

The helper enforces a validated verdict set and picks the `Next steps` line from the verdict, so the file never drifts from that shape.

## Checkpoint writes (harness / non-interactive runs)

When `${outputDir}` is provided (via the harness's generated-file location directive), write the helper output to `${outputDir}/report.md` at three checkpoints so it always exists even when a run parks at a confirmation gate:

1. **After Phase 2** — render with `verdict:"PENDING CONFIRMATION"` (create path) or the applicable ALREADY-CREATED / needsActivation state.
2. **After Phase 6 (or Phase 2b activation)** — re-render with the create-succeeded (or reactivation-succeeded) state; leave `verify` as `pending`.
3. **After Phase 8** — re-render with the final verdict (CREATED / ALREADY-CREATED / ACTIVATED / DECLINED / FAILED).

Each write overwrites the same file, so the last state on disk is always the most complete. The helper produces a ~30-line report — do NOT append extra sections (raw HTTP commands, full JSON bodies, per-phase narratives, remediation walkthroughs, session notes) to the report file; those belong in the assistant's turn-side response only.

## Interactive runs

Skip these writes when running interactively for a user in a chat surface — write only when `${outputDir}` was passed as an explicit destination. In chat, the assistant may add turn-side narrative context above or below the helper output (raw command traces, error diagnostics, remediation walkthroughs) — the *report* is what the helper emits, the *turn* can be as rich as the situation warrants.
