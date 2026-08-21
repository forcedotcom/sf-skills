# Reactivation path — activating an existing inactive IT Service Employee Agent

Split from `references/cli-invocation.md` — this file documents the direct
`BotVersion` activation call used when the Phase-2 classifier reports the agent
already exists but its latest version is `Inactive`. `cli-invocation.md` covers
the create/publish/activate happy path; this file covers "skip create/publish,
just reactivate what's already there".

## When this path fires

`scripts/classify-agent-existence.mjs` (called with the template's
`botDefinitionId` as the PRIMARY idempotency key and the collected
`DeveloperName` as the FALLBACK — see `cli-invocation.md` → "Enumerate the
existing agent") returns
`{ exists:true, needsActivation:true, latestVersionId, latestVersionStatus:"Inactive" }`.
That means a `BotDefinition` matching the template (by `botDefinitionId`) or the
collected `DeveloperName` already exists (created on a prior run, or — for the
broad Employee agent — by the platform) but its most-recent `BotVersion` is
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
That guard fires only when the `DeveloperName` being created already exists — so
it catches a repeat run of THIS skill (same collected `developerName`), but it
does **not** catch the pre-provisioned broad Employee agent, whose live
`DeveloperName` (`IT_Service_Employee`) differs from this skill's guess
(`IT_Service_Employee_Agent`). The Phase-2 read closes that gap and upgrades the
outcome from a hard error to a graceful skip: it keys on the template's
`botDefinitionId` (primary — catches the pre-provisioned agent regardless of
name) and falls back to the collected `DeveloperName` (catches a self-created
repeat), so both surface as ALREADY-CREATED / reactivation instead of a
`DUPLICATE_VALUE` from the create call.
