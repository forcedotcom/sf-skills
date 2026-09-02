---
name: service-itsm-agentic-setup-agent-runtime-access-assign
description: "Grant a user the runtime permissions an activated ITSM agent's actions need so the actions do not fail on permission errors. After a Fulfiller or Employee agent is activated, this skill detects which platform feature permission sets are provisioned (Prompt Templates, Data Cloud, Unified Catalog), lets you pick a tier (user/agent vs admin) per feature and which user(s) to assign, then assigns them (license first when license-gated). It also creates a custom \"Agent Access\" permission set granting the activated agents you choose and assigns it to the user — all via the Salesforce CLI. Use to grant a user access to an activated agent, to assign prompt-template, data-cloud, or unified-catalog access, or to create an Agent Access permission set. DO NOT TRIGGER for enabling Agentforce for IT Service toggles, creating or activating an agent, the Fulfiller activation action-surfacing gap (service-itsm-agentic-setup-itsm-agentforce-permset-assign), CMDB access, or generic permission-set assignment."
metadata:
  version: "1.1"
  domains: ["Service", "Agentforce"]
  minApiVersion: "67.0"
  relatedSkills:
    - "service-itsm-agentic-setup-agentforce-studio-configure"
    - "service-itsm-agentic-setup-cmdb-access-assign"
    - "service-itsm-agentic-setup-employee-agent-configure"
    - "service-itsm-agentic-setup-fulfiller-agent-configure"
    - "service-itsm-agentic-setup-itsm-agentforce-permset-assign"
  cliTools:
    - tool: ["node"]
      semver: ">=18.0.0"
    - tool: ["sf"]
      semver: ">=2.0.0"
  accessCheck:
    - type: "license"
      value: "Agentforce"
allowed-tools: |
  Bash
  Read
  AskUserQuestion
---

# Grant Runtime Access for an Activated ITSM Agent

An ITSM agent (Fulfiller or Employee) can be created and activated, yet **fail the moment it's opened** — its actions call platform features the **user** can't execute. This skill closes that gap after activation via two write-capable steps behind one confirmation:

1. **Runtime action-execution permissions.** Detect which **feature permission sets** are provisioned, let the user pick a **tier per feature** (user/agent vs admin) and which **user(s)** to grant, then assign — **license first** when license-gated.
2. **A custom "Agent Access" permission set.** Create (or reuse) **Agent Access**, grant the **activated agents** the user chooses (one `SetupEntityAccess` per agent), then assign it to the same user(s).

The verified feature → tier → permset matrix lives in `references/permset-topology.md`. **No org has all three features** — assign only what is provisioned and report the rest as unavailable, never failing on an absent feature.

Every read and write runs through the **Salesforce CLI (`sf`)** — no metadata XML, no token extraction, no MCP.

## Scope

- **In scope**: detecting which platform feature permsets are provisioned; per-feature tier selection; asking which user(s) to grant (running user offered, never silent) and resolving them; PSL-then-permset assignment (license-gated tiers) idempotently; creating/reusing the custom `Agent_Access` permission set; adding a `SetupEntityAccess` grant per chosen **activated** agent; assigning `Agent_Access` to the user(s); verifying assignments by read-back.
- **Out of scope** (owning skill parenthesized): the *Agentforce for IT Service* Go toggles / Studio config (`service-itsm-agentic-setup-agentforce-studio-configure`); creating or activating the Employee (`service-itsm-agentic-setup-employee-agent-configure`) or Fulfiller (`service-itsm-agentic-setup-fulfiller-agent-configure`) agent; the **Fulfiller activation** action-surfacing gap (create/activate-time, not this runtime one — `service-itsm-agentic-setup-itsm-agentforce-permset-assign`); CMDB access (`service-itsm-agentic-setup-cmdb-access-assign`); generic non-ITSM permission-set assignment; authoring/editing feature permsets.

## Helper scripts (all invoked via `Bash`) hold every deterministic decision (A9)

Full I/O contracts in `references/helper-contracts.md`.

