---
name: service-itsm-agentic-setup-itsm-agentforce-permset-assign
description: "Resolve missing ITSM Intelligence invocable actions so a Fulfiller NGA agent can activate. Reads which of the three Core Fulfiller persona permsets (IncidentFulfiller, ProblemFulfillerPermSet, ChangeRequestFulfillerPermSet) are provisioned, then assigns the running user the selected persona (plus backing PSL when license-gated) so svc_itsm_intelligence__* actions surface; hands off to service-itsm-agentic-setup-agentforce-studio-validate if none are provisioned. Use when the Fulfiller agent-configure skill reports missing actions on activate, when 'Invocable action svc_itsm_intelligence__X does not exist' surfaces, when a user asks to grant themselves Fulfiller prompt-template access, when asked to assign the Incident, Problem, or Change Fulfiller persona permission set, or when resolving missing ITSM Intelligence action access for the Fulfiller agent. DO NOT TRIGGER for Employee-agent access, Agentforce for IT Service toggles, agent creation, CMDB access, or generic permset assignment."
metadata:
  version: "1.1"
  domains: ["Service", "Agentforce"]
  minApiVersion: "67.0"
  relatedSkills:
    - "dx-org-permission-set-assign"
    - "service-itsm-agentic-setup-agentforce-studio-validate"
    - "service-itsm-agentic-setup-cmdb-access-assign"
    - "service-itsm-agentic-setup-fulfiller-agent-configure"
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

# Assign an ITSM Fulfiller Persona Permission Set (Prompt-Template Access)

Grants the **running user** one of the Core-shipped **Fulfiller persona permission sets** that expose the `svc_itsm_intelligence__*` prompt-template **invocable actions** on the target org — the actions the Fulfiller NGA agent scripts reference via `source:` / `target: generatePromptResponse://...`. When those invocables are not surfaced by `/services/data/v67.0/actions/custom/generatePromptResponse` for the running user, the Fulfiller agent-configure skill's Phase 6 `activate` call returns **HTTP 200** with a silent `{success:false, messages:[{... "does not exist"}]}` body and the agent never becomes usable. This skill fixes that gap by assigning the correct Fulfiller persona permset (and its backing license when one exists) — **or**, when no Fulfiller persona permset is provisioned on the org at all, hands off to the Agentforce Studio configure/validate skill so the ITSM AddOn(s) can be enabled first.

The three Fulfiller persona permsets, their AddOns, PSLs, and the userPerms they grant are documented in `references/permset-topology.md`. All are Core-shipped in namespace `force` — there is no managed-package namespaced permset for this feature.

**Employee agent is out of scope.** The Employee NGA agent's access model is separate (org-preferences + a different persona layer) and does not map onto these three persona permsets.

Every call runs through the **Salesforce CLI (`sf`)**:
- `sf api request rest` — authenticated Connect API GET (identity, verify read).
- `sf data query` — SOQL on `PermissionSet` (persona presence), `PermissionSetAssignment` / `PermissionSetLicenseAssign` (idempotency).
- `sf org assign permset` — assigning the permission set for the running user.
- No token is ever extracted; no MCP is used.

## Scope

