# Report Format — Fulfiller Agent Create & Activate

The report layout is generated deterministically by `scripts/render-report.mjs` — the single source of report text for both the chat-turn response and the harness's `${outputDir}/report.md` file, so the two never diverge. Never hand-compose the layout, field placement, stage rows, or next-step wording in prose (authoring standard A9); always shell out to the helper.

## Rendered shape

```text
# Fulfiller Agent — Create & Activate

IT Service Fulfiller Agent Creation (via service-itsm-agentic-setup-fulfiller-agent-configure)

Org:      <org-alias> (API v67.0)
Agent:    <developerName> ("<label>") — NGA-native bundle

Stage 2 — install & activate the agent from its template:

| Stage | Status |
| --- | --- |
| Preflight | Studio hasAccess=<true/false/cannot-confirm>; template agentScript present=<yes/no>; verdict=<READY/NOT-READY/CANNOT-CONFIRM> |
| Enumerate | target agent exists before write=<yes/no>; latest version status=<Active/Inactive/n/a>; verdict=<exists:...> |
| Confirm-to-write | user-confirmed=<true/false/pending> |
| Create bundle | <bundleVersionId=... / ALREADY-CREATED / skipped (reactivation path) / pending confirmation / skipped / FAILED> |
| Publish | <publishedBotId=... / skipped / pending confirmation / FAILED> |
| Activate | <succeeded (created) / succeeded (reactivated existing) / skipped / pending confirmation / FAILED> |
| Verify | <BotDefinition present: yes/no; latest version Active: yes/no / skipped / pending> |

Verdict: CREATED | ALREADY-CREATED | ACTIVATED | PENDING CONFIRMATION | DECLINED | FAILED
Reason:  <plain-language explanation naming the atomicity constraint, the idempotency decision, and any decline/skip reasoning — the caller populates this before invoking the helper, so it can be as rubric-facing as the situation warrants without repeating raw API calls>

Next steps:
  - <helper-generated line keyed off the verdict>
```

The helper enforces a validated verdict set and picks the `Next steps` line from the verdict, so the file never drifts from that shape.

## Checkpoint writes (harness / non-interactive runs)

When `${outputDir}` is provided (via the harness's generated-file location directive), invoke the helper at three checkpoints so a report always exists even when a run parks at a confirmation gate:

1. **Before Phase 3's confirmation gate** — verdict `PENDING CONFIRMATION` with Preflight + Enumerate rows populated; the helper marks Confirm-to-write / Create / Publish / Activate as `pending confirmation` and Verify as `skipped`. On the user's "no" at the gate, re-render with verdict `DECLINED` and a one-line `reason` naming the decline (the helper flips write rows to `skipped`).
2. **After Phase 6 (or the Phase-2b reactivation activation)** — verdict is still not the final verdict yet; the helper is re-invoked with the create-succeeded (or reactivation-succeeded) state and Verify `pending`.
3. **After Phase 8** — verdict `CREATED` / `ALREADY-CREATED` / `ACTIVATED` / `FAILED` with all rows filled in.

Each invocation overwrites `${outputDir}/report.md`, so the last state on disk is always the most complete. Skip these writes when running interactively for a user in a chat surface — write only when `${outputDir}` was passed as an explicit destination.

## Interactive runs

When talking to the user in a chat surface, the assistant may still add turn-side narrative context above or below the helper output (raw command traces, error diagnostics, remediation walkthroughs, "why this is blocking" prose) — the *report* is what the helper emits, the *turn* can be as rich as the situation warrants. Only the report file has the strict shape.
