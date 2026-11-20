# Org Calls — headless-360 and Salesforce CLI

**When to load:** Workflow steps 3–6 (reads) and 8 (writes). Reads run only after the user agrees to the org read; a write runs only after the user confirms that object's records table.

Each call is shown for both connections, headless-360 and the Salesforce CLI (with the org's alias); they return the same result. See SKILL.md → Mechanism. Read CLI output from `--json` on stdout only; a warning on stderr mixed into it breaks the JSON.

---

## Volunteer Management check

Every call uses API v67.0. The Salesforce CLI forms run `sf api request rest`, `sf sobject describe`, and `sf data query` against `--target-org <alias>`.

**1. Org preference**

```text
headless-360:  dispatch_readonly({"path": "/services/data/v67.0/setup/org/preferences/VolunteerManagementEnabled", "method": "GET"})
Salesforce CLI: sf api request rest "/services/data/v67.0/setup/org/preferences/VolunteerManagementEnabled" --target-org <alias>
```

Response: `{"isPreferenceEnabled": true}` (a 360 call may wrap it as `{"status_code": 200, "body": {...}}` — read `body.isPreferenceEnabled`).

| Result | Meaning | Do |
|---|---|---|
| `true` | Volunteer Management is on | Continue to the describe |
| `false` | It's off | Stop. An admin turns it on in Setup → Volunteer Management Settings |
| 404 `NOT_FOUND` | The org doesn't have the preference (VM not provisioned) | Stop, same message |
| 403 | The user can't read org settings | Stop and say so; this is not the same as "off" |

**2. User access**

```text
headless-360:  dispatch_readonly({"path": "/services/data/v67.0/sobjects/VolunteerInitiative/describe", "method": "GET"})
Salesforce CLI: sf sobject describe --sobject VolunteerInitiative --api-version 67.0 --target-org <alias> --json
```

| Result | Meaning | Do |
|---|---|---|
| 200 | The user can see the Volunteer Management objects | Continue |
| 404 `NOT_FOUND` / `INVALID_TYPE`, or 403 | The user can't see them | Stop. The user needs the Manage Volunteer Data permission set |

Don't query permission-set assignments up front; the describe answers the question.

---

## Queries (reuse checks, existing shifts, read-backs)

Every query uses the same call:

```text
headless-360:  dispatch_readonly({"path": "/services/data/v67.0/query", "method": "GET", "query_params": {"q": "<SOQL>"}})
Salesforce CLI: write the SOQL to a file, then
                sf data query --file <soql-file> --api-version 67.0 --target-org <alias> --json
```

**Never put names in a shell command line.** Names come from the user, so on the CLI path write the SOQL to a file (a quoted heredoc, `<<'EOF'`, or a file-write tool) and pass `--file`. Do not use `-q "<SOQL>"` with a name interpolated into it: a `"`, `$(…)` or backtick in a name would run in the shell.

**Apostrophes:** escape an apostrophe inside a SOQL string literal with a backslash — `'Driver\'s License'`, `'O\'Brien Hall'`. Doubling it (`''`) fails with `MALFORMED_QUERY`. Inside a headless-360 JSON argument the backslash itself must be escaped, so write `O\\'Brien` in the JSON string. In the SOQL file, write `O\'Brien` as is. This applies to every name below.

### Reuse checks (step 4)

Put only the planned names in the `WHERE`; never query an object without a filter.

| Object | SOQL | Reuse when |
|---|---|---|
| Volunteer Initiative | `SELECT Id, Name, Status, ParentVolunteerInitiativeId FROM VolunteerInitiative WHERE Name IN ('Weekly Food Pantry')` | Name matches |
| Location | `SELECT Id, Name, LocationType, TimeZone, VisitorAddressId FROM Location WHERE Name IN ('Eastside Pantry')` | Name matches. A non-empty `VisitorAddressId` means it already has an Address — don't create one |
| Competency | `SELECT Id, Name FROM Competency WHERE Name IN ('Forklift Operation')` | Name matches |
| Examination | `SELECT Id, Name FROM Examination WHERE Name IN ('Driver\'s License')` | Name matches |
| Position | `SELECT Id, Name, Status FROM Position WHERE Name IN ('Driver')` | Name matches |
| Job Position | `SELECT Id, Name, Title, VolunteerInitiativeId, LocationId FROM JobPosition WHERE Name IN ('Driver') AND VolunteerInitiativeId = '<Volunteer Initiative Id>'` | Name **and** Volunteer Initiative match. When the Volunteer Initiative is New, no Job Position can match — skip this query |
| Operating Hours (only when requested) | `SELECT Id, Name, TimeZone, (SELECT DayOfWeek, StartTime, EndTime FROM TimeSlots) FROM OperatingHours WHERE TimeZone = 'America/Chicago'` | Same Time Zone **and** the same set of Time Slot windows. The name never decides reuse |

When an exact name finds nothing but the user's wording suggests a near match, widen to a distinctive stem (`WHERE Name LIKE '%Forklift%'`) and ask before reusing a near match.

### Existing shifts (step 5)

For each reused Job Position, by its Id and the series' start-date range (SOQL date literals are unquoted):

```text
SELECT Id, StartDate, EndDate, StartTime, EndTime FROM JobPositionShift
WHERE JobPositionId = '<reused Job Position Id>' AND StartDate >= 2027-06-05 AND StartDate <= 2027-08-28
```

Pass the returned rows unchanged as `excludeExisting` to `scripts/expand-series.py`. With a `count` and no end date, use the last date the script would generate as the upper bound (run the script once without `excludeExisting` to see it).

### Read-back after a write

```text
SELECT Id, Name, <the fields just written> FROM <Object> WHERE Id IN ('<new Id>', ...)
```

Every written record appears with the values sent → the write is confirmed. A missing record or a different value → report it in the final report; don't re-write automatically.

---

## Object descriptions (step 6)

```text
headless-360:  dispatch_readonly({"path": "/services/data/v67.0/sobjects/<Object>/describe", "method": "GET"})
Salesforce CLI: sf sobject describe --sobject <Object> --api-version 67.0 --target-org <alias> --json
```

From `fields[]`:

- **Required custom field:** `custom == true && createable == true && nillable == false && defaultedOnCreate == false`.
- **Picklist values:** `picklistValues[]` where `active == true`. A write accepts only these values; a new one has to be added to the list first (Adding a picklist value).
- **Label:** `label` — use it in the records table (pass it to `render-review-table.py` as `labels`).

---

## Writes (step 8)

### Several records of one object — one tree call

All records of one object in one call, up to 200 records. The call is all-or-nothing: either every record is created or none is.

```text
headless-360:  dispatch({"path": "/services/data/v67.0/composite/tree/<Object>", "method": "POST", "body": {"records": [
                 {"attributes": {"type": "<Object>", "referenceId": "<Object>_1"}, "Name": "...", ...},
                 {"attributes": {"type": "<Object>", "referenceId": "<Object>_2"}, "Name": "...", ...}]}})
Salesforce CLI: save the same {"records": [...]} body to a file, then
                sf data import tree --files <file>.json --api-version 67.0 --target-org <alias> --json
```

| Result | Meaning | Do |
|---|---|---|
| 201, `hasErrors: false` | Every record was created | Map each `referenceId` to its returned `id` and feed the Ids to the children |
| 400, `hasErrors: true` | Nothing in this call was created | Show each `errors[]` entry, fix, re-send the whole call |

- `scripts/expand-series.py` output is already this body.
- A parent written in an earlier call is a literal Id in the child field (`"JobPositionId": "0Jp..."`). A `@refId` reference (`"@JobPosition_1"`) works only for a parent in the same body.
- Over 200 records: send one call per batch (`expand-series.py --out-dir` writes one body per batch). If a later batch fails, the earlier batches stay; report which records exist.

### One record

```text
headless-360:  dispatch({"path": "/services/data/v67.0/sobjects/<Object>", "method": "POST", "body": {"Name": "...", ...}})
Salesforce CLI: save the same body to a file, then
                sf api request rest "/services/data/v67.0/sobjects/<Object>" --method POST --body @<body>.json --target-org <alias>
```

The CLI form reads the body from a file; never build a `--values "Name='...'"` string from user-supplied text.

201 with `{"id": "...", "success": true}` → created. 400 → not created; read `errorCode` and `message`.

### Location ↔ Address back-fill

After the Address exists, point its Location at it:

```text
headless-360:  dispatch({"path": "/services/data/v67.0/sobjects/Location/<Location Id>", "method": "PATCH", "body": {"VisitorAddressId": "<Address Id>"}})
Salesforce CLI: save {"VisitorAddressId": "<Address Id>"} to a file, then
                sf api request rest "/services/data/v67.0/sobjects/Location/<Location Id>" --method PATCH --body @<body>.json --target-org <alias>
```

204 → updated.

### Common write errors

| Error | Meaning | Fix |
|---|---|---|
| `REQUIRED_FIELD_MISSING` | A required field (often a custom one or a validation rule) is empty | Ask the user for the value, re-send |
| `INVALID_OR_NULL_FOR_RESTRICTED_PICKLIST` | A value isn't in the field's list of values | Offer the live values from the describe, or offer to add the value (Adding a picklist value) |
| `MALFORMED_ID` | A `@refId` pointed outside its body, or at the same object in the same body | Use the parent's literal Id |
| `INVALID_FIELD` | A field that doesn't exist on the object | Remove it; only field-guide fields are written |
| `FIELD_CUSTOM_VALIDATION_EXCEPTION` | A customer validation rule rejected the record | Show the message; ask the user how to proceed |

---

## Adding a picklist value

Only for a field in the value-set table below (never Time Zone or Time Slot Day of Week and Type, whose values are fixed), and only after the user says yes to adding that specific value (step 6).

How the value gets added depends on the connection:

| Connection | Who adds the value | How |
|---|---|---|
| headless-360 | The user, in Setup | Ask them to add it (Adding it in Setup), wait for "done", then describe the object again |
| Salesforce CLI | You, for the user | Retrieve, edit, check, deploy, describe again (Command patterns) |

Never write a value set through headless-360. It can't read one (`/headless/metadata` returns 400 `UNSUPPORTED_OPERATION` for `StandardValueSet`), and writing one without reading it first drops values.

Either way, the new value is used only after a fresh describe shows it in that field's `picklistValues[]`. If it isn't there yet, say so and ask the user to check Setup again or pick one of the live values; never send the write with it.

### Value sets

Every picklist the skill writes, except the platform ones, keeps its values in a standard value set:

| Field | Value set |
|---|---|
| Location → Location Type, Address → Location Type | `LocationType` |
| Address → Address Type | `AddressType` |
| Competency → Category | `CompetencyCategory` |
| Examination → Status | `LPIExaminationStatus` |
| Position → Type | `PositionTypeEnum` |
| Volunteer Initiative → Status | `VolunteerInitiativeStatus` |
| Position → Status | `PositionStatus` |
| Job Position → Status | `JobPositionStatus` |
| Job Position Shift → Status | `JobPositionShiftStatus` |
| Position Qualification → Proficiency Level, Job Position Qualification → Proficiency Level | `ProficiencyLevelEnum` |

Location Type is one set shared by Location and Address, and Proficiency Level one set shared by both qualification objects, so a value added for one appears on both.

### Adding it in Setup (headless-360)

Tell the user exactly what to add and where, in one message:

```text
Add "{value}" to {Object} → {Field}:
Setup → Object Manager → {Object} → Fields & Relationships → {Field} → Values → New
(/lightning/setup/ObjectManager/{Object}/FieldsAndRelationships/{Field API name}/view)
Enter "{value}" as the value, leave "Default" unchecked, and save. Reply "done" when it's added.
```

When the value set is shared (Location Type, Proficiency Level), say that the value also appears on the other object. On "done", describe the object again before using the value.

### Command patterns (Salesforce CLI)

Run from inside a Salesforce project (`sf project generate --name <dir>` makes one).

| Intent | Command |
|---|---|
| Read the current value set | `sf project retrieve start --metadata StandardValueSet:<value set> --api-version 67.0 --target-org <alias> --json` |
| Check the edited set without saving it | `sf project deploy start --dry-run --metadata StandardValueSet:<value set> --test-level NoTestRun --api-version 67.0 --target-org <alias> --json` |
| Deploy the edited set | `sf project deploy start --metadata StandardValueSet:<value set> --test-level NoTestRun --api-version 67.0 --target-org <alias> --json` |
| Confirm the value is live | `sf sobject describe --sobject <Object> --api-version 67.0 --target-org <alias> --json` — the value appears in that field's `picklistValues[]` |

The edit, in `force-app/main/default/standardValueSets/<value set>.standardValueSet-meta.xml`: add one block after the last `<standardValue>` (or before `</StandardValueSet>` when the set is empty) and leave the existing ones unchanged.

```xml
<standardValue>
    <fullName><approved value></fullName>
    <default>false</default>
    <label><approved value></label>
</standardValue>
```

A check reports `"checkOnly": true` and `"success": true` when the set is valid; then deploy.

### Rules

| Constraint | Rationale |
|---|---|
| Retrieve before every deploy and keep every existing value | The deploy replaces the whole value set; a value missing from the file is removed from the org |
| Add only the value the user approved, with `default` false | Any other change to the set wasn't approved |
| Check, then deploy, with `--test-level NoTestRun` | A value set carries no Apex; without it an org with low test coverage rejects the deploy |
| Describe again before using the new value | The write is confirmed only when the value is in `picklistValues[]` |

### Troubleshooting

| Issue | Resolution |
|---|---|
| "`<dir>` does not contain a valid Salesforce DX project" | Create a project with `sf project generate --name <dir>` and run from inside it |
| The check or deploy fails | Show the error and don't retry with a guessed change; ask the user to pick one of the live values |
| The user says "done" but the describe doesn't list the value | Say the value isn't there yet; ask them to check that it was saved on the right field, or to pick one of the live values |
