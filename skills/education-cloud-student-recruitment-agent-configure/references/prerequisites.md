# Prerequisites, licenses, and the three SRA gates

Read this at Workflow step 1. It covers what must be true before any SRA setup step, how to **verify each gate with a concrete call**, and the license/permission matrix.

> The org's current API version is resolved at Step 0 (`SKILL.md`), before this file is ever read — every `vXX` below reuses that literal. If Step 0 hasn't run yet, run it before any check in this file, rather than guessing a version here.

## Readiness tiers

The **Tier** column below uses the three-tier ladder (see `execution-model.md`): **T1** (headless — a named `dispatch`/`dispatch_readonly` REST call over `/headless/metadata`, sObject, Connect, or Tooling-by-Id) · **T2** (`sf` CLI — MDAPI deploy / discovery query, needs a shell) · **T3** (manual UI, or a Salesforce/commercial grant the agent cannot touch).

## Prereq vs. in-skill — the scope boundary (draw this line first)

The dividing question is **"can the skill flip it via API?"**:

- **Prerequisites → verify only.** If unmet, tell the user to fix it, then **re-verify** — never enable it here. These are: the **Einstein for Education Cloud license** (P3, commercial/provisioning grant); **Education Cloud enablement** (P2 — owned by base Education Cloud domain setup); the **EinsteinGPT add-on license** (the commercial entitlement — distinct from the `EinsteinGPTPlatformEnabled` *toggle*, which IS in-skill-flippable at step 2, next bullet); and the running user being a **System Administrator**.
- **In-skill → check if present, enable if not**, through the tier ladder **Headless → other MCPs → `sf` CLI → manual UI**. These are: **Einstein Setup** (`EinsteinGPTPlatformEnabled`) and the **SRA toggle** (`RecruitmentAgentEnabled` — the skill's defining action).

## The preflight gate — run this FIRST, before any enable or build work

**Step 1 is a hard gate, not a formality.** Before enabling or configuring anything (the toggles at Step 2 onward), verify every prerequisite the skill **cannot fix itself**. If one is unmet, **do not proceed into the skill's own work** — stop, or ask the user to fix it themselves, then re-verify. Building permissions / OWD / grounding for an agent that can never exist is wasted effort; catch it here at Step 1, not when agent creation 501s at Step 9.

Classify each check into one of three outcomes:

| Outcome | Prerequisites | Action if unmet |
|---|---|---|
| **STOP** — external grant; nothing in our ecosystem can flip it | **P4** Agentforce provisioning · **P3** Einstein-for-EDU license · the **SRA Gater** (`StudentRecruitmentAgent256`) · **P5 / F-iv** Data Cloud entitlement · **P1** edition | Report exactly which grant is missing and **halt**. Request it from Salesforce / the account team. Do **not** start the toggles (Step 2). |
| **ASK-USER** — foundation this skill doesn't own, but the user can self-serve it | **P2 / F-i** EDU enablement · **F-ii** Person Accounts · **F-iii** R&A domain schema | Ask the user to complete that Education Cloud foundation setup to fill that gap, then **re-verify** and continue. Do not re-implement it here. |
| **ENABLE in-skill** — the skill flips these via the tier ladder | **Einstein Setup** (`EinsteinGPTPlatformEnabled`) · the **SRA toggle** (`RecruitmentAgentEnabled`); running-user builder PS **assignment** is likewise in-skill (Step 4) | Not a gate — Einstein/SRA toggles are the enablement step's job (item 3, `platform-enablement.md`), the PS assignment is item 4's. Check, enable if off, verify. |

**Proceed to the toggles (Step 2) only when every STOP and ASK-USER check is green.** These are definitive *now*, at Step 1 — you don't have to wait for a downstream failure to learn the answer. In particular, **provisioning is detectable here**: if `BotDefinition` is an unqueryable / `INVALID_TYPE` object (vs. a `200` with zero rows, which means "provisioned, no bots yet"), the org isn't Agentforce-provisioned — that's a STOP at Step 1, not a surprise 501 at Step 9. Use the concrete verify call for each requirement in the tables below.

> **WARNING: When reporting findings, an ENABLE-in-skill item being off is not a FAIL.** `RecruitmentAgentEnabled = false` and `EinsteinGPTPlatformEnabled = false` are the expected starting state — this skill turns them on itself at Step 2/3. Report them as not-yet-enabled/no external action needed, and reserve FAIL/STOP language for the STOP row's unmet external grants.

## Configure vs. verify — the honest split

Almost nothing here is *purely* manual. For each prerequisite, separate **can the agent configure it (and at which tier)** from **can the agent verify it**. Even the truly-manual grants get a concrete verify call so the agent confirms org state instead of assuming.

| # | Requirement | Configure? (tier) | **Verify call (run this)** | Tier |
|---|---|---|---|---|
| P1 | Edition (Enterprise / Performance / Unlimited / Developer) | **No** — commercial | Edition has no SOQL/tooling query field and no tier-1 GET (this one genuinely has no `/query` form, unlike the WHERE-filter verifies below); verify at tier 2 (`sf`) or a tier-3 UI check (Setup → Company Information).<br>Tier 2: `sf org display --target-org <alias> --json` → check `.result.edition` ∈ {Enterprise, Performance, Unlimited, Developer} | T3 |
| P2 | Education Cloud enabled | **Yes** — verify here (step 2a); if off, ask the user to enable it, then re-verify | **T1** — `dispatch_readonly` GET `/services/data/vXX/tooling/sobjects/IndustriesSettings/bWRjLzBIRS9JbmR1c3RyaWVzU2V0dGluZ3M=` (deterministic DurableId) → top-level **`IsEducationCloudEnabled == true`** (the top-level field; **not** `.Metadata.enableEducationCloud` — that's the write-path member name, see `platform-enablement.md`) | T1 |
| P3 | **Einstein for Education Cloud license** (the license gate on the SRA toggle) | **No** — **commercial/license grant — verify only** — `OrgPermissions.EinsteinForEducationCloud`, granted by the *Einstein for Education Cloud add-on*. **If absent, the `RecruitmentAgentEnabled` toggle can't be enabled** (it's part of the toggle's `editAccess`). Report it and stop — the skill can't flip a license. | **T1** — `dispatch_readonly` `/query`: `SELECT Status FROM PermissionSetLicense WHERE DeveloperName='EinsteinForEducationCloudPsl'` → confirm **`Status='Active'`** (`OrgPermissions.EinsteinForEducationCloud` itself has no SOQL surface; this PermissionSetLicense is the underlying grant) → fall back to `sf data query` (T2) → UI (T3) | T1 verify (license itself is T3/commercial) |
| P4 | **Agentforce provisioned** | **No** — **Salesforce grant — no API** | **Preflight STOP check — resolve at Step 1.** Attempt tier-1 `/query` (routable over `dispatch_readonly`) for `BotDefinition` existence → fall back to `sf data query` (T2) → tier-3 UI check.<br>Tier 2: `sf data query -q "SELECT Id FROM BotDefinition LIMIT 1" --target-org <alias>`.<br>**Read the result precisely:** a **`200` with zero rows = provisioned, just no agents yet → PASS** (do not stop). Only an **error / `INVALID_TYPE` / 501 (object not queryable) = NOT provisioned → STOP now**, don't defer to the Step-9 501. | T1 verify (dispatch_readonly /query) → T2 sf (provisioning itself T3) |
| P5 | Data Cloud / Data 360 | **No** — Home Org grant | query a Data Cloud object / confirm Data Cloud app available | T1 (comes with Home Org) |

> **The only prerequisite the agent truly cannot touch via API is P4 (provisioning)** (a Salesforce grant), alongside the commercial license gates P1/P3 and the Data Cloud entitlement P5. Everything else is configurable or delegated, and each gets a verify call.
>
> **Running-user access is not a separate gate.** The person running this skill must be a **System Administrator** (stated in the scope line above) plus hold the builder permission sets the config work needs — but **assigning those sets is the skill's own job, done at tier 1** as part of the Step 4 permissions work (`permissions.md`), not a stop/ask-user prerequisite. See "assignment and the perm-set clone are tier 1" below for the mechanics.
>
> **Message-consumption billing is out of scope.** Flex Credits / Conversations billing is a *runtime commercial* concern, not a setup gate — SRA configures fine without it and you only feel it at message volume. Confirm SKUs with the account team; the skill does not verify or stop on it.

### Assignment and the perm-set clone are tier 1 (sObject REST)

**Assigning** an existing permission set is a **tier-1** sObject POST —

Tier 1 (write-enabled `dispatch`):

```json
dispatch({
  "url": "/services/data/vXX/sobjects/PermissionSetAssignment",
  "method": "POST",
  "body": { "AssigneeId": "<userId>", "PermissionSetId": "<psId>" }
})
```

Tier 2 (`sf`, if a shell is present):
```bash
sf org assign permset --name EducationCloudFullAccess --target-org <alias>
# or, explicitly:
sf data create record -s PermissionSetAssignment \
  -v "AssigneeId=<userId> PermissionSetId=<psId>" --target-org <alias>
```

**Creating/cloning** a permission set (`EducationCloudAiAgentAccess`, `permissions.md` step 4b) is also **tier 1** — the clone runs over **plain sObject REST + the collections API** (`POST /sobjects/PermissionSet` → `POST /composite/sobjects` for the object/field-perm rows → `POST /sobjects/PermissionSetAssignment`), all routing over `dispatch`, granular with per-row errors. (`PermissionSet` is *also* on the `/headless/metadata` CRUD allowlist, but the sObject-REST path is the one used here — cleaner and more granular than a metadata deploy. `sf`-deploy / UI remain the tier-2/3 fallbacks.) See `permissions.md` Step 4b for the full row shapes.

## The three SRA gates — verify all three with concrete calls

SRA is gated behind three conditions. If any is false, most agent steps 501/403. **Run the verify call; report which gate is missing rather than guessing.**

1. **Agentforce provisioned** (P4).

   Attempt the tier-1 `/query` (routable over `dispatch_readonly`) for `BotDefinition` existence → fall back to `sf data query` (T2) → UI (T3).

   Tier 2 form:
   ```bash
   sf data query -q "SELECT Id FROM BotDefinition LIMIT 1" --target-org <alias>
   ```
   **A `200` with zero rows = provisioned (no agents yet) → PASS.** An **error / `INVALID_TYPE` / 501 = NOT provisioned → STOP at Step 1** and request provisioning — don't start the foundation work and wait for the Step-9 agent-creation call to fail. No API enables provisioning.
2. **Education Cloud enabled** — **T1** — top-level **`IsEducationCloudEnabled == true`** on IndustriesSettings via `dispatch_readonly` tooling GET-by-DurableId (the top-level field; **not** `.Metadata.enableEducationCloud`, which is the write-path member name — see `platform-enablement.md`).
3. **SRA gate** — the runtime access check `orgHasStudentRecruitmentAgentBetaAccess` is a **three-part AND**, from core `IndustriesEducation.accessChecks.xml`:

   ```text
   orgHasStudentRecruitmentAgentBetaAccess =
       OrgPermissions.EinsteinForEducationCloud        ← the license gate (P3)
     , OrgPreferences.RecruitmentAgentEnabled          ← the toggle we flip
     , Gater.com.salesforce.StudentRecruitmentAgent256 ← a perm-Gater / feature flag (Salesforce-granted)
   ```
   (The older sibling check `orgHasEducationAdmissionsAgentAccess` uses the un-suffixed `Gater.com.salesforce.StudentRecruitmentAgent`; the `256` suffix is the current one.)

   - **The toggle's presence, not its value** — same `IndustriesSettings` GET-by-DurableId as item 2: the response including a top-level `IsStudentRecruitmentAgentEnabled` field (regardless of `true`/`false`) confirms the preference exists in this org. Its current value doesn't matter here — Step 2/3 sets it.
   - **License gate (P3) — what makes the toggle non-editable.** The `RecruitmentAgentEnabled` pref's `editAccess` requires `OrgPermissions.EinsteinForEducationCloud && EinsteinGPT.orgHasEinsteinGPTEnabled` (+ `isAdminUser && ViewSetup` — a **System Administrator** satisfies the admin half). Missing the license or Einstein → the toggle can't be enabled. The **license** (P3) is verify-only; **Einstein Setup** the skill can flip at tier 1 — an `EinsteinGptSettings` headless-metadata PUT of member `<enableEinsteinGptPlatform>` (see `platform-enablement.md` Toggle 1). Read it back per `platform-enablement.md` Toggle 1's verify — the tooling query form `SELECT IsEinsteinGptPlatformEnabled FROM EinsteinGptSettings` (GET-by-DurableId 400s here). Report a license miss and stop; enable Einstein Setup if that's what's off, then retry.
   - **The Gater** (`StudentRecruitmentAgent256`) is a **Perm-Gater / feature flag, NOT a perm-set org permission** — it is **not** grantable via a permission set and there is no reliable `PermissionSet WHERE Permissions*=true` SOQL for it (`PermissionsAccsStuRecruitmentAgent` is a licensing-catalog artifact, not the runtime gate — see the note below). Confirm the gater indirectly: the "Enable Student Recruitment Agent" toggle is present/editable in Setup, and `RecruitmentAgentEnabled` can be turned on. If the toggle is missing or the write 501/403s after P3 is satisfied, the gater hasn't been enabled on the org — request enablement from Salesforce.

> `RecruitmentAgentEnabled` is the **enablement** pref (the toggle we flip — see `platform-enablement.md`). The **actual runtime gate** is the three-part expression above (Einstein-for-EDU license + pref + Gater). **WARNING: `AccsStuRecruitmentAgent` is NOT the runtime gate** — it appears only in EBF *licensing* metadata (`.pld.xml`, `Accs*Agent` family, default off), never in the SRA access-check. Treat it as a licensing-catalog SKU line, not the perm the runtime evaluates.

## Step 2a — Verify the EDU foundation (head-start check, not a blind delegation)

SRA is built **on top of** the Education Cloud R&A foundation. Do **not** assume base Education Cloud domain enablement has been run — **verify each piece**, and if one is missing, ask the user to complete that setup to fill *that gap*, then re-verify. Never re-implement its enablement here, and never proceed on an unverified foundation.

Opening line to the user: *"If you've already set up your Education Cloud foundation for Recruitment & Admissions, that's a great head start — let me confirm the parts your admissions agent needs are actually in place."*

| # | Foundation piece | Why SRA needs it | Verify | Tier |
|---|---|---|---|---|
| F-i | **Education Cloud enabled** | Everything below assumes it | **T1** — the IndustriesSettings GET-by-DurableId above → top-level `IsEducationCloudEnabled == true` | T1 |
| F-ii | **Person Accounts** enabled | Flows B2/B4/B5 all *Process Person Account*; SRA record creation breaks without it | `IsPersonAccountEnabled` on the org / `Account` has a `IsPersonAccount` field; attempt tier-1 `/query` (routable over `dispatch_readonly`) for the WHERE-filter/describe read, e.g. `SELECT Id FROM Account WHERE IsPersonAccount = true LIMIT 1` → fall back to `sf data query` (T2) → tier-3 UI check (Setup → Person Accounts). **Read the result precisely: a `200` with zero rows = the `IsPersonAccount` field exists and is queryable, i.e. Person Accounts IS enabled — there just aren't any Person Account records yet → PASS** (do not stop). Only an **error / `INVALID_FIELD` (field not recognized on `Account`) = NOT enabled → STOP now.** Zero rows is not ambiguous — it is a clean query against a field that only exists once the feature is on. | T1 verify (dispatch_readonly /query) → T2 sf |
| F-iii | **R&A / Admissions domain objects available** (schema, not records) | Flows and subagent actions bind to the objects. The agent *creates* records at runtime — **empty objects are fine; record presence is not a setup prerequisite** | existence of `AcademicInterest`, `AcademicTerm`, `Learning`, `ApplicationTimeline`, `ProgramTermApplnTimeline`, `IndividualApplication` via `EntityDefinition` — attempt tier-1 `/tooling/query` (routable over `dispatch_readonly`; `EntityDefinition` is tooling-only, so use `/tooling/query` not data `/query`) → fall back to `sf data query` (T2) → tier-3 UI (Object Manager) | T1 verify (tooling /query) → T2 sf |
| F-iv | **Data Cloud available** | Learning Program grounding (P5) | `SELECT Id FROM DataStream LIMIT 1` at **T1** (routable over `dispatch_readonly`) — a `200` confirms Data Cloud is provisioned, even if the only rows are internal/system streams (Education-specific streams are F-iv.a's concern, not this check's) → fall back to `sf` (T2) → tier-3 UI | T1 verify (dispatch_readonly /query) (comes with Home Org) |
| F-iv.a | **Standard DMOs pre-provisioned** (Learning Program, Academic Term, PTAT, Application Timeline) | Grounding retriever indexes them | These come pre-provisioned with Education Cloud (F-i) + Data Cloud (F-iv) — nothing to install. Verify directly via the DMO's own Connect REST resource (not a SOQL-queryable sObject, and not `DataStream`): `GET /services/data/vXX/ssot/data-model-objects/ssot__<Object>__dlm` (routable over `dispatch_readonly`), using the DMO's own name — `LearningProgram`, `AcademicTerm`, `ApplicationTimeline`, and **`ProgramTermApplicationTimeline`** (**WARNING:** spelled out in full — not F-iii's abbreviated `ProgramTermApplnTimeline` sObject name, which 404s here) → `200` = present → fall back to `sf` (T2) → tier-3 UI (Data Cloud → Data Model). A `404` here (not a `DataStream` search or a guessed sObject name erroring) is the only valid absence signal | T1 verify (dispatch_readonly GET /ssot/data-model-objects) → T2 sf |

> **WARNING: F-iii's pass condition is `EntityDefinition` presence alone — do not additionally require a live `describe`/query-as-data success on these objects.** The running user's ability to actually query or describe them as data depends on the builder persona's EDU permission sets (*Education Cloud Full Access*, etc.), which this skill itself assigns later at step 4a — not something F-iii should presuppose. A `describe`/query attempt against one of these objects failing with an access- or "not supported"-shaped error **before** step 4a runs is expected, not a sign the domain schema is missing (see SKILL.md Gotchas: EDU objects show 0 fields until *Education Cloud Full Access* is assigned). Only treat the object as genuinely missing — and only then ask the user to complete Education Cloud foundation setup — if it's absent from `EntityDefinition` itself.

> **WARNING: F-iv.a's pass condition is DMO presence alone — do not also check for the `DataStream`/DLO ingestion pipeline and report its absence as a gap.** The CRM connector, data streams, and DLO→DMO mapping that actually populate these DMOs are built by *this skill* at setup time (see `grounding.md`'s Mechanism 2 data-spine section) — they are work this skill owns, not a foundation prerequisite to verify beforehand. Finding zero `LearningProgram`/`AcademicTerm`/etc. data streams during preflight is the expected starting state, not something to flag as a readiness gap — same category as F-iii's "0 records is fine."

### AEA/Employee path only — community licensing prerequisite

If the customer wants the AEA/Employee agent's authenticated community access, verify the org carries the community licenses and profiles the Campus Tours sharing rule's target portal group depends on (`permissions.md` Step 6b) — **4 UserLicenses** (`Customer Community`, `Customer Community Login`, `Customer Community Plus`, `Customer Community Plus Login` — these are base UserLicenses, not add-on PermissionSetLicenses; querying `PermissionSetLicense` for these names returns 0 rows even on a fully-licensed org) and **4 Profiles** (`Customer Community Login User`, `Customer Community Plus Login User`, `Customer Community Plus User`, `Customer Community User`). Skip entirely on an ASA/Service-only build — the sharing rule's authenticated-community target only matters for the AEA path.

Verify (attempt T1 `/query` over `dispatch_readonly` → `sf` fallback):
```sql
SELECT Name FROM UserLicense WHERE Name IN ('Customer Community','Customer Community Login','Customer Community Plus','Customer Community Plus Login')
SELECT Name FROM Profile WHERE Name IN ('Customer Community Login User','Customer Community Plus Login User','Customer Community Plus User','Customer Community User')
```
If none of these are present, the AEA path's portal group (`permissions.md` Step 6b) likely doesn't exist yet — flag that to the customer rather than assuming Step 6b's target is already there.

Match each missing piece to how it actually gets fixed — don't treat every gap as one blanket foundation-setup ask, since Data Cloud isn't part of that foundation setup:

- **F-i, F-ii, F-iii** (EDU enablement, Person Accounts, R&A domain schema) → *"The agent needs <piece>, which isn't set up yet — let's get your Education Cloud foundation set up first, then I'll re-verify and continue."* Ask the user to complete base Education Cloud domain enablement (which drives `enableEducationCloud`, Person Accounts, and R&A-domain enablement, bringing the object schema).
- **F-iv** (Data Cloud) → **do not** fold this into the Education Cloud foundation ask above — Data Cloud is a **Home-Org entitlement** (P5): if it's absent, treat it like the other Salesforce grants (P3/P4) — report the gap and stop; it is not something this skill can flip. The grounding *setup* built on top of Data Cloud is done later **inside this skill** (`grounding.md`), not here.

## Org requirement — provisioned + entitled, not a bare org

Any org this skill runs against must be **Agentforce-provisioned** (P4), carry the **Einstein for Education Cloud** license (P3, `OrgPermissions.EinsteinForEducationCloud`) with **EinsteinGPT enabled**, and have the **SRA Gater** (`Gater.com.salesforce.StudentRecruitmentAgent256`) turned on — these are Salesforce grants a bare scratch org does **not** have, and **none of them can be flipped by this skill**. They are **preflight STOP checks (Step 1)**: verify them before any Step 2+ work and halt if any is missing, rather than doing the foundation build and hitting the wall at Step 9 (agent creation 501s / the SRA toggle is absent or "not editable"). (See "The preflight gate" and "The three SRA gates" above for how to verify each.)

## Org permissions (classify — don't lump together)

| Org perm / gate | Class | Notes |
|---|---|---|
| `OrgPermissions.EinsteinForEducationCloud` | **SRA license gate (P3)** | The add-on org perm the `RecruitmentAgentEnabled` toggle's `orgAccess`/`editAccess` require (with `EinsteinGPT.orgHasEinsteinGPTEnabled`). Missing it → the toggle can't be enabled. |
| `Gater.com.salesforce.StudentRecruitmentAgent256` | **SRA feature gate** | The perm-**Gater** the runtime actually evaluates in `orgHasStudentRecruitmentAgentBetaAccess`. NOT a perm-set org permission; Salesforce-granted; not SOQL-queryable as a `Permissions*` field. |
| ~~`AccsStuRecruitmentAgent`~~ | **licensing-catalog artifact — NOT the runtime gate** | Appears only in EBF `.pld.xml` licensing metadata (`Accs*Agent` family, default off), never in core SRA access-checks. Do not treat as the perm the runtime checks. |
| `BotHyperforceRuntime` | Generic platform | Agentforce runtime prereq — applies to any Agentforce agent, not SRA-specific. |
| `CopilotDigitalChannelsPilot` | Generic platform | Copilot/digital-channels prereq — not SRA-specific. |

## Licenses / add-ons (confirm real SKUs with account team)

The **customer-facing minimum**: Agentforce Service (unauth) / Employee (auth) + Education Cloud + Einstein for Education Cloud + Data Cloud + Knowledge + Messaging. Confirm the exact SKUs with the account team.

A fully-provisioned org may additionally carry: `AgentforceServiceAgentAddOn` + `AgentforceEmployeeAgentAddOn` (+ `…ManagerAddon`), `EducationCloudAddOn` + `EducationCloudExprcCloudAddOn`, `EinsteinForEducationCloudAddOn`, EinsteinGPT add-ons (Copilot/Platform/PromptBuilder), `CustomerCommunity(Plus)(Login)`, `EmbeddedServiceMessaging(+UserPsl)`, `ChatbotEnabled`, `KnowledgeUser`, `GenieDataPlatformStarter`, `CdpSegmentsActivationsCard` — treat this as a superset (some entries are Transfer-Credit- or community-specific and not required for SRA).
