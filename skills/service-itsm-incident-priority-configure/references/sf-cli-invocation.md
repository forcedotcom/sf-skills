# sf CLI invocation reference — service-itsm-incident-priority-configure

This skill invokes every read and write through the **`sf` CLI**. Two transports are used:

- `sf api request rest` — direct authenticated REST call against the org.
- `sf data query --use-tooling-api` / `sf data delete record --use-tooling-api` — Tooling API convenience wrappers with better parsing than raw REST.
- `sf project retrieve start` + `sf project deploy start` — for the `StandardValueSet` metadata that carries the default fallback priority.

Every invocation below was verified 200 (or `Succeeded` for the metadata deploy) against `orgfarm-afdcaf38b6` on 2026-08-04. Path prefixes are load-bearing; do not strip `/services/data/v67.0/` or `/services/data/v67.0/tooling/`.

## Authentication

`sf` mints the bearer token from the CLI's authenticated org — the skill never handles tokens. Confirm the target org first:

```bash
sf org list
sf org display --target-org <alias>
```

If the org is not `Connected`, run `sf org login web --alias <alias>` (or the JWT equivalent) and re-verify. Every command below takes `--target-org <alias>`.

## Response envelope

`sf api request rest` outputs the raw HTTP body (append `--include` to see the status line + headers). Tooling REST GETs return standard `{records: [...], size: N, totalSize: N, done: true, ...}`. PATCH on the two Setup Connect API prefs returns `{"isPreferenceEnabled": <bool>}` — the new state is echoed, so no re-read is needed.

`sf data query` normalizes Tooling SOQL results into a table by default; add `--json` for a machine-parseable envelope.

---

## Routes

### 1. Preflight — Incident describe (`sf api request rest`)

```bash
sf api request rest \
  "/services/data/v67.0/sobjects/Incident/describe" \
  --method GET \
  --target-org <alias>
```

**Expected:** HTTP 200. Body carries the entity schema. Extract active picklist values for `Impact`, `Urgency`, `Priority` from the `fields[]` array — each field has `picklistValues[]` and each entry has `value` (API name), `label`, and `active` (only `true` counts). Use `value`, not `label` — customers rename labels but the server stores API values.

If the describe response is very large (>1MB), dispatch a subagent (haiku tier) to pull just the three picklists.

If the response is a `404 NOT_FOUND`, Incident Management is not enabled on the org. Direct the user to enable it first (use the `service-itsm-incident-mgmt-configure` skill).

### 2. Matrix enable flag — `IncPriorityMatrixEnabled`

**Read:**

```bash
sf api request rest \
  "/services/data/v67.0/setup/org/preferences/IncPriorityMatrixEnabled" \
  --method GET \
  --target-org <alias>
```

Response: `{"isPreferenceEnabled": <bool>}` — 200.

**Write:**

```bash
sf api request rest \
  "/services/data/v67.0/setup/org/preferences/IncPriorityMatrixEnabled" \
  --method PATCH \
  --header "Content-Type:application/json" \
  --body '{"desiredState": true}' \
  --target-org <alias>
# use '{"desiredState": false}' to disable
```

Response: `{"isPreferenceEnabled": <bool>}` — 200. **The response echoes the new state**, so no re-read is required.

Disabling stops the server from deriving Priority on future Incident writes. Matrix rows and the default priority are **not** cleared; re-enabling restores derivation instantly. Existing Incidents keep their stamped priority.

### 3. Manual override — `IncPriorityOverrideEnabled`

Same shape as `IncPriorityMatrixEnabled` — same URL path except the pref name changes. Read/write via `sf api request rest`, same body shape, same response.

The override flag controls whether users can override the derived priority on an individual Incident record. Flipping it does **not** touch matrix rows or the default priority.

### 4. Matrix rows — read

```bash
sf data query \
  --use-tooling-api \
  --target-org <alias> \
  --query "SELECT Id, DeveloperName, ReferenceObject, Urgency, Impact, Priority FROM ServiceOpPriorityConfig WHERE ReferenceObject = 'Incident'"
```

Zero to `|Impact| × |Urgency|` rows returned. Row keys are PascalCase (`Id`, `DeveloperName`, `ReferenceObject`, `Urgency`, `Impact`, `Priority`) — these are Tooling SObject field names, not the lowercase JSON keys the Aura controller used. `DeveloperName` is included so the add step can derive a fresh unique suffix from existing rows.

For programmatic scripts, add `--json` and parse `result.records[]`.

### 5. Matrix rows — add

