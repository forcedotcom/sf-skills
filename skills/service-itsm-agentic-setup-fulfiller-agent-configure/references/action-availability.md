# Action-availability preflight + activate-result classification

Each action block in the Fulfiller template's Agent Script is a `source:` / `target:` pair — `source:` is the planner-facing agent-action alias, `target:` is the real invocation URI (`generatePromptResponse://<name>`, `flow://<name>`, `apex://<name>`, or `standardInvocableAction://<name>`). The alias and the target name **routinely differ for the same action** (e.g. `source: …CreateIncidentResolutionSummary` → `target: generatePromptResponse://…IncidentResolutionSummarizationPrompt`; `source: …CreateIncidentRootCauseSummary` → `target: flow://…CreaIncRootCse`, an abbreviated flow API name). `activate` returns **HTTP 200** with `{success:false, messages:[{… "does not exist"}]}` (silent-failure body) when a **`generatePromptResponse://` target** isn't surfaced for the running user by `/actions/custom/generatePromptResponse` (the ITSM Intelligence permset gates exactly those prompt-response actions). Only those targets are checkable here — `flow://`, `apex://`, and `standardInvocableAction://` targets live in other action buckets the endpoint never lists, and the `source:` alias is never itself a `generatePromptResponse` entry, so the gate keys on the **`generatePromptResponse://` target name** and ignores aliases and non-prompt targets (checking either of those false-flagged an alias whose real target was present and blocked a valid activation). Two helpers catch the real gap — one before the write, one after.

## Phase 2c — `scripts/classify-action-availability.mjs`

Called on the **create path only** — after Phase 2 (idempotency) returns `exists:false`, and before Phase 3 (confirm-to-write). An already-existing **Active** agent (ALREADY-CREATED) skips this gate entirely: its actions are already wired, so re-checking availability would wrongly park a no-op run. A reactivation (Phase 2b) relies on the activate-result classifier below rather than this preflight. Reads:
- `/tmp/agent-templates.json` (Phase-1 capture — the decoded template `agentScript` is the source of truth for the referenced `generatePromptResponse://` targets). **The classifier strips the Release Management subagent first (`strip-release-management.mjs`) — the identical strip `build-create-body.mjs` applies — so `generatePromptResponse://svc_itsm_intelligence__SummarizeRelease` is not in the checkable set and never blocks activation. Both scripts must stay in lock-step.**
- `/tmp/generate-prompt-response.json` — a fresh GET of `/services/data/v67.0/actions/custom/generatePromptResponse` (the two response shapes are `{actions:[{name,...}]}` and `{actions:{<name>:{...}}}`; the classifier handles both).

Invocation:

```bash
sf api request rest "/services/data/v67.0/actions/custom/generatePromptResponse" \
  --method GET --target-org <alias> > /tmp/generate-prompt-response.json 2>/tmp/generate-prompt-response.err || true
node "<skill_dir>/scripts/classify-action-availability.mjs" \
  /tmp/agent-templates.json "IT Service Fulfiller" /tmp/generate-prompt-response.json
```

Emits `{ referenced, present, missing, skippedNonPromptTargets, verdict, reasons }` — `referenced` is the `generatePromptResponse://` target set this gate verifies; `skippedNonPromptTargets` is the recorded-but-unchecked `flow://` / `apex://` / `standardInvocableAction://` targets. Branching:

| verdict | Meaning | Caller action |
|---|---|---|
| `READY` | `missing.length === 0` (all `generatePromptResponse://` targets present), or the template references only non-prompt targets (nothing this gate governs) | Continue to Phase 3 (confirm-to-write) |
| `NOT-READY` | ≥1 `generatePromptResponse://` target absent from `generatePromptResponse` | Present under an **"Attention"** heading (never label it "Blocker"); offer permset hand-off (below) — no writes |
| `CANNOT-CONFIRM` | no `target:` URIs parsed at all (unexpected script shape / decode failure) | Surface reasons; proceed with caution — Phase 6 activate-result will catch a silent-failure body |

**Hand-off wording on `NOT-READY`** — present this outcome under an **"Attention"** heading, never the word "Blocker" (it is a resolvable prerequisite gap, not a hard blocker), then raise the `AskUserQuestion`:

> "`missing.length` invocable action(s) referenced by the Fulfiller template are not available on this org for your user (e.g. `<first 3 of missing>`). Run `service-itsm-agentic-setup-itsm-agentforce-permset-assign` to assign the ITSM Intelligence permission set (if installed) or to route you to the content-bundle step (if the package isn't installed)?" (options: **Yes, resolve action availability** / **No, stop here**)

- On **Yes**: delegate to `service-itsm-agentic-setup-itsm-agentforce-permset-assign`, then re-run Phase 2c.
- On **No**: stop and report missing actions verbatim — no writes.

## Phase 2b / Phase 6 — `scripts/classify-activate-result.mjs`

Called on both the create-path activate (`POST /nextgen-authoring/bundle-versions/<id>/activate`) and the reactivation activate (`POST /connect/bot-versions/<id>/activation`). Reads the response body captured to a file. Emits `{ verdict, success, isActivated, messages, reasons }`.

| Body shape | verdict | Handling |
|---|---|---|
| empty stdout | `PASS` | Documented success — fall through to Phase 7 verify |
| `{"success":true, ...}` | `PASS` | Fall through to Phase 7 verify |
| `{"success":false, "messages":[...]}` | `FAIL` | Do NOT report CREATED — surface `messages[]` verbatim; if a message names a missing invocable action, offer the same Phase-2c hand-off (`service-itsm-agentic-setup-itsm-agentforce-permset-assign`) |
| Connect error array `[{errorCode, message}]` | `FAIL` | Surface verbatim and stop |
| Unparseable body | `CANNOT-CONFIRM` | Fall through to Phase 7 SOQL verify — let it decide |

The classifier's "does the message name a missing invocable action" test matches `/does not exist|not found|no such action|invocable action/i`.

## Why both phases exist

Phase 2c catches the failure **before** create+publish+activate — expensive to unwind after the bundle exists. Phase 6/2b is the belt-and-braces: on rare org state changes between Phase 2c and the activate call (permset revoked mid-flow), the activate body is the only surviving signal that Phase 2c's verdict is stale. Never trust HTTP 200 alone on activate.
