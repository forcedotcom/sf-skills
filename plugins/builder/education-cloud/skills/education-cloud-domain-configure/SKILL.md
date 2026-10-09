---
name: education-cloud-domain-configure
description: "Use this skill to configure Education Cloud domains (Student Success, Recruitment & Admissions, Academic Operations, Alumni Relations, Student Management, or Mentoring) through conversational setup. Triggers when a user wants to enable or configure Education Cloud features. Guides step-by-step: enables Person Accounts prerequisite, activates target domain, then configures domain sub-features. Covers support processes, case record types, success teams, care plans, applications, admissions, course catalog, alumni engagement, fundraising, enrollment, programs, and mentoring. Explains each feature, confirms before proceeding, verifies every change took effect, and warns that domain and feature toggles are IRREVERSIBLE. DO NOT TRIGGER for metadata generation, custom objects, or package deployment — this configures existing platform features via org settings, not metadata files."
metadata:
  version: "1.0"
  minApiVersion: "60.0"
  domains:
    - "Education"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.9.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "platform-custom-field-generate"
    - "platform-custom-object-generate"
    - "platform-metadata-deploy"
    - "platform-permission-set-generate"
    - "platform-validation-rule-generate"
  accessCheck:
    - type: "license"
      value: "Education Cloud"
---

# Configuring Education Cloud Domains

Guide users through conversational setup of Education Cloud domains. Enable Person Accounts prerequisite, activate target domain via Setup, and configure domain-specific sub-features with user confirmation at each step.

## Scope

- **In scope**: Education Cloud domain configuration (Student Success, Recruitment & Admissions, Academic Operations, Alumni Relations, Student Management, Mentoring), Person Accounts enablement, sub-feature configuration, API-first with UI fallback
- **Out of scope**: Generating custom metadata or objects (delegate to `platform-custom-object-generate`), deploying managed packages, data migration, EDA (Education Data Architecture) configuration — native Education Cloud only

---

## Required Inputs

Gather before starting:

- **Target domain**: Which Education Cloud domain to configure (Student Success, Recruitment & Admissions, Academic Operations, Alumni Relations, Student Management, or Mentoring)
- **Target org**: Active Salesforce org with admin access
- **Sub-features** (optional): Specific sub-features the user wants enabled within the domain

Defaults:
- Confirmation style: Ask before each step
- Error handling: Explain errors, suggest fixes, wait for user decision

---

## Domain & Feature Toggle Write Path (authoritative)