```bash
sf api request rest \
  "/services/data/v67.0/tooling/sobjects/ServiceOpPriorityConfig" \
  --method POST \
  --header "Content-Type:application/json" \
  --body '{"ReferenceObject": "Incident", "Urgency": "<one of the fetched Urgency values>", "Impact": "<one of the fetched Impact values>", "Priority": "<one of the fetched Priority values>", "DeveloperName": "ServiceOpPriorityConfigIncident<unique-suffix>", "MasterLabel": "ServiceOpPriorityConfigIncident<same-suffix>"}' \
  --target-org <alias>
```

Pass the body inline with `--body '{...}'`. `sf api request rest` accepts either inline JSON or `--body @file`; inline keeps the payload in the skill's control and avoids writing to a path outside the project.

Response: `{"id": "<Id>", "success": true, "errors": [], "warnings": [], "infos": []}` — 201.

Suffix pattern: pattern-match the existing rows' `DeveloperName` values from the Phase-2 read and pick a fresh integer that isn't already used. `DeveloperName` uniqueness is enforced by the Tooling API.

**Important:** The Tooling REST endpoint does NOT enforce picklist validation on `Urgency`, `Impact`, `Priority`. Garbage values are accepted at the wire level but the runtime matrix evaluator refuses to use them. Validate every value against the Phase-1 picklist values before dispatch.

**Duplicates:** the server does NOT enforce `(ReferenceObject, Urgency, Impact)` uniqueness — a second POST on the same coordinate is accepted as a separate row (verified 2026-08-04 on `itsm-eval-org`: two rows with identical `(Incident, Medium, High)` both persisted with distinct `Id`s). Client-side dedup against the Phase-2 snapshot is the ONLY guard against duplicate matrix cells; if you skip it, the runtime picks one of the duplicates non-deterministically.

**ReferenceObject:** the server accepts any string for `ReferenceObject` (verified: a `Problem` row inserted successfully). `ServiceOpPriorityConfig` is the shared SObject for Incident / Problem / ChangeRequest matrices. Scope to `Incident` is skill-enforced only — refuse any other value client-side.

### 6. Matrix rows — change

```bash
sf api request rest \
  "/services/data/v67.0/tooling/sobjects/ServiceOpPriorityConfig/<Id>" \
  --method PATCH \
  --header "Content-Type:application/json" \
  --body '{"Priority": "<new value>"}' \
  --target-org <alias>
```

Response: 204 No Content. Look up `<Id>` from the Phase-2 SOQL results by matching `(ReferenceObject=Incident, Urgency, Impact)`.

**Duplicate coordinates:** if more than one Phase-2 row matches the coordinate (the server does not enforce uniqueness), do NOT dispatch the PATCH — the choice of `<Id>` would be non-deterministic. Report all matching rows (`Id`, `DeveloperName`, current `Priority`) and require the user to name the exact `Id` to change or approve a consolidation plan (delete the extras, then change the survivor).

Validate the new Priority against the Phase-1 picklist values.

### 7. Matrix rows — remove

```bash
sf data delete record \
  --sobject ServiceOpPriorityConfig \
  --record-id <Id> \
  --use-tooling-api \
  --target-org <alias>
```

Response: `Successfully deleted record: <Id>`. Look up `<Id>` from the Phase-2 SOQL results by matching `(ReferenceObject=Incident, Urgency, Impact)`.

**Duplicate coordinates:** if more than one Phase-2 row matches the coordinate, do NOT dispatch — deleting an arbitrary duplicate leaves the matrix non-deterministic. Report all matching rows (`Id`, `DeveloperName`, current `Priority`) and require the user to name the exact `Id`(s) to delete or explicitly confirm "delete all rows at this coordinate".

**Note:** `sf api request rest ... --method DELETE` on a Tooling SObject currently fails with `SfError: No 'mode' found in 'body' entry` in `sf` CLI 2.143. Use `sf data delete record` instead.

### 8. Default fallback priority — read

```bash
sf api request rest \
  "/services/data/v67.0/tooling/query/?q=SELECT+Id,MasterLabel,Metadata+FROM+StandardValueSet+WHERE+MasterLabel='IncidentPriority'" \
  --method GET \
  --target-org <alias>
```

Response: 200 with `records[0].Metadata.standardValue[]`. Find the entry with `"default": true` — its `valueName` is the current fallback priority. Every other entry has `"default": false`.

### 9. Default fallback priority — write

Editing `default: true` on a `StandardValueSet` is a metadata operation — the Tooling REST PATCH on `StandardValueSet/<Id>` returns `FIELD_INTEGRITY_EXCEPTION: Unable to load specified entity`. The canonical `sf` CLI path is metadata deploy.