- **In scope**: detecting which of the three Fulfiller persona permsets (`IncidentFulfiller`, `ProblemFulfillerPermSet`, `ChangeRequestFulfillerPermSet`) are provisioned on the org, letting the user pick which persona to assign, checking existing assignments, assigning the permission-set license (when the persona is license-gated) and permission set to the running user (or a named user), verifying the target `svc_itsm_intelligence__*` invocable actions surface via a follow-up `/actions/custom/generatePromptResponse` read.
- **Out of scope**: Employee-agent access (different access model, different skill), installing/enabling the ITSM AddOn(s) or content bundle (hand off to `service-itsm-agentic-setup-agentforce-studio-validate`), enabling org-level Agentforce feature toggles, creating a permission set, creating or activating the Fulfiller agent (that's `service-itsm-agentic-setup-fulfiller-agent-configure`), CMDB access (`service-itsm-agentic-setup-cmdb-access-assign`), generic non-ITSM permission-set assignment (`dx-org-permission-set-assign`).

## Mechanism

Two branches, decided by a read-only detection step first:

- **Branch A — one or more Fulfiller persona permsets exist on the org.** Ask the user which persona to assign (do not auto-select — a Fulfiller commonly needs only one). Idempotent assign: PSL first when the persona is license-gated, then permission set, verified by read-back and by a follow-up `/actions/custom/generatePromptResponse` read.
- **Branch B — none of the three Fulfiller persona permsets exist on the org.** The ITSM AddOn(s) are not provisioned; permset-assign is a no-op. STOP and hand off to `service-itsm-agentic-setup-agentforce-studio-validate` so the AddOn(s) can be enabled first.

The two-branch shape is deliberate — the failure signature ("`svc_itsm_intelligence__X` does not exist" on activate) looks identical whether a persona is present-and-unassigned or the AddOn is absent entirely, and there is no way to tell from the activate response alone. The pre-check on the three persona `PermissionSet` names is what disambiguates them.

## Four helper scripts (all invoked via `Bash`) hold every deterministic decision (A9). Full I/O contracts in `references/helper-contracts.md`; workflow-level usage summarized below:

- `scripts/classify-permset-availability.mjs` — Branch A vs B and the per-persona `needsPsl` flag. Returns the full `candidates[]` (personas actually on the org) for the caller to prompt on.
- `scripts/resolve-target-user.mjs` — extracts `005…` running-user Id from the API-root `identity` URL. Fails closed on any malformed shape.
- `scripts/classify-assignment-state.mjs` — idempotency; pass the sentinel `NO-PSL` in place of the PSLA path when the selected persona's `needsPsl:false`.
- `scripts/classify-action-surface.mjs` — Phase 4 verify verdict from the `/actions/custom/generatePromptResponse` capture (with optional expected-actions CSV).

---

## Preconditions

1. **`sf` CLI installed and authenticated to the target org** (`sf org display -o <alias>` shows Connected). All calls use `--target-org <alias>`; never extract or pass the access token by hand.
2. **API v67.0+**.
3. **`node` ≥ 18** on PATH.

If a precondition fails, `sf` surfaces an auth or `401`/`403`/`404`; report the raw response verbatim and stop.

---

## Clarifying questions

Ask only what cannot be inferred from conversation:

- **Target org** — the `sf` alias. Default to `sf config get target-org` if unset.
- **Target user** — default to the **running user** (resolved via `scripts/resolve-target-user.mjs`). If the user asks to assign on behalf of a named user, resolve them by `Username` first.
- **Which Fulfiller persona?** Incident / Problem / Change. Only ask about personas that are actually provisioned on the org (from `candidates[]`). Do not auto-select — a Fulfiller commonly needs only one persona (e.g. Incident) even when others are provisioned.
- **Confirm the write** — assigning a permission-set license consumes a seat and takes effect for a live user session. Present the target user + org + persona permset name, and require an explicit "yes" via `AskUserQuestion` before writing.

---

## Workflow

All calls go through `sf`; substitute `<alias>` with the target org.

### Phase 1 — Read: which Fulfiller persona permsets are provisioned on this org?

1. Query `PermissionSet` for the three known Fulfiller persona DeveloperNames:

   ```bash
   sf data query \
     -q "SELECT Id, Name, Label, LicenseId FROM PermissionSet WHERE Name IN ('IncidentFulfiller','ProblemFulfillerPermSet','ChangeRequestFulfillerPermSet')" \
     --target-org <alias> --json > /tmp/itsm-personas.json 2>/tmp/itsm-personas.err || true
   ```

   (The `PermissionSet` namespace on all three is `force` — do NOT filter by `NamespacePrefix`.)

2. Classify:

   ```bash
   node "<skill_dir>/scripts/classify-permset-availability.mjs" /tmp/itsm-personas.json
   ```

   The classifier prints `{ personasFound, personasMissing, candidates, verdict, reasons }`, where each `candidates[]` row is `{Id, Name, Label, LicenseId, needsPsl}`:
   - `verdict:"ASSIGN"` (≥1 persona present) ⇒ continue to Phase 2. Present the `personasFound` list to the user via `AskUserQuestion` and get the selected persona; record its `Id`, `LicenseId`, and `needsPsl` — they drive whether Phase 2b/2d touch the PSL at all.
   - `verdict:"HAND-OFF"` (none of the three personas present) ⇒ Phase 2 is impossible on this org; go to Phase 3 (Branch B hand-off).
   - `verdict:"CANNOT-CONFIRM"` (query failed) ⇒ surface the raw CLI error verbatim; stop.

### Phase 2 — Assign path (Branch A)

2a. **Resolve the target user.** Read the identity URL, then extract the user Id via the resolver (do NOT parse the URL by hand; do NOT use `USER_ID()` — Apex-only, rejected by REST; do NOT rely on `/chatter/users/me` — `403` when Chatter is off):

   ```bash
   sf api request rest "/services/data/v67.0/" --method GET --target-org <alias> > /tmp/api-root.json 2>/tmp/api-root.err || true
   node "<skill_dir>/scripts/resolve-target-user.mjs" /tmp/api-root.json
   ```

   The resolver prints `{ userId, identity, verdict, reasons }`. On `verdict:"RESOLVED"` use `userId` as the running user; on `verdict:"CANNOT-CONFIRM"` surface the reasons verbatim and stop — do NOT guess.

   If the user asks to assign on behalf of a **named** user instead, resolve by `Username`:

   ```bash
   sf data query \
     -q "SELECT Id, Username, Name, IsActive FROM User WHERE Username = '<username>'" \
     --target-org <alias> --json > /tmp/user-lookup.json 2>/tmp/user-lookup.err || true
   ```

2b. **Idempotency read.** Query the `PermissionSetAssignment` for the target user + selected persona's `Id` (SOQL shape in `references/cli-invocation.md`), and then branch on the selected persona's `needsPsl`:

   - **`needsPsl:true`** — query the `PermissionSetLicenseAssign` for the target user + the persona's `LicenseId`, then classify:

     ```bash
     node "<skill_dir>/scripts/classify-assignment-state.mjs" /tmp/psa-existing.json /tmp/psla-existing.json
     ```

   - **`needsPsl:false`** — skip the PSLA query entirely; pass the sentinel:

     ```bash
     node "<skill_dir>/scripts/classify-assignment-state.mjs" /tmp/psa-existing.json NO-PSL
     ```

   The classifier prints `{ permsetAssigned, licenseAssigned, needsWrite, verdict, reasons }`. If `needsWrite:false` ⇒ Phase 4 (verify only). Else continue to Phase 2c.

2c. **Confirm-to-write checkpoint (REQUIRED).** Present the target user + org + persona permset name and require an explicit "yes" via `AskUserQuestion`. On "no", stop and report the current state without any writes.

2d. **Assign** — order depends on the selected persona's `needsPsl`:

   - **`needsPsl:true`** — POST the PSL to `/sobjects/PermissionSetLicenseAssign` FIRST, then run `sf org assign permset --name <permsetName> --on-behalf-of <userId>`. Assigning the permission set without the PSL sticks the assignment but the license backing it never activates. Exact call shapes: `references/cli-invocation.md`.
   - **`needsPsl:false`** — SKIP the PSL POST entirely; run `sf org assign permset` only. (A persona whose `PermissionSet` has no backing `LicenseId` is not license-gated — there is no PSL seat to hold, so assigning the permset alone is the correct and complete write.) _Retained defensively:_ every shipped persona is now PSL-backed (`needsPsl` is derived per-row from `LicenseId`), so this `false` branch and its `NO-PSL` wiring are currently unexercised by shipped data — kept for correctness against a future persona whose `PermissionSet` carries no backing `LicenseId`.

   Response handling:
   - `201` on POST / `success:true` on `sf org assign permset` ⇒ assigned.
   - `400 DUPLICATE_VALUE` on the PSL POST ⇒ user already had it; treat as success, not error.
   - `400 INSUFFICIENT_ACCESS` / seat-exhaustion on the PSL POST ⇒ STOP for this write; tell the user the PSL has no seats available.

### Phase 3 — Hand-off path (Branch B: no Fulfiller persona provisioned)

3. When Phase 1 returns `verdict:"HAND-OFF"`, none of the three Fulfiller persona permsets exist on this org — the ITSM AddOn(s) are not provisioned. Permset-assign is a no-op in this state. Present the discovery via `AskUserQuestion`:

   _"None of the Fulfiller persona permission sets (Incident, Problem, Change) is provisioned on this org — no permset can grant access to actions that don't exist yet. Run `service-itsm-agentic-setup-agentforce-studio-validate` to diagnose which AddOn needs enabling?"_ (options: **Yes, run the readiness check** / **No, stop here**).

   - On **Yes**: delegate to `service-itsm-agentic-setup-agentforce-studio-validate` and let it recommend the configure/bundle-deploy skill.
   - On **No**: stop and report the current state (no persona provisioned, cannot assign) — no writes.

### Phase 4 — Verify

4. Regardless of write vs skip, re-read `/actions/custom/generatePromptResponse` and classify via the helper (never by prose grep — A9). CSV shape and both invocation forms live in `references/helper-contracts.md` / `references/cli-invocation.md`:

   ```bash
   sf api request rest "/services/data/v67.0/actions/custom/generatePromptResponse" \
     --method GET --target-org <alias> > /tmp/generate-prompt-response.json 2>/tmp/generate-prompt-response.err || true
   node "<skill_dir>/scripts/classify-action-surface.mjs" /tmp/generate-prompt-response.json [expectedActions-csv]
   ```

   The helper prints `{ present, missing, totalItsmActionsSeen, verdict, reasons }`. On `SURFACED` proceed to Phase 5; on `PARTIAL` / `MISSING` after a successful assign, tell the user the write succeeded but the actions are not surfaced — session refresh or wrong persona. Do not falsely report success. On `CANNOT-CONFIRM` surface the reasons verbatim.

### Phase 5 — Aggregate verdict

5. Report one of:
   - **ASSIGNED** — Branch A wrote, verify saw the target actions surface.
   - **ALREADY-ASSIGNED** — Branch A found `needsWrite:false`; verify saw the target actions surface. (Assignment is already in place; no writes needed.)
   - **HAND-OFF** — Branch B; no Fulfiller persona is provisioned. Named the follow-up skill.
   - **VERIFY-INCONCLUSIVE** — write completed but the verify read didn't surface the expected action set. Surface the observed state verbatim; do not report success.
   - **FAILED** — any Phase 2d write returned an error other than `DUPLICATE_VALUE`. Report the raw error.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Detect Fulfiller persona presence via the three fixed `PermissionSet.Name` values BEFORE any permset write | The failure signature ("action does not exist" on activate) is identical for AddOn-absent and permset-not-assigned; only the pre-check disambiguates them. The three personas are Core-shipped in namespace `force` — a `NamespacePrefix` filter never returns them |
| Ask the user which persona to assign — never auto-select | A Fulfiller commonly needs only one persona (e.g. Incident). Auto-assigning the first row returned would over-grant |
| All decisions are made by helper scripts, never by prose | Assignment/idempotency logic is deterministic; prose interpretation is not (A9) |
| Assign the PSL before the permission set — ONLY when the selected persona's `needsPsl:true` | The permission set is license-backed; the license seat must be held before the assignment sticks. When the selected persona has no `LicenseId`, `needsPsl:false` and the PSL POST is skipped entirely |
| Read `needsPsl` from the SELECTED persona's `LicenseId`, per-row — never from a namespace-wide PSL query | Different personas can have different license shapes on the same org; falling back to a namespace-wide PSL would POST a wrong `PermissionSetLicenseAssign` |
| Resolve the running-user Id via `scripts/resolve-target-user.mjs` — never by prose parsing the `identity` URL | The identity URL's segment shape (`005…`, 15 or 18 chars) is a hard rule; the classifier validates and fails closed |
| Classify the Phase 4 action surface via `scripts/classify-action-surface.mjs` — never by prose grep of the response | Verify is the gate for reporting SUCCESS vs VERIFY-INCONCLUSIVE; the decision must be deterministic |
| Treat `400 DUPLICATE_VALUE` on PSL POST as success | It means the user already has that assignment — idempotent, not an error |
| Never create or edit a permission set | This skill only assigns the standard Fulfiller persona permission set(s); authoring perm sets is out of scope |
| Never install the AddOn / never toggle org-level Agentforce features | That is the `service-itsm-agentic-setup-agentforce-studio-validate` / `-configure` scope; this skill hands off, it does not enable |
| Verify after write via `/actions/custom/generatePromptResponse` — never trust POST return code alone | The assignment can succeed while the target action surface still doesn't include what the Fulfiller template needs (wrong persona, cache) |
| Confirm-to-write checkpoint before Phase 2d | A permset assign consumes a license seat and takes effect for a live user session |
| Never extract the access token | Use `sf api request rest` / `sf data query` / `sf org assign permset` — they use the CLI's stored session |
| Report exact error text from the CLI response | Enables support to diagnose failures |

---

## Verification Checklist

- [ ] Persona availability classified by `scripts/classify-permset-availability.mjs` against the three fixed persona Names — never by prose scanning the query output.
- [ ] User was asked to pick a persona from `personasFound[]` — no auto-selection.
- [ ] Target user Id resolved by `scripts/resolve-target-user.mjs` — never by prose splitting the identity URL.
- [ ] The SELECTED persona's `needsPsl` drove Phase 2b/2d: PSL SOQL + POST were performed when `true` and skipped when `false`.
- [ ] `permsetLicenseId` used for the PSL POST came from the SELECTED persona's own `LicenseId` — never a fallback from a namespace-wide query.
- [ ] On Branch A: existing assignments read via `sf data query` before any write, classified by `scripts/classify-assignment-state.mjs` (with `NO-PSL` sentinel when `needsPsl:false`).
- [ ] On Branch A: user confirmed the write at the Phase 2c checkpoint.
- [ ] On Branch A + `needsPsl:true`: PSL was POSTed before the permission set was assigned.
- [ ] `DUPLICATE_VALUE` on the PSL POST was treated as success, not failure.
- [ ] On Branch B: no write was attempted; the hand-off to `service-itsm-agentic-setup-agentforce-studio-validate` was offered.
- [ ] Phase 4 verify classified via `scripts/classify-action-surface.mjs` — no false ASSIGNED without the helper returning `verdict:"SURFACED"`.
- [ ] Aggregate verdict reported (ASSIGNED / ALREADY-ASSIGNED / HAND-OFF / VERIFY-INCONCLUSIVE / FAILED).

---

## Output Format

```text
ITSM Fulfiller Persona Permset Assignment (via service-itsm-agentic-setup-itsm-agentforce-permset-assign)

Org:            <org-alias> (API v67.0)
Target user:    <username> (<userId>)
Persona:        <Incident | Problem | Change>
PermSet:        <DeveloperName>

  Personas provisioned on org ...... <comma-separated list | none>
  Existing PSL assignment .......... <yes | no | n/a>
  Existing permset assignment ...... <yes | no>
  Write PSL ........................ <succeeded | already-had | skipped | FAILED>
  Write permset .................... <succeeded | already-had | skipped | FAILED>
  Verify actions surface ........... <yes | partial | no>

Verdict: ASSIGNED | ALREADY-ASSIGNED | HAND-OFF | VERIFY-INCONCLUSIVE | FAILED
Reason:  <plain-language explanation, or empty on success>

Next steps:
  - <If ASSIGNED / ALREADY-ASSIGNED: "Re-run service-itsm-agentic-setup-fulfiller-agent-configure — the invocable actions should now surface, and the activate call will succeed.">
  - <If HAND-OFF: "No Fulfiller persona is provisioned on this org. Run service-itsm-agentic-setup-agentforce-studio-validate to identify which AddOn needs enabling.">
  - <If VERIFY-INCONCLUSIVE: list the observed state verbatim; a session refresh or a different persona may be required>
  - <If FAILED: list the observed error verbatim + remediation>
```

Keep internal jargon (record Ids, HTTP status codes, `FUNCTIONALITY_NOT_ENABLED`, `DUPLICATE_VALUE`, object/developer names, `sf api request rest`) out of user-facing output.

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/permset-topology.md` | Any change to the persona list — the three Core-shipped Fulfiller permsets, their AddOns/PSLs/userPerms, and the fixed-lookup discovery query |
| `references/cli-invocation.md` | Every phase — exact `sf api request rest` / `sf data query` / `sf org assign permset` call shapes, the never-extract-token rule, response envelopes |
| `references/helper-contracts.md` | The input/output shapes of all four helper scripts (`classify-permset-availability.mjs`, `resolve-target-user.mjs`, `classify-assignment-state.mjs`, `classify-action-surface.mjs`) and how to interpret each verdict |
