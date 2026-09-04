# Set Up Dependent Features — Cross-Product Toggles

"Set Up Dependent Features" in Setup → Set Up Education Cloud enables and configures cross-product features that make the most of Education Cloud. These are **not owned by a single domain** — some overlap with sub-features referenced in the per-domain files under `domain-features/` (noted per feature below). Present these to the customer as their own group, separate from the 6 domains, but cross-reference domain overlap when relevant.

This is part of Setup's own "Setup Basics" grouping (Person Accounts → Dependent Features → Data Space Mapping) that sits before the domain sections. Configuring Dependent Features is **recommended, not required**, before enabling a domain — **always ask the user which of these they want enabled**, since most are optional and several only matter once a specific domain sub-feature needs them.

Same method as everywhere else in this skill: READ (tooling GET by `DurableId`) → WRITE (`PUT /services/data/v68.0/headless/metadata`, via the write-enabled `dispatch` tool) → cold-VERIFY (repeat GET — `success:true` alone is not proof).

---

## Clean wins — `IndustriesSettings`, first-try, no gotcha

Same object/DurableId as domain toggles (`IndustriesSettings`, DurableId `bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=`, `fullName: Industries`). IRREVERSIBLE — warn before flipping.

| Feature | What it does | Metadata element | Flat read field | Notes |
|---------|---------------|-------------------|------------------|-------|
| Care Plans | Lets staff create structured plans (goals, tasks, barriers) to support a student's wellbeing or case, tracking progress over time | `enableCarePlansPreference` (NOT `enableCarePlans` → `FIELD_INTEGRITY_EXCEPTION`) | `IsCarePlansPreferenceEnabled` | Same toggle as Student Success Step 4 (`domain-features/student-success.md`) — run AFTER Success Teams, BEFORE Support Programs per executed order |
| Case Proceedings | Manages formal hearings/proceedings tied to a case (e.g., disciplinary hearings), tracking participants, decisions, and outcomes | `enableCaseProceedingsPref` | `IsCaseProceedingsPrefEnabled` | Overlaps Student Success case workflows |
| Case Referral | Lets staff refer a case/student to another team, department, or service provider for additional support | `enableCaseReferralPref` | `IsCaseReferralPrefEnabled` | Overlaps Student Success case workflows |
| Einstein Academic Insights | AI-driven insights (built on Data Cloud) highlighting academic risk factors or trends for students, helping advisors intervene early | `enableAcademicInsightsAI` | `IsAcademicInsightsAiEnabled` | License-gated (Einstein GenAI) — write succeeds regardless of license; feature itself won't function without the license |
| Einstein Advising Summary | Uses generative AI to summarize a student's advising history/interactions so advisors get up to speed quickly | `enableAdvisingSummaryAI` | `IsAdvisingSummaryAiEnabled` | Overlaps Student Success (Advisor Console); license-gated same as above |
| Turn On Record Alert Access | Displays contextual alerts/banners on records (e.g., "Student on academic probation") to flag important info to staff | `enableRecordAlertCustomSharingPref` | `IsRecordAlertCustomSharingPrefEnabled` | Overlaps Student Success Performance Alerts |
| Program and Benefit Management (4 toggles) | Manages enrollment in programs and benefits (e.g., financial aid, services), including eligibility and assignment | `enableBenefitManagementPreference`, `enableBenefitAndGoalSharingPref`, `allowBenefitAssignmentWithInactiveProgramEnrollment`, `enableProgramCohorts` | `IsBenefitManagementPreferenceEnabled`, `IsBenefitAndGoalSharingPrefEnabled`, `AllowBenefitAssignmentWithInactiveProgramEnrollment`, `IsProgramCohortsEnabled` | Same 4 toggles as Student Success "Support Programs" (`domain-features/student-success.md` Step 5) and Mentoring "Set Up Mentoring Programs" (`domain-features/mentoring.md` Step 2) — idempotent, cold-read first and skip any already `true` |
| Salesforce Scheduler for Education Cloud (org prefs only) | Lets students/staff book appointments (advising, tutoring) directly with the right staff member based on availability | `enableEventManagementOrgPref`, `enableShareSaWithArOrgPref` | `IsEventManagementOrgPrefEnabled`, `IsShareSaWithArOrgPrefEnabled` | **Partial** — same 2 API-writable prefs as Student Success Scheduler step (`domain-features/student-success.md` Step 6); the Scheduler master enable itself is license-gated (Field Service) and manual/UI only |