```bash
# Prepare a scratch project (only needed once per session).
# The force-app/main/default/ path is dictated by packageDirectories[0].path in
# sfdx-project.json below — sf project retrieve start writes the metadata there
# by convention, not by user choice.
WORKDIR=$(mktemp -d)
mkdir -p "$WORKDIR/force-app/main/default/standardValueSets"
cat > "$WORKDIR/sfdx-project.json" <<'EOF'
{
  "packageDirectories": [{"path":"force-app","default":true}],
  "namespace": "",
  "sfdcLoginUrl": "https://test.salesforce.com",
  "sourceApiVersion": "67.0"
}
EOF

# Step 1: retrieve current StandardValueSet
cd "$WORKDIR" && sf project retrieve start \
  --metadata "StandardValueSet:IncidentPriority" \
  --target-org <alias>

# Step 2: edit the XML to set <default>true</default> on the new default
#         and <default>false</default> on every other value.

# Step 3: deploy the modified file
sf project deploy start \
  --metadata "StandardValueSet:IncidentPriority" \
  --target-org <alias> \
  --wait 10
```

**Expected:** `Status: Succeeded` in the deploy output. On failure, report the raw deploy output verbatim.

The XML shape is:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<StandardValueSet xmlns="http://soap.sforce.com/2006/04/metadata">
    <sorted>false</sorted>
    <standardValue>
        <fullName>Critical</fullName>
        <default>false</default>
        <label>Critical</label>
    </standardValue>
    <standardValue>
        <fullName>High</fullName>
        <default>true</default>
        <label>High</label>
    </standardValue>
    <!-- ... one <standardValue> block per active picklist value ... -->
</StandardValueSet>
```

Exactly one `<default>true</default>` should be present at deploy time.

---

## Idempotency contract

| Concern | Match rule (skip the write when …) |
|---------|-------------------------------------|
| `IncPriorityMatrixEnabled` | Phase-2 `isPreferenceEnabled` already equals the requested boolean |
| `IncPriorityOverrideEnabled` | Phase-2 `isPreferenceEnabled` already equals the requested boolean |
| Add a cell | A Phase-2 row already matches `(ReferenceObject, Urgency, Impact)` — even if its Priority differs (surface the mismatch and ask; add is not a change) |
| Change a cell | The Phase-2 row's `Priority` already equals the requested value |
| Remove a cell | No Phase-2 row matches `(ReferenceObject, Urgency, Impact)` |
| Default fallback priority | The Phase-2 `default: true` entry's `valueName` already equals the requested value |

When idempotent, report `ALREADY-<state>` and skip Phase 4 entirely.

---

## Picklist extraction

From the Phase-1 Incident describe response, iterate `fields[]`:

- Look up each field by exact `name` (`Impact`, `Urgency`, `Priority`).
- Keep only `picklistValues[]` entries with `active == true`.
- Use `value` (API name), not `label` — the server stores API values on `ServiceOpPriorityConfig`.

If the describe response is very large, dispatch a subagent (haiku tier) to extract just the three picklists.

Every `Impact`, `Urgency`, `Priority` in an add or change payload — including the default value in the `StandardValueSet` deploy — must be in the fetched active set. Never hardcode `High/Medium/Low` or `Critical/High/Moderate/Low`; customers rename, add, or remove values.

For an uncustomized org the defaults are `High/Medium/Low` on `Impact` and `Urgency`, and `Critical/High/Moderate/Low` on `Priority` — treat as examples, not guarantees.

---

## Gotchas

| Issue | Detail |
|-------|--------|
| Tooling REST accepts garbage picklist values | The wire-level POST/PATCH does NOT validate `Urgency` / `Impact` / `Priority` against the picklist. Runtime matrix evaluation ignores garbage rows. Always validate client-side before dispatch. |
| Duplicate `(ReferenceObject, Urgency, Impact)` rows | Accepted silently at the wire level — the server does NOT enforce uniqueness. Both rows persist and the runtime picks one non-deterministically. Deduplicate against the Phase-2 snapshot before POST; this check is the only guard. |
| `ReferenceObject` accepts any string | The `ServiceOpPriorityConfig` SObject is shared with `Problem` and `ChangeRequest` matrices; the server accepts any value in `ReferenceObject`. Scope to `Incident` is skill-enforced only — refuse other values client-side. |
| `sf api request rest ... --method DELETE` on Tooling | Fails with `SfError: No 'mode' found in 'body' entry` (sf CLI 2.143). Use `sf data delete record --use-tooling-api` instead. |
| `/headless/invoke/service/service-itsm/...` returns 404 through `sf api request rest` | Those routes are Aura-dispatcher only; not addressable via the REST API host. Use the Tooling SObject and Setup Connect API prefs instead — that's what this skill does. |
| Direct PATCH on `StandardValueSet/<Id>` via Tooling REST | Returns `FIELD_INTEGRITY_EXCEPTION: Unable to load specified entity`. Metadata deploy is the canonical path for picklist defaults. |
| Existing Incidents' Priority | Not re-derived on matrix change. New writes use the new matrix; the stamped Priority on existing Incident records stays put. |
