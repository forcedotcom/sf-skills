# CLI invocation reference — Create the IT Service Fulfiller Agent

This skill uses the **Salesforce CLI (`sf`)** as its only transport:
`sf api request rest` for the NGA Connect API reads/writes, `sf data query` for the
`BotDefinition` idempotency + verify SOQL, and two Node helper scripts for the
deterministic decisions. It extracts no access tokens.

The agent is created as a **Next-Gen Authoring (NGA) native agent** via the
`/nextgen-authoring/*` Connect API — **not** via the legacy
`/connect/service-itsm/createAgent` route. That legacy route creates a
Setup-page bot that shows an external-link icon in Agentforce Studio and is
also listed on the old Setup > Agentforce Agents page; the NGA bundle pipeline
below produces an agent that is native to Agentforce Studio's Agents list with
no external-link icon, matching the platform's own "IT Service Employee Agent".

## Why `sf api request rest` / `sf data query`, never curl + token

Both commands authenticate using the CLI's stored session for the
`--target-org` alias — the CLI mints/refreshes the token internally and never
exposes it. **Do not** do:

<!-- skill-validate: ignore -->
```bash
# FORBIDDEN — leaks a bearer token into shell context, bypasses the CLI session
TOKEN=$(sf org display --json -o <alias> | jq -r '.result.accessToken')
curl -X POST -H "Authorization: Bearer $TOKEN" .../nextgen-authoring/bundles
```

Every call this skill makes is a plain `/services/data/v67.0/...` Connect API or
`/query` path — exactly what `sf api request rest` and `sf data query` proxy.
There is no reason to fall back to curl.

## Target org, API version, and the `--json` split

- **Target org**: always `--target-org <alias>` (or `-o <alias>`). Resolve the
  alias from the user or the default org (`sf config get target-org`).
- **API version**: pinned in the URL path (`/services/data/v67.0/...`). Do not
  hand-edit it below `metadata.minApiVersion` (`67.0`).
- **`--json` rule** — the two commands differ:
  - `sf api request rest` prints the **raw** Connect response body to stdout;
    do **not** add `--json` (it is unsupported on some Connect endpoints and
    errors). The stdout body is already JSON.
  - `sf data query --json` **does** wrap results in a `{status, result:{records[]}}`
    envelope — that envelope is exactly what `scripts/classify-agent-existence.mjs`
    expects. Always pass `--json` to `sf data query`.

## Thread the collected developerName / label through the create body

The `<developerName>` and `<label>` are collected from the user (defaults
`IT_Service_Fulfiller_Agent` / `IT Service Fulfiller Agent`). The **same**
`<developerName>` must appear in the `createBundleWithVersion` body's outer
`apiName` AND its `resourceContent`'s internal `config.developer_name` —
otherwise the bundle's outer identity diverges from the script's internal
identity. The idempotency and verify reads do **not** key on `<developerName>`:
they query `BotDefinition` by the template's `botDefinitionId` (idempotency) or
the publish response's `publishedBotId` (verify) — see the Enumerate/Verify
sections below for why an Id-keyed read is the only reliable guard.

## The source content — the legacy template's `agentScript` field

The legacy `agent-templates` read (still used, read-only) returns each
template's full **Agent Script** (AFScript) in an `agentScript` field,
HTML-entity-encoded (sometimes double-encoded). This is the SAME content
format an NGA bundle version's `resourceContent` expects — there is no
separate "NGA template catalog" endpoint; the fix simply routes this existing
read's content into the NGA bundle pipeline instead of the legacy
`createAgent` call.

```text
GET /services/data/v67.0/connect/service-itsm/agent-templates?agentType=AgentforceEmployeeAgent
```

Response: `{data:[{id, masterLabel, agentScript, isInstalled, isActivated, botDefinitionId, ...}]}`.
The classifier (`scripts/classify-preflight.mjs`) finds the item whose
`masterLabel` matches `"IT Service Fulfiller"` and confirms `agentScript` is a
non-empty string. `scripts/build-create-body.mjs` re-reads the same captured
file, re-locates the match, and does the actual decode + substitution (see
below) — the classifier only confirms presence, it does not re-emit the ~70KB
script content on stdout.

## The NGA Connect API