Every domain/sub-feature toggle lives on the `IndustriesSettings` settings file (NOT Core's `ORG_PREFERENCES` allowlist) and is **IRREVERSIBLE** (`false → true` only — warn before flipping, never promise a revert). Write sequence is always **READ (tooling GET by DurableId) → WRITE (`PUT /services/data/v68.0/headless/metadata` via the write-enabled `dispatch` tool) → cold-VERIFY (repeat the GET — `success:true` alone is not proof)**. Read `references/toggle-write-path.md` before any toggle write for the full endpoint table, exact `xmlRep` shape, the `DurableId` constant, and the confirmed failure classes (silent no-op, cold-verify 500s, license-gating).

---

## Authoring conventions

1. **Feature-first framing.** Lead with the FEATURE NAME and a plain-language description of what it does for the customer (e.g. "Enforce Time Conflicts — prevents learners registering for course offerings with conflicting schedules") — not the toggle's API element name (`enableCosConflicts`). Keep the element name only in the technical/API-call subsection.
2. **Describe before toggling.** For every feature and sub-feature, include a one-line "What it does" so the customer understands what's being enabled before confirming.
3. **List sub-features + confirm.** When a domain has sub-features, enumerate all of them and ask the customer to confirm or exclude before proceeding.
4. **Announce every C/U/D.** Before any create/update/delete, state the operation and offer approve / reject / modify.
5. **Flag manual steps.** If a step can't be done via API, note it as manual and surface it at the end of the domain's configuration.
6. **Always cold-verify.** `success:true` on a write is not proof. Re-read state (GET on the record or settings object) and confirm the intended field/element value.

---

## Execution Transport

Before first call, probe transport health: `GET /services/data/vXX.X/limits` via headless-360 dispatch. 2xx → route all calls through it. On absent/4xx/5xx → probe other available transports (other Salesforce MCP, authenticated `sf` CLI, custom MCP) with the same read, use first healthy, announce it. None healthy → stop, ask user to connect one; never fabricate.

> **SOQL routes via headless-360 — pass the query through `queryParams`, NOT inline `?q=` in `url`.** `GET /services/data/vXX.0/query` (or `/tooling/query`) with `queryParams: {"q": "SELECT ..."}` returns records normally; putting `?q=...` directly in the `url` string 404s (`ROUTE_NOT_FOUND`) — a call-shape mistake, not a platform limitation. `?fields=` on a plain sObject GET is still not supported (router treats it as an external-id path segment) — use `/describe` for field lists instead. Prefer a direct SOQL existence/Id lookup over asking the user to supply a record Id; where no REST route exists at all (license/permission provisioning UI-only), ask the user or confirm in Setup UI.

---

## Workflow

### Phase 0 — Foundation Prerequisites (Org-Level)

All Education Cloud domains require these foundation settings. Verify before proceeding to domain configuration.

1. **Check org edition** — query `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT OrganizationType FROM Organization"}` (singleton, no Id needed), then pipe the record into `scripts/check_org_edition.py --allowed "Enterprise Edition,Performance Edition,Unlimited Edition,Developer Edition"` (stdin: `{"records": [...]}`). `eligible: false` → warn user Education Cloud requires Enterprise+ edition.

2. **Check Lightning Experience** — verify Lightning Experience is enabled. If not enabled, instruct user to navigate to Setup → User Interface → Enable Lightning Experience.

3. **Check Education Cloud license** — permission set names vary by org/release (neither of two confirmed orgs shipped `EducationCloudUser`; look for `%EducationCloud%` matches instead). Query `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT Id, Name FROM PermissionSet WHERE Name LIKE '%EducationCloud%'"}` and `GET /services/data/v68.0/sobjects/BusinessProfile/describe` (capture `createable`, or `null` if it 404'd), then pipe both into `scripts/check_license_provisioned.py` (stdin: `{"permissionSets": [...], "businessProfileDescribe": {...}}`). `provisioned: false` → not provisioned, tell the user and stop. `provisioned: true` with empty `matchingPermissionSets` → treat as provisioned but note the mismatch.

4. **Assign Education Cloud Full Access** — resolve the running user's Id (ask for their username if unknown), query `GET /services/data/v68.0/query` with `queryParams: {"q": "SELECT Id, PermissionSet.Name FROM PermissionSetAssignment WHERE AssigneeId='<running user Id>' AND PermissionSet.Name LIKE '%EducationCloud%'"}`, and pipe the result into `scripts/check_permission_assigned.py` (stdin: `{"records": [...]}`). `assigned: false` → instruct user to assign the org's actual permission set (from step 3's `matchingPermissionSets`) via Setup → Permission Sets → Manage Assignments.

   > **No Bash tool available on this surface?** These scripts are local data transforms only — no org call, no credentials. Perform the equivalent comparison inline instead of skipping the check.

5. **Enable Education Cloud Foundation** — **IRREVERSIBLE — warn the user before flipping; do NOT promise a revert.** This does NOT go through the metadata PUT path (confirmed silent no-op on `enableEducationCloud`) — it needs the dedicated invoke endpoint. Read `references/toggle-write-path.md` ("Enabling the foundation") for the READ → WRITE → cold-VERIFY sequence and the UI fallback. Proceed to step 6 once cold-verify shows `true`.

### Phase 1 — Enable Person Accounts

6. **Confirm domain choice** — ask user which domain to configure if not already specified. Present list:
   - Student Success
   - Recruitment & Admissions
   - Academic Operations
   - Alumni Relations
   - Student Management
   - Mentoring

7. **Explain Person Accounts** — explain: "Person Accounts are required for Education Cloud. They allow individuals (students, applicants, alumni) to be tracked as both Accounts and Contacts in a unified record."

   > **WARNING**: Person Accounts cannot be disabled once enabled. Confirm user understands this is irreversible before proceeding.

8. **Enable Person Accounts (UI)** — Person Accounts has no supported org-preferences write API (the `setup/org/preferences/{name}` endpoint returns 404). Instruct user to navigate to Setup → Quick Find → "Account Settings" → Select Account Settings → Turn on "Enable Person Accounts" → Click Save. Wait for user confirmation toggle is ON and saved, then proceed to Phase 1.5.

    To verify: `GET /services/data/v68.0/sobjects/Account/describe` and confirm `IsPersonAccount`/`Person*` fields are present in the `fields` array; if headless routing is unavailable, fall back to `sf sobject describe -s Account` and grep for the same. This describe call is the ONLY valid verification method — do NOT run any SOQL query against `IsPersonAccount` or Person-Account fields (on `Account`, `Organization`, or any object) to check enablement status; SOQL on an unrecognized field returns `INVALID_FIELD`/"No such column", and that failure does NOT mean Person Accounts is off — it means you used the wrong check.

### Phase 1.5 — Setup Basics: Dependent Features & Data Space Mapping

This mirrors Setup's own "Setup Basics" grouping (Person Accounts, Dependent Features, Data Space Mapping) that sits before the domain sections. Several dependent features are referenced by more than one domain's sub-features, so configuring them here avoids re-discovering them mid-domain.

9. **Present Dependent Features** — read `references/dependent-features.md` and present the full list to the user, grouped by category (confirmed API toggle / manual-UI-only / untested), leading with feature name + one-line "what it does", not the API element name. **Always present this list and ask which to enable now**, even if the user declines all of them — record that decision explicitly and proceed to Phase 2 rather than skipping the step. Anything declined can be revisited later.

10. **Configure each selected Dependent Feature** — `references/dependent-features.md` categorizes every feature into one of four shapes; look up the selected feature there for its exact element names, DurableIds, and gotchas:
    - **Confirmed `IndustriesSettings` toggle** — IRREVERSIBLE, warn user. Use the **Domain & Feature Toggle Write Path**: READ → WRITE (`PUT /services/data/v68.0/headless/metadata`) → cold-VERIFY.
    - **Confirmed toggle via a different mechanism** (e.g. Einstein Generative AI master toggle) — a Setup-Connect **org preference**, not `IndustriesSettings`: `GET /services/data/v68.0/setup/org/preferences/<PrefName>` → `PATCH` same path with `{"desiredState": true|false}` → cold-VERIFY. Some of these are reversible — check the reference before assuming one-way.
    - **Overlaps a domain sub-feature** (several toggles are shared with Student Success and/or Mentoring sub-features) — cold-read first; if already `true` from a prior domain's configuration, report as already enabled rather than re-writing.
    - **Manual UI only, no API route** — instruct user to the Setup path in the reference. Flag where a custom permission set / object permissions are also required, not just a toggle — surface as manual follow-up.

11. **Enable OmniStudio** — OmniStudio is included with Education Cloud license. Attempt API call or instruct user to navigate to Setup → OmniStudio Settings → Enable.

12. **Enable Business Rules Engine** — Business Rules Engine is included with Education Cloud license. Instruct user to navigate to Setup → Business Rules Engine → Enable.

13. **Data Space Mapping** — via the `DataSpaceFeatureMappings` Setup Operation Recipe (`/headless/invoke/platform/data-space-feature-mappings`). Unlike most toggles in this skill, it's **reversible** (delete supported). Full pre-flight/READ/WRITE/cold-VERIFY/undo sequence, valid feature values, and status-code handling are in `references/dependent-features.md` ("Data Space Mapping" section). If the pre-flight check fails or any invoke call errors, fall back to manual UI (Setup → "Set Up Education Cloud" → Data Space Mapping).

### Phase 2 — Enable Target Domain

14. **Explain domain purpose** — look up the selected domain in `references/domain-features.md`'s index and open the linked per-domain file (e.g. `references/domain-features/student-success.md`) to explain to user what the domain provides, including prerequisites.

15. **Check domain-specific prerequisites** — beyond OmniStudio/Business Rules Engine (already enabled in Phase 0), most domains need an added license: Experience Cloud (Recruitment & Admissions, Mentoring, and portals generally), Salesforce Scheduler (Student Success, Recruitment & Admissions), Fundraising (Alumni Relations, if using gift management), or a prior domain (Student Management requires Academic Operations already configured). See the selected domain's file under `references/domain-features/` for the full list. If prerequisites are missing, warn user and ask whether to continue with available features or provision prerequisites first.

16. **Confirm domain enablement** — **IRREVERSIBLE — one-way by design (`false → true` only).** Warn the user explicitly and do NOT promise a revert/rollback. Ask: "Ready to enable [Domain Name]? This activates domain-specific objects, fields, and setup features and CANNOT be turned off afterward."

17. **Enable the domain toggle** — each domain is an `enableXXX` field on `IndustriesSettings`. Follow the **Domain & Feature Toggle Write Path**: READ (tooling GET via DurableId) → WRITE (`PUT /services/data/v68.0/headless/metadata` with the single `<enableXXX>true</enableXXX>` element in `xmlRep`, via the `dispatch` write tool) → VERIFY (tooling GET shows `true`).

    Toggle field per domain:

    | Domain | `IndustriesSettings` field |
    |--------|----------------------------|
    | Student Success | `enableStudentSuccess` |
    | Academic Operations | `enableAcademicOperations` |
    | Mentoring | `enableMentoring` |
    | Alumni Relations | `enableAlumniRelations` |
    | Recruitment & Admissions | **No master toggle** — configured via 2 independent sub-feature settings (`enableApplnDecStdSharing`, `enableAppMaterialsProtection`); skip this step, go to `references/domain-features/recruitment-admissions.md` "Enablement & Toggles" |
    | Student Management | `enableStudentManagement` |

    On success (`200 { success: true }`, synchronous, no polling), proceed to step 18. On failure, instruct user to navigate to Setup → "Set Up Education Cloud" → the domain section (e.g., "Set Up the Student Success App") → turn on the domain toggle → Save, and wait for confirmation.

18. **Verify domain active** — the step-17 cold-verify (`Is<Domain>Enabled` = `true`) already confirms the toggle. To confirm object provisioning, `GET /services/data/v68.0/sobjects/CaseTeamTemplate/describe`: 200 means the object exists (domain active); 404/NOT_FOUND → wait 1-2 minutes for async provisioning and retry. A SOQL `SELECT count() FROM <Object>` via `queryParams` also works.

### Phase 3 — Configure Sub-Features

19. **Read sub-feature reference** — load the selected domain's file under `references/domain-features/` to identify available sub-features and their detailed setup steps.

20. **Present sub-feature options** — list the sub-features available for the domain (per the domain's `references/domain-features/` file) and ask user which to configure. Student Success has a required execution order (Support Process → Case Record Types → Success Teams → Care Plans → Support Programs → Salesforce Scheduler → consoles/portal); the other domains' sub-features are independent of each other.

21. **Configure each selected sub-feature** — explain what it does, warn if irreversible, confirm with user, then follow the exact setup path in the domain's `references/domain-features/` file (covers all five shapes: record creation via Data/Tooling API, `IndustriesSettings` toggles via the Toggle Write Path, app/console setup, Experience Cloud portal setup, OmniStudio activation — with endpoints, body shapes, gotchas, and verification per sub-feature). Toggles follow the same IRREVERSIBLE + READ→WRITE→cold-VERIFY rule as domain toggles; cold-read first if already set from Phase 1.5. On API failure, fall back to the Setup UI path in the reference.

22. **Summary** — after all sub-features configured, list what was enabled via which method (API, UI, OmniStudio). Report any failures or manual steps required. If suggesting next steps, limit them to genuine blockers/dependencies actually surfaced during this session (e.g. a prerequisite that's still off, a sub-feature the user asked about but deferred) — not a generic list of every related feature or domain regardless of relevance.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Foundation, Person Accounts, OmniStudio, and Business Rules Engine must be enabled before any domain | Domains depend on these foundation objects/settings, and on OmniStudio/BRE for portal components and policy rules |
| Always confirm with user before each step and explain what a feature does first | Conversational workflow pattern — no commands without explicit user approval or understanding |
| Wait for user confirmation after UI fallback steps, and cold-verify after every enablement | Never assume success — re-read state (tooling GET, describe, record GET, or `SELECT ...` via `queryParams`) |
| Check domain-specific prerequisites before domain enablement | Some domains need added licenses or a prior domain already configured |
| Use the `scripts/` helpers for Phase 0 checks, not inline prose logic | Deterministic, fast, no org call/credentials — run the equivalent comparison inline only if no Bash tool is available |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Education Cloud license not provisioned | Contact Salesforce account team to provision the license before proceeding |
| Person Accounts, Education Cloud Foundation, and domain toggles cannot be disabled once ON | Warn user before attempting enablement — this is a one-way operation |
| `setup/org/preferences/{name}` returns 404 for EDU toggles | Not in the ORG_PREFERENCES allowlist — write via `PUT /services/data/v68.0/headless/metadata` instead |
| Tooling sObject `PATCH` on `IndustriesSettings` returns 400 `JSON_PARSER_ERROR` | complexvalue fields reject PATCH — use the headless metadata PUT path; tooling GET is for read/verify only |
| Tooling GET needs the real `DurableId`, not `000000000000000AAA` | Query `SELECT Id,DurableId FROM IndustriesSettings` first |
| Domain/sub-feature enablement may take 1-2 minutes to propagate | If verification returns nothing right after the API call, wait 2-3 minutes and retry |

See `references/toggle-write-path.md` for the AURA-IS-CANONICAL silent no-op, cold-verify 500, and license-gating failure classes, and `references/gotchas-extended.md` for lower-frequency gotchas.

---

## Final Verification Checklist (Irreversible Writes)

Before reporting any of the following as complete, confirm both boxes for that write:

- [ ] **Education Cloud Foundation** — user was warned it cannot be turned off, and cold-verify (`educationCloudEnabled: true` on a fresh read) passed after enabling.
- [ ] **Person Accounts** — user was warned it cannot be disabled once enabled, and `Account` describe confirms `IsPersonAccount`/`Person*` fields are present.
- [ ] **Each domain toggle enabled this session** — user confirmed "cannot be turned off afterward" before the write, and the tooling GET cold-verify shows `Is<Domain>Enabled: true`. (Object-describe in step 18 confirms object provisioning only — not a substitute for this cold-verify.)
- [ ] **Each irreversible sub-feature/dependent-feature toggle enabled this session** — user confirmed before the write, and cold-verify shows the field is `true`.

Do not include a feature in the final summary as "enabled" unless both its approval and cold-verify boxes are checked.

---

## Output Expectations

This skill produces no files — configuration happens via Setup navigation, CLI commands, or API calls. Expected outputs: conversational confirmation after each step, verification results showing configuration is active, error messages with suggested fixes on failure, and a final summary listing all configured features.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Create custom objects for Education Cloud | `platform-custom-object-generate` |
| Create custom fields on Education Cloud objects | `platform-custom-field-generate` |
| Generate validation rules | `platform-validation-rule-generate` |
| Configure permission sets | `platform-permission-set-generate` |
| Deploy metadata packages | `platform-metadata-deploy` |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/domain-features.md` | Index of per-domain reference files — start here to find the right file for the selected domain |
| `references/domain-features/<domain>.md` | Phase 2 step 14 (explain domain purpose), Phase 3 step 19 (identify sub-features), Phase 3 step 21 (sub-feature configuration setup paths and API preference names) |
| `references/dependent-features.md` | Phase 1.5 steps 11-12 (Setup Basics — present and configure Dependent Features before any domain), and whenever the user asks about a cross-product feature not owned by one domain — surface as "Set Up Dependent Features" and note domain overlap where relevant |
| `references/gotchas-extended.md` | When an error doesn't match one of the 10 entries in the Gotchas table above |
| `scripts/check_org_edition.py` | Phase 0 step 1 (org edition check) |
| `scripts/check_license_provisioned.py` | Phase 0 step 3 (Education Cloud license check) |
| `scripts/check_permission_assigned.py` | Phase 0 step 4 (Education Cloud Full Access assignment check) |