**API call** (one PUT can flip several at once):
```http
PUT /services/data/v68.0/headless/metadata
```
```json
{
  "type": "IndustriesSettings",
  "fullName": "Industries",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><IndustriesSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableCaseProceedingsPref>true</enableCaseProceedingsPref><enableCaseReferralPref>true</enableCaseReferralPref><enableAcademicInsightsAI>true</enableAcademicInsightsAI><enableAdvisingSummaryAI>true</enableAdvisingSummaryAI><enableRecordAlertCustomSharingPref>true</enableRecordAlertCustomSharingPref></IndustriesSettings>"
}
```

**Verification** (cold read): `GET /services/data/v68.0/tooling/sobjects/IndustriesSettings/bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=` — confirm each `.Metadata.<element>` and its flat `Is*Enabled` read `true`.

---

## Different sObject — own `DurableId`/`fullName`, not `IndustriesSettings`

These live on their own settings sObjects. Same PUT/GET shape, but different `type`, `fullName`, and `DurableId` — do not use the `IndustriesSettings` DurableId for these.

### Checklist Items w/ Attachments — `DocumentChecklistSettings`

- **What it does**: lets staff define required documents/items for a process (e.g., admissions) and track submission status, including attachments per checklist item.
- **Setup label**: Checklist Items w/ Attachments
- **sObject / fullName**: `DocumentChecklistSettings`, `fullName: DocumentChecklist`
- **Metadata element**: `deleteDCIWithFiles` — exact case matters (two wrong-case guesses failed before this one landed)

```http
PUT /services/data/v68.0/headless/metadata
```
```json
{
  "type": "DocumentChecklistSettings",
  "fullName": "DocumentChecklist",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><DocumentChecklistSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><deleteDCIWithFiles>true</deleteDCIWithFiles></DocumentChecklistSettings>"
}
```

**Verification** (cold read, own DurableId — resolve it first with a SOQL query via `queryParams`, no need to ask the user):
```http
GET /services/data/v68.0/tooling/query
```
`queryParams: {"q": "SELECT Id, DurableId FROM DocumentChecklistSettings"}`
```http
GET /services/data/v68.0/tooling/sobjects/DocumentChecklistSettings/<DurableId>
```

### Interest Tagging — `InterestTaggingSettings`

- **What it does**: lets you tag records with interests (e.g., programs, majors) to support personalization and segmentation.
- **Setup label**: Interest Tagging
- **sObject / fullName**: `InterestTaggingSettings`, `fullName: InterestTagging`
- **Metadata element**: `enableInterestTagging`

```http
PUT /services/data/v68.0/headless/metadata
```
```json
{
  "type": "InterestTaggingSettings",
  "fullName": "InterestTagging",
  "xmlRep": "<?xml version=\"1.0\" encoding=\"UTF-8\"?><InterestTaggingSettings xmlns=\"http://soap.sforce.com/2006/04/metadata\"><enableInterestTagging>true</enableInterestTagging></InterestTaggingSettings>"
}
```

**Verification** (cold read, own DurableId — resolve via SOQL first):
```http
GET /services/data/v68.0/tooling/query
```
`queryParams: {"q": "SELECT Id, DurableId FROM InterestTaggingSettings"}`
```http
GET /services/data/v68.0/tooling/sobjects/InterestTaggingSettings/<DurableId>
```

---

## Not writable via this API surface at all — manual UI only

Feature confirmed to have no working API toggle (tested this session) — different from "not yet tested." Present these with a one-line "what it does" and the Setup path; do not attempt an API write for rows with no failure detail (Action Launcher through Accounting Subledger below) — go straight to manual UI.

