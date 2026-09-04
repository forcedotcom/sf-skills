---
name: education-cloud-student-recruitment-agent-configure
description: "Use this skill to set up and configure the Education Cloud Student Recruitment Agent (SRA) — the packaged Agentforce agent (namespace sturecruitment) that answers admissions FAQs, captures inquiries, registers campus tours, and files applications for prospective students. TRIGGER when the user wants to: create or configure an admissions, recruitment, or enrollment agent, set up the Student Recruitment Agent, deploy SRA to an Experience Cloud site, clone the SRA flows or permission sets, add the SRA subagents (Admissions and Enrollments FAQ; Admissions Application; Campus Tours, Visits, and Events Registration; Request for Information), wire Learning Program grounding, or build the escalation subagent. Guides platform enablement, permissions, grounding, agent creation, and channel deployment — API-first with UI fallback. DO NOT TRIGGER for the Transfer Credit Agent, generic Agentforce authoring (use agentforce-generate), or base Education Cloud domain enablement."
metadata:
  version: "1.0"
  minApiVersion: "67.0"
  domains: ["Education"]
  relatedSkills:
    - "agentforce-generate"
    - "platform-custom-field-generate"
    - "platform-metadata-deploy"
    - "platform-sharing-owd-configure"
    - "platform-sharing-rules-generate"
  # Runtime tier 1 is the headless `dispatch`/`dispatch_readonly` MCP tools.
  # `sf` is the tier-2 fallback (MDAPI deploy + discovery/aggregate verifies) for
  # runtimes that have a shell. See the three-tier ladder in `references/execution-model.md`.
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "license"
      value: "Agentforce"
    - type: "orgPerm"
      value: "EinsteinForEducationCloud"
---

# Configuring the Education Cloud Student Recruitment Agent

## Scope

- **In scope**: The full SRA setup sequence — the three platform toggles (Einstein, SRA, Omni-Channel; Agentforce provisioning is a verify-only Step-1 gate, not a toggle the skill flips), the `EducationCloudAiAgentAccess` permission set + OWD/sharing foundation, Learning Program grounding (Data Cloud data stream + hybrid search index + prompt template) and Knowledge/data-library grounding, creating the Service (unauth) and Employee (auth) agents, adding the 4 packaged SRA subagents, building the customer escalation subagent, cloning and configuring the 6 admissions flows (Service path), and deploying to Experience Cloud channels with user verification.
- **Out of scope**: The **Transfer Credit Agent** (separate agent, own perms/help — never include its steps); generic Agentforce agent authoring from scratch (see Cross-Skill Integration below); Data Cloud connector plumbing beyond the SRA grounding path; deciding the substance of Knowledge article content — Claude may draft an article for the customer to review, but the customer owns what it says.
- **The EDU foundation is a checked dependency, not an assumption**: SRA depends on base Education Cloud enablement, Person Accounts, R&A domain objects, and Data Cloud. This skill doesn't re-implement base Education Cloud domain enablement, but verifies each piece concretely (step 2a) and only surfaces a gap to the user to *fill what it detects*.

---

## Required Inputs

Gather or infer before starting:

- **Target org**: An Agentforce- and Education-Cloud-provisioned org with admin access — see Workflow step 1 for the gate.
- **Agent path(s)**: Unauthenticated (**Service** agent — the ASA, runs as the Einstein Agent User service account; no guest user), authenticated (**Employee** agent), or both.
- **Which subagents/topics** the customer wants live (default: all 4 packaged subagents + a custom escalation subagent).
- **Whether to add Create Inquiry to the Escalation subagent** (case-adjacent record creation on live-agent handoff) — ask if unspecified; the two outcomes are handoff-only, or handoff-plus-Create-Inquiry.

Defaults unless specified:
- Configure both agent paths if the org has both Service and Employee Agentforce licenses; otherwise the unauth/Service path only.
- Confirmation style: conversational, one-step-at-a-time — never autonomous. See *Talking to the user* below.

---

## How this skill runs — read first

**Step 0 resolves the org's current API version; Step 1 is a hard prerequisites gate — clear both before touching anything else.** The rest is a linear, sequential set of steps (0–13); confirm before every irreversible or org-shaping action, and end every step with its verify call. (See *Talking to the user* below.)

**Every org-changing step walks a three-tier ladder, then verifies — tier = what runtime you have:** **T1** headless MCP (`dispatch`/`dispatch_readonly`, no shell) · **T2** `sf` CLI (needs a shell) · **T3** Setup UI. Try T1; drop to T2 on a route/allowlist failure; T3 if no shell. Steps carry a best-tier tag; the verify-only preflight (step 1) uses STOP/ASK-USER labels instead. `references/execution-model.md` has the ladder detail — allowlist, route signals, query-routing, API-version policy; read it whenever a tier or route is unclear.

