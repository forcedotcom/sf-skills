# 1. Student Success

**Purpose**: Track student advising, success interventions, care plans, and wellness support.

**Prerequisites**:
- All Foundation prerequisites (Section 0)
- Cases enabled — advising uses case-based workflows
- Salesforce Scheduler — for advising appointment booking
- Experience Cloud license — for Learner Portal (student-facing)
- OmniStudio — for portal components and guided experiences
- CRM Analytics / Education Analytics — for Advisor Insights and KPI dashboards (optional)
- Einstein Generative AI — for Einstein Advising Summary (optional)

**Core features**:
- Student records (Person Accounts)
- Advising case management
- Success teams for collaborative support
- Care plans to track interventions
- Alerts and notifications
- Salesforce Scheduler for appointment booking

### Sub-Feature Configuration

> **Executed order (from Student Success testing):** Support Process → Case Record Types → Success Teams (create `CaseTeamTemplate` first) → Care Plans → Support Programs → Salesforce Scheduler. Do Care Plans AFTER Success Teams and Support Programs BEFORE Scheduler.

> **License-gating on Care Plans / Support Programs / Scheduler writes.** These three toggle writes can return `400 INSUFFICIENT_ACCESS_OR_READONLY` (nothing written) on an under-licensed org — confirmed on a test org where the identical write failed on day 1 and succeeded (`success:true`) on day 2 after the org was given more licenses, with no skill/API change in between. Treat this error as **"check licensing on this org first,"** not as a fixed product limitation — retry after the admin confirms licensing rather than concluding the feature is unreachable via API.

> **`IndustriesSettings` tooling GET cold-verify can 500 org-wide.** `GET /services/data/v68.0/tooling/sobjects/IndustriesSettings/<DurableId>` has been observed returning HTTP 500 `UNKNOWN_EXCEPTION` on every value read (any field, any API version) in at least one org, root-caused to a null UDD `LogicalFieldDefinition` on one preference column in that org's data — an org-data defect, not a skill or transport bug (`describe` and `SELECT Id, DurableId` still return 200; only value reads fail). If this GET 500s on 3 consecutive attempts, stop retrying the API path and ask the admin to confirm the toggle's ON state in Setup UI instead — record that the write's `success:true` was confirmed via Setup UI, not cold-verified via API, and say so explicitly in any summary.

#### Step 1 — Create Support Process

**What it does**: Creates a Support Process named "Student Advising" to organize case statuses. Used as the `businessProcess` on the case record types in Step 2.

**API approach** (works — try first):
```bash
POST /services/data/v68.0/sobjects/BusinessProcess
{"Name":"Student Advising","TableEnumOrId":"Case","Description":"Advising case support process"}
```
Do **NOT** send `IsActive` on insert — it is `INVALID_FIELD_FOR_INSERT_UPDATE`. The BusinessProcess is active by default. Capture the returned `Id` and the `Name` ("Student Advising") — Step 2 references the process by **Name**, not Id.

**Setup path** (UI fallback):
1. Navigate to Setup → Quick Find → "Support Processes" → Click New
2. For "Existing Support Process", select Master
3. Enter support process name: "Student Advising"
4. Click Save; leave Case Status as default, click Save again

**Verification** (read back by the Id captured at creation — a SOQL `SELECT Id FROM <Object> WHERE ...` via `queryParams` also works if you need to re-find the record later):
```http
GET /services/data/v68.0/sobjects/BusinessProcess/<id-captured-from-create-response>
```

---

#### Step 2 — Create Advising Case Record Types

**What it does**: Creates specialized case record types for different advising scenarios.

**API approach** (works — try first). Use the Tooling `RecordType` with the `FullName` + `Metadata` shape (NOT flat columns). `businessProcess` = the BusinessProcess **Name** from Step 1, not its Id:
```http
POST /services/data/v68.0/tooling/sobjects/RecordType
{"FullName":"Case.Academic","Metadata":{"label":"Academic","active":true,"businessProcess":"Student Advising","description":"Academic advising cases"}}
```
Repeat with `FullName` `Case.Health`, `Case.Wellbeing` (and `Case.FinancialAid` if used), changing `label`.

**Profile permissions (record type visibility) are NOT applied via this API** — the record type is created but not assigned to any profile. Assigning it to profiles is a separate step (Setup → Profiles → Record Type Settings, or a `Profile` metadata deploy).

