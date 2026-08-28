# CLI invocation reference — service-itsm-agentic-setup-agentforce-studio-configure

This skill uses the **Salesforce CLI (`sf`)** as its only transport. It is
**write-capable**: it reads the *Agentforce for IT Service* Salesforce Go
feature toggles via Connect API (`sf api request rest`), computes a
dependency-ordered enable plan with a Node helper script, and — after explicit
user confirmation — enables each disabled toggle via the same Connect API
route. It extracts no access tokens.

## Why `sf api request rest`, never curl + token

`sf api request rest` authenticates using the CLI's stored session for the
`--target-org` alias — the CLI mints/refreshes the token internally and never
exposes it. **Do not** do:

<!-- skill-validate: ignore -->
```bash
# FORBIDDEN — leaks a bearer token into shell context, bypasses the CLI session
TOKEN=$(sf org display --json -o <alias> | jq -r '.result.accessToken')
curl -X POST -H "Authorization: Bearer $TOKEN" \
  https://.../connect/setup/discovery/feature/sales-cloud-agent-studio/enable
```

Every call this skill makes — read and write — is a plain
`/services/data/v67.0/connect/...` Connect API path, exactly what
`sf api request rest` proxies. There is no reason to fall back to curl.

## The feature toggles and dependency order

| UI toggle | featureApiName | Depends on |
|-----------|----------------|------------|
| Einstein Generative AI | `sales-cloud-einstein-generative-ai` | none |
| Turn on Agentforce Studio | `sales-cloud-agent-studio` | Einstein GenAI |
| Agentforce for IT Service | `service-cloud-agentforce-for-itsm` | Studio, Einstein GenAI |
| IT Service Fulfiller Template | `service-cloud-it-fulfiller-agent` | parent umbrella |
| IT Service Employee Template | `service-cloud-requestor-agent` | parent umbrella |
| Specialized Agent Templates for Employee | `service-cloud-it-service-employee-agent` | parent umbrella |

**Label rule (report output).** Render every toggle by its report label — `Einstein Generative AI`, `Agentforce Studio`, `Agentforce for IT Service`, `IT Service Fulfiller Template`, `IT Service Employee Template`, `Specialized Agent Templates for Employee` — verbatim, and identical across every report and both toggling skills (`-configure` and `-validate`). These match the first-column labels above, except the Studio row: its Go-page toggle reads "Turn on Agentforce Studio", but the rendered report label is simply `Agentforce Studio`. The `Template` suffix on the two agent-template toggles is the authoritative, deliberate report label — it intentionally differs from the shorter setup-page toggle caption (`IT Service Fulfiller` / `IT Service Employee`), the same way the Studio row's caption `Turn on Agentforce Studio` renders simply as `Agentforce Studio`. It marks these as the agent templates enabled at this stage, distinct from the installed agent that the agent-configure skills name `IT Service Fulfiller Agent` / `IT Service Employee Agent` (no `Template`) — do not simplify the report label to the bare caption. Never add an invented role qualifier such as "Requestor", "Specialized", or "parent" to a label. The fulfiller path shows one path-specific row (`IT Service Fulfiller Template`); the employee path shows two (`IT Service Employee Template` **and** `Specialized Agent Templates for Employee`) — never collapse them to a single row or disambiguate them with any other suffix.

Enable order: Einstein GenAI → Studio → parent umbrella → path-specific
template(s). The read response echoes unmet dependencies in
`dependencyStatuses[]`; the classifier encodes this same order in `ORDER` so
the enable loop never attempts a child before its parent.

## Target org, API version, and the `--json` rule

- **Target org**: always `--target-org <alias>` (or `-o <alias>`).
- **API version**: pinned in the URL path (`/services/data/v67.0/...`). Do not
  hand-edit below `metadata.minApiVersion` (`67.0`).
- **`--json`**: do **not** add `--json` to `sf api request rest` — it is
  unsupported on some Connect endpoints and errors; the raw stdout body is
  already JSON.

