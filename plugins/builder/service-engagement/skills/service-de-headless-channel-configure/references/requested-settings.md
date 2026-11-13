---
name: service-de-headless-channel-configure-requested-settings
description: "Load when running Stage 4.5 of the headless channel setup orchestrator (the request asked for auto-responses, messaging keywords, or session inactivity) or rendering those settings in the Stage 5 report. Covers what to forward to service-de-channel-settings-configure, per-type applicability, the configured / notApplicable / failed classification, the known Facebook metadata defect, and the report block. DO NOT load for the consent facet, which runs before activation in Stage 3.5."
metadata:
  version: "1.0"
  related-skills: service-de-headless-channel-configure
---

# Requested settings (Stage 4.5 + Stage 5)

## Invoke the settings leaf once

Invoke `service-de-channel-settings-configure` **once**, with:

- `{CHANNEL_ID}`, `{ORG_ALIAS}`
- `{FACETS}` = the requested subset of `auto-responses`, `keywords`, `inactivity`
- the values from the request (response text per `<type>`, `responseTimeoutInMins`, keyword lists,
  timeout minutes). Forward them, and don't invent defaults for values the user didn't give.

The leaf enforces per-type applicability. For the types this orchestrator creates, **the idle and
inactive-session timeouts are MIAW-only**, so they never apply here. Only
`isAgentMessageResetInactivityEnabled` applies, and only on Apple and Facebook. Expect
`facet-not-applicable` for the rest and report it. That's correct behavior, not a failure.

## Classify each requested item

| Leaf outcome for the item | Bucket |
| --- | --- |
| In `facetsConfigured` and verified, or `noop: true` | `configured` |
| `facet-not-applicable` | `notApplicable` (with the leaf's `hint`) |
| `metadata-deploy-failed` / `verify-failed` / any other `ok:false` | `failed` (with the leaf's `kind` + `message` verbatim) |

**Never fail the run here.** The channel is already live. Append `"settings"` to `STEPS_RUN` if
anything was configured, and carry failures to Stage 5 as warnings.

**Facebook:** Facebook channels currently reject real metadata changes with an opaque numeric error
like `(-462367322)` (see `service-de-channel-settings-configure` `references/gotchas.md` #16). Report
it as `failed` with the leaf's hint, and don't retry.

## Stage 5 report block

Add `"settings": {"configured": [...], "notApplicable": [...], "failed": [...]}` to the success
envelope (shape in `references/output-envelopes.md`). Below the standard success lines, render:

```text
   Requested settings:
   - Configured: {each configured item}
   - Not applicable to {MESSAGE_TYPE}: {each item} — {reason}
   - Failed: {each item} — {kind}: {message}
```

If any item is `failed`, lead the report with
`Warning: channel is live, but {N} requested setting(s) were not applied` instead of an unqualified
`Success`, and add the same text to the envelope's `warnings`. **Every item captured in Stage 0 must
appear in exactly one bucket.** Check the count before rendering.