**Setup path** (UI fallback):
1. Setup → Quick Find → "Set Up Education Cloud" → Set Up Education Cloud → under "Create Advising Case Record Types" click "Create Case Record Types"
2. On Case Record Types → New; for "Existing Record Type" select Master
3. Enter label (e.g., "Academic"), Tab to auto-populate name
4. For "Support Process" select "Student Advising"; select Active
5. Select profile permissions → Next → Save
6. Repeat for Health, Wellbeing (and optional Financial Aid)

**Verification** (RecordType is a tooling object — use `/tooling/sobjects` for GET-by-Id, or `/tooling/query` via `queryParams` for a SOQL lookup):
```http
GET /services/data/v68.0/tooling/sobjects/RecordType/<id-captured-from-create-response>
```
Repeat per record type created (Academic, Health, Wellbeing, and FinancialAid if used), using each one's Id from its own create response.

---

#### Step 3 — Set Up Success Teams

**What it does**: Creates success teams for collaborative case management, keyed to a case record type.

**PREREQUISITE** — a `CaseTeamTemplate` must exist first; `SuccessTeam` references it by **Name** via `DefaultUnassignedCaseTeam`. Check existence first with `GET /services/data/v68.0/query` and `queryParams: {"q": "SELECT Id FROM CaseTeamTemplate WHERE Name='<name>'"}`; if none found, create directly and read back by the Id captured at creation:
```http
POST /services/data/v68.0/sobjects/CaseTeamTemplate
{"Name":"Advising Team","Description":"Default advising success team"}
```
```http
GET /services/data/v68.0/sobjects/CaseTeamTemplate/<id-captured-from-create-response>
```

**Create the Success Team** (`IsActive` IS writable here, unlike BusinessProcess). `CaseRecordTypeId` = the RecordType Id from Step 2; `DefaultUnassignedCaseTeam` = the CaseTeamTemplate **Name**:
```http
POST /services/data/v68.0/sobjects/SuccessTeam
{"Name":"Academic Success Team","CaseRecordTypeId":"<Academic RecordType Id>","DefaultUnassignedCaseTeam":"Advising Team","IsActive":true}
```
Repeat per case record type (Wellbeing, Health).

**Setup path** (UI fallback): Student Success app → Success Teams tab → New → name, select case record type, select/create case team → Save.

**Verification** (read back each by the Id captured at creation — a SOQL `SELECT Id FROM <Object> WHERE ...` via `queryParams` also works if you need to re-find records later):
```http
GET /services/data/v68.0/sobjects/SuccessTeam/<id-captured-from-create-response>
```
Repeat per case record type's Success Team created above.

---

#### Step 4 — Enable Care Plans (after Success Teams)

**What it does**: Enables care plans to track intervention plans, goals, and progress for at-risk students.

**Write approach** (works — `IndustriesSettings` toggle). **IRREVERSIBLE.** Element is **`enableCarePlansPreference`** — do NOT use `enableCarePlans` (→ `FIELD_INTEGRITY_EXCEPTION`). Use the SKILL.md **Domain & Feature Toggle Write Path**:
```json
{
  "type": "IndustriesSettings",
  "fullName": "Industries",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableCarePlansPreference>true</enableCarePlansPreference></IndustriesSettings>"
}
```
Do NOT use `setup/org/preferences/{name}` (404).

**Verification** (cold read — `success:true` alone unreliable): tooling GET `IndustriesSettings` by DurableId `bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=` and confirm `.Metadata.enableCarePlansPreference` / flat `IsCarePlansPreferenceEnabled` is `true`. If the GET 500s, fall back to a Setup UI confirmation (see license-gating/cold-verify note above) rather than reporting unverified.

If the write itself 400s `INSUFFICIENT_ACCESS_OR_READONLY`, this is likely license-gated on this org — see note above.

---

#### Step 5 — Enable Support Programs (before Scheduler)

**What it does**: Enables benefit/program management used by Student Success programs. Four toggles flip in a **single** metadata PUT.

**Write approach** (works — `IndustriesSettings` toggles). **IRREVERSIBLE.** One PUT with all four elements:
```json
{
  "type": "IndustriesSettings",
  "fullName": "Industries",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableBenefitManagementPreference>true</enableBenefitManagementPreference><enableBenefitAndGoalSharingPref>true</enableBenefitAndGoalSharingPref><allowBenefitAssignmentWithInactiveProgramEnrollment>true</allowBenefitAssignmentWithInactiveProgramEnrollment><enableProgramCohorts>true</enableProgramCohorts></IndustriesSettings>"
}
```