All three calls live under `/nextgen-authoring/`, owning team **Agentforce
Platform**. Org access check: `NextGenAuthoring.orgHasNextGenAgentAuthoringEnabled
&& NextGenAuthoring.userCanAccessNextGenAgentAuthoring`. User access check:
`NextGenAuthoring.userCanAccessAuthoringBundle` (create) /
`NextGenAuthoring.userCanEditAuthoringBundle` (publish/activate).

| Route | Method | Purpose |
|-------|--------|---------|
| `/services/data/v67.0/nextgen-authoring/bundles` | POST | `createBundleWithVersion` — create the bundle + its first DRAFT version from an Agent Script |
| `/services/data/v67.0/nextgen-authoring/bundle-versions/{bundleVersionId}/publish` | POST | `publishBundleVersion` — publish the version, creating the underlying `BotDefinition`/`BotVersion` |
| `/services/data/v67.0/nextgen-authoring/bundle-versions/{bundleVersionId}/activate` | POST | `activateBundleVersion` — activate the published version |
| `/services/data/v67.0/nextgen-authoring/bundles` | GET | List bundles (optional post-hoc check for `isLegacy:false`) |

> **The legacy `createAgent` / `create-agents` / `activate-agents` routes under
> `/connect/service-itsm/` are NOT part of this flow.** They create a
> Setup-page bot with an external-link icon in Agentforce Studio — the wrong
> kind of agent. Do not fall back to them even on an NGA-route error; surface
> the error and stop instead.

## Preflight — Studio access + template's Agent Script presence (one classifier)

Capture both reads, then let `scripts/classify-preflight.mjs` make the
deterministic decisions (do not read `hasAccess` or search `data[]` in prose — A9):

```bash
sf api request rest "/services/data/v67.0/agentforce-studio/access/Agents" \
  --method GET --target-org <alias> > ${SCRATCH_DIR}/studio-access.json 2>${SCRATCH_DIR}/studio-access.err || true
sf api request rest "/services/data/v67.0/connect/service-itsm/agent-templates?agentType=AgentforceEmployeeAgent" \
  --method GET --target-org <alias> > ${SCRATCH_DIR}/agent-templates.json 2>${SCRATCH_DIR}/agent-templates.err || true
node "<skill_dir>/scripts/classify-preflight.mjs" ${SCRATCH_DIR}/studio-access.json ${SCRATCH_DIR}/agent-templates.json "IT Service Fulfiller"
```

**Studio access** body: `{ "hasAccess": true, "productName": "Agents" }`. The
classifier maps `hasAccess=true`→PASS, `false`→FAIL (offer the hand-off to
`service-itsm-agentic-setup-agentforce-studio-validate`), a **confirmed** `404`
(gate not wired, expected on scratch orgs)→CANNOT-CONFIRM (does not block — a
successful create/publish/activate is authoritative), and any other parseable
error body (`401`/`403`/unexpected)→**ERROR** (surface the raw response and
stop — do not treat an auth/permission failure as an unwired gate). The
product in the path must be `Agents` (any other value ⇒ `400 Invalid product name`).

**agent-templates**: the `agentType` query param is **required** — omitting it
returns `400 MISSING_ARGUMENT: agentType`; the value is `AgentforceEmployeeAgent`
(a wrong value returns an empty `data[]`). The classifier finds the item whose
`masterLabel` matches the label arg ("IT Service Fulfiller") and confirms its
`agentScript` field is a non-empty string — that field, not `id`, is what
Phase 4 consumes. Empty/no-match `data[]` ⇒ `template.signal=FAIL`; a `404` ⇒
CANNOT-CONFIRM — hand off to the readiness check; a match with no/empty
`agentScript` ⇒ CANNOT-CONFIRM (nothing to build the NGA bundle from).

Classifier output:

```json
{
  "studio":   { "hasAccess": true, "signal": "PASS|FAIL|CANNOT-CONFIRM|ERROR", "reason": "..." },
  "template": { "present": true, "id": "svc_itsm_intelligence__ITSrvcMgmtFulfiller", "hasAgentScript": true, "botDefinitionId": "0Xx...", "signal": "PASS|FAIL|CANNOT-CONFIRM", "reason": "..." },
  "verdict": "READY | NOT-READY | CANNOT-CONFIRM | ERROR",
  "reasons": ["..."]
}
```