| Feature | What it does | Setup label | What happens | Resolution |
|---------|---------------|-------------|--------------|------------|
| Industries Cloud Common Decision Tables Access | Business Rules Engine feature letting admins define decision logic in a spreadsheet-like table instead of code, used to drive automation (e.g., eligibility rules) | Decision Tables | `BREDecisionTableAccess` — backing call is an internal Aura action; no REST/Tooling/MDAPI route exists | Manual UI only — do not keep probing endpoints |
| Intelligent Question Generation | AI-generated follow-up questions within the Discovery Framework to dynamically tailor assessments/questionnaires | Intelligent Question Generation | `enableSmartAsmtQstnGeneration` — field exists, name correct, write returns `INSUFFICIENT_ACCESS_OR_READONLY: "cannot be accessed using the API."`. Setup surfaces this under Discovery Framework settings, but it is an independent `IndustriesSettings` field, not a sub-toggle of `enableIndustriesAssessment` | Manual UI only |
| Discovery Framework | Guided, dynamic questionnaires/assessments to gather structured information from students or applicants (e.g., needs assessments) | Discovery Framework | `enableIndustriesAssessment` — `true→false` returns HTTP 500 `UNKNOWN_EXCEPTION`. One-way confirmed; enable path (`false→true`) untested since it was already `true` in this org | Treat `true→false` as blocked; if enabling from `false`, try the standard write path first |
| Omnistudio Metadata | Low-code tools (OmniScripts, FlexCards, DataRaptors) for building guided processes and dynamic UI without heavy custom code | OmniStudio Settings | `OmniStudioSettings`, `fullName: OmniStudio` (name guessed by analogy to other settings types, confirmed working for write) — PUT succeeds, but no GET/verify path found via Tooling or EntityDefinition | Write succeeds; **parked** — confirm success via Setup UI only. Open item: find a GET/verify API for `OmniStudioSettings` — still unresolved |
| Timeline | Shows a chronological, unified view of all activities and interactions related to a record | Timeline | `TimelineSettings` — PUT returns HTTP 400 `UNSUPPORTED_OPERATION: "MetadataCrud does not support UPDATE on type: Timeline"`. Block is on the whole type — no `fullName` variant fixes it | Manual UI only |
| Video Calls | Enables built-in video calling directly from Salesforce records (e.g., for advising sessions) without leaving the platform | Video Calls | `VideoCallsSettings` — same HTTP 400 `UNSUPPORTED_OPERATION` type-level block as Timeline | Manual UI only |
| Action Launcher | Presents users with a guided list of contextual actions/tasks (e.g., macros, flows, quick actions) relevant to a record, so staff know what to do next | Action Launcher | No toggle found on `IndustriesSettings` or any tested settings sObject | Manual UI only — Setup → Quick Find → "Action Launcher" |
| Actionable Relationship Center | Visualizes relationships between records (e.g., student, household, program) as an interactive graph so users can navigate and act on related records | Actionable Relationship Center | No toggle found | Manual UI only — Setup → Quick Find → "Actionable Relationship Center" |
| Actionable Segmentation | Lets you build and act on dynamic segments of records (e.g., students meeting certain criteria) for targeted outreach or processes | Actionable Segmentation | No toggle found; enabled per linked-doc segment configuration, not a single flip | Manual UI only — see Setup Help doc for per-segment setup |
| Clause Management | Manages standardized legal/policy clause text (e.g., for contracts or agreements) so they can be reused and inserted consistently | Clause Management | No toggle found; configured via clause category setup | Manual UI only |
| Contacts to Multiple Accounts | Allows a single Contact (e.g., a student) to be associated with more than one Account (e.g., household + employer), reflecting real-world relationships | Contacts to Multiple Accounts | No toggle found; set up per linked Setup Help doc | Manual UI only |
| Disclosure and Compliance Hub | Centralizes compliance disclosures and regulatory documentation (e.g., consumer/financial disclosures) for tracking and audit | Disclosure and Compliance Hub | No toggle found; set up per linked Setup Help doc | Manual UI only |
| Group Membership | Tracks a person's membership in groups (e.g., clubs, cohorts, teams) and manages associated roles/status | Group Membership | No toggle found; set up per linked Setup Help doc | Manual UI only |
| Intelligent Document Reader | Uses AI/OCR to extract data from uploaded documents (e.g., transcripts, IDs) and populate Salesforce records automatically | Intelligent Document Reader | No toggle found | Manual UI only — flag the Government Cloud data-boundary caution from the Setup doc before enabling |
| Marketing Cloud for Education | Integrates Education Cloud data with Marketing Cloud for targeted recruitment/engagement campaigns | Marketing Cloud for Education | No toggle found; external product connection, not an org preference | Manual UI only — see Setup Help doc |
| Outcome Management | Tracks measurable outcomes/goals tied to programs or cases, letting staff manage and report on progress against defined outcomes | Outcome Management | No toggle found | Manual UI only. **Also requires a permission set** — create/assign one granting "Manage Outcomes" and "Run Flows" |
| Stage Management | Visualizes and automates a record's progress through defined stages/fulfillment plans (e.g., admissions pipeline), tracking steps and dependencies | Stage Management | No toggle found | Manual UI only. **Also requires a custom permission set** — Dynamic Common Orchestrator User plus object permissions on Fulfillment Plans, Fulfillment Steps, Fulfillment Dependencies, Fulfillment Sources, and Stage Transition Entries |
| Accounting Subledger | Tracks detailed financial transactions (tuition, fees, payments) tied to student accounts, giving institutions a sub-ledger view feeding into general accounting | Accounting Subledger | No toggle found | Manual UI only. **Also requires**: add users, set up data pipelines, create/assign permission sets — flag all three as separate manual follow-ups, not a single step |