**Several steps land on T3 with no tier-1/tier-2 write path at all** (hand the user the Setup path, then verify) — each is tagged inline where it occurs (e.g. `[T3 · ...]` on steps 8, 9a, 12); every other action has a tier-1 path.

---

## Talking to the user — customer-facing narration (not optional)

**Mandatory, every run: read `references/customer-narration.md` in full before your first message to the customer — this is not background reading, it's the exact wording rules you follow at every step boundary for the entire session.** In short: the step numbers, tier tags (`T1`/`T2`/`T3`), and words like "gate," "the spine," or "per the doc" are internal authoring scaffolding — never say them to the customer, who has no idea this skill file exists. Lead every step boundary with the plain-language outcome, not the internal label; give a manual (UI) hand-off its complete concrete detail in the same message that asks the customer to go do it; and before every single create/update/delete, no matter how small, explain what it does and why in plain language, then wait for an explicit go-ahead — never on silence, never batched. `references/customer-narration.md` has the exact phrasing table and the do/don't examples — read it now.

---

## Workflow

All steps are sequential. Each step is one action + its best tier + a pointer to the reference that carries the exact calls, API names, and traps — read that reference before executing the step. Confirm before irreversible actions; end every step with its verify call.

### 0 — Resolve the org's current API version

> **Do this first — before Step 1, before any other call in the run. Every `vXX` used in every step and reference file below comes from this resolution; never substitute a remembered or hardcoded version.** **CRITICAL: If this session has more than one Salesforce connection available, pin whichever one you use for this call as the org connection for the rest of the run — including after a context compaction.** A compacted summary can lose track of which connection was active; don't let that cause a switch to a different one partway through.

0. **Resolve the current API version** [T1] — `dispatch_readonly({"url": "/services/data/", "method": "GET"})` on the org connection you're pinning for this run → take the **highest numeric `version`** from the returned array and reuse that literal, on that same connection, for every `vXX` call for the rest of this run. A stale/hardcoded version can make a real entity or feature absent from a schema-catalog read and misread as "the org doesn't have this." Full rationale and the per-surface version-floor exceptions: `references/execution-model.md`.

### 1 — Verify prerequisites & gates

> **Step 1 is a hard gate — clear it before enabling or building anything.** If a STOP check (external grant the skill can't flip) or an ASK-USER check (foundation the skill doesn't own) fails, **do not start the toggles or the foundation build** — stop and request the grant, or have the user complete the missing Education Cloud foundation setup, then re-verify. **Also confirm now, before saying anything to the customer: `references/customer-narration.md` has been read in full this run (see *Talking to the user* above) — this gate isn't cleared until that's true too.** Don't build permissions/OWD/grounding for an agent that can't exist. Full preflight-gate table and every verify call: `references/prerequisites.md`.

1. **Confirm edition & the Einstein-for-EDU license.** Both are STOP checks — halt if either is missing. (Agentforce provisioning is verified in item 2; Data Cloud in item 2a.)
2. **Verify the three SRA gates** — Agentforce provisioning, Education Cloud enabled, and the runtime `orgHasStudentRecruitmentAgentBetaAccess` check (a three-part AND — its exact composition and per-part verify live in `references/prerequisites.md`). Stop if provisioning, the license, or the Gater is missing.
   - **2a — Verify the EDU foundation** (don't assume base Education Cloud domain enablement has run): EDU enablement, Person Accounts, R&A domain schema, and Data Cloud. Ask the user to complete the first three, then re-verify; Data Cloud is a Home-Org grant (that's a STOP, not something the user can self-serve).

### 2 — Enable the platform toggles

3. **Enable the three platform toggles** [T1] — each has its own write path: Einstein Setup (`EinsteinGPTPlatformEnabled`), `RecruitmentAgentEnabled`, and Omni-Channel (`OmniChannelSettings` — required for channel deploy). → `references/platform-enablement.md`

### 3 — Permissions & sharing foundation
→ `references/permissions.md`

4. **Clone + configure the persona permission sets, and assign the builder persona** [T1] — the OOTB `EducationCloudAiAgentAccess` is an empty shell, so clone it and customize its object/field matrix (assign the **clone**, never per-topic). **Assign the Admin/builder persona to the running user before cloning** — it grants the EDU field visibility the matrix build needs. **Auth/Employee path only:** also clone + configure `EducationCloudExprcCloudAccess` (Run Flows + object settings) for the community persona. The Einstein-user assignment is agent-dependent — Claude creates that user itself and grants it at **step 9**. The community-user assignment (and Enable Agent Access) is likewise agent-dependent → **step 10**.
5. **Set OWD to Public Read Only on the 6 admissions objects** [T1 · one UI exception].
6. **Do the topic-specific prep — 5 blocks** [T1 · two UI exceptions]: Campaign "Recruitment Event" picklist value + "Campus Tours" sharing rule, the Individual Application record type + its `ApplicationRecordTypeConfig`, and record-type→profile visibility.