`template.botDefinitionId` is copied from the matched `agent-templates` row. **`botDefinitionId` is the PRIMARY Phase-2 idempotency key**, but the Fulfiller is never pre-provisioned and this skill's create path never stamps `templateName`, so its template `botDefinitionId` is `null` on every run — the collected `<developerName>` is therefore the guard that actually protects repeat runs. Carry `<developerName>` into the Phase-2 read as the fallback key. (`isInstalled`/`isActivated` are no longer emitted: they ride the same AgentTemplate join as `botDefinitionId`, so they read false for self-created agents and nothing consumes them.)

`verdict=ERROR` (`studio.signal="ERROR"` — a parseable non-404 Studio-access
error, e.g. `401`/`403`) ⇒ surface the raw error and stop; takes priority over
template state so a present template cannot outrun a failed prerequisite read.
`verdict=NOT-READY` (studio FAIL or template FAIL) ⇒ hand off / stop.
`verdict=READY` ⇒ proceed to Phase 2. It exits `0` on usable args.

## Enumerate the existing agent — SOQL on `BotDefinition` BY Id (falling back to DeveloperName)

Idempotency is keyed **PRIMARILY** on the template's `botDefinitionId` (from the
Phase-1 row) and **FALLS BACK** to the collected `<developerName>`. If the
Fulfiller agent already exists under a `DeveloperName` that differs from this
skill's default guess `IT_Service_Fulfiller_Agent`, a name-only read
false-negatives (`exists:false`) and the create then collides on `apiName` with
`DUPLICATE_VALUE`. `botDefinitionId` is the platform's authoritative link from
the template to the `BotDefinition` it was instantiated into — but it is
back-filled onto the template row **only** for pre-provisioned agents, and the
Fulfiller is never pre-provisioned: this skill's create path never stamps
`templateName`, so its template `botDefinitionId` stays `null` on the first run
and every run after. The `DeveloperName`-keyed fallback is therefore the guard
that actually protects repeat runs here — never short-circuit straight to create
when `botDefinitionId` is absent.

- **`botDefinitionId` empty/null** (the normal Fulfiller case — template row
  never joined) ⇒ fall back to a DeveloperName-keyed read and let the classifier
  match on it:
  ```bash
  sf data query -q "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE DeveloperName='<developerName>'" \
    --target-org <alias> --json > ${SCRATCH_DIR}/bot-existing.json 2>${SCRATCH_DIR}/bot-existing.err || true
  node "<skill_dir>/scripts/classify-agent-existence.mjs" ${SCRATCH_DIR}/bot-existing.json "" "<developerName>"
  ```
- **`botDefinitionId` present** (a pre-provisioned instantiation, if any — never
  the normal Fulfiller case) ⇒ read the `BotDefinition` by Id **`OR` by the
  collected `<developerName>`** in one query, then classify. The `OR DeveloperName=`
  clause catches a **dangling** link — a `botDefinitionId` whose target row was
  since deleted: the by-Id half returns nothing, the live same-name agent still
  surfaces, and the classifier falls back to it (`matchedBy:"developerName"`)
  rather than concluding `exists:false` and colliding with `DUPLICATE_VALUE`:
  ```bash
  sf data query -q "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE Id='<botDefinitionId>' OR DeveloperName='<developerName>'" \
    --target-org <alias> --json > ${SCRATCH_DIR}/bot-existing.json 2>${SCRATCH_DIR}/bot-existing.err || true
  node "<skill_dir>/scripts/classify-agent-existence.mjs" ${SCRATCH_DIR}/bot-existing.json "<botDefinitionId>" "<developerName>"
  ```

Only when **both** `botDefinitionId` and `<developerName>` are absent does the
classifier return `exists:false` without reading a query file — in practice the
collected `<developerName>` is always present, so the fallback read always runs.

The `BotVersions` subquery (child relationship on `BotDefinition`) is what lets
the classifier see the latest version's `Status` — omit it and
`latestVersionStatus`/`needsActivation` come back `null`/`false` even when the
existing agent is actually inactive. The classifier prints
`{ exists, count, matchedBy, agentId, botDefinitionId, developerName, latestVersionId, latestVersionStatus, needsActivation }`
(`matchedBy` is `"botDefinitionId"` | `"developerName"` | `null`; `developerName`
is the ACTUAL live agent's DeveloperName read from the record — surface it in the
report instead of the collected guess):
- `exists:false` ⇒ proceed to create.
- `exists:true` and `needsActivation:false` (latest version `Active`) ⇒
  **ALREADY-CREATED** (skip the entire create/publish/activate sequence).
