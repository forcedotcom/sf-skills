# Permissions & sharing foundation

Read at Workflow steps 4–6, 9 & 10. Each create/change here walks the **three-tier ladder** (see `execution-model.md`): **tier 1** `/headless/metadata` if the type is allowlisted, else **tier 2** `sf`-deploy of local source (needs a shell), else **tier 3** Setup-UI. The tier per operation is called out below. Every step ends in a **concrete verify call** so the agent confirms org state after the change — do not assume success.

> **Tiering summary.** **OWD** (`CustomObject` `sharingModel`), **RecordType** create, `ApplicationRecordTypeConfig`, and the **Campaign Type picklist value** all have a **tier-1** path; only **sharing-rule create** and **record-type→profile visibility** are tier-3 gaps. **SOQL `/query`/`/tooling/query` route over `dispatch_readonly` (tier 1)** — so every verify below is a tier-1 attempt first, with `sf` (tier 2) / UI as the fallback (including for a transient `/query` outage window — see `execution-model.md`).

- **`PermissionSet` is on the `/headless/metadata` allowlist (CRUD).** But the **cloning path used here is plain sObject REST + the collections API, not `/headless/metadata`** (see Step 4b): `POST /sobjects/PermissionSet` → `POST /composite/sobjects` for the object/field-perm rows → `POST /sobjects/PermissionSetAssignment`. All tier 1, granular, per-row errors.
- **OWD (`CustomObject` `sharingModel`) — TIER 1.** `PUT /services/data/vXX/headless/metadata` with `{type:"CustomObject", fullName:"<obj>", xmlRep:"<CustomObject …><sharingModel>Read</sharingModel></CustomObject>"}` → `200 {success:true}`. Only **internal** OWD is set (external stays Private). **`ActionPlanTemplate` is the one exception — tier-3-UI-only**; see Step 5 for the root cause and the don't-hardcode rule.
- **`RecordType` create — TIER 1.** `POST /services/data/vXX/tooling/sobjects/RecordType` with the **nested** body `{FullName:"<Obj>.<DevName>", Metadata:{active:true, label:"<Label>"}}` → 201. A `400 JSON_PARSER_ERROR` means the body used flat columns instead of the nested `Metadata` object — fix the shape, don't fall back. See Step 6.
- **Campaign `Type` picklist value — TIER 1.** `PUT /headless/metadata type:StandardValueSet fullName:CampaignType` (whole-set replace). See Step 6.
- **Sharing-rule create is a tier-1/2 gap → tier-3 UI.** See Step 6b for the exact error and why the sibling deploy skills can't help either.
- **Record-type→profile visibility is a tier-3-UI step** (tooling PATCH on `Profile` is unsupported; the only API write is a whole-file `Profile` MDAPI replace, too high-blast-radius for a 3-click task). See Step 6.

## Configure vs. verify at a glance

| Step | Operation | Best tier | **Verify call** |
|---|---|---|---|
| 4a | Assign the **Admin/builder** persona's sets (the AI Agent Access **clone** goes to the Einstein Agent User at **step 9**, not here — that user doesn't exist until Claude creates it as part of step 9) | **T1** — `PermissionSetAssignment` sObject POST | query PSA (below) — attempt T1 `/query`, `sf` fallback |
| 4b | Clone + customize `EducationCloudAiAgentAccess` (**required** — OOTB set is an empty shell) | **T1** — sObject `POST /sobjects/PermissionSet` + `/composite/sobjects` for obj/field perms + PSA POST (NOT `/headless/metadata`) | query the cloned PS + its perms (below) |
| 5 | OWD → Public Read Only on 6 objects | **T1** — `PUT /headless/metadata CustomObject sharingModel` (5/6); **`ActionPlanTemplate` is T3-UI-only** (`IsCustomizable=false`) | tooling query `EntityDefinition.InternalSharingModel` — attempt T1 `/tooling/query`, `sf` fallback |
| 6a | Campaign "Recruitment Event" picklist value | **T1** — `PUT /headless/metadata StandardValueSet:CampaignType` (whole-set replace) | query picklist value (below) |
| 6b | Campaign "Campus Tours" sharing rule | **T3** — `SharingCriteriaRule`/`SharingOwnerRule` CREATE is a real MDAPI gap (fails at T1 AND `sf`) → UI | query sharing rule (below) |
| 6c | Individual Application record type | **T1** — `POST /tooling/sobjects/RecordType` nested `{FullName,Metadata}` | query `RecordType` (below) |
| 6d | `ApplicationRecordTypeConfig` (registers the RT into the admissions feature) | **T1** — `POST /tooling/sobjects/ApplicationRecordTypeConfig` | tooling query `ApplicationRecordTypeConfig` (below) |
| 6e | Record type → profile visibility (3 profiles) | **T3** — tooling PATCH on `Profile` unsupported; only API write is whole-file `Profile` MDAPI replace (too risky) → UI | tooling GET Profile `recordTypeVisibilities` (below) |

