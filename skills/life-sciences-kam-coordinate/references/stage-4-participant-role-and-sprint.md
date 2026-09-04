# Stage 4 — Participant Role & Sprint (KAM)

Creates two records that later KAM stages depend on: a `ParticipantRole` (used by Account Plan participation) and a `Sprint` (the execution window for the KAM plan). Run entirely as the **admin** (`--target-org <admin>`). This is Stage 4 of `life-sciences-kam-coordinate`; the coordinator invokes it after territories (Stage 3) are active.

Only the **name** of each record is shown to and confirmed with the admin (accept the default or supply a different name). Every other field is auto-derived and kept **internal — do NOT display it to the admin.**

---

## Record 1 — ParticipantRole

**Show the admin only the "Participant Role Name"** (default `Rep Execution Specialist`) and ask them to accept the default or supply a different name. This name is stored internally in the `MasterLabel` field — do **NOT** surface the field name "MasterLabel" to the admin, and do **NOT** show any of the internal fields below.

| Field | Value | Shown to admin? |
|-------|-------|-----------------|
| `MasterLabel` | the confirmed name, e.g. `Rep Execution Specialist` | Shown **as "Participant Role Name"** (never as "MasterLabel") |
| `DeveloperName` | derived from the name: replace spaces with `_`, e.g. `Rep_Execution_Specialist` | Internal — not shown |
| `IsActive` | `true` | Internal — not shown |
| `ParentObject` | `AccountPlan` | Internal — not shown |
| `DefaultAccessLevel` | `Edit` | Internal — not shown |

> **DeveloperName derivation:** take the confirmed Participant Role Name and replace every space with `_` (e.g. `Rep Execution Specialist` → `Rep_Execution_Specialist`). Compute it internally; never ask the admin for it.

```bash
sf data create record --sobject ParticipantRole --target-org <admin> \
  --values "MasterLabel='Rep Execution Specialist' DeveloperName=Rep_Execution_Specialist IsActive=true ParentObject=AccountPlan DefaultAccessLevel=Edit" --json
```

> `ParticipantRole` may be a Metadata/Tooling-backed entity in some orgs. If `sf data create record` reports the sObject is not createable via the data API, create it with the Tooling API (`--use-tooling-api`) or as metadata; the field values above are unchanged. Verify with a Tooling query if the standard query returns nothing.

### Verify

```bash
sf data query --query "SELECT Id, MasterLabel, DeveloperName, IsActive, ParentObject, DefaultAccessLevel FROM ParticipantRole WHERE DeveloperName = 'Rep_Execution_Specialist'" --target-org <admin> --json
```

Expect exactly 1 record with `IsActive=true`. Capture its Id in `OrchestrationState`.

---

## Record 2 — Sprint

Dates are relative to the run date. Compute them from the current date at run time — do **not** hardcode a date.

**Before creation, show the admin only the Sprint Name** (default `Sprint 1 – Immunexis P&T Prep`) and ask them to accept the default or supply a different name. Do **NOT** show the dates or `Status` before creation.

| Field | Value | Shown to admin? |
|-------|-------|-----------------|
| `Name` | the confirmed name, e.g. `Sprint 1 – Immunexis P&T Prep` | Shown before creation (accept default or change) |
| `EffectiveStartDate` | Today (run date) | Internal — not shown before creation |
| `EffectiveEndDate` | Start + 2 weeks (14 days) | Internal — not shown before creation |
| `Status` | `Not Started` | Internal — not shown before creation |

> **After the Sprint is created, display** its `Name`, Start Date, End Date, and Status to the admin — a post-creation summary. This is the only point at which the dates and `Status` are shown.

Derive the dates so the two-week window is exact:

```bash
START=$(date +%F)
END=$(date -v+14d +%F 2>/dev/null || date -d "+14 days" +%F)   # macOS / GNU date
sf data create record --sobject Sprint --target-org <admin> \
  --values "Name='Sprint 1 – Immunexis P&T Prep' EffectiveStartDate=$START EffectiveEndDate=$END Status='Not Started'" --json
```

> The em dash in the name (`–`, U+2013) is intentional — keep it as written. Wrap the value in single quotes so the shell preserves it.

### Verify

```bash
sf data query --query "SELECT Id, Name, EffectiveStartDate, EffectiveEndDate, Status FROM Sprint ORDER BY CreatedDate DESC LIMIT 1" --target-org <admin> --json
```

Expect the sprint with `Status='Not Started'` and a 14-day window. Capture its Id.

---

## Confirmation Before Creating

For **each** record, show the admin **only its name** — the Participant Role Name and the Sprint Name — and ask them to accept the default or supply a different one. Do **NOT** show the internal/auto-derived fields (`DeveloperName`, `IsActive`, `ParentObject`, `DefaultAccessLevel`, the Sprint dates, `Status`) before creating. After the Sprint is created, display its `Name`, Start Date, End Date, and Status as a post-creation summary.

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| `date -v+14d` fails | That is BSD/macOS syntax; on GNU/Linux use `date -d "+14 days" +%F` (the command above tries both) |
| `DUPLICATE_DEVELOPER_NAME` on ParticipantRole | The role already exists (idempotent re-run) — query it and reuse rather than treating as an error |
| Em dash mangled in the Sprint name | Ensure the terminal/locale is UTF-8 and the value is single-quoted; re-create if it landed as `?` or `-` |
| `Status` rejected | The value must match the `SprintStatus` StandardValueSet confirmed in Stage 2 — `Not Started` is the default entry |