## Read — feature status

```bash
sf api request rest "/services/data/v67.0/connect/setup/discovery/features/status" \
  --method POST \
  --body '{"featureApiNames":["sales-cloud-einstein-generative-ai","sales-cloud-agent-studio","service-cloud-agentforce-for-itsm","service-cloud-it-fulfiller-agent","service-cloud-requestor-agent","service-cloud-it-service-employee-agent"]}' \
  --target-org <alias> > /tmp/enable-status-before.json 2>/tmp/enable-status-before.err
echo $? > /tmp/enable-status-before.exit
```

Response shape (abridged):

```json
{
  "items": [
    { "apiName": "sales-cloud-einstein-generative-ai", "status": "ENABLED", "enableBlockedReasons": [], "dependencyStatuses": [] },
    { "apiName": "sales-cloud-agent-studio", "status": "NOT_ENABLED", "enableBlockedReasons": [], "dependencyStatuses": [{ "apiName": "sales-cloud-einstein-generative-ai", "status": "ENABLED" }] }
  ]
}
```

- `status: "ENABLED"` ⇒ already on ⇒ skip the write (idempotent).
- `status: "NOT_ENABLED"` with empty `enableBlockedReasons` ⇒ enable-able.
- `status: "NOT_ENABLED"` with non-empty `enableBlockedReasons` ⇒ **do not
  attempt to enable** — report the blocker.
- A confirmed `404`/NOT_FOUND error body ⇒ whole read is CANNOT-CONFIRM (gate
  not wired).
- An empty body (CLI exited non-zero) or an auth/permission/unexpected error
  body ⇒ whole read is ERROR — surface `rawError` and stop.

## Write — enable a feature

```bash
sf api request rest "/services/data/v67.0/connect/setup/discovery/feature/sales-cloud-agent-studio/enable" \
  --method POST \
  --body '{}' \
  --target-org <alias>
```

Replace the path segment with the exact `featureApiName`. The endpoint itself
takes **no meaningful body** — but `sf api request rest --method POST` with no
`--body` flag at all fails with `Error (SfError): No 'mode' found in 'body'
entry` (verified on CLI 2.140.6 and 2.145.6 — this is a CLI-parser quirk, not
version-specific). Always pass `--body '{}'` explicitly. An optional
`solutionApiName` query param can bind the feature to a specific SKU/license
solution (omit for default — not used by this skill).

Response shape:

```json
{ "success": true }
```

`{success:true}` = enabled (or was already enabled). If the response is an
error (e.g. `enableBlockedReasons` still present, missing license, unmet
dependency), record it verbatim and continue to the next toggle in the plan —
do not let one failure block the rest.

Capture every `/enable` response to a file and immediately hand it to
`scripts/record-enable-result.mjs` (below) — do not eyeball the JSON body in
prose to decide ENABLED vs FAILED.

## Re-check before every toggle — never trust one snapshot for the whole loop

A toggle whose dependency is still off at read time carries a non-empty
`enableBlockedReasons` — but that dependency may be enabled by an *earlier*
step in this same loop. If the loop trusts the Phase-1/Phase-2 snapshot for
every toggle, a child that becomes enable-able mid-loop is permanently
written off as blocked. **Re-read `features/status` and re-run
`classify-enable-plan.mjs` immediately before each toggle attempt**, and
branch on that toggle's *current* signal:

- `PASS` → already enabled, skip.
- `FAIL` with empty `enableBlockedReasons` → POST `/enable`, then record the
  result.
- `FAIL` with non-empty `enableBlockedReasons` → still genuinely blocked,
  skip to the next toggle.
- `CANNOT-CONFIRM`/`ERROR` on that specific re-read → stop the loop and
  surface the failure; do not guess.

One failed or blocked toggle does not stop the loop from attempting the
remaining toggles in `order`.

## Enablement is confirm-gated — never a silent write