## Step 4 — Clone, customize, and assign the Education Cloud AI Agent Access permission set

> **CRITICAL: DO NOT assign the OOTB `EducationCloudAiAgentAccess` — it is an EMPTY SHELL.** The standard set (one of the 5 canonical EDU standard permission sets) ships with **0 object perms, 0 field perms, every `Permissions*` boolean false**. Assigning it to the Einstein Agent User grants **nothing**, yet reads like the agent has Education Cloud access — actively misleading. It exists to be **cloned FROM**. So **4b (clone + customize) is REQUIRED, not optional.** **CRITICAL: Order within Step 4: assign the Admin/builder persona to the running user FIRST (4a), THEN build the clone (4b)** — the builder sets (especially *Education Cloud Full Access* + *Einstein for Education Cloud Access*) are what make the **license-gated EDU object fields visible** to the running admin; without them the objects show **0 fields** in Object Manager and 4b's field-matrix build has nothing to reference. Only the clone's **Einstein-Agent-User** assignment is deferred to step 9 (that running user doesn't exist until agent creation at that step).

**Step 4a (DO THIS FIRST — before building the clone in 4b) — Assign the Admin/builder persona to the running user; DEFER the clone's Einstein-Agent-User assignment to step 9 (T1, concrete call):**

The clone's assignment to the **Einstein Agent User** cannot happen at step 4 — that running user doesn't exist yet, and Claude creates + grants it directly at **step 9** (see `agent-and-subagents.md` step 9, points 2–3; the full mechanism lives there, not here). What to do **here, before building the clone**: assign the **Admin/builder** persona's sets to the running user so the human can build — critically *Education Cloud Full Access* and *Einstein for Education Cloud Access*, which unlock visibility of the **license-gated EDU object fields**. **CRITICAL: Symptom if 4b runs first:** see the note above — assign these two sets first, then clone.

- **Tier 1 (headless):** `POST /services/data/vXX/sobjects/PermissionSetAssignment` via the write-enabled `dispatch` tool, one row per builder set, body `{ "AssigneeId": "<builderUserId>", "PermissionSetId": "<psId>" }`. sObject REST routes over dispatch. (`DUPLICATE_VALUE` on re-assign is benign/idempotent.)
- **Tier 2 (`sf` CLI, if a shell is present):** `sf org assign permset --name <builder set> --target-org <alias>`.
- **Tier 3 (manual):** Setup → Permission Sets → the set → Manage Assignments → Add Assignment → the builder user.

**Verify (attempt T1 `/query` over `dispatch_readonly` → `sf` fallback):**
```bash
# Tier 2 fallback:
sf data query -q "SELECT PermissionSet.Name, PermissionSet.Label FROM PermissionSetAssignment WHERE AssigneeId = '<builderUserId>'" --target-org <alias>
```
Confirm a row for each Admin/builder set from the persona table below (Agentforce Default Admin, Education Cloud Full Access, Einstein for Education Cloud Access, etc.) — a set missing from the results means the assignment didn't take.

**Step 4b — Clone + customize the full matrix (T1, sObject REST — NOT `/headless/metadata`):**

The tier-1 path is plain sObject REST + the collections API — cleaner and more granular than a metadata deploy:

1. **Create the clone** — `POST /services/data/vXX/sobjects/PermissionSet` body `{Name:"SRA_AI_Agent_Access", Label:"Education Cloud AI Agent Access (Student Recruitment Agent)", Description:"…", PermissionsAccessEducationCloud:true, PermissionsUseEducationCloudComp:true, PermissionsActionPlansUserAccess:true}` → 201. **Use the fixed `Name` `SRA_AI_Agent_Access`** (`Name` is the PermissionSet API/developer key — there is no separate `developerName` field on this sObject) so step 9 and the verify below re-find it by **exact `Name`, not a fuzzy `LIKE`**; a `DUPLICATE_DEVELOPER_NAME` on re-run means it already exists → read it back, don't treat as failure. **The three "system permissions" are boolean COLUMNS on the PermissionSet record**, set inline at create: *Access Education Cloud Objects* = `PermissionsAccessEducationCloud`; *Access Education Cloud Components* = `PermissionsUseEducationCloudComp`; *Access the Action Plans feature* = `PermissionsActionPlansUserAccess`. (Do NOT hunt for `CustomPermission`/`SetupEntityAccess` — wrong surface.)
2. **Object perms** — `POST /services/data/vXX/composite/sobjects` (`allOrNone:false`) with one `ObjectPermissions` row per object. Row shape: `{"attributes":{"type":"ObjectPermissions"}, "ParentId":"<clonePsId>", "SobjectType":"AcademicInterest", "PermissionsRead":true, "PermissionsCreate":true}` (omit or set `false` the perms you don't grant; `PermissionsRead` is required for any other object perm). **CRITICAL: `EducationalInfoRequest` Read requires `Case` Read** (`FIELD_INTEGRITY_EXCEPTION: depends on Read Case`) — the SRA help doc's object list omits `Case`; **add it**. Objects (all R unless noted): AcademicInterest (C,R), Account (C,R), AcademicTerm, ActionPlan, ActionPlanTemplate, ApplicationStageDefinition, ApplicationTimeline, Campaign, Contact, ContactRequest, EducationalInfoRequest, IndividualApplicationTask, Learning, LearningProgram, `PreliminaryApplicationRef`, `ProgramTermApplnTimeline`, **+ `Case` (R)**. (17 objects — the 16 above plus `Case`; `/composite/sobjects` caps at 200 rows/call, so one call covers all.)
3. **Field perms** — `POST /services/data/vXX/composite/sobjects` (`allOrNone:false`) with one `FieldPermissions` row per field. Row shape: `{"attributes":{"type":"FieldPermissions"}, "ParentId":"<clonePsId>", "SobjectType":"AcademicInterest", "Field":"AcademicInterest.ReceivedDate", "PermissionsRead":true, "PermissionsEdit":true}` — **CRITICAL: `SobjectType` is its own required column, even though `Field` is already fully-qualified** — omitting it 400s; it is not redundant with `Field`. `Field` is the fully-qualified `SobjectType.FieldName`, and `PermissionsEdit:true` requires `PermissionsRead:true` on the same row. Fields (R = `PermissionsRead` only; R+E = both): AcademicInterest{AcademicTermId, AccountId, ContactId, ContactRequestId, EducationalInfoRequestId, LearningProgramId, ReceivedDate, Subscription}=R+E; AcademicTerm{IsActive, StartDate}=R; ApplicationTimeline{ApplicationCategory, ApplicationCloseDate, ApplicationCloseDateTime, ApplicationOpenDate}=R; Contact{AccountId}=R; IndividualApplicationTask{ApplicationStageDefinitionId}=R; Learning{AcademicLevel}=R; LearningProgram{AcademicLevel, IsActive}=R; ProgramTermApplnTimeline{AcademicTermId, ActionPlanTemplateVersionId, ApplicationTimelineId, LearningProgramId}=R.

> **CRITICAL: API-name traps (fail hard on a wrong `SobjectType`/`Field`):** "Preliminary Application Reference" → **`PreliminaryApplicationRef`** and "Program Term Application Timeline" → **`ProgramTermApplnTimeline`** (both truncated — full spellings 404). Use exact API names; resolve field API names via `/sobjects/<Obj>/describe` (label→name) rather than `FieldDefinition` queries, which can 404 for metadata-entity lookups.

**Verify the clone was built correctly (attempt T1 `/query` over `dispatch_readonly` → `sf` fallback):**
```bash
# Tier 1 first (dispatch_readonly): GET /services/data/vXX/query?q=<the SOQL below, URL-encoded>
# Tier 2 fallback:
sf data query -q "SELECT Id, Name, Label, IsCustom, PermissionsAccessEducationCloud, PermissionsUseEducationCloudComp, PermissionsActionPlansUserAccess FROM PermissionSet WHERE Name = 'SRA_AI_Agent_Access'" --target-org <alias>
```
Confirm the clone is `IsCustom:true` with all three system booleans true (`PermissionsAccessEducationCloud`, `PermissionsUseEducationCloudComp`, `PermissionsActionPlansUserAccess`). The clone→Einstein-Agent-User PSA (and its `PermissionSetAssignment WHERE PermissionSet.Name = 'SRA_AI_Agent_Access'` verify) is confirmed at **step 9**.

That query only confirms the 3 system booleans on the parent `PermissionSet` row — it never checks that the 17 `ObjectPermissions` and 23 `FieldPermissions` child rows from points 2–3 above actually landed (the `/composite/sobjects` calls are `allOrNone:false`, so a partial failure on some rows returns `200` alongside the successful ones). Verify those too:
```bash
sf data query -q "SELECT SobjectType FROM ObjectPermissions WHERE ParentId='<clonePsId>'" --target-org <alias>
sf data query -q "SELECT Field FROM FieldPermissions WHERE ParentId='<clonePsId>'" --target-org <alias>
```
Expect **17** `ObjectPermissions` rows (the 16 objects + `Case`) and **23** `FieldPermissions` rows. A short count means some rows 400'd silently in the composite call — check each row's `errors[]` in the original response before re-sending just the missing ones.

> **Do NOT clone per-subagent.** Clone the permission set **once** and assign that single clone. A per-subagent object/field breakdown (Create Admissions Application / Campus Tours / FAQ / Escalation) is useful only as a field-level reference for what each subagent touches — it must never become a series of setup steps or separate clones.

### Three-persona permission model (this is the correct model to encode)

Permissions map to **three distinct user personas**, not one:

| Persona | Who | Permission sets |
|---|---|---|
| **Admin / builder** | The human setting up + owning the agent | Agentforce Default Admin; Education Cloud Full Access; Einstein for Education Cloud Access; **(Legacy) Data Cloud Marketing Admin** (API name `GenieMarketingAdmin` — the label resolves to the *Legacy* set; the non-legacy Data Cloud sets are Admin/Architect/Activation, a different grant); Prompt Template Manager + User; Knowledge (Lightning Knowledge Manager). PSL: Messaging — **WARNING:** the label "Messaging for In-App and Web User" is **ambiguous**: `EasyServiceMessagingSessionPsl` ("Messaging User") vs `EmbeddedServiceMessagingUserPsl` ("Enhanced Chat User"); pick per the org's messaging setup and assign by **API name**, not label. |
| **Einstein Agent User** (the Digital/Agent User the ASA agent runs as — **ASA/Service path only**; the AEA agent has no service account) | The service account the Service agent acts under | The full parity set required for this restricted-license user: **6 PermissionSetLicenses** (`PermissionSetLicenseAssign`, assign first — this restricted-license user's other assignments fail `FIELD_INTEGRITY_EXCEPTION` without them): `AgentforceServiceAgentUserPsl`, `EducationCloudAiAgentUserPsl`, `AgentforceServiceAgentBuilderPsl`, `EinsteinGPTPromptTemplatesPsl`, `EasyServiceKnowledgeBasePsl`, `GenieDataPlatformStarterPsl`. **8 PermissionSetAssignments**: `AgentforceServiceAgentBase`, `AgentforceServiceAgentUser`, `AgentforceServiceAgentBuilder`, `ServiceLightningKnowledgeManager`, `EinsteinGPTPromptTemplateUser`, `GenieUserEnhancedSecurity`, `RunFlow`, and the **`SRA_AI_Agent_Access` clone** from step 4b (NOT the OOTB `EducationCloudAiAgentAccess` set — see the CRITICAL note above). Without the full 14-grant set, `publish`/Commit Version fails with a generic *"User doesn't have access to agent"* — a sharing-flavored message that is actually a missing-license/permission-set problem. |
| **Community user** (authenticated Experience Cloud path — **AEA agent only**) | Authenticated prospective students on the community | Clone of `EducationCloudExprcCloudAccess` — create with the **fixed `Name` `SRA_Exprc_Cloud_Access`**, Label "Education Cloud for Experience Cloud Access (Student Recruitment Agent)" (re-find by exact `Name`, same rule as the AI Agent Access clone) — with the **Run Flows** app perm (`PermissionsRunFlow`) set on the clone; **plus separate PS assignments** (not clone settings): **Prompt Template User**, Knowledge, Data Cloud starter. **This whole persona is AEA/auth-path only** — the ASA/Service agent runs under the Einstein Agent User, so an ASA-only build skips it. **Clone + config at Step 4** (same as the Einstein clone); the **Enable Agent Access → AEA agent** selection and the assignment to community users happen at **step 10** (both need the agent to exist). **Clone target differs by path** (see below). |

Each persona's *assignment* is a tier-1 `PermissionSetAssignment` POST (or `sf org assign permset` at tier 2) once the sets exist. The community-user PSL *clone* (AEA path) uses the same **tier-1 sObject-REST path as step 4b** (`POST /sobjects/PermissionSet` + `/composite/sobjects`), with `sf`-deploy / UI as tier-2/3 fallbacks (see below).

**Before the Step 4a assignment above, self-resolve the running user's Id at tier 1 — don't presuppose you already know your own display name.** A `/query WHERE Name='<current user>'` only works once something has already told you that name; when nothing has, resolve identity via the current-user/"me" lookup your runtime exposes (discover it if you don't already know which one) rather than guessing at a `WHERE` clause you can't populate yet, then reuse that Id directly. (Routes over `dispatch_readonly`.)

**Resolve Ids, then select interactively — do NOT blindly assign all three personas.** Many orgs already carry some of these sets, and the two agent-dependent personas (whichever agent paths are in scope) can't be assigned at Step 4 — they're deferred until the agent exists (Einstein Agent User at step 9, community persona at step 10 — see the sequencing below):

1. **Resolve the Einstein Agent User's Id from `BotDefinition`, not by profile.** The **Einstein Agent User exists only for the ASA/Service agent** (the AEA/Employee agent has no service account — authenticated community users invoke it as themselves). Since step 9 creates this user itself and knows its Id directly, there's no need to query it back before granting — `SELECT BotUserId FROM BotDefinition WHERE DeveloperName='<ASA agent>'` is a **verify**, not a discovery step, once step 9 is done, and should read back the exact user Id step 9 created and granted. Do **not** resolve it by `WHERE Profile.Name='Einstein Agent User'` (it can match other digital-agent users in the org). A **null** `BotUserId` at verify time means the sentinel substitution was skipped in step 9 — fix that, not an expected state. (Routes over `dispatch_readonly`.)
2. **Ask the customer which personas/users to assign** — all three, or a subset — rather than assuming. Then assign per their selection.
3. **Skip duplicates** — a `DUPLICATE_VALUE` error on an existing assignment is benign/idempotent; don't treat it as a failure.
4. **Sequencing — only the Admin/builder persona is assigned at Step 4; the other two are agent-dependent.** Einstein Agent User grant → step 9; community agent-access-enable + user assignment → step 10. See the persona table above for what each grant is and why — same fact, not a new one.

### The unauthenticated path has NO guest user — do not build a guest PSL

The Service (ASA) path runs entirely under the **Einstein Agent User** service account (the three-persona model above); there is **no guest/unauthenticated Salesforce user in the SRA model**, so do **not** clone or assign a guest permission-set license (e.g. `EducationCloudGuestAccessPsl`). The ASA's Education Cloud access is the `SRA_AI_Agent_Access` clone of `EducationCloudAiAgentAccess` (built step 4b), assigned to the agent's running user at step 9. The only cloned community set is for the **authenticated** path:

- **Authenticated community (AEA only)** → clone `EducationCloudExprcCloudAccess`; its license is `EducationCloudExprcCloudAccessPsl`.

## Step 5 — OWD (internal) → Public Read Only on 6 objects

Set internal OWD to **Public Read Only** on exactly these 6:

1. Academic Interest
2. Academic Term
3. Action Plan Template
4. Application Timeline
5. Learning
6. Program Term Application Timeline

**NOT** Learning Program (it's `ControlledByParent` — can't set OWD on a child-controlled object), **NOT** Campaign (Campaign uses a sharing rule instead — step 6). **NOT** Individual Application (it gets RecordTypes at step 6, not OWD).

> **CRITICAL: API-name correction:** the 6th object's real API name is **`ProgramTermApplnTimeline`** ("Application"→"Appln"), NOT `ProgramTermApplicationTimeline`. The full spelling doesn't exist as an entity, so a verify query using it silently returns 0 rows for that object → the customer thinks OWD is set when the object was never touched. (Note the sibling `ApplicationTimeline` keeps its full spelling — only the compound name is truncated.)

- 🟡 **OWD (`CustomObject` `sharingModel`) — attempt Tier 1, but confirmed to fail org-wide on at least one gateway.** `PUT /services/data/vXX/headless/metadata` body `{type:"CustomObject", fullName:"<obj>", xmlRep:"<CustomObject xmlns=\"http://soap.sforce.com/2006/04/metadata\"><sharingModel>Read</sharingModel></CustomObject>"}` → attempt for all 6 objects. Only **internal** OWD is set; `ExternalSharingModel` stays Private (intended). Cold-verify the write with the read below — a `200`/`success:true` alone is not proof the value changed. ⚠️ **Confirmed failure mode:** on some orgs, ALL 6 — not just `ActionPlanTemplate` — return `400 UNSUPPORTED_OPERATION: MetadataCrud does not support UPDATE on type: CustomObject`, including a retry using `externalSharingModel` instead of `sharingModel`. On this exact error, drop straight to Setup UI for all 6 — don't retry reshaped, and don't assume the other 5 are fine just because they're not `ActionPlanTemplate`.
  - **CRITICAL: `ActionPlanTemplate` has its own, separate, always-true exception → T3-UI-only regardless of the above.** Root cause: `EntityDefinition.IsCustomizable=false` (the other 5 are `true`) — MDAPI rejects it as a "non-customizable CustomObject" (`500`), and `sf` hits the identical wall. This is a *different* failure than the blanket `UNSUPPORTED_OPERATION` above — object-specific, not gateway-specific — so `IsCustomizable` alone doesn't predict the broader failure; check it only to confirm this one exception.
  - **Tier 2 (`sf`, fallback):** deploy each object's `sharingModel = Read` via `sf project deploy start`.
  - **Tier 3 (manual):** Setup → Sharing Settings → Edit → set the object's Default Internal Access to **Public Read Only** → Save.

**Verify OWD (attempt T1 `/tooling/query` over `dispatch_readonly` → `sf` fallback):** **WARNING:** `EntityDefinition` **rejects disjunctions** (`WHERE … OR …` → `400 MALFORMED_QUERY: Disjunctions not supported`) — use an `IN (...)` list (below) or separate filtered queries.
```bash
# Tier 1 first (dispatch_readonly): GET /services/data/vXX/tooling/query/?q=<the SOQL below, URL-encoded>
# Tier 2 fallback:
sf data query --use-tooling-api -q "SELECT QualifiedApiName, InternalSharingModel, ExternalSharingModel, IsCustomizable FROM EntityDefinition WHERE QualifiedApiName IN ('AcademicInterest','AcademicTerm','ActionPlanTemplate','ApplicationTimeline','Learning','ProgramTermApplnTimeline')" --target-org <alias>
```
Confirm `InternalSharingModel = 'Read'` for all 6. (Note `ProgramTermApplnTimeline` — the corrected API name.)

## Step 6 — Topic-specific prep

### 6a — Campaign "Recruitment Event" picklist value (Campus Tours) — 🟡 Tier 1 attempt (confirmed org-dependent)
Add a **"Recruitment Event"** value to Campaign **Type** (backing set `StandardValueSet:CampaignType`).
- **Tier 1:** `PUT /services/data/vXX/headless/metadata`, `type:StandardValueSet`, `fullName:CampaignType`, `xmlRep` listing **all existing values + Recruitment Event** → `200 {success:true}`. **WARNING: Whole-set-replace semantics — you MUST echo every existing value** or the omitted ones are deleted. Read current values first (e.g. `ui-api/object-info/Campaign/picklist-values/{rtId}/Type`). ⚠️ **Confirmed failure mode:** both this write and a direct read (`GET .../headless/metadata?type=StandardValueSet&fullName=CampaignType`) can 400 `UNSUPPORTED_OPERATION: MetadataCrud does not support READ/UPDATE on type: StandardValueSet` on some orgs. On that error, go straight to Tier 2/3 — don't retry reshaped.
- **Tier 2/3 fallback:** `sf`-deploy the `StandardValueSet` source, or Setup → Object Manager → Campaign → Fields → Type → New value.

**Verify (attempt T1 `/query` → `sf` fallback):**
```bash
# Tier 2 fallback:
sf data query --use-tooling-api -q "SELECT Metadata FROM FieldDefinition WHERE EntityDefinition.QualifiedApiName='Campaign' AND QualifiedApiName='Type'" --target-org <alias>
```

### 6b — Campaign "Campus Tours" criteria sharing rule — CONFIRMED GENUINE MDAPI GAP → TIER 3 UI
Criteria-based Campaign sharing rule: `Type = Recruitment Event` → shared to a portal group, access **Read Only**.
- **CRITICAL: `SharingCriteriaRule`/`SharingOwnerRule` CREATE is unsupported through ANY MDAPI path.** Attempt: `POST /headless/metadata` with the correct `<SharingRules><sharingCriteriaRules>…</sharingCriteriaRules></SharingRules>` shape → `400 UNSUPPORTED_OPERATION: MetadataCrud does not support CREATE on type: SharingCriteriaRule`. Since the failure is on the CREATE *operation* (MetadataCrud), `sf`-deploy hits the **identical** wall — this is NOT a tier-1-vs-2 gap. `platform-sharing-rules-generate`/`platform-metadata-deploy` cannot help.
- **Tier 3 (the reliable path):** Setup → Sharing Settings → Campaign Sharing Rules → New. The target portal group/profile already exists in the org — Experience Cloud site setup does not create it, so this does **not** need to wait for Step 12. As a T3-UI step it's fine to defer to the end of the build if that's how the skill is sequencing its manual steps, but re-prompt for it there rather than treating step 12 as a hard dependency.
- **CRITICAL: This sharing rule's target audience is authenticated-community-only — largely an AEA concern.** The portal group it shares Campaign records to only has members on the authenticated (AEA) path; the ASA/Service agent already reads Campaign via its `SRA_AI_Agent_Access` clone's object perms (Step 4b) and doesn't need this rule. If the customer wants the AEA path, don't assume the portal group's underlying community licensing already exists — verify it first (`prerequisites.md`'s AEA community-licensing prerequisite: 4 UserLicenses + 4 Profiles). If those are missing, the "already exists in the org" assumption above doesn't hold and this step has nothing to share to yet.
- If attempting tier 1 first, use the exact router-expected shape — the `<SharingRules><sharingCriteriaRules>…</sharingCriteriaRules></SharingRules>` wrapper — so the attempt fails cleanly on the unsupported CREATE *operation* rather than on a malformed body, confirming the tier-3 fallback is genuinely required.

**Verify:** `GET /sharing/rules/Campaign` (tier 1, readonly) → confirm the `Campus_Tours` rule with `ruleType:Criteria`, `mainAccessLevel:"Read Only"`.

### 6c — Individual Application record type (Admissions Application) — 🟢 TIER 1
- **Tier 1:** `POST /services/data/vXX/tooling/sobjects/RecordType` with the **nested** body `{FullName:"IndividualApplication.Admissions_Application", Metadata:{active:true, label:"Admissions Application"}}` → 201. A `400 JSON_PARSER_ERROR` means the body used flat columns instead of the nested `Metadata` object — fix the shape, don't fall back to another tier.
- **CRITICAL: Do NOT prescribe a record-type description** — leave it to the customer (omit it). Watch the BusinessProcess coupling rule for other objects (Opportunity/Lead/Case/Solution need a paired `.businessProcess-meta.xml`; `IndividualApplication` does not).
- **Tier 2/3 fallback:** `sf project deploy start -m RecordType:IndividualApplication.<Name>`, or Setup → Object Manager → Individual Application → Record Types → New.

**Verify (attempt T1 `/query` → `sf` fallback):** use **data** `/query`, not tooling — see `execution-model.md`'s query-routing nuance (c) for why (`RecordType.DeveloperName` 400s `INVALID_FIELD` on the tooling surface).
```bash
# Tier 2 fallback:
sf data query -q "SELECT Id, Name, DeveloperName FROM RecordType WHERE SobjectType='IndividualApplication'" --target-org <alias>
```

### 6d — `ApplicationRecordTypeConfig` (registers the RT into the admissions feature) — 🟢 TIER 1
Creating the record type (6c) is necessary but **not sufficient** — Education Cloud needs a **second** record that registers that record type into the admissions feature, or the SRA admissions flow won't recognize it.
- **It's a tooling-tier entity, invisible to the data API** (`KeyPrefix 0jJ`, `IsCustomizable=false`, `PublisherId=System`) — `/sobjects/ApplicationRecordTypeConfig/describe` returns 404 and data `/query` returns `400 INVALID_TYPE`. Read + write + verify all go through `/tooling/...`.
- **Tier 1 create:** `POST /services/data/vXX/tooling/sobjects/ApplicationRecordTypeConfig` body `{DeveloperName:"Admissions_Application", MasterLabel:"Admissions Application", ApplicationUsageType:"EDU", ObjectName:"IndividualApplication", RecordTypeName:"Admissions Application"}` → 201.
- **CRITICAL: `RecordTypeName` takes the record type's LABEL** ("Admissions Application"), NOT the DeveloperName and NOT the Id (despite `idLookup:true`) — both of those return `400 INVALID_API_INPUT: "Invalid record type"`. Picklist API values: `ApplicationUsageType` = **`EDU`**; `ObjectName` = **`IndividualApplication`** (only value).

**Verify (tooling `/query`; data `/query` throws `INVALID_TYPE`):**
```bash
# Tier 2 fallback:
sf data query --use-tooling-api -q "SELECT DeveloperName, ApplicationUsageType, ObjectName, RecordTypeName FROM ApplicationRecordTypeConfig WHERE DeveloperName='Admissions_Application'" --target-org <alias>
```

### 6e — Record type → profile visibility — CRITICAL: TIER 3 UI
After 6c/6d, the record type must be made **visible to the profiles** that use it or the personas can't select it. Assign `IndividualApplication.Admissions_Application` to **Customer Community Plus User, Einstein Agent User, System Administrator**.
- **CRITICAL: The three PROFILES already exist, independent of whether their users do.** `Einstein Agent User` is a standard profile present in every org from the start — assigning record-type visibility to it does not wait on the specific running user Claude creates at step 9. Don't defer this step or tell the customer it'll come back around once that user exists; it's assignable now.
- **CRITICAL: Tooling PATCH on `Profile` is UNSUPPORTED** (`400 INSUFFICIENT_ACCESS_ON_CROSS_REFERENCE_ENTITY: Operation UPDATE cannot be applied on … Profile … through Tooling API`) — no surgical/merge write for `recordTypeVisibilities`. The only API write is `PUT /headless/metadata type:Profile` = **whole-file REPLACE** (profiles are enormous — 400+ fieldPermissions, userPermissions incl. `DigitalAgentUser`; a partial echo silently strips the rest). Too high blast radius for a 3-click task.
- **→ Tier 3 UI, per profile:** Setup → Profiles → open each of **Einstein Agent User**, **Customer Community Plus User**, **System Administrator** → Record Type Settings → Individual Application → move **Admissions Application** from Available Record Types to Selected Record Types → Save. Set default where appropriate.

> **WARNING: Page-layout *assignment* to a record type is a separate piece with no tier-1/2 path** — no `layoutAssignments` handling exists in any catalog skill. If needed, expect tier-3 UI.

**Verify (T1 readonly, one profile per call):** `GET /services/data/vXX/tooling/sobjects/Profile/{id}` → inspect `body.Metadata.recordTypeVisibilities` for the `Admissions_Application` entry (`visible:true`). **WARNING:** Two gotchas: (a) **one profile per call** (multi-row `Metadata`/`FullName` retrieval → `MALFORMED_QUERY`); (b) payload is **large** (System Administrator ~515KB) — extract only the `recordTypeVisibilities` slice.

> All five blocks (6a–6e) are hard prerequisites for their subagents. 6a/6c/6d are **T1**; 6b + 6e are tier-3-UI gaps.
