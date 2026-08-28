# Matrix Operations — CLI Invocation Templates

Every mutation is a single `sf` CLI command. The Tooling REST endpoints operate on **one row at a time** — the read-modify-write step is client-side only. Add, change, and remove are three distinct wire calls, not one replace.

Templates below start from this hypothetical current matrix (Tooling SOQL result):

```json
{
  "records": [
    { "Id": "1NHSG00000007374AA", "ReferenceObject": "Incident", "Impact": "High",   "Urgency": "High",   "Priority": "High" },
    { "Id": "1NHSG00000007384AA", "ReferenceObject": "Incident", "Impact": "Medium", "Urgency": "Medium", "Priority": "Moderate" },
    { "Id": "1NHSG00000007394AA", "ReferenceObject": "Incident", "Impact": "Low",    "Urgency": "Low",    "Priority": "Low" }
  ]
}
```

Assume the current default priority (from `StandardValueSet:IncidentPriority`) is `Low` and manual override is `false`. Neither is affected by row-level writes — each concern has its own dedicated CLI invocation.

Replace `<alias>` with the user's target-org alias. Replace `<unique>` with an integer suffix that is not present in any existing row's `DeveloperName` (typically the next integer after the maximum currently-used suffix).

---

## Coordinate Match Protocol

Every mutation resolves against the Phase-2 snapshot on the coordinate `(ReferenceObject, Urgency, Impact)`. Match count drives the dispatch decision:

- **Add** — refuse the POST if the coordinate is already present in the snapshot (that would be a Change; surface and ask).
- **Change — zero matches** → treat as an add; surface and ask.
- **Change — exactly one match** → dispatch the PATCH on that row's `Id`.
- **Change — more than one match** → do not dispatch. Report every matching row (`Id`, `DeveloperName`, current `Priority`) and require the user to either name the exact `Id` to change or approve a consolidation plan (remove the extras, then change the survivor).
- **Remove — zero matches** → short-circuit with "nothing to remove".
- **Remove — exactly one match** → dispatch the delete on that row's `Id`.
- **Remove — more than one match** → do not dispatch. Report every matching row (`Id`, `DeveloperName`, current `Priority`) and require the user to either name the exact `Id`(s) to remove or explicitly confirm "remove all rows at this coordinate".

Add, Change, and Remove templates below reference this protocol.

---

## Add — insert a new cell

Add `Medium × High → High`. Resolve against the Coordinate Match Protocol first — the coordinate `(ReferenceObject=Incident, Impact=Medium, Urgency=High)` must not be present in the Phase-2 snapshot.

```bash
sf api request rest \
  "/services/data/v67.0/tooling/sobjects/ServiceOpPriorityConfig" \
  --method POST \
  --header "Content-Type:application/json" \
  --body '{"ReferenceObject": "Incident", "Impact": "Medium", "Urgency": "High", "Priority": "High", "DeveloperName": "ServiceOpPriorityConfigIncident<unique>", "MasterLabel": "ServiceOpPriorityConfigIncident<unique>"}' \
  --target-org <alias>
```

Pass the JSON body inline with `--body '{...}'` — `sf api request rest` accepts inline content or `--body @file`; inline keeps the payload in the skill's control instead of a path outside the project.

Response: `201 {"id": "<new Id>", "success": true, ...}`.

Client-side validation before dispatch:

- `ReferenceObject == "Incident"`. `ServiceOpPriorityConfig` is shared with the Problem and ChangeRequest matrices; scope to Incident is skill-enforced.
- `Impact`, `Urgency`, `Priority` are in the Phase-1 active picklist sets. Validate every value client-side — do not rely on the wire to reject unknown picklist entries.
- `(ReferenceObject, Impact, Urgency)` is not already present in the Phase-2 snapshot (see Coordinate Match Protocol).

---

## Change — replace a cell's Priority

Change `High × High` from `High` to `Critical`. Resolve against the Coordinate Match Protocol first; the single-match case looks up `<Id>` from the Phase-2 snapshot (the row where `Impact=High` and `Urgency=High` → `Id=1NHSG00000007374AA`).

```bash
sf api request rest \
  "/services/data/v67.0/tooling/sobjects/ServiceOpPriorityConfig/1NHSG00000007374AA" \
  --method PATCH \
  --header "Content-Type:application/json" \
  --body '{"Priority": "Critical"}' \
  --target-org <alias>
```