---

## Confirmed — org preference API (different write mechanism, not `IndustriesSettings`)

Not every toggle lives on `IndustriesSettings`. This one is a **Setup-Connect org preference**, a different API surface entirely — no metadata `type`/`fullName`/`xmlRep`, just a named preference path.

### Einstein Generative AI (master toggle) — `EinsteinGPTCopilotEnabled`

- **What it does**: enables generative AI features platform-wide (e.g., drafting emails, summarizing records) within Education Cloud.
- **Setup label**: Set Up Einstein for Education Cloud → Einstein Generative AI
- **Reversible — confirmed by live test.** `PATCH` with `{"desiredState": false}` succeeds and cold-verifies `false`. Unlike most `IndustriesSettings` toggles in this skill, this one is a genuine two-way org preference.

```http
GET /services/data/v68.0/setup/org/preferences/EinsteinGPTCopilotEnabled
```
Returns `{"isPreferenceEnabled": <bool>}`.

```http
PATCH /services/data/v68.0/setup/org/preferences/EinsteinGPTCopilotEnabled
```
```json
{ "desiredState": true }
```
Response echoes the post-write state directly — `{"isPreferenceEnabled": true}`. Cold-verify with a repeat GET anyway (same discipline as everywhere else in this skill).

---

## Confirmed — Setup Operation Recipe (Aura-backed controller, not a simple metadata toggle)

### Data Space Mapping — `DataSpaceFeatureMappings`

- **Setup label**: Setup Basics → Data Space Mapping
- Binds an Education Cloud feature (`Student Success` / `STUDENT_SUCCESS` or `Financial Aid` / `FINANCIAL_AID` — the only two valid for this workflow) to a Data Cloud Data Space. **Reversible** — delete is supported, unlike most toggles in this skill.
- Requires Data Cloud (CDP) provisioned + user has Data Cloud app access. Pre-flight check tells you which.

```http
GET /headless/invoke/platform/data-space-feature-mappings
```
Returns `true`/`false` (Data Cloud provisioned + accessible). `false` → stop, fall back to manual Setup UI.

```http
GET /headless/invoke/platform/data-space-feature-mappings/get-data-spaces
GET /headless/invoke/platform/data-space-feature-mappings/get-data-space-features
```
First returns candidate Data Spaces (`devName`); second returns the two EDU-scoped feature choices (`{label, value}`).

```http
PATCH /headless/invoke/platform/data-space-feature-mappings/create-data-space-feature-mapping
```
```json
{ "feature": "STUDENT_SUCCESS", "dataSpace": "<devName>" }
```
HTTP is always 200 — check `body.status`: `'200'` success (includes `mappingId`), `'400'` duplicate (a mapping for that feature already exists — not an error), `'500'` other failure.

**Verification** (cold read):
```http
GET /headless/invoke/platform/data-space-feature-mappings/get-data-space-features-mapping
```
Confirm the new row; its `id` is the `mappingId` for delete.

**To undo** (this one supports it):
```http
DELETE /headless/invoke/platform/data-space-feature-mappings/delete-data-space-feature-mapping
```
`queryParams: {"mappingId": "<id>"}`. Not idempotent — re-deleting an already-gone `mappingId` returns `status:'500'` with a "doesn't exist" message; treat that as already-deleted, not a real error.

---

## Explicitly out of scope for this skill

- **Managed Package Runtime** — skipped at user's explicit request; do not attempt to enable.
- **Deploy Custom LWC in Standard Runtime** — skipped at user's explicit request; do not attempt to enable.
