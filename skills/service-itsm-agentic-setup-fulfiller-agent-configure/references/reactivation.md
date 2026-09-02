# Reactivation path — activating an existing inactive IT Service Fulfiller Agent

Split from `references/cli-invocation.md` — this file documents the direct
`BotVersion` activation call used when the Phase-2 classifier reports the agent
already exists but its latest version is `Inactive`. `cli-invocation.md` covers
the create/publish/activate happy path; this file covers "skip create/publish,
just reactivate what's already there".

## When this path fires

`scripts/classify-agent-existence.mjs` (called with the template's
`botDefinitionId` as the PRIMARY idempotency key, the BotDefinition's
`AgentTemplate` — the template's OOTB source id — as the first FALLBACK, and the
collected `DeveloperName` as the last FALLBACK —
see `cli-invocation.md` → "Enumerate the existing agent") returns
`{ exists:true, needsActivation:true, latestVersionId, latestVersionStatus:"Inactive" }`.
That means a `BotDefinition` matching the collected `DeveloperName` (the
Fulfiller's template `botDefinitionId` AND `AgentTemplate` are both null, so the
`DeveloperName` fallback is what matches)
already exists from a prior run of this skill but its most-recent `BotVersion` is
inactive; creating a new bundle would produce a duplicate. Instead, flip the
existing version to `Active`.

## Activate an existing inactive version — `POST /connect/bot-versions/{id}/activation`

```bash
sf api request rest "/services/data/v67.0/connect/bot-versions/<latestVersionId>/activation" \
  --method POST --body '{"status":"Active"}' \
  --target-org <alias> > ${SCRATCH_DIR}/activate-existing.json 2>${SCRATCH_DIR}/activate-existing.err || true
```

`<latestVersionId>` is the captured `latestVersionId` from the Phase-2
classifier output — **not** a bundle version id. This is a direct
`BotVersion` activation toggle that bypasses the NGA bundle pipeline entirely,
because the `BotDefinition`/`BotVersion` records already exist. Skips create
(Phase 4) and publish (Phase 5) — go straight to activate, then verify.

## Verify — same SOQL as the happy path

Run the Phase-7 verify read (see `cli-invocation.md` → "Verify the agent is
live"). Confirm `exists:true` with `count:1` **and**
`latestVersionStatus:"Active"`. If `latestVersionStatus` is still `Inactive`
after a successful activation call, report the discrepancy verbatim — do not
fabricate success.

## Idempotency semantics

| Signal | Verdict |
|--------|---------|
| Neither the template's `botDefinitionId` nor the collected `DeveloperName` matches a live `BotDefinition` — classifier returns `exists:false` | proceed to CREATE |
| Phase-2 classifier returns `exists:true` and `needsActivation:false` (latest version `Active`), matched by `botDefinitionId` or the `DeveloperName` fallback | ALREADY-CREATED (skip create/publish/activate entirely) |
| Phase-2 classifier returns `exists:true` and `needsActivation:true` (latest version `Inactive`), user confirms reactivation, and the bot-version activation call succeeds | ACTIVATED (skip create/publish entirely — direct `BotVersion` activation only) |
| `createBundleWithVersion` → `publish` → `activate` all succeed and Phase-7 classifier (keyed on the publish `publishedBotId`) confirms `exists:true` with `latestVersionStatus:"Active"` | CREATED |

The server-side create path **does** reject a duplicate, but keyed on
`DeveloperName`, not `apiName`: a pre-validation lookup
(`lookupBotDefinitionIdByDeveloperName`) plus a publish-time `BotDefinition`
DeveloperName unique-constraint catch that cleans up the orphaned bundle version.
That guard fires when the `DeveloperName` being created already exists, so it
catches a repeat run of this skill — but only as a hard error. The Phase-2 read
is what makes the repeat graceful: because the Fulfiller is never pre-provisioned
and this skill's create path never stamps `templateName`, the template's
`botDefinitionId` is always `null`, so the read falls back to the collected
`DeveloperName` to detect the existing agent and offer ALREADY-CREATED /
reactivation instead of letting the create call fail with `DUPLICATE_VALUE`.