- `scripts/classify-platform-permset-availability.mjs` — which features are provisioned, each tier's `present` + `needsPsl`, and the org's own display label per tier.
- `scripts/resolve-target-user.mjs` — running-user Id from the API-root `identity` URL (fails closed on a malformed shape).
- `scripts/rank-candidate-users.mjs` — up to five real, non-service candidate users to offer, ranked by audience (standard-license first for a Fulfiller agent, Unified Employee first for an Employee agent).
- `scripts/gate-unified-catalog-tiers.mjs` — per target user, which Unified Catalog tiers to offer (Community User → Unified Employee; Admin → System Administrator), else omit UC for that user.
- `scripts/classify-activated-agents.mjs` — the activated-agent candidate list (BotDefinition `InternalCopilot` with ≥1 `Active` BotVersion).
- `scripts/classify-agent-access-state.mjs` — whether `Agent_Access` must be created and which chosen agents still need a grant (idempotency).
- `scripts/classify-assignment-state.mjs` — per user+permset idempotency; pass the sentinel `NO-PSL` when the selected tier's `needsPsl:false`.

---

## Preconditions

1. **`sf` CLI installed and authenticated to the target org** (`sf org display -o <alias>` shows Connected). All calls use `--target-org <alias>`; never extract or pass the access token by hand.
2. **API v67.0+**.
3. **`node` ≥ 18** on PATH.

If a precondition fails, `sf` surfaces an auth or `401`/`403`/`404`; report the raw response verbatim and stop — do not fabricate state.

---

## Clarifying questions

Ask only what cannot be inferred from conversation:

- **Target org** — the `sf` alias. Default to `sf config get target-org` if unset.
- **Target user(s)** — never a silent default: if unnamed, **ASK** via `AskUserQuestion` (see Phase 2); if named, honor it.
- **Tier per provisioned feature** — for EACH provisioned feature, ask which tier (lighter **user/agent** vs full **admin**); never auto-select.
- **Which activated agents** — multi-select from the activated-agent list; if only one is activated, still confirm it.
- **Confirm the write** — one consolidated confirmation covering every write; require an explicit "yes" via `AskUserQuestion` before any write.

---

## Workflow

All calls go through `sf`; substitute `<alias>` with the target org. **Use the skill's absolute directory** for every script path. Exact command shapes: `references/cli-invocation.md`.

### Phase 1 — Read: what is provisioned, and what is activated?

1. Query the six platform feature permsets, capture to a file, and classify:

   ```bash
   sf data query \
     -q "SELECT Id, Name, Label, LicenseId FROM PermissionSet WHERE Name IN ('EinsteinGPTPromptTemplateUser','EinsteinGPTPromptTemplateManager','GenieUserEnhancedSecurity','GenieAdmin','UnifiedCatalogCommunityUser','UnifiedCatalogAdmin')" \
     --target-org <alias> --json > /tmp/itsm-platform-permsets.json 2>/tmp/itsm-platform-permsets.err || true
   node "<skill_dir>/scripts/classify-platform-permset-availability.mjs" /tmp/itsm-platform-permsets.json
   ```

   The classifier returns `{ features, provisionedFeatures, absentFeatures, verdict }`. `verdict:"ASSIGNABLE"` ⇒ ≥1 feature is provisioned; `verdict:"NONE-PROVISIONED"` ⇒ no feature permset can be assigned (still continue to the Agent Access concern); `verdict:"CANNOT-CONFIRM"` ⇒ surface the raw error and stop.

2. Query the activated agents (BotDefinition + active-version child subquery), capture, and classify:

   ```bash
   sf data query \
     -q "SELECT Id, DeveloperName, MasterLabel, (SELECT Status FROM BotVersions WHERE Status='Active') FROM BotDefinition WHERE Type='InternalCopilot'" \
     --target-org <alias> --json > /tmp/itsm-agents.json 2>/tmp/itsm-agents.err || true
   node "<skill_dir>/scripts/classify-activated-agents.mjs" /tmp/itsm-agents.json
   ```

   `verdict:"AGENTS-FOUND"` ⇒ present `activatedAgents[]` for the multi-select; `verdict:"NONE-ACTIVE"` ⇒ there is nothing for `Agent_Access` to grant (report it; if `NONE-PROVISIONED` also holds there is no work — stop).

### Phase 2 — Choose target user(s) (never a silent default)