### 4 — Grounding (two independent mechanisms)
→ `references/grounding.md`

7. **Set up Knowledge grounding** [T1 · article authoring is human] — **check for existing Knowledge articles first and always ask the customer before drafting anything** (never auto-create — see `references/grounding.md` 7a), then create the Knowledge-sourced data library. Attaching it to the agent happens at **step 9** (a top-level AFScript field, wired into the same draft-only pass — no need to wait for the agent to be committed); the create itself needs no agent. Once wired, newly published articles are picked up automatically — no re-wire per article.
8. **Wire Data Cloud grounding — 3 grounded objects, 2 search-index/retriever builds** (Learning Program; Academic Term shares the PTAT build) [T1 data spine · T3 index/retriever/prompt build].

### 5 — Agent, subagents & flows

9. **Create the agent(s) — headless, draft only** [T1] — fetch the real base template (Service: "Agentforce Service Agent", Employee: "Agentforce Employee Agent"), and in one combined pass: resolve `NEW_AGENT_USER` by creating the ASA's Einstein Agent User + granting it full perm/license parity (ASA only), strip the 7 default topics incl. the default Escalation topic (ASA only), author a handoff-only Escalation subagent (both paths — no Create Inquiry yet), and wire the step-7 knowledge library (both paths). Stop at `compile` — **do not `publish`**; UI fallback available at T3. → `references/agent-and-subagents.md`
   - **If step 8's Data Cloud data spine was deferred while streams were still provisioning, check back on it now.** If it's still provisioning, check again at the end of each subsequent step (9a, 10, 11, 12) — it must be finished, including the T3 index/retriever/prompt-template build, before step 13's final verify. See `references/grounding.md` Mechanism 2 step 3.
   - **9a — The customer's one Builder session** [T3 · Asset Library + Builder UI] — open the draft agent and: add the 4 packaged SRA subagents (Admissions and Enrollments FAQ; Admissions Application; Campus Tours, Visits, and Events Registration; Request for Information) from the Asset Library so the correct action `source`/`target` is set (not hand-authorable; watch for `TransferCreditEquivalency` in that list — Transfer Credit Agent's, not SRA's); delete the Create Admissions Application action (non-functional — confirm with the customer first); add Create Inquiry to the Escalation subagent via Builder's action picker per the Required Inputs choice, or skip it for handoff-only (left out at step 9 — its input mapping isn't safe to hand-author blind). Then **Save, then Commit Version — once**; nothing from step 9/9a is queryable before that. → `references/agent-and-subagents.md`
10. **AEA/Employee-only: enable community access** [T1 write] — skip entirely on an ASA/Service-only build; the ASA path has nothing left here (topic cleanup, escalation authoring, knowledge, running-user grants all happen in step 9). Set **Enable Agent Access → the AEA agent** on the `SRA_Exprc_Cloud_Access` clone (built at step 4), then query existing community users and ask before assigning the clone + sibling PSs to them. → `references/agent-and-subagents.md` & `references/permissions.md`
11. **Clone and configure the 6 admissions flows — unauthenticated/Service path only** [T1]. Two waves: clone + activate the wave-1 flows first — the 2 reusable subflows plus the 1 standalone flow (`GetPlnCampaigns`, which has no dependencies) — then clone the 3 consumers and re-point them at the active subflow clones. Skip entirely if building only the Employee agent. → `references/flows.md`

### 6 — Deploy to channels & route
→ `references/routing.md`

12. **Deploy each agent to its channel + stand up Omni-Channel routing** [T1 routing objects · T3 messaging deployment & site] — read what exists first; front-load Experience Cloud site creation for any agent that doesn't already have one (the slowest part of this stack), then build the routing config → queue → inbound flow → channel stack while it provisions, then come back to the site to add the component and publish. One agent per channel = separate sites. **Auth/Employee path:** also enable user verification inline (two checkboxes, channel + site component; the unauthenticated/Service path gets neither).
13. **Final structural verification** [verify] — run the queryable roll-up (agent active, all subagents present, flows active, channel + site up), then summarize which tier each step landed on and list anything left manual. **Finish here — do not wait on any manual action.** The conversational smoke test (messaging the agent so subagents respond, grounding answers, actions produce records) needs a live channel session that can't be driven headlessly; hand the user that short checklist to run themselves and don't poll for its results.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Never promise a rollback you haven't confirmed | Reversibility differs per toggle — see `references/platform-enablement.md`; warn before any flip |
| Knowledge articles must be Published and contain no non-public data | The FAQ action is public; draft articles make the agent answer "no information" |
| Always confirm before *any* create/update/delete; run every step and its verify yourself — never delegate any part of this workflow to a separate helper process | See *Talking to the user* — the confirmation model depends on one continuous conversation; a delegated helper can prompt the customer on its own. polling isn't delegation |
| Do not deploy or push metadata packages | This skill configures a live org; package deployment belongs to a separate lifecycle skill |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| Org can't run SRA (agent endpoints 501 / `BotDefinition` not queryable, or `RecruitmentAgentEnabled` toggle absent/not-editable) | Preflight STOP check — catch at Step 1, not the Step-9 wall. Traces to one of three missing grants: Agentforce provisioning, the Einstein-for-EDU license, or the `StudentRecruitmentAgent256` Gater. Detect which and request it; don't retry lower tiers. See `references/prerequisites.md` |
| Messaging channel created headlessly but the agent isn't reachable at runtime | The channel record is tier 1, but the ESD cascade behind it is UI-only — hand the customer the UI deployment path in `references/routing.md` |
| Cloned consumer flows fail at runtime | Wave-2 consumers need subflow replacement + `DefaultUserOwnerId`, not just a clone — see `references/flows.md` |
| Subagent action target `compile`s clean but won't `publish` | `compile` is syntax-only and echoes back any target; only `validate`/`publish` check existence. Never hand-author targets — add subagents from the Asset Library so the correct `source`/`target` is injected. See `references/agent-and-subagents.md` |
| Only **Create Admissions Application** fails validate | The lone `api://` action; broken by a platform issue everywhere, not fixable from this org. Delete it at step 9a rather than working around it — every other action still publishes. See `references/agent-and-subagents.md` |
| Agent answers "no information" | Two causes: (1) Knowledge articles still Draft — publish them (tier-1 API-able), or (2) the data library isn't attached — check the AFScript's `knowledge.rag_feature_config_id` is `ARFPC_<libraryId>`, not empty. Check both |
| EDU objects (e.g. Academic Interest) show **0 fields** in Object Manager / the step-4 field-matrix build finds nothing | Ordering issue — the admin lacks the builder EDU-access sets. Assign **Education Cloud Full Access** + **Einstein for Education Cloud Access** first, before the field-matrix clone — fields are license-gated until then. See `references/permissions.md` |
| OWD or `ApplicationRecordTypeConfig` verify silently returns 0 rows | API-name traps: OWD's 6th object is **`ProgramTermApplnTimeline`** (truncated, not `...ApplicationTimeline`); perm-set uses `PreliminaryApplicationRef`. `RecordTypeName` takes the record type's **LABEL**, not DeveloperName/Id. See `references/permissions.md` |
| `/headless/metadata` returns `400 UNSUPPORTED_OPERATION` or `500 METADATA_CRUD_ERROR` | Drop to tier 2/3, don't retry — but first rule out a wrong-surface or missing-perm error, not an allowlist gap. See `references/execution-model.md`; the `setup/org/preferences` `ROUTE_NOT_FOUND` case: `references/platform-enablement.md` |
| `/query` returns `404` and looks like a platform outage | Check the call shape first — often self-inflicted: SOQL appended as `?q=...` instead of `queryParams: {"q": "<SOQL>"}`. A real outage is transient and all-versions-at-once. See `references/execution-model.md` |
| An earlier step genuinely needed `sf`/UI, and later steps keep using it too, out of habit | The tier ladder resets every step — re-attempt T1 first on each new action regardless of where the last step landed. See `references/execution-model.md` |

---

## Output Expectations

This skill configures a live org; no repository files. Expected outputs:

- Confirmation messages after each step (what was done, and at which tier — headless / `sf` CLI / manual UI).
- A **verify query result after every step** showing each toggle, perm set, flow, agent, subagent, and channel is in the expected state.
- A final summary listing which tier each step landed on, plus any items left pending on the T3-only steps.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Generic Agentforce agent authoring or metadata generation | `agentforce-generate` |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/execution-model.md` | Any step — tier-ladder detail: allowlist, route signals, query-routing, API-version policy |
| `references/prerequisites.md` | Step 1 — edition/license check, the three SRA gates, EDU foundation verify |
| `references/platform-enablement.md` | Step 3 — per-toggle write paths |
| `references/permissions.md` | Steps 4–6, 9 & 10 — persona perm model, OWD list, topic-specific prep, agent-dependent grants |
| `references/grounding.md` | Steps 7–8 — Knowledge article/library flow, Data Cloud grounding builds |
| `references/agent-and-subagents.md` | Steps 9, 9a & 10 — agent creation, subagent + escalation wiring, the Builder session, AEA community grants |
| `references/flows.md` | Step 11 — flow inventory, 2-wave clone ordering |
| `references/routing.md` | Steps 12–13 — channel deploy, Omni-Channel routing, final structural verify |