- `exists:true` and `needsActivation:true` (latest version `Inactive`) ⇒ do
  **not** create a duplicate — take the reactivation path documented in
  `references/reactivation.md` (direct `BotVersion` activation, skips
  create + publish).
- **Exit 3** ⇒ the query itself failed (auth error, malformed SOQL) — surface
  the raw CLI error and stop; do **not** assume the agent is absent.

Any existing-agent hit here is a `matchedBy:"developerName"` fallback (the
Fulfiller's template `botDefinitionId` is always `null`), so Phase 7 verifies the
agent using the classifier's returned live `agentId` / `botDefinitionId` — the
actual matched `BotDefinition.Id` — **never** the Phase-1 template
`botDefinitionId`, so the verify read never degrades to `WHERE Id=''` and never
false-fails after a successful skip or reactivation.

Use the skill's **absolute** `<skill_dir>` in the `node` invocation — a bare
`./scripts/...` resolves against the shell CWD, not the skill dir.

## Create the NGA bundle — `createBundleWithVersion`

```bash
node "<skill_dir>/scripts/build-create-body.mjs" ${SCRATCH_DIR}/agent-templates.json "IT Service Fulfiller" "<developerName>" "<label>" ${SCRATCH_DIR}/create-bundle-body.json
sf api request rest "/services/data/v67.0/nextgen-authoring/bundles" \
  --method POST \
  --body @${SCRATCH_DIR}/create-bundle-body.json \
  --target-org <alias> > ${SCRATCH_DIR}/create-bundle.json 2>${SCRATCH_DIR}/create-bundle.err || true
```

`build-create-body.mjs` re-reads `${SCRATCH_DIR}/agent-templates.json` (the SAME file
captured in Phase 1), re-locates the item whose `masterLabel` matches
`"IT Service Fulfiller"`, and:
1. Fully HTML-decodes its `agentScript` — named entities (`&amp;`, `&quot;`,
   `&#39;`, `&lt;`, `&gt;`) AND numeric entities (`&#(\d+);` →
   `String.fromCharCode`), applied in a loop (up to 4 passes) to fully unwind
   double-encoding. A naive single-pass decode leaves artifacts (e.g.
   `&amp;quot;`, an undecoded `&#92;` for a literal backslash) that break
   AFScript parsing.
2. Substitutes the script's `config.developer_name` / `config.agent_label`
   with the collected `<developerName>` / `<label>` via a regex replace on the
   `developer_name: "..."` / `agent_label: "..."` lines. If either
   substitution doesn't land (pattern not found), the script exits 3 rather
   than silently building a body with the wrong internal identity.
3. Writes `{ apiName: <developerName>, label: <label>, assets: [{ resourceName:
   "agentDefinition", resourceType: "agentDefinition", sections: [],
   resourceContent: <decoded+substituted script> }] }` to the output path.

Response on success — a bundle-version detail:

```json
{
  "apiName": "IT_Service_Fulfiller_Agent",
  "label": "IT Service Fulfiller Agent",
  "bundleId": "1bY...",
  "id": "1bZ...",
  "versionStatus": "DRAFT",
  "assets": [ { "resourceName": "agentDefinition", "resourceType": "agentDefinition", "resourceContent": "...", "sections": [] } ],
  "publishedBotId": null,
  "publishedBotVersionId": null
}
```

**Capture `id` — that is the `bundleVersionId`** used in the publish/activate
calls below. `bundleId` is the bundle's own Id, not the version's; passing it
to `/bundle-versions/{...}` returns a 404.

Common errors:

| HTTP | Error code | Meaning | Action |
|------|-----------|---------|--------|
| 403 / 404 | `FUNCTIONALITY_NOT_ENABLED` / not found | NGA authoring namespace not provisioned on the org | Trigger the Phase-1 hand-off — `AskUserQuestion` → on Yes delegate to `service-itsm-agentic-setup-agentforce-studio-validate` |
| (script exit 3) | — | `build-create-body.mjs` couldn't find the template / its `agentScript` / couldn't substitute developer_name or agent_label in `${SCRATCH_DIR}/agent-templates.json` | Surface the script's stderr verbatim; re-verify Phase 1's `template.hasAgentScript:true` rather than hand-typing a body |

## Publish the bundle version — `publishBundleVersion`

```bash
sf api request rest "/services/data/v67.0/nextgen-authoring/bundle-versions/<bundleVersionId>/publish" \
  --method POST --body '{}' \
  --target-org <alias> > ${SCRATCH_DIR}/publish-bundle.json 2>${SCRATCH_DIR}/publish-bundle.err || true
```

Path param only — the body is ignored by the endpoint but `--body '{}'` is
still required (see Gotchas). Response on success:

```json
{ "lastPublishedOn": "2026-08-05T01:22:54.278Z", "publishedBotId": "0Xx...", "publishedBotVersionId": "0X9..." }
```

This is the call that creates the underlying `BotDefinition`/`BotVersion`. An
error here means the DRAFT version failed platform-side validation.

## Activate the bundle version — `activateBundleVersion`

```bash
sf api request rest "/services/data/v67.0/nextgen-authoring/bundle-versions/<bundleVersionId>/activate" \
  --method POST --body '{}' \
  --target-org <alias> > ${SCRATCH_DIR}/activate-bundle.json 2>${SCRATCH_DIR}/activate-bundle.err || true
```

Success returns an **empty response body** (`EmptyRepresentation`) — do not
treat empty stdout as a failure signal. Check the CLI exit code, then confirm
success via the Phase-7 `BotDefinition`/`BotVersion` verify read, not by
parsing this call's output.

## Verify the agent is live — SOQL on `BotDefinition` BY Id

```bash
sf data query -q "SELECT Id,DeveloperName,MasterLabel,(SELECT Id,Status FROM BotVersions ORDER BY VersionNumber DESC LIMIT 1) FROM BotDefinition WHERE Id='<verifyId>'" \
  --target-org <alias> --json > ${SCRATCH_DIR}/bot-verify.json 2>${SCRATCH_DIR}/bot-verify.err || true
node "<skill_dir>/scripts/classify-agent-existence.mjs" ${SCRATCH_DIR}/bot-verify.json "<verifyId>"
```

The verify `<verifyId>` is the create path's **`publishedBotId`** (captured from
the Phase-5 publish response) or, on the ALREADY-CREATED / reactivation path, the
**live matched Id the Phase-2 classifier returned** (its `botDefinitionId` /
`agentId` output — the actual `BotDefinition.Id` of the matched record) — **not**
the Phase-1 template `botDefinitionId`, which is always `null` for the Fulfiller,
so on any existing-agent hit (always a `matchedBy:"developerName"` fallback)
using it would run the verify as `WHERE Id=''` and falsely report failure after a
successful skip/activation. Never the collected `<developerName>`.
Confirm `exists:true` with `count:1`, and — whether the create or the
reactivation path was taken — `latestVersionStatus:"Active"`. `exists:false`
after a successful activate ⇒ report the discrepancy verbatim, do not fabricate
success. Optionally cross-check
`GET /services/data/v67.0/nextgen-authoring/bundles` for an entry with
`apiName=<developerName>` and `isLegacy:false` — this is the same shape as the
platform's own "IT Service Employee Agent" entry and confirms the created
agent is NGA-native (no external-link icon in Agentforce Studio).

## Idempotency semantics

The full `ALREADY-CREATED` / `ACTIVATED` / `CREATED` verdict table (Phase-2
classifier signal → verdict) — plus the note on how the Phase-2 SOQL read turns
the server's `DeveloperName`-keyed duplicate rejection into a graceful skip —
lives in `references/reactivation.md`.

## Errors and gotchas

The response-body error codes each phase can return (auth,
`FUNCTIONALITY_NOT_ENABLED`, missing `agentType`, build-script exit codes,
empty-response semantics) and the recurring foot-guns (legacy-`createAgent`,
`--body '{}'`, `bundleId` vs `bundleVersionId`, multi-pass HTML decode,
threading the collected `<developerName>`, token+curl, …) live in
`references/error-taxonomy.md`.