3. Resolve the running user (to offer as a labelled option) and query active org users so a helper can rank real, non-service candidates to offer as ready picks — never proceed with an *unstated* default:

   ```bash
   sf api request rest "/services/data/v67.0/" --method GET --target-org <alias> > /tmp/api-root.json 2>/tmp/api-root.err || true
   node "<skill_dir>/scripts/resolve-target-user.mjs" /tmp/api-root.json
   sf data query -q "SELECT Name, Profile.Name, Profile.UserLicense.Name FROM User WHERE Id='<userId>'" --target-org <alias> --json > /tmp/itsm-running-user.json 2>/dev/null || true
   sf data query -q "SELECT Id, Name, Username, Profile.Name, Profile.UserLicense.Name FROM User WHERE IsActive = true ORDER BY LastLoginDate DESC NULLS LAST LIMIT 25" --target-org <alias> --json > /tmp/itsm-candidate-users.json 2>/dev/null || true
   node "<skill_dir>/scripts/rank-candidate-users.mjs" /tmp/itsm-candidate-users.json <audience> <userId>
   ```

   On `verdict:"RESOLVED"` keep `userId`; take its `Name` from `/tmp/itsm-running-user.json` for the label; on `CANNOT-CONFIRM` surface the reasons and stop. **If the prompt already named the target user(s)** ("grant me" / a username), honor it without asking. **Otherwise** set `<audience>` from the agent this grant is for — **`fulfiller`** (prefer **standard-license** users) or **`employee`** (prefer **Unified Employee** users), else **`any`** — inferring it from the agent named in the request/handoff or the Phase-1 activated set; `rank-candidate-users.mjs` returns up to five real, non-service candidates ranked for that audience. **Present an `AskUserQuestion` (multi-select) with those users as direct selectable options — never a plain-prose username request:** the running user (labelled **"Me — <name>"**, or just **"Me"**; recommended) plus the top candidates. The picker allows four options, so offer **"Me" + the top three ranked candidates**; its built-in **"Other"** takes any username(s) not listed. Resolve each chosen/typed user by `Username` (query shape in `references/cli-invocation.md`, capturing each to its own file); skip inactive/unknown with a note. The confirmed user Ids drive every assignment below.

### Phase 3 — Selections (no writes)

4. For each **provisioned** feature, ask the tier (user/agent vs admin) via `AskUserQuestion` and record the selected tier's `{ name, Id, LicenseId, needsPsl }`; report each **absent** feature as "not provisioned on this org — skipped". **Unified Catalog is license-shape gated per selected user** — run `scripts/gate-unified-catalog-tiers.mjs` once per user against that user's own capture and offer only its `offer[]` tiers: **Community User** only to a **Unified Employee** user, **Admin** only to a **System Administrator**; on `omit`, skip Unified Catalog for that user as "not applicable for this user's license/profile — skipped" — never offered, never a failed write.
5. Ask which **activated** agents to add to `Agent_Access` via `AskUserQuestion` (multi-select). Record their BotDefinition Ids as a comma-separated list.

### Phase 4 — Idempotency reads (no writes)

6. **Agent Access state.** Query the `Agent_Access` permset and (only if it exists) its existing `BotDefinition` grants — capture to `/tmp/agent-access.json` and `/tmp/sea.json` (query shapes in `references/cli-invocation.md` → Phase 4) — then classify against the chosen agent Ids:

   ```bash
   node "<skill_dir>/scripts/classify-agent-access-state.mjs" /tmp/agent-access.json <sea.json|NO-PERMSET> "<chosenAgentIds-csv>"
   ```

   Pass `NO-PERMSET` for the second arg when `Agent_Access` does not exist yet. The classifier returns `{ permsetExists, permsetId, missingAgentIds, needsCreate, needsGrants, verdict }`.

7. **Per user + permset.** For each target user × (each selected feature tier **and** `Agent_Access`), read existing assignments (`PermissionSetAssignment`, plus `PermissionSetLicenseAssign` only when `needsPsl:true`; shapes in `references/cli-invocation.md`) and classify. `Agent_Access` is standalone (`needsPsl:false` → `NO-PSL`); a feature tier uses `needsPsl` from its own row. **If step 6 flagged `Agent_Access` absent (`needsCreate:true`), skip its keyed `PermissionSetAssignment` read** — no permset ⇒ verdict `NEEDS-WRITE`; Phase 6 creates it, then assigns **by name**. Run the keyed read for `Agent_Access` only when step 6 returned an existing `permsetId`:

   ```bash
   node "<skill_dir>/scripts/classify-assignment-state.mjs" /tmp/psa.json </tmp/psla.json|NO-PSL>
   ```

### Phase 5 — Confirm-to-write checkpoint (REQUIRED)

