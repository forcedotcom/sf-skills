# Admissions flows — inventory & clone recipe

Read at Workflow step 11 (the last of the agent-build block, after the agent is committed in step 9a and right before channel deploy — unauthenticated/Service path only, **not** the foundation phase). Package flows live in the `eduadmissions` namespace.

The whole flow lifecycle is **tier 1**: inventory, retrieve, clone (as override or from template), and edit run over the Connect-REST `/flowbuilder/*` surface (`dispatch`/`dispatch_readonly`); **activation** is the tier-1 Tooling `FlowDefinition` PATCH (step 4 below), and verify is a tier-1 `/query`. No tier-2/tier-3 fallback is needed for the clone itself.

> **WARNING: Sequencing — do this with the unauthenticated-agent build, not in the foundation phase.** This entire file is **unauthenticated/Service (ASA) agent path ONLY** — skip it entirely if you're only building the authenticated/Employee agent. The flows have no ordering dependency on the *agent* build (the override links by reference to the managed original, so packaged subagent actions keep resolving through it, and the only user-ish input is `DefaultUserOwnerId` = a System Admin Id, resolved inline from the running user (below) — not any agent's running user). But do not front-load it into the early permissions/OWD foundation block — it belongs with unauthenticated-agent creation and channel deploy. In a partial build, defer it until the ASA agent is actually being built.

## The two clone mechanisms (one endpoint, one linkage key apart)

Every clone is the **same** call — `POST /services/data/vXX/flowbuilder/flow/actions/save` (note the `/actions/` segment — the bare `/flowbuilder/flow/save` path 405s `METHOD_NOT_ALLOWED`, GET/HEAD only) with `saveType:"createNewFlow"`, fed the platform's own retrieved flow JSON. The mechanisms differ **only** by which key you add to `metadata`:

| Mechanism | Source flow property | Key you add to `metadata` | Populates | Runtime behavior |
|---|---|---|---|---|
| **Override** | `isOverridable:true` | `overriddenFlow: "<managed ApiName>"` **and set `isOverridable:false`** on the clone itself | `FlowDefinitionView.OverriddenFlowId` | Intercepts the managed original at runtime |
| **Create-from-template** | `isTemplate:true` | `sourceTemplate: "<template ApiName>"` + `isTemplate:false` | `FlowDefinitionView.SourceTemplateId` | Standalone new flow seeded from the template |

> **CRITICAL: an override clone must flip `isOverridable` to `false` on itself.** The retrieved managed source carries `isOverridable:true`; saving the clone as-is with that flag still `true` fails `FLOW_OVERRIDABLE_CANNOT_BE_OVERRIDE` ("a flow that overrides another can't itself be overridable"). Only the managed original stays overridable — the override clone must set `isOverridable:false` alongside adding `overriddenFlow`.

Do **not** use `POST /flowbuilder/flow/actions/clone` on a managed source — it tries to modify the managed `InteractionDefinitionVersion` and fails `MANAGED_INSTALLED`. `save createNewFlow` creates a *new* unmanaged flow and is the one recipe for both buckets.

> **CRITICAL: An overridable flow accepts only ONE override — a pre-existing override blocks a fresh clone.** If the managed original is already overridden (by a customer's own customization, or a prior/partial SRA build), a second override `save` still returns `201 isSuccess:true` but with `status:"InvalidDraft"` and a `FLOW_ALREADY_OVERRIDDEN` warning — activation-blocking, not a hard error. **WARNING: The step-1 `FlowDefinitionView.OverriddenFlowId` read does NOT reliably detect this** — an inactive/Draft override leaves `OverriddenFlowId` null yet still blocks a new one. So on a `FLOW_ALREADY_OVERRIDDEN` warning, the existing override named in the message is the one to reuse or remove — do not create a duplicate; adopt the existing override clone (or delete it first if it's a stale partial), rather than assuming a null `OverriddenFlowId` means the slot is free.

## Flow inventory & the 2-wave ordering

The 6 flows fall into three roles: **reusable subflows** (called by others), **consumers** (which call those subflows), and one **standalone** (`GetPlnCampaigns` — no dependencies, rides in wave 1 only because nothing blocks it). The dependency is between subflows and consumers, creating a hard producer→consumer ordering: **clone AND activate the wave-1 flows first** (the 2 subflows + the standalone), then clone the wave-2 consumers and re-point them at the active subflow clones. (If a consumer references a still-Draft subflow clone, its save returns a `SUBFLOW_NO_ACTIVE_VERSION` warning that blocks activation.)