Response: `204 No Content`. Validate the new Priority against the Phase-1 active picklist before dispatch.

---

## Remove — delete a cell

Remove `Medium × Medium`. Resolve against the Coordinate Match Protocol first; the single-match case looks up `<Id>` from the Phase-2 snapshot (`Id=1NHSG00000007384AA`).

```bash
sf data delete record \
  --sobject ServiceOpPriorityConfig \
  --record-id 1NHSG00000007384AA \
  --use-tooling-api \
  --target-org <alias>
```

Response: `Successfully deleted record: 1NHSG00000007384AA.`

Use `sf data delete record --use-tooling-api` for Tooling SObject deletes — `sf api request rest ... --method DELETE` on a Tooling SObject is not supported in `sf` CLI 2.143.

---

## Toggle manual override

Direct pref route — PATCH echoes the new state so no re-read is needed.

```bash
sf api request rest \
  "/services/data/v67.0/setup/org/preferences/IncPriorityOverrideEnabled" \
  --method PATCH \
  --header "Content-Type:application/json" \
  --body '{"desiredState": true}' \
  --target-org <alias>
```

Response: `200 {"isPreferenceEnabled": true}`. Does **not** touch matrix rows or the default priority.

---

## Enable / disable the matrix

Same shape as manual override, on `IncPriorityMatrixEnabled`:

```bash
sf api request rest \
  "/services/data/v67.0/setup/org/preferences/IncPriorityMatrixEnabled" \
  --method PATCH \
  --header "Content-Type:application/json" \
  --body '{"desiredState": false}' \
  --target-org <alias>
```

Response: `200 {"isPreferenceEnabled": false}`. Disabling does **not** clear matrix rows or the default priority; existing Incidents keep their stamped priority. Re-enabling restores derivation immediately.

---

## Set default (fallback) priority

The default lives in the `StandardValueSet:IncidentPriority` metadata — the value with `<default>true</default>` is the current fallback. Change is via metadata deploy; direct Tooling PATCH on `StandardValueSet/<Id>` returns `FIELD_INTEGRITY_EXCEPTION`.

```bash
# One-time: prepare a scratch project directory.
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

# Step 1 — retrieve the current StandardValueSet
cd "$WORKDIR" && sf project retrieve start \
  --metadata "StandardValueSet:IncidentPriority" \
  --target-org <alias>

# Step 2 — edit the retrieved XML file. Exactly one <default>true</default>
#          must remain; every other <standardValue> block must carry
#          <default>false</default>. Example: set default to "High".

# Step 3 — deploy the modified file
sf project deploy start \
  --metadata "StandardValueSet:IncidentPriority" \
  --target-org <alias> \
  --wait 10
```

Deploy result must be `Status: Succeeded`. On any other state (e.g. `Failed`, `Canceled`), report the raw deploy output verbatim.

The XML shape after editing (default `High`):

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
    <standardValue>
        <fullName>Moderate</fullName>
        <default>false</default>
        <label>Moderate</label>
    </standardValue>
    <standardValue>
        <fullName>Low</fullName>
        <default>false</default>
        <label>Low</label>
    </standardValue>
</StandardValueSet>
```

Validate the target value against the Phase-1 active picklist first.

---

## Mark the Salesforce Go setup step complete (Phase 5, after a mutation)

Once a functional write above has been dispatched **and** the Phase-5 verify confirms it landed,
flip the "Define Priority Matrix" tile in the Salesforce Go setup checklist to Done. This step is a
user-override step: configuring the matrix functionally does **not** move its checkmark — the
completion has to be written explicitly (route 10 in `references/sf-cli-invocation.md`).

```bash
sf api request rest \
  "/services/data/v67.0/connect/setup/discovery/feature/service-cloud-itsm-incident/configuration/step/definePriorityMatrix/progress" \
  --method PUT \
  --header "Content-Type:application/json" \
  --body '{"isComplete": true}' \
  --target-org <alias>
```

Response: `200` with the updated step progress. Notes:

- **`isComplete` is required** — omitting it returns HTTP 500, not 400.
- Send it **only when Phase 4 actually wrote something**. On a view-only read or an idempotent
  no-op (e.g. disabling an already-disabled matrix), dispatch nothing — the PUT is itself a mutation.
- It rides on the confirmation the user already gave for the functional change; it is not a
  separately-confirmed write.
