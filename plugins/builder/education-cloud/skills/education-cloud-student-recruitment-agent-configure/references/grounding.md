# Grounding — two independent mechanisms

Read at Workflow steps 7–8 and 9. SRA grounding is **two separate mechanisms — do not conflate them.**

1. **Knowledge grounding** (FAQ subagent) — answers over published Knowledge articles via a Knowledge-sourced **data library**. No Data Cloud involved. **Fully TIER 1** — article create/publish/verify and data-library create/index/verify all route over `dispatch`/`dispatch_readonly`.
2. **Data Cloud grounding** — structured Education Cloud data (Learning Program, Academic Term, PTAT) surfaced through **Data Cloud + hybrid-search indexes + retrievers + prompt templates**: 3 grounded objects/DMOs/prompt templates, but only **2** physical search-index/retriever builds (Academic Term shares the PTAT build; Application Timeline rounds out the data spine as a relationship source only, with no index/retriever/prompt template of its own — see Mechanism 2 below). **The data spine is TIER 1** (Connect REST over `dispatch`); the **index build, retriever create, and prompt-template edit are TIER 3 (Setup UI)** — no supported public API. There is **NO tier-2 `sf`-deploy path** for grounding metadata.

> **WARNING: Two mechanisms, do not conflate.** Mechanism 1 (Knowledge) is **fully tier 1** — article create/publish + data-library create over `dispatch`. Mechanism 2 (Data Cloud) is **three prompt-template-backed retrieval actions** (Learning Program, Academic Term, Program Term Application Timeline), not one — but only 2 of those 3 have their own search-index/retriever build; Academic Term grounds on the PTAT retriever. The data spine underneath maps a 4th DMO, Application Timeline, alongside those three — it backs 3 of the PTAT retriever's return fields by relationship but is never itself indexed or retrieved. Every verify below is a **tier-1 `/query`/`/tooling/query` attempt first**, `sf` as fallback — both route over `dispatch_readonly`.

---

## Mechanism 1 — Knowledge grounding (step 7 + step 9 wiring) — FULLY TIER 1

The `AnswerQuestionsWithKnowledge` action (`EmployeeCopilot__AnswerQuestionsWithKnowledge`) answers over **published Knowledge articles** surfaced through a **Knowledge-sourced data library**. Articles must be **Published (Online)** and cover the 4 areas: **learning programs, support programs, application processes, campus & support information**. No specific article type/data category is mandated.

- **WARNING:** The FAQ action is **public** → articles must contain **NO non-public data**.
- Draft articles cause the agent to answer "no information" — the classic failure mode. Publish before testing.
- A Knowledge-sourced library indexes the **live** Knowledge object: once wired (step 9), newly **Published (Online)** articles matching the library's filters are picked up automatically on the index's refresh cycle — **no re-wiring or re-publish of the agent**. Drafts, archived, and filtered-out articles are excluded. So after the one-time wiring, ongoing article authoring alone keeps the agent current — tell the customer this so they don't expect to re-touch the agent per article.

### 7a — Author + publish a Knowledge article — 🟢 TIER 1

Content authoring is a human decision — **never auto-create articles.** Check first, then ask:

1. **Check for existing coverage first.** Query `Knowledge__kav` for `PublishStatus='Online'` (and `'Draft'`, to show what's in progress) and skim titles against the 4 required areas — **learning programs, support programs, application processes, campus & support information**. Do this **before** proposing any create.
2. **Always ask the customer — do not draft anything until they answer.** Report what you found (e.g. "You already have 6 Online articles; they look like they cover learning programs and application processes, but I don't see anything on campus & support info") and offer exactly one of three choices per gap, resolved on the spot rather than left open:
   - **Draft placeholder content now**, for the customer to edit and finalize later.
   - **The customer supplies the content now**, for you to create as draft articles.
   - **Defer entirely** — the customer authors and publishes their own articles later, on their own schedule.

   Only proceed to step 3 for the gaps where the customer picked the first or second option. Whichever way each gap resolves, **move on to 7b (the data library) immediately after** — library creation never waits on article content existing; anything published later is picked up automatically (see the Wiring note below).
3. **Prereq (once the customer has asked for a draft):** Lightning Knowledge enabled. Read the createable fields off `GET /services/data/vXX/sobjects/Knowledge__kav/describe` first — the required, non-defaulted fields are `Title` (string 255), `UrlName` (string 255, must be **unique**), and `Language` (picklist, e.g. `en_US`); the **body field API names are org/article-type-specific** (e.g. `Answer__c`, `Question__c`, `Detail__c`) — take them from describe (§7a step 1), do **not** hardcode. If the org's Knowledge object is a custom type, the `*__kav` API name differs too.
4. **Create the draft** — `POST /services/data/vXX/sobjects/Knowledge__kav` body `{"Title":"...","UrlName":"<unique-slug>","Language":"en_US","<bodyField__c>":"<html>"}` → 201 `{"id":"ka0…","success":true}`. New article starts `PublishStatus:"Draft"`, `VersionNumber:0`, with a `KnowledgeArticleId` (the `kA0…` durable id grouping versions).
5. **Publish** — `PATCH /services/data/vXX/knowledgeManagement/articleVersions/masterVersions/<articleVersionId>` body `{"publishStatus":"Online"}` → **204 No Content** (success). The `<articleVersionId>` is the `ka0…` `Knowledge__kav` row Id (the draft version), **NOT** the durable `KnowledgeArticleId`. (Add `"flagAsNew":true` for a major version on republish.) Publishing mutates the version row in place (Draft/v0 → Online/v1). Draft→Online is fully API-driven over `dispatch`; no UI needed. (Do **not** use a `publishKnowledgeArticles` invocable/Apex action — use the masterVersions PATCH.)
6. **Verify (attempt T1 `/query` → `sf` fallback):**
```bash
# Tier 1 first (dispatch_readonly): GET /services/data/vXX/query?q=<URL-encoded SOQL below>
# Tier 2 fallback:
sf data query -q "SELECT PublishStatus, COUNT(Id) total FROM Knowledge__kav GROUP BY PublishStatus" --target-org <alias>
sf data query -q "SELECT Id, Title, PublishStatus, KnowledgeArticleId FROM Knowledge__kav WHERE PublishStatus='Online'" --target-org <alias>
```
`PublishStatus='Online'` = live articles the FAQ action can read; `Draft` articles are invisible to the agent. (The aggregate `GROUP BY` read routes at tier 1.)

### 7b — Create the Knowledge-sourced data library — 🟢 TIER 1

The FAQ subagent grounds on a **data library** whose source is Knowledge (NOT Data Cloud — do not conflate with Mechanism 2). Creating it **auto-provisions the backing stream + search index + retriever** — no separate index-build step, no agent needed until the wiring at step 9.

- **Preconditions:** Data 360 (Data Cloud) set up; the running user needs **Data Cloud Admin AND System Administrator**; the org-access check on the create op is "Generative AI Setup enabled." Library indexing consumes Data 360 credits.
- **Tier 1 create:** `POST /services/data/vXX/einstein/data-libraries` over `dispatch`, body:
  ```json
  {
    "masterLabel": "Student Recruitment Knowledge Library",
    "developerName": "SRA_Knowledge_Library",
    "description": "<desc>",
    "groundingSource": {
      "sourceType": "KNOWLEDGE",
      "knowledgeConfig": {
        "primaryIndexField1": "Title",
        "primaryIndexField2": "Summary",
        "contentFields": ["<bodyField__c>"]
      }
    }
  }
  ```
  → **201** returning `libraryId`, `dataSpaceScopeId`, `sourceType:"KNOWLEDGE"`, `status:"IN_PROGRESS"`, `featureAssignments:[]`. Use the **fixed `developerName` `SRA_Knowledge_Library`** (never a per-org-run name) so the step-9 wiring can re-find the library deterministically — by that exact developerName, not by `sourceType` (the org may already have other KNOWLEDGE libraries) and never by asking the customer what it was called. Re-running create with the same developerName returns a `DUPLICATE`-class error → treat as "already exists, read it back," not a failure. **BOTH `primaryIndexField1` AND `primaryIndexField2` are mandatory** (the UI's two "identifying fields" — text/textarea, keep ≤255 chars to stay under the 512-token cap); the create 400s naming each missing field in turn until both are present. **Content is the array key `contentFields`** (NOT `contentField1` — a singular key is silently dropped); the `*__kav` field API names come from describe (§7a step 1). Optional Knowledge filters live in `knowledgeConfig`: `isRestrictToPublicArticle`, `isDataCategoryRuleEnabled` + `dataCategorySelectionIds`/`Names` (SRA needs neither for the basic path). The KNOWLEDGE source skips the file-upload chain (`file-upload-urls`/`add-files`) — create alone kicks indexing.
- **Tier 3 fallback:** Setup → Agentforce → Data Library → New → Knowledge source, if the Connect call 403/404/501s on the org.
- **Verify (T1 readonly):** `GET .../einstein/data-libraries/<libraryId>` returns the full config — confirm `sourceType:"KNOWLEDGE"` and `contentFields` is non-empty; `GET .../einstein/data-libraries` lists all. **Don't wait on indexing to finish here** — wiring the library into the agent (step 9) only needs the `libraryId`, not a completed index, and indexing runs on its own async schedule (large sets can take 30 min–several hours) with nothing in this flow gated on it.

### Wiring (step 9) — attach the data library to the agent — 🟢 TIER 1 (T3 fallback)

Grounding is **one agent-level field**, not a per-subagent link. In the agent's NGA bundle AFScript, the top-level `knowledge:` block carries the binding:

```yaml
knowledge:
    rag_feature_config_id = "ARFPC_<libraryId>"
    citations_enabled: True
```

- **`rag_feature_config_id`** = the literal string `ARFPC_` + the data library's `libraryId` verbatim (e.g. library `1JDVW000001KWPl4AO` → `ARFPC_1JDVW000001KWPl4AO`). `ARFPC` = *Agent RAG Feature Config*; the id is derived from the library itself — you do **not** query a separate config object for it (`GenAiFeatureConfig`/`AiFeatureConfiguration` etc. are not valid sobjects here). **Re-read the `libraryId` here, don't rely on carrying it from step 7** — `GET /services/data/vXX/einstein/data-libraries` (readonly) lists all libraries with their Ids; match the row by the **exact `developerName` `SRA_Knowledge_Library`** (the fixed name from step 7b — not `sourceType`, which won't disambiguate from pre-existing KNOWLEDGE libraries).
- This one field grounds Knowledge **agent-wide**: every packaged subagent's existing `AnswerQuestionsWithKnowledge` action (source `EmployeeCopilot__AnswerQuestionsWithKnowledge`, target `standardInvocableAction://streamKnowledgeSearch`) reads `@knowledge.rag_feature_config_id`. There is **nothing to add per subagent** — the FAQ subagent's action list is byte-identical before and after wiring.
- **Fold it into step 9's initial bundle-create pass** — set the two lines above in the AFScript alongside the subagent edits. No `validate`/`publish` needed here (no new action target is being added); publish stays reserved for the customer's single Commit Version at step 9a (see `agent-and-subagents.md`).
- **The data library's own `featureAssignments` stays `[]`** — it is **not** the link (it's an output-only feature-family field; `PATCH /einstein/data-libraries/{id}` won't accept it). Do not treat a link as a `featureAssignments` write, and don't promise a `DataLibrary` MDAPI `sf project deploy` — there is no such metadata type.
- **Tier 3 fallback:** the Agentforce Builder data-library UI on the agent (Setup → the agent → connect data library) sets the same field — use it if the NGA lifecycle 403/404/501s.
- **Verify wiring:** re-GET the bundle version and confirm `knowledge.rag_feature_config_id` is `ARFPC_<libraryId>` (was `""`); the step-13 conversational smoke test (user-run in the deployed channel) then returns article-grounded, cited answers.

---

## Mechanism 2 — Data Cloud grounding (step 8) — 3 retrieval actions, 2 retriever builds

Step 8 wires **3** prompt-template-backed retrieval actions — one per grounded object/DMO/prompt template, genuinely 3 of each. But only **2 physical search-index/retriever builds** back them, because Academic Term has no search index or retriever of its own — its prompt template grounds directly on the PTAT retriever:

| # | Retrieval action (retriever-backed) | Grounded object | DMO | Base prompt template (dev name) | Search index / retriever build |
|---|---|---|---|---|---|
| 1 | Get Learning Program Data | Learning Program | `ssot__LearningProgram__dlm` | `sturecruitment__getLearningPrograms` | **Learning Program build** |
| 2 | Get Academic Term Data | Academic Term | `ssot__AcademicTerm__dlm` | `sturecruitment__getAcademicTerms` | **PTAT build** (shared — see below) |
| 3 | Get Application Timeline Data | **Program Term Application Timeline** | `ssot__ProgramTermApplicationTimeline__dlm` | `sturecruitment__getApplicationTimelines` | **PTAT build** (shared — see below) |

> **CRITICAL: Academic Term has no dedicated search index/retriever — by design, not a gap to fill.** Its prompt template's own Data Model Object field is **Program Term Application Timeline**, not Academic Term, and its `GROUNDING_DATA` line reads `Retrievers:Program Term Application Timeline Retriever`. Do not build a separate Academic Term index/retriever — there's nothing to wire it to; both the Academic Term and PTAT rows above share the one PTAT retriever build (see the retriever field config below).
>
> **CRITICAL: Row 3's retrieval action grounds Program Term Application Timeline (PTAT), NOT ApplicationTimeline.** `GetApplicationTimelineData` (template `sturecruitment__getApplicationTimelines`) has **source object/DMO `ssot__ProgramTermApplicationTimeline__dlm`** — a different object than `ApplicationTimeline`. The retriever/index may be **labeled** "Application Timeline" or "PTAT" (matches the template's user-facing output), but the underlying object/DMO is PTAT. If a target org's field set ever looks off, the authoritative source is the base template's own `resultFieldApiKey=` references (`GET /einstein/prompt-templates/<devName>`), not the step's display name. **`ApplicationTimeline` itself still needs its own DMO mapped into the spine below** — the PTAT retriever's return fields reach 3 of its fields (Application Open/Close Date, Application Category) through a relationship lookup, and that lookup only resolves once `ApplicationTimeline` is mapped; it never gets a search index or retriever of its own.

> **CRITICAL: `GetProgramTermApplicationTimelineData` is a SEPARATE, deterministic STANDARD_INVOCABLE action — do NOT confuse it with the retriever-backed `GetApplicationTimelineData` above.** It invokes packaged flow/apex (complex active-program-term filtering retrievers don't support) and is **not** retriever-backed — do not wire a retriever/prompt template for it. (Naming collision, not a typo: the retriever action is `GetApplicationTimelineData`; the invocable action is `GetProgramTermApplicationTimelineData`.) The perm-set/OWD API name for the object is the truncated `ProgramTermApplnTimeline` — different surface, different spelling again.

> **Prompt-template scope — exactly 3 base-SRA templates, exclude the 2 Transfer Credit ones.** Five `promptTemplate/sturecruitment/` YAMLs exist, but namespace path alone does NOT prove SRA membership. In scope: `getLearningPrograms`, `getAcademicTerms`, `getApplicationTimelines`. **Out of scope (Transfer Credit Agent only, gated `orgHasTransferCreditEquivalencyAccess`): `getInstitutionData`, `getExternalLearningData`** — do NOT wire retrievers for these (consistent with the "do NOT include TransferCreditEquivalency" rule in `agent-and-subagents.md`).

> **Create-action types (not all flows):** `CreateAdmissionsApplication` is an **API** action (ConnectApi `Industries-Education.postPreliminaryApplicationReferences`) — currently deleted from the Admissions Application subagent at step 9a, see `agent-and-subagents.md`; `CreateCampusTourRegistration`, `CreateAcademicInterest`, and `GetCampusTourCampaigns` are **FLOW**. These read/grounding actions apply to **both** agent paths (auth/AEA + unauth/ASA), unlike the flow surgery (unauth-only — see `flows.md`).

> **Scope — the Learning Program *source records* are not this skill's job.** The programs, courses, academic calendar/terms, and campus hierarchy the agent retrieves are created by other Education Cloud skills (Academic Operations setup) and seeded as demo/customer data (same rule as the R&A domain objects — see `prerequisites.md` F-iii). This skill wires the *grounding* over that data; it does **not** create those records. Confirm the source data exists, but do not create it here.

### The tier split — data spine is T1, index/retriever/prompt are T3

- 🟢 **TIER 1 — prereq (separate from the agent-user perm-set clone) — grant 3 EDU system perms to the Data Cloud *Salesforce Connector* permission set.** The **Platform Integration User** that Data 360 uses to read CRM data authenticates through this permission set — it comes bundled with connecting the org to Data Cloud itself, not a separate grant to create. Before any EDU object ingests, enable System Permissions **Access Education Cloud Components** (`PermissionsUseEducationCloudComp`), **Access Education Cloud Objects** (`PermissionsAccessEducationCloud`), and **Access Education Cloud Review Features** (`PermissionsAccessEducationCloudReview`) — ref KB 001983512. This is separate from the Einstein-Agent-User clone in `permissions.md`; without it, the data streams silently ingest nothing for EDU objects.
  - **CRITICAL:** `PATCH /services/data/vXX/sobjects/PermissionSet/<Id>` (standard Data API — `/tooling/sobjects/` accepts the same body but doesn't apply these 3 fields) body `{"PermissionsAccessEducationCloud":true, "PermissionsUseEducationCloudComp":true, "PermissionsAccessEducationCloudReview":true}`. Find `<Id>` by **Label**, not a hardcoded `Name` — some orgs show a legacy label (*Salesforce CDP Salesforce Connector Integration*, *Customer Data Platform Salesforce Connector Integration*, *Customer 360 Audiences Salesforce Connector Integration*) instead of "Data Cloud Salesforce Connector."
  - **Verify (T1 `/query` → `sf` fallback):** `SELECT Id, Label, PermissionsAccessEducationCloud, PermissionsUseEducationCloudComp, PermissionsAccessEducationCloudReview FROM PermissionSet WHERE Label LIKE '%Salesforce Connector%'` — confirm all three read `true`.
- 🟢 **TIER 1 (Connect REST over `dispatch`) — the Data Cloud data spine, in order:**
  1. **Verify the 4 standard DMOs are pre-provisioned** — do NOT create them. `GET /services/data/vXX/ssot/data-model-objects/ssot__<Object>__dlm` (`ssot__LearningProgram__dlm`, `ssot__AcademicTerm__dlm`, `ssot__ProgramTermApplicationTimeline__dlm`, `ssot__ApplicationTimeline__dlm`) → 200, `creationType:Standard`. An unmapped DMO reads `isEnabled:false`; a mapped one flips to `isEnabled:true` with `isMapped:true` on each mapped field.
  2. **Create the CRM data stream per object** — `POST /services/data/vXX/ssot/data-streams`, one object per call. Body:
      ```json
      {
        "name": "<Object>_Home",
        "connectorInfo": {
          "connectorType": "SalesforceDotCom",
          "connectorDetails": { "name": "SalesforceDotCom_Home", "sourceObject": "<CRMObjectApiName>" }
        },
        "dataLakeObjectInfo": {
          "category": "Other",
          "label": "<Object>_Home",
          "name": "<Object>_Home__dll",
          "dataspaceInfo": [ { "name": "default" } ]
        }
      }
      ```
      → 201; the DLO field list **auto-derives** from `sourceObject` (do not author fields). **Naming: use the connector default `<Object>_Home` / DLO `<Object>_Home__dll`** (NOT a custom `_SRA` suffix) so API-created and UI-created streams match and downstream references line up. **PTAT is the one exception — create it as `"name": "ProgramTermApplnTimeline_Home"`, `dataLakeObjectInfo.label`/`name`: `"ProgramTermApplnTimeline_Home"` / `"ProgramTermApplnTimeline_Home__dll"`** (the truncated CRM object spelling, not the full `ProgramTermApplicationTimeline`): Data Cloud provisions this one DLO under the truncated spelling regardless of what's requested, so asking for it directly keeps the name it's created under identical to the name every later step needs to reference. **Attempt create directly for each of the 4 objects — don't page through the existing streams list first.** The fixed naming above makes this safe: a duplicate-name error on create means that stream already exists → read it back, don't treat it as a failure (same idiom as the PermissionSet clone and Knowledge-library create above). **Body gotchas (each is a real 400):** no top-level `dataStreams` array wrapper; `connectorType` goes **inside** `connectorInfo`; do NOT include `connectorDetails.type` (output-only); exactly one of `dataLakeObjectInfo`/`existingDataLakeObjectInfo`; the dataspace key is `dataspaceInfo` (input side, entries take only `name` — the read side spells it `dataSpaceInfo` with `{label,name}`). `connectorDetails.name` `"SalesforceDotCom_Home"` is the OOTB CRM connector — if the org's differs, `GET /ssot/data-streams` and copy an existing SalesforceDotCom stream's `connectorDetails.name`.
  3. **Never wait on `PROCESSING` here — always defer, unconditionally, with no status check at all yet.** A stream can only be PATCHed (step 4) while Active/Error/Inactive — `PROCESSING` happens right after creation, and again briefly after the step-4 PATCH — and how long it takes to clear scales with how much data is already in the org, so it's never safe to assume a quick check will catch it ready. **Move straight into step 9 (agent creation) without checking status even once here** — checking now only means polling in a loop or gambling on timing, and neither is worth it; narrate the deferral to the customer first, per SKILL.md's *Talking to the user*. **Steps 9 and 9a are one continuous unit for the customer (headless creation straight into their one Builder session) — don't break that up to check in between.** Check status for the first time at the end of step 9a, once that whole unit is done; if still `PROCESSING`, check again at the end of each subsequent step (10, 11, 12) — this must be complete, including the T3 index/retriever/prompt-template build, before step 13's final verify, which depends on it. Once all 4 read Active/Error/Inactive at one of those checkpoints, continue to step 4 then. **Do not attempt step 4 or step 5 in the same pass as creation, even opportunistically** — a stream created this turn is almost always still `PROCESSING`, and jumping ahead to `auto-map-dlos` (step 5) against it returns a not-found on the DLO. That not-found means "not ready yet," never "wrong name" — see the note on step 5 below.
  4. **Fix Boolean/Date type mismatches (`AcademicTerm_Home` / `LearningProgram_Home` / `ApplicationTimeline_Home`).** The CRM connector always derives a source Boolean field as DLO type **Text** and a source Date field as DLO type **DateTime** — never the DMO's actual Boolean/Date. DMO mapping needs an exact type match, so these fields won't map until cast. Fix: `PATCH /services/data/vXX/ssot/data-streams/<streamName>` (write `dispatch`) with body `{"mappings":[{"targetFieldName":"<Name>__c","transformationFormula":"<expr>","targetFieldReturntype":"Boolean"|"Date"}, ...]}` — batch every field for a stream into the one array in a single PATCH. Two templates cover every field: **Boolean** — `IF(ISEMPTY(sourceField['<SourceField>']),null,IF(sourceField['<SourceField>'] == 'true', true, false))`; **Date** — `IF(ISEMPTY(sourceField['<SourceField>']),null,DAYPRECISION(sourceField['<SourceField>']))`. Apply:

      | Stream | Target field | Type | Source field |
      |---|---|---|---|
      | `AcademicTerm_Home` | `Is_Active_Transformed__c` | Boolean | `IsActive` |
      | `AcademicTerm_Home` | `Start_Date_Transformed__c` | Date | `StartDate` |
      | `AcademicTerm_Home` | `End_Date_Transformed__c` | Date | `EndDate` |
      | `LearningProgram_Home` | `Is_Active_Transformed__c` | Boolean | `IsActive` |
      | `LearningProgram_Home` | `Is_Top_Level_Program_Transformed__c` | Boolean | `IsTopLevelProgram` |
      | `LearningProgram_Home` | `Does_Create_Opportunity_Transformed__c` | Boolean | `DoesCreateOpportunityRecord` |
      | `LearningProgram_Home` | `Active_From_Date_Transformed__c` | Date | `ActiveFromDate` |
      | `LearningProgram_Home` | `Active_To_Date_Transformed__c` | Date | `ActiveToDate` |
      | `ApplicationTimeline_Home` | `Application_Open_Date_Transformed__c` | Date | `ApplicationOpenDate` |
      | `ApplicationTimeline_Home` | `Application_Close_Date_Transformed__c` | Date | `ApplicationCloseDate` |
      | `ApplicationTimeline_Home` | `Decision_Release_Date_Transformed__c` | Date | `DecisionReleaseDate` |
      | `ApplicationTimeline_Home` | `Graduation_Appln_Deadline_Transformed__c` | Date | `GraduationApplnDeadline` |
      | `ApplicationTimeline_Home` | `Early_Action_Open_Date_Transformed__c` | Date | `EarlyActionOpenDate` |
      | `ApplicationTimeline_Home` | `Early_Action_Close_Date_Transformed__c` | Date | `EarlyActionCloseDate` |
      | `ApplicationTimeline_Home` | `Early_Application_Open_Date_Transforme__c` | Date | `EarlyApplicationOpenDate` |
      | `ApplicationTimeline_Home` | `Early_Application_Close_Date_Transform__c` | Date | `EarlyApplicationCloseDate` |
      | `ApplicationTimeline_Home` | `Early_Appln_Dec_Rel_Date_Transformed__c` | Date | `EarlyApplnDecisionRelDate` |

      `ApplicationTimeline_Home` has no Boolean fields needing the cast — Date only, 9 fields, same template. **Only `Application_Open_Date_Transformed__c` and `Application_Close_Date_Transformed__c` back a return field the PTAT retriever actually uses** (Application Category, the 3rd return field sourced from Application Timeline, is a picklist and needs no cast); the other 7 exist on the object but aren't wired to a retriever field today — fix all 9 in the one PATCH regardless, so the mapping isn't left partially fragile.

      `auto-map-dlos` (step 5) needs no further wait once this PATCH itself returns 200 — the brief `PROCESSING` it triggers (per step 3) clears on its own.
  5. **Map the DLO to its standard DMO — all 4 in one pass, after step 4 lands for `AcademicTerm_Home`/`LearningProgram_Home`/`ApplicationTimeline_Home`.** Two Connect calls over the **write `dispatch`** (they are writes, so NOT `dispatch_readonly` — a `ROUTE_NOT_FOUND` here means the readonly dispatcher, not a version issue; use the org's current `vXX`, unless it's below this surface's documented floor — see `execution-model.md`):
      1. Precheck: `POST /services/data/vXX/ssot/simple-start/sobject-recommendations` body `{"sobjectNames":["LearningProgram","AcademicTerm","ProgramTermApplnTimeline","ApplicationTimeline"]}` → 201, each returns `category:"Related"` (confirms they're opinionated/auto-mappable objects). **WARNING:** `sobjectNames` takes **source platform sObject** API names (like `LearningProgram`/`AcademicTerm`), so the PTAT entry is the **truncated** `ProgramTermApplnTimeline` — NOT the DMO's full-spelling `ssot__ProgramTermApplicationTimeline__dlm` (different surface — see `permissions.md`); `ApplicationTimeline` needs no such truncation. The full spelling does **not** error: the call still returns 201 but that object comes back **without a `category` field** (unrecognized), so it silently drops from the mapping. Send the truncated PTAT name and confirm every object echoes `category:"Related"`.
      2. Map: `POST /services/data/vXX/ssot/simple-start/auto-map-dlos` body `{"dloNames":["<Object>_Home__dll"]}` → 201 `{"mappedDloNames":[...]}`. **CRITICAL: ONE DLO per call** — passing 2+ names → 500 INTERNAL_ERROR. Loop the objects, including `ProgramTermApplnTimeline` — it needs no step 4, but map it in this same pass rather than earlier; nothing downstream needs it before the other three are ready. **If a call 404s / reports the DLO not found, use the exact name each stream was created under in step 2** (PTAT's is the truncated `ProgramTermApplnTimeline_Home__dll` — see step 2) — there's nothing else to look up. A not-found on the right name means that stream is still `PROCESSING` (step 3) and hasn't materialized yet; re-verify with `GET /ssot/data-streams/<name>` if needed, then defer this one DLO's mapping to the next status checkpoint (per step 3) rather than paging through the streams list.
  - Together, steps 1–5 = the **complete T1 grounding spine** — the bundle-deploy UI path is NOT required for these opinionated EDU objects. The mapping lands as `isMapped:true` on the DMO field metadata (the stream's `mappings[]` stays `[]` even when fully mapped — don't check there).
- **CRITICAL: TIER 3 (Setup UI) — no supported public API.** This whole leg is a hand-off: walk the customer through the Setup UI screen by screen rather than handing them this section's API/DMO vocabulary — name what a screen or field does for the agent ("this is the field the agent uses to tell students the term name"), not its dev name, matching the register in SKILL.md's *Talking to the user*. The exact field lists and filter below are what to translate live, not a script to read verbatim.
  - **Build the hybrid-search index — 2 builds, not 3.** Data Cloud → Search Index → New → **Easy Setup** → pick the DMO → Save. Easy Setup ⇒ Search Type = **HYBRID**, auto-creates the chunk DMO + vector/index DMO, and auto-selects the fields to chunk — but **filtering fields are a separate, manual pick on this same Easy Setup screen, not automatic**, and there is no supported way to add one after Save. Set every filtering field listed below for the DMO being built, in this pass — an index saved without one can't be retro-fitted, so the retriever built on top of it will be permanently missing that filter option. Builds on Save — no separate build action. (A raw `POST /ssot/search-index` route exists but requires pre-authoring the chunk DMO/vector DMO/chunking config/embedding model Easy Setup derives in one click, and 500s if those don't pre-exist — not worth it vs. the 3-click UI; treat index create as **T3 Easy Setup**.) Field configuration, both hybrid, both embedding model **E5 Large V2**:
    - **Learning Program** (DMO `ssot__LearningProgram__dlm`): 8 chunked/text fields (Passage Extraction) — Name, Academic Level, Cip Code, Description, Duration Unit, Learning, Provider, Short Description; 1 filtering field — Data Source.
    - **Program Term Application Timeline** (DMO `ssot__ProgramTermApplicationTimeline__dlm`): 4 chunked fields — Academic Term Id, Application Timeline Id, Learning Program Id, Name; 3 filtering fields — Academic Term > Is Active, Learning Program > Learning Program Id, Data Source.
    - Academic Term gets **no index of its own** — do not build one; its template grounds on the PTAT retriever below.
  - **Create the retriever — 2 builds, not 3 — Einstein Studio Individual Retriever.** Retriever create/read has **NO API surface** (every `/ssot/retrievers`, `/connect/retrievers`, and `AiRetriever` tooling route 404s), so this is T3-only with no API existence check. Click-path: Data Cloud → **Einstein Studio → Retrievers tab → New Retriever → Individual Retriever** → Next → source = **Data Cloud**, data space = **default**, DMO + search index from the matching build above → Next → filters (see below) → **Configure Retriever Results** (see below) → Save → name it → **Activate** (quick action, upper-right). **CRITICAL: Retriever API names are auto-generated and non-deterministic** (pattern `<Name>_1Cx_yZB<8 hex>`) — cannot be hardcoded; read the API Name back from the retriever detail page (Overview → Retriever Details → API Name) to wire the template. Configuration:
    - **Learning Program Retriever**: DMO Learning Program, no filters, 20 results, citations Off. Return fields (Direct Attributes → Learning Program): **Name, Learning Program Id**.
    - **Program Term Application Timeline Retriever**: DMO PTAT, filter **`Is Active` Equal To `TRUE`** AND **`Learning Program Id` Equal To `{!$Learning_Program_Id}`** (the 2nd condition is marked **Dynamic**), 20 results, citations Off. Return fields (6, several via related-object lookups): **Academic Term Name** (Academic Term → Name), **Program Term Application Timeline Id**, **Application Open Date** (Application Timeline → Application Open Date), **Application Close Date** (Application Timeline → Application Close Date), **Application Category** (Application Timeline → Application Category), **Academic Term Id** (Academic Term → Academic Term Id). This one retriever backs both the Academic Term and PTAT rows in the table above.
  - **Edit the prompt template to wire each retriever (T3 manual) — 3 templates, 2 retrievers.** Open each of the 3 base templates in Prompt Builder — **editing a managed `sturecruitment` template spawns a local `*_Override` template** (e.g. `getLearningPrograms_Override`, `IsOverride:true`, `ManageableState:unmanaged`); the base stays managed/read-only and gets `OverriddenTemplates:[...]`. Wire the retriever at its `PLACEHOLDER_FOR_DATA_RETRIEVER` line via **Insert Resource → Search → `<object>` → `<retriever>`** — the picker resolves the retriever **by label** so the customer never types the non-deterministic API suffix. If the picker isn't used, paste the API Name copied from the retriever detail page. Wiring per template:
    - `getLearningPrograms` → **Learning Program Retriever**; Data Model Object **Learning Program**; search text `Input:learningProgramName`.
    - `getAcademicTerms` → **Program Term Application Timeline Retriever**; Data Model Object **Program Term Application Timeline**; search text `Input:academicTermName`; pre-filter `Learning Program.Learning Program Id` Equal `Input:learningProgramId`.
    - `getApplicationTimelines` → same retriever, DMO, and pre-filter as `getAcademicTerms`; search text `Input:academicTermName`.
    Save & Activate. The wiring produces two changes: the Content placeholder becomes `{!$EinsteinSearch:<RetrieverApiName>.results}`, and a `GenAiPromptTemplateDataProvider` child is added (params `searchText` = `{!$Input:<inputParam>}`, `outputFieldNames` = JSON array of the retriever's return fields, `resultCount`). Sequence: build+activate the retriever FIRST, then wire the template(s) that use it — build the PTAT retriever once, then wire both `getAcademicTerms` and `getApplicationTimelines` to it. (No viable clone/create-automation for the override — the create body schema is unpublished; do it in Prompt Builder.)

> **WARNING: There is NO tier-2 `sf project deploy` path for grounding metadata** — `DataLibrary`/`SearchIndex`/`AIRetrieverDefinition`/`DataSemanticSearch`/`GenAiPromptTemplate`-retriever-wiring are not in the supported-metadata-type index, and MDAPI deploy does NOT build the index. Do not present tier 2 as a path for Mechanism 2. Attempt T1 for the data spine; everything downstream is T1-verify-only around a T3 UI build.

### T1 verify — per leg (each has a different surface; the retriever has NONE)

Most of the spine is verifiable at tier 1, but the surfaces differ by leg — do not use one query for all:

- **DMO mapped (data spine):** `GET /services/data/vXX/ssot/data-model-objects/ssot__<Object>__dlm` (dispatch_readonly) → assert `isEnabled:true` and the required fields show `isMapped:true`.
- **Search index built:** `GET /services/data/vXX/ssot/search-index` (list) or `GET .../ssot/search-index/<developerName>` (dispatch_readonly) → poll `runtimeStatus == "READY"` before wiring the retriever (a just-created index reads `null` while indexing, then flips to READY on its own).
- **Retriever: NO API existence check exists** (create/read have no API surface — see the T3 bullet). The retriever is **not** a Tooling sObject; do **not** attempt `SELECT ... FROM AIRetrieverDefinition`/`AiRetriever` (404s). Verify in the UI: Einstein Studio → Retrievers list shows it **Active**, and copy its API Name from the detail page.
- **Prompt template wired (T1):** `GET /services/data/vXX/einstein/prompt-templates/<devName>` (dispatch_readonly) → assert the active version's `Content` contains `{!$EinsteinSearch:<RetrieverApiName>.results}` and that a `GenAiPromptTemplateDataProviders` child with `Definition: invocable://getEinsteinRetrieverResults/<RetrieverApiName>` is present. (`GET .../einstein/prompt-templates` lists all.)

### Caveats

- **Keep the two index surfaces separate.** The Knowledge-sourced library (Mechanism 1) and the Data Cloud hybrid index (Mechanism 2) are distinct — do not attempt to share one index across both.
- **The prompt-template retriever wiring is a T3 UI step, but its verify is T1.** There is no supported Connect endpoint/body for inserting a retriever into a prompt template (the create-body schema is unpublished) — do the wiring in Prompt Builder. **Verify** it, though, with the tier-1 `GET /einstein/prompt-templates/<devName>` assertion above (Content merge field + `GenAiPromptTemplateDataProviders` child), not just a retriever read-back.
- **CRITICAL: DLO→DMO mapping of Boolean/Date fields is fragile — verify it, don't assume auto-map alone is enough.** `auto-map-dlos` leaves Boolean- and Date-sourced fields unmapped until the formula-field fix above is applied (the CRM connector derives them as Text/DateTime on the DLO, which won't type-match the DMO). Verify these mappings hold:
  - **AcademicTerm (`ssot__AcademicTerm__dlm`)** — `ssot__Name__c` (= `Academic_Term_Name`) plus season map correctly out of the box; `IsActive`, `StartDate`, `EndDate` do not (Text/DateTime on the DLO) — need the Boolean/Date formula-field fix above before they'll map.
  - **LearningProgram (`ssot__LearningProgram__dlm`)** — same story, 5 fields (`IsActive`, `IsTopLevelProgram`, `DoesCreateOpportunityRecord`, `ActiveFromDate`, `ActiveToDate`) — same fix, see the table above.
  - **ApplicationTimeline (`ssot__ApplicationTimeline__dlm`)** — same story, 9 Date fields (no Booleans on this object) — `ApplicationOpenDate`, `ApplicationCloseDate`, `DecisionReleaseDate`, `GraduationApplnDeadline`, `EarlyActionOpenDate`, `EarlyActionCloseDate`, `EarlyApplicationOpenDate`, `EarlyApplicationCloseDate`, `EarlyApplnDecisionRelDate` — same fix, see the table above.

### Verify (either mechanism)

Step-13 conversational smoke test (user-run in the deployed channel) — the agent returns a Learning-Program-grounded (and Academic-Term / PTAT-grounded) answer to a program query, and a Knowledge-grounded answer to an FAQ query.