| Wave | Flow (label) | Package API name | Role | Mechanism |
|---|---|---|---|---|
| **1** | EDU Admissions: Get Planned Campaigns | `GetPlnCampaigns` | standalone (unauthenticated campaign read) | override, no edits |
| **1** | EDU Admissions: Process Person Account | `ProcPersAcct` | reusable subflow | create-from-template |
| **1** | EDU Cloud: Inquiry: Academic Interest Processing | `InquiryAIProcessing` | reusable subflow | create-from-template |
| **2** | EDU Admissions: Create Campus Tour Registration | `CreateCampusTourRgstr` | consumer | override + subflow edits |
| **2** | EDU Admissions: Process Academic Interest | `ProcessAcademicInterest` | consumer | override + subflow edits |
| **2** | EDU Admissions: Create Inquiry | `CreateInquiry` | consumer | override + subflow edits |

> The two create-from-template flows ship **Draft-only** (no active version) — expected, since a template is instantiated rather than run directly. Their clones must be activated for wave 2 to reference them.
>
> `CreateInquiry` ships wired to **no** packaged subagent by design — it gets wired into the customer-built escalation subagent, added by the customer in step 9a (see `agent-and-subagents.md`). It creates Case + Educational Info Request + Academic Interest.

## The clone lifecycle (tier 1, per flow)

All calls over Headless `dispatch`/`dispatch_readonly`; substitute the org's current API version for `vXX` (the flow verify `/query` needs **v62.0+** as a minimum — see the API version policy in `execution-model.md`).

1. **Retrieve the managed source** (`dispatch_readonly`): `GET /services/data/vXX/flowbuilder/flow/{activeVersionId}` (or `{ApiName}-{versionNumber}`, or `LatestVersionId` for a Draft-only template) → `body.flow.metadata` is the flow body to edit. (Managed flows ARE readable here.)
2. **Edit the metadata** (no call — mutate `flow.metadata` in place): add the linkage key for the mechanism (`overriddenFlow`, or `sourceTemplate` + `isTemplate:false`). **For an override clone, also set `isOverridable:false`** on the clone's own metadata — the retrieved source carries `isOverridable:true`, and saving it unchanged fails `FLOW_OVERRIDABLE_CANNOT_BE_OVERRIDE`. For every cloned flow set the run mode to system context (below). Consumers additionally swap subflows + set the owner constant (below).
3. **Save as new flow** (`dispatch`): `POST /services/data/vXX/flowbuilder/flow/actions/save` (the `/actions/` segment is required — the bare `/flowbuilder/flow/save` path returns `405 METHOD_NOT_ALLOWED`, GET/HEAD only) body `{ "saveType":"createNewFlow", "builderType":"FlowBuilder", "flow": { "fullName":"{newUnmanagedApiName}", "metadata": { ...edited... } } }` → `201 { isSuccess:true, status:"Draft", versionNumber:1, definitionId, flowId, errors:[], warnings:[...] }`. Inspect `warnings[]` even on success — `SUBFLOW_NO_ACTIVE_VERSION` / `SUBFLOW_DIFFERENT_RUNMODE` are activation-blocking and mean a wave-1 clone isn't active yet or a run-mode is mismatched; `FLOW_RUN_AS_SYSTEM_MODE_WITH*_CONTEXT_WARNING` is benign for a system-context flow on the unauthenticated path. (To edit an existing clone → same call with `"saveType":"saveAsNewVersion"` + `"currentFlowId":"{priorVersionFlowId}"`.)
4. **Activate** (`dispatch`): the working path is a Tooling `FlowDefinition` PATCH — query `FlowDefinition` by DeveloperName for the `300`-prefix def Id, then `PATCH /services/data/vXX/tooling/sobjects/FlowDefinition/{defId}` `{"Metadata":{"activeVersionNumber":N}}` (N = version number, 0 to deactivate) → **204**. This activates a version *by number* without rewriting it. **WARNING:** Do **not** use `PATCH /tooling/sobjects/Flow/{flowId}` `{Metadata:{status:'Active'}}` — it overwrites the version body and 400s `INVALID_STATUS` once a version has been active. The native `POST /flowbuilder/flow/{flowId}/actions/activate` endpoint is not reliably available (it 404s on some orgs) — attempt only if preferred, falling back to the FlowDefinition PATCH on a 404. Read `FlowDefinitionView.IsActive` first and only activate if false.
5. **Cold-verify** (`dispatch_readonly`): re-run the inventory query (below), don't trust the activate response alone.

