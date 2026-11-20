# Org Calls — headless-360 and Salesforce CLI

**When to load:** Workflow steps 2 and 5. Every call here is a read and runs only after the user agrees to the org read.

Each call is shown for both connections, headless-360 and the Salesforce CLI (with the org's alias); they return the same result. See SKILL.md → Mechanism.

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

## Reuse checks

All reuse checks use the same query call. Put only the planned names in the `WHERE`; never query an object without one.

```text
headless-360:  dispatch_readonly({"path": "/services/data/v67.0/query", "method": "GET", "query_params": {"q": "<SOQL>"}})
Salesforce CLI: write the SOQL to a file, then
                sf data query --file <soql-file> --api-version 67.0 --target-org <alias> --json
```

Prefer headless-360 when it is connected: the name travels inside a JSON value and never reaches a shell. **Never put names in a shell command line.** Names come from the user, so on the CLI path write the SOQL to a file (a quoted heredoc, `<<'EOF'`, or a file-write tool) and pass `--file`. Do not use `-q "<SOQL>"` with a name interpolated into it: a `"`, `$(…)` or backtick in a name would run in the shell.

**Apostrophes.** Escape an apostrophe in a name with a backslash: `O\'Brien`. Doubling it (`''`) fails with 400 `MALFORMED_QUERY`. Inside a headless-360 JSON argument the backslash itself must be escaped, so write `O\\'Brien` in the JSON string. In the SOQL file, write `O\'Brien` as is.

| Check | SOQL |
|---|---|
| Volunteer Initiative | `SELECT Id, Name FROM VolunteerInitiative WHERE Name IN ('Weekly Food Pantry', 'O\'Brien Youth Mentoring')` |
| Location | `SELECT Id, Name FROM Location WHERE Name IN ('Eastside Pantry', 'Virtual')` |
| Position | `SELECT Id, Name FROM Position WHERE Name IN ('Team Lead')` |
| Competency | `SELECT Id, Name FROM Competency WHERE Name LIKE '%Driv%' OR Name LIKE '%License%'` |
| Examination | `SELECT Id, Name FROM Examination WHERE Name LIKE '%Background%' OR Name LIKE '%Check%'` |
| Job Position, existing initiative | `SELECT Id, Name, VolunteerInitiative.Name, Location.Name FROM JobPosition WHERE Name IN ('Driver') AND VolunteerInitiativeId = '<initiative Id>'` |
| Job Position, new initiative | `SELECT Id, Name, VolunteerInitiative.Name, Location.Name FROM JobPosition WHERE Name IN ('Driver')` |

- For Competency and Examination, build the `LIKE` terms from the distinctive stem plus the category noun (`%Driv%` and `%License%`), not one spelling (`%Driving%` misses "Driver's License"). Escape `%` or `_` with a backslash when they're part of the name.
- When a stem query finds nothing but the org may word the record differently, run it again with a shorter stem (`%Lic%` instead of `%License%`) before planning the record as New.
- The Job Position initiative Id comes from the Volunteer Initiative check. With a new initiative, any match belongs to another initiative, so plan the Job Position as New.

| Result | Meaning |
|---|---|
| 200, `totalSize: 0` | No match; plan the record as New |
| 200 with `records` | Show each match (name and parent names) and ask whether it's the one the user means |
| 400 `MALFORMED_QUERY` | Usually an unescaped apostrophe; fix the escape and retry |
| 400 `INVALID_TYPE` / 404 | The object isn't visible; go back to the Volunteer Management check |