8. Present ONE consolidated summary — every target user, each feature tier to assign (and each absent feature being skipped), whether `Agent_Access` will be created and which agents it will grant, and every permset assignment — and require an explicit "yes" via `AskUserQuestion`. On "no", stop and report the planned state with no writes. Assigning a license-gated tier consumes a **license seat** and takes effect for a live session.

### Phase 6 — Writes (only what Phase 4 flagged as needed)

9. **Agent Access permset** (once): if `needsCreate`, POST to `/sobjects/PermissionSet` `{"Name":"Agent_Access","Label":"Agent Access"}` and capture the new `id`. Then for each Id in `missingAgentIds`, POST to `/sobjects/SetupEntityAccess` `{"ParentId":"<permsetId>","SetupEntityId":"<agentId>"}` — **do not send `SetupEntityType`** (it is not createable; it is derived from the `0Xx` key prefix). `DUPLICATE_VALUE` on a grant ⇒ already granted, treat as success.
10. **Feature tiers**, per user, for each tier whose Phase 4 verdict was `NEEDS-WRITE`, ordered by `needsPsl`:
    - `needsPsl:true` — POST the PSL to `/sobjects/PermissionSetLicenseAssign` (using the tier's own `LicenseId`) FIRST, then `sf org assign permset --name <tierName>` (running user: **omit** `--on-behalf-of`; named user: `--on-behalf-of "<username>"`).
    - `needsPsl:false` — skip the PSL POST; run `sf org assign permset` only.
11. **Agent Access assignment**, per user: `sf org assign permset --name Agent_Access` (running user: **omit** `--on-behalf-of`; named user: `--on-behalf-of "<username>"`) when its Phase 4 verdict was `NEEDS-WRITE`. `--on-behalf-of` resolves by `Username`, never a `005` Id or a `$USERNAME` shell var (see `references/cli-invocation.md`).

    Response handling (all writes): success ⇒ done; `DUPLICATE_VALUE`/`already has` ⇒ idempotent success; `INSUFFICIENT_ACCESS`/seat-exhaustion on a PSL POST ⇒ STOP and tell the user no seats are available; any other error ⇒ surface verbatim, mark FAILED. (Full taxonomy in `references/cli-invocation.md`.)

### Phase 7 — Verify + aggregate

12. Re-read the assignments written (`PermissionSetAssignment` / `PermissionSetLicenseAssign` for the target user(s); `SetupEntityAccess` for `Agent_Access`) and confirm each intended row is present. Then report one aggregate verdict:
    - **ASSIGNED** — at least one write occurred and every read-back confirms it.
    - **ALREADY-ASSIGNED** — nothing needed writing; all intended state was already present.
    - **PARTIAL** — some assignments succeeded and at least one FAILED or didn't read back. List which.
    - **NONE-PROVISIONED** — no feature provisioned AND no agent activated: nothing to assign. Point at the create/enable skills.
    - **FAILED** — every attempted write returned an error other than a duplicate. Report the raw errors.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Detect provisioned features before assigning; report absent features as "not provisioned", never fail on them | No org has all three; an absent permset errors and masks real state |
| Ask the tier (user/agent vs admin) per provisioned feature — never auto-select | The lighter tier suffices to use the feature; admin over-grants |
| Offer **standard-license** users for a Fulfiller agent, **Unified Employee** for an Employee agent; the ranker drops service/bot accounts | The wrong cohort offers users who can't run that agent |
| Offer a **Unified Catalog** tier only to a user who can hold it (Community User → Unified Employee; Admin → System Administrator), else omit for that user — via `scripts/gate-unified-catalog-tiers.mjs` | UC PSLs are license-shape gated; an ineligible tier is a hard write-time failure, not a seat shortage |
| All availability / idempotency / activation decisions are made by helper scripts, never by prose | They gate writes/success; scripts are deterministic, prose is not (A9) |
| `needsPsl` is read PER ROW from the selected tier's own `LicenseId`; the PSL POST uses that `LicenseId` — never a hard-coded PSL name | Different orgs carry different license shapes; a wrong `PermissionSetLicenseId` POSTs the wrong seat |
| Assign the PSL before the permission set when `needsPsl:true` | The permset is license-backed; hold the seat first |
| `Agent_Access` grants access to activated agents ONLY, via `SetupEntityAccess` rows whose `SetupEntityId` is the `BotDefinition` Id | Access is granted like Apex-class access — one grant row per agent |
| POST `SetupEntityAccess` with `ParentId` + `SetupEntityId` ONLY — never `SetupEntityType` | Not createable — derived from the `SetupEntityId` key prefix; sending it errors |
| Create `Agent_Access` via the standard data API POST to `/sobjects/PermissionSet` — never Tooling/Metadata XML | Createable over the data API with just `Name`+`Label`; no deploy needed |
| One consolidated confirm-to-write before ANY write | The full plan (seats consumed, live-session effect) must be approved once |
| Treat `DUPLICATE_VALUE` / `already has` as idempotent success on every write | Re-running must be safe; a duplicate means the state already holds |
| Verify by read-back before reporting ASSIGNED | A POST return code alone doesn't prove the row is present |
| Never extract the access token; never use an MCP dispatcher | Extracting a token leaks a bearer credential |
| Report exact error text from the CLI response | Enables support to diagnose failures |

---

## Verification Checklist

- [ ] Provisioned features classified by `scripts/classify-platform-permset-availability.mjs`; absent reported "not provisioned", not failed.
- [ ] A tier (user/agent vs admin) was chosen per provisioned feature — no auto-selection; Unified Catalog tiers gated per user by `scripts/gate-unified-catalog-tiers.mjs`.
- [ ] Activated agents classified by `scripts/classify-activated-agents.mjs`; only active-version agents were offered.
- [ ] Target user(s) confirmed — when unnamed, asked via `AskUserQuestion` (running user + audience-ranked users from `scripts/rank-candidate-users.mjs` + "Other"), never silent. Running user via `scripts/resolve-target-user.mjs`; named by `Username`.
- [ ] `Agent_Access` create/grant decided by `scripts/classify-agent-access-state.mjs`; `SetupEntityAccess` POSTs sent `ParentId`+`SetupEntityId` only.
- [ ] Per user+permset idempotency classified by `scripts/classify-assignment-state.mjs` before any write.
- [ ] The selected tier's own `LicenseId` drove the PSL POST when `needsPsl:true`, POSTed before the permset.
- [ ] One consolidated confirm-to-write gate preceded every write.
- [ ] `DUPLICATE_VALUE` / `already has` treated as success; other errors surfaced verbatim.
- [ ] Assignments verified by read-back; one aggregate verdict reported (see Phase 7).

---

## Output Format

```text
ITSM Agent Runtime-Access Assignment (via service-itsm-agentic-setup-agent-runtime-access-assign)

Org:            <org-alias> (API v67.0)
Target user(s): <username> (<userId>)[, ...]

Runtime action permissions:
  Prompt Templates ...... <tier chosen: User | Manager | skipped | not provisioned>  -> <assigned | already-had | FAILED>
  Data Cloud ............ <tier chosen | skipped | not provisioned>                   -> <assigned | already-had | FAILED>
  Unified Catalog ....... <tier chosen | skipped | not provisioned>                   -> <assigned | already-had | FAILED>

Agent Access permission set:
  Permission set ........ <created | already existed>
  Agents granted ........ <comma-separated agent names, or none>
  Assigned to user(s) ... <assigned | already-had | FAILED>

Verdict: ASSIGNED | ALREADY-ASSIGNED | PARTIAL | NONE-PROVISIONED | FAILED
Reason:  <plain-language explanation, or empty on success>

Next steps:
  - <If ASSIGNED / ALREADY-ASSIGNED: "The user can now open and exercise the agent(s) in Agentforce Studio — action calls should no longer fail on missing permissions.">
  - <If PARTIAL: list which assignments succeeded and which failed, verbatim.>
  - <If NONE-PROVISIONED: nothing to assign — create/activate an agent and enable its features first.>
  - <If FAILED: list the observed error(s) verbatim + remediation.>
```

Keep internal jargon (record Ids, HTTP codes, `DUPLICATE_VALUE`, object/dev names) out of user-facing output.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/permset-topology.md` | Any change to the feature/tier matrix — the six platform permsets, their tiers, PSLs, and the `Agent_Access` / `SetupEntityAccess` agent-access mechanism |
| `references/cli-invocation.md` | Every phase — exact `sf data query` / `sf api request rest` POST / `sf org assign permset` call shapes, the `--json` rule, the never-extract-token rule, response envelopes, and the error taxonomy |
| `references/helper-contracts.md` | The input/output shapes of all seven helper scripts and how to interpret each verdict |