### Common edit for every cloned flow — system-context run mode

Set `metadata.runInMode = "SystemModeWithoutSharing"` (the UI's *Show Advanced → How to Run the Flow → "System Context Without Sharing – Access All Data"*). **Mandatory** for the unauthenticated/Service path, not optional polish.

### Consumer edits (wave 2) — subflow swap + owner constant

For each wave-2 consumer, before `save`: repoint each subflow element's `flowName` to your **active** wave-1 clone (keep the element `name` unchanged so downstream dotted references like `{subflowName}.incomingPersonAccount.PersonContactId` stay valid), and set the `DefaultUserOwnerId` constant's `value.stringValue` to a System Admin user Id. **Always ask the customer** whether that owner should be the current (running) user or someone else — don't silently default. The running user is already required to be a System Administrator (see `prerequisites.md`), so offer it as the default: reuse the Id already resolved at Step 4a (`permissions.md`) — no need to re-derive it. If that Id isn't available, resolve it via `SELECT Id FROM User WHERE Username='<current user>'` over `dispatch_readonly`, then confirm before using it; if they name a different owner, look that user up instead (`SELECT Id FROM User WHERE …`).

- **`CreateCampusTourRgstr`** — swap the one `Process Person Account` subflow → active `ProcPersAcct` clone; input `incomingPersonAccount = {!PersonAccountDetails}`.
- **`ProcessAcademicInterest`** — swap TWO subflows: (a) `Process Person Account` → active `ProcPersAcct` clone, `incomingPersonAccount = {!PersonAccountDetails}`; (b) `Academic Interest Processing` → active `InquiryAIProcessing` clone, inputs `academicTermId = {!AcademicInterestDetails}`, `incomingPersonAccount = {!ProcessPersonAccount.incomingPersonAccount}`, `isNewPersonAccount = {!ProcessPersonAccount.isNewPersonAccount}`, `selectedLearningProgramIds = {!learningProgramIds}`; manually-assigned output `newAcademicInterestIds = {!academicInterestIds}`.
- **`CreateInquiry`** — same pattern as `ProcessAcademicInterest`.

## Verify (concrete call — run after cloning each wave)

Use the Data-API **`FlowDefinitionView`** (backs the Setup → Flows list) over `dispatch_readonly` — **not** Tooling `FlowDefinition`, which is blind to package-namespaced flows and returns 0 rows for these. Presence of the packaged flows is gated on `NamespacePrefix='eduadmissions'`, **not** on `InstalledSubscriberPackage` (which does not register these feature packages).

```text
GET /services/data/vXX/query/?q=
  SELECT ApiName, Label, NamespacePrefix, ManageableState, IsActive,
         ActiveVersionId, LatestVersionId, OverriddenFlowId, SourceTemplateId
  FROM FlowDefinitionView
  WHERE NamespacePrefix='eduadmissions'
    AND ApiName IN ('GetPlnCampaigns','ProcPersAcct','InquiryAIProcessing',
                    'CreateCampusTourRgstr','ProcessAcademicInterest','CreateInquiry')
```

Notes: `FlowDefinitionView` has **no `Status` field** (use `IsActive`); the field is **`ApiName`**, not `DeveloperName`; the WHERE clause does **not** support OR/disjunctions — use `IN (...)` or split into separate queries. To confirm a clone: query it by its new `ApiName` and check `ManageableState='unmanaged'`, `IsActive=true`, and the linkage field (`OverriddenFlowId` = the managed original, or `SourceTemplateId` = the template). This `/query` read is the tier-1 normal path; keep the `sf data query` (tier 2) / UI fallback ready for a transient `/query` outage window (see `execution-model.md` on the query-family caveat).

## Notes

- Help ref: `sfdo.ec_inquiry_flows_setup.htm`.
- These flows run in system context (`SystemModeWithoutSharing`, above) under the ASA's **Einstein Agent User** service account — there is no guest user (see `permissions.md`). Object access (e.g. Create on `Account`) comes from that account's `SRA_AI_Agent_Access` clone (of `EducationCloudAiAgentAccess`, built step 4b), not a guest profile.