This skill mutates org state. Before any `/enable` POST, the exact `pending`
list (from the classifier) must be presented to the user via
`AskUserQuestion` and explicitly confirmed. Do not skip this checkpoint even
when the skill was reached via a hand-off from the validate skill's
NOT-READY report — that report names what is off, it does not constitute
confirmation to write.

## The classifier — `scripts/classify-enable-plan.mjs`

The deterministic plan/verdict logic lives in the script, not in the workflow
prose (authoring standard A9). Invoke it with the captured file, the agent
type, and the captured exit status, using the skill's **absolute** directory:

```bash
node "<skill_dir>/scripts/classify-enable-plan.mjs" /tmp/enable-status-before.json <fulfiller|employee> "$(cat /tmp/enable-status-before.exit)"
```

Output (to stdout):

```json
{
  "agentType": "fulfiller | employee",
  "readState": "ok | not-wired | error",
  "features": { "<apiName>": { "status": "ENABLED|NOT_ENABLED|UNKNOWN", "signal": "PASS|FAIL|CANNOT-CONFIRM|ERROR", "enableBlockedReasons": [] } },
  "order": ["<apiName>", "..."],
  "alreadyEnabled": ["<apiName>", "..."],
  "pending": ["<apiName>", "..."],
  "blocked": ["<apiName>", "..."],
  "unconfirmed": ["<apiName>", "..."],
  "verdict": "ALL-ENABLED | NEEDS-ENABLE | CANNOT-CONFIRM | ERROR",
  "reasons": ["..."],
  "rawError": "null | <error snippet>"
}
```

`unconfirmed` lists any required `apiName` that was missing from the response
or carried a status the classifier doesn't recognize — neither confirmed
`ENABLED` nor `NOT_ENABLED`. `verdict` is `NEEDS-ENABLE` whenever `pending` is
non-empty; otherwise `CANNOT-CONFIRM` whenever `unconfirmed` is non-empty; only
`ALL-ENABLED` when both are empty. An empty `pending` alone does **not** mean
every toggle is enabled — always check `unconfirmed` too.

Call the script at least **three times** across the flow: once on the Phase-2
read (before any write) to compute the confirm checkpoint and seed
`alreadyEnabled`; then **once per toggle, immediately before each attempt**,
inside the Phase-4 loop (see re-check rule above); and once more on the
Phase-5 re-read (after the enable loop) to feed `classify-final-report.mjs`.

## Recording each enable attempt — `scripts/record-enable-result.mjs`

Deterministic per-toggle response classifier/accumulator (authoring standard
A9) — call it once per toggle, right after that toggle's `/enable` POST, from
inside the Bash loop:

```bash
node "<skill_dir>/scripts/record-enable-result.mjs" /tmp/enable-<apiName>.json <apiName> /tmp/enable-results.json
```

- `<response.json>` — the raw stdout captured from that toggle's `/enable`
  POST.
- `<apiName>` — the featureApiName just attempted.
- `<results.json>` — an accumulator file read (if present) and rewritten each
  call, keyed by `apiName`.

Emits/writes `{ "<apiName>": { "status": "ENABLED|FAILED", "reason": "null | <snippet>" } }` merged with any prior entries. `success:true` in the response body ⇒ `ENABLED`; any error body, empty body, or unexpected shape ⇒ `FAILED` with the reason captured verbatim. Never left unrecorded — even a malformed response becomes a `FAILED` entry, not a skipped one.

## Final verdict — `scripts/classify-final-report.mjs`

Deterministic final-report aggregator (authoring standard A9) — run once,
after the Phase-5 re-read, combining the Phase-2 plan, the Phase-4 results
accumulator, and the Phase-5 re-classification:

```bash
node "<skill_dir>/scripts/classify-final-report.mjs" /tmp/enable-plan-before.json /tmp/enable-results.json /tmp/enable-plan-after.json
```

Pass `-` for the results arg if Phase 4 never ran (Phase-2 verdict was already
`ALL-ENABLED` or `CANNOT-CONFIRM`/`ERROR`). Output:

```json
{
  "features": { "<apiName>": { "finalStatus": "ALREADY-ENABLED|ENABLED|FAILED|CANNOT-CONFIRM|ERROR", "reason": "..." } },
  "order": ["<apiName>", "..."],
  "overall": "SUCCESS | PARTIAL | FAILED | CANNOT-CONFIRM | ERROR",
  "reasons": ["..."]
}
```

Render `features` and `overall` directly into the Output Format — do not
re-derive the per-feature or aggregate verdict in prose.

## Error taxonomy

- **Auth error / `401 Unauthorized`** — session expired or wrong alias.
  Re-run `sf org login web`; there is no token to refresh by hand.
- **`403 Forbidden`** — the user/org lacks the Agentforce license
  (`accessCheck` gate). Surface verbatim.
- **`404 Not Found`** on `features/status` — the feature-discovery surface is
  not wired on the org tier. The classifier maps a confirmed 404/NOT_FOUND
  error body to CANNOT-CONFIRM.
- **Empty body / unexpected shape** — the classifier maps these to ERROR (not
  CANNOT-CONFIRM): surface `rawError` and stop.
- **`enableBlockedReasons` non-empty** on a toggle — an unmet dependency or a
  purchase/licensing gate; the classifier keeps the toggle out of the enable
  loop (`blocked`) and reports the reason. Do not retry the POST — but do
  re-check on the next loop iteration in case an earlier toggle's `/enable`
  just unblocked it.
- **A required `apiName` missing from the response, or an unrecognized
  `status` string** — neither confirmed `ENABLED` nor `NOT_ENABLED`; the
  classifier lists it in `unconfirmed` and the verdict is `CANNOT-CONFIRM`
  even if `pending` is empty. Never report `ALL-ENABLED`/`SUCCESS` while
  `unconfirmed` is non-empty.

## Gotchas

| Issue | Resolution |
|-------|------------|
| `sf api request rest --json` errors | Don't pass `--json` — the raw stdout body is already JSON |
| `sf api request rest --method POST` with no `--body` flag errors `No 'mode' found in 'body' entry` | The `/enable` endpoint takes no meaningful body, but the CLI still requires the flag — always pass `--body '{}'` explicitly (verified on CLI 2.140.6 and 2.145.6) |
| Bare `./scripts/classify-enable-plan.mjs` "not found" | Use the skill's absolute `<skill_dir>` in the `node` invocation |
| Enabling a child before its dependency | Always enable in the classifier's `order` — Einstein GenAI → Studio → parent → child template(s) |
| Attempting to enable a toggle whose *current* re-checked `enableBlockedReasons` is non-empty | Never — report the reasons instead of POSTing; the write would fail |
| Trusting the Phase-2 `blocked`/`pending` snapshot for the whole Phase-4 loop | Re-read + reclassify immediately before each toggle — a child blocked only because an earlier dependency was off becomes enable-able the instant that dependency's `/enable` succeeds |
| Reporting `ALL-ENABLED`/`SUCCESS` because `pending` is empty | Also check `unconfirmed` — a missing/unrecognized feature status is neither ENABLED nor NOT_ENABLED |
| Re-deriving the per-toggle or final aggregate verdict in prose | Use `record-enable-result.mjs` (per toggle) and `classify-final-report.mjs` (final) — deterministic scripts, not model judgment (authoring standard A9) |
| Skipping the confirm-to-write checkpoint on a hand-off from validate | Never — a NOT-READY report names what is off, it is not user confirmation to write |
| `updateOrgPref` → 500 `Invalid prefName` for an agent pref | Wrong write path — IPCManagement `updateOrgPref` is for IPC Management (Incident/Problem/Change) prefs only. Use `feature/{apiName}/enable` |
| Tempted to token+curl for "just a POST write" | Never — `sf api request rest` handles auth for `/services/data/...` paths |