**Verification** (cold read): tooling GET by DurableId; confirm `.Metadata.enableBenefitManagementPreference`, `enableBenefitAndGoalSharingPref`, `allowBenefitAssignmentWithInactiveProgramEnrollment`, and `enableProgramCohorts` are all `true`. If the GET 500s, fall back to Setup UI confirmation (see license-gating/cold-verify note above).

If the write itself 400s `INSUFFICIENT_ACCESS_OR_READONLY`, this is likely license-gated on this org — see note above.

---

#### Step 6 — Enable Salesforce Scheduler (partial — for advising appointments)

**What it does**: Enables Salesforce Scheduler for students to book advising appointments. **Partially API-writable** — two org prefs flip via metadata PUT; the master enable + a couple settings are manual/UI only.

**API-writable** (`IndustriesSettings` toggles — one PUT):
```json
{
  "type": "IndustriesSettings",
  "fullName": "Industries",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableEventManagementOrgPref>true</enableEventManagementOrgPref><enableShareSaWithArOrgPref>true</enableShareSaWithArOrgPref></IndustriesSettings>"
}
```
Cold-verify `enableEventManagementOrgPref` and `enableShareSaWithArOrgPref` are `true`. If the cold-verify GET 500s, fall back to Setup UI confirmation (see license-gating/cold-verify note above); if the write 400s `INSUFFICIENT_ACCESS_OR_READONLY`, check licensing on this org before concluding the toggle is unreachable via API.

**Manual / UI only** (NOT API-writable):
- **Scheduler master enable** — license-gated (Field Service). Setup → Quick Find → "Salesforce Scheduler Settings" → turn on Salesforce Scheduler. If no license, enablement fails.
- **Multiple Topics for Shifts** — skip (has its own prerequisites; not needed for advising).
- **Schedule Appointments Using Engagement Channels** — enable manually in Salesforce Scheduler Settings.

---

#### Step 7 — Set Up the Advisor Console

**What it does**: Configures the Advisor Console app with care plans, alerts, success teams, and appointment scheduler components.

**Setup path**:
1. Navigate to Setup → App Manager → Find "Advisor Console"
2. Click Edit
3. Assign page layouts and record types to advisor profiles
4. Add relevant components to app:
   - Care Plans
   - Alerts
   - Success Teams
   - Appointment Scheduler
   - Student 360 view
5. Save and assign to advisor user profiles

**Verification**: Check App Launcher shows Advisor Console for advisor users.

---

#### Step 8 — Set Up the Director Console (Student Success)

**What it does**: Configures the Director Console with KPI components for directors.

**Setup path**:
1. Navigate to Setup → App Manager → Find "Director Console"
2. Click Edit
3. Configure visibility and KPI components for directors:
   - Student Success KPIs
   - Advisor performance metrics
   - Care plan pipeline
4. Save and assign to director user profiles

**Verification**: Check App Launcher shows Director Console for director users.

---

#### Step 9 — Configure Performance Alerts

**What it does**: Configures alert types (attendance, grades, concerns) and maps them to Success Teams.

**Setup path**:
1. Navigate to Student Success app → Alert Settings tab
2. Configure alert types:
   - Attendance alerts (threshold: < 80%)
   - Grade alerts (threshold: < C average)
   - Concern alerts (flagged by faculty)
3. Map alerts to Success Teams and case record types
4. Optionally connect to Care Plans via "Apply Care Plans to Alerts" feature
5. Save

**Verification**: Check Alert Settings show configured alert types.

---

#### Step 10 — Set Up the Learner Portal (Experience Cloud)

**What it does**: Deploys student-facing portal with Action Center, Pulse Checks, Career Planning, Degree Planning.

**Prerequisites**: Experience Cloud license required.

**Setup path**:
1. Navigate to Setup → Digital Experiences → All Sites
2. Create new Experience Cloud site or configure existing site
3. Add Student Success components:
   - Action Center (tasks, alerts)
   - Pulse Checks (wellness check-ins)
   - Career Planning
   - Degree Planning
   - Appointment booking
4. Configure access for authenticated students
5. Publish and activate the portal

**Verification**: Navigate to portal URL and verify components load for student users.

---

