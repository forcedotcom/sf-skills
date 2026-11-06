---
name: nonprofit-fundraising-configure
description: "Configure Nonprofit Cloud Fundraising on an org headlessly — assign permission sets/groups org-wide, enable Fundraising, create a default Gift Designation, configure gift/recurring-donation-failure settings and feature toggles, and offer optional enhanced features (Interest Tags, Interaction Summaries, Record Alerts, Life Events, Timeline). Use when the user asks to set up or enable Nonprofit Cloud Fundraising, configure gift/donation settings, provision an org for fundraising, assign Fundraising permission sets/groups, or create a default gift designation. Also: turn on Fundraising, set up recurring donations, prep an org for testing. Toggle writes use headless-360 operations, never the `IndustriesSettings` Metadata API; the Person Account profile-visibility fix is the one Profile metadata write. DO NOT TRIGGER when: enabling Person Accounts on its own (this skill's Layer 0 gate only), creating gift/donation records post-configuration, or configuring NPSP/Nonprofit Success Pack."
metadata:
  version: "1.0"
  minApiVersion: "68.0"
  domains: ["Nonprofit"]
  mcpTools:
    headless-360:
      tools: ["describe", "discover", "dispatch", "dispatch_readonly"]
      semver: ">=1.0.0"
  cliTools:
    - tool: ["sf"]
      semver: ">=2.0.0"
  relatedSkills:
    - "service-itsm-agentic-setup-uel-user-create"
    - "service-itsm-incident-mgmt-configure"
  accessCheck: "((UserPermissions.AssignPermissionSets) && (UserPermissions.CustomizeApplication)) && (OrgPermissions.FundraisingAccess)"
delegates_to: [npc-pulsars/FundraisingSettings, npc-pulsars/FundraisingGiftEntrySettings, npc-titan/FundraisingSourceCodeGen, health-cloud-r2-d2/Timeline, fsc-obi-wan/InterestTaggingSettings]
allowed-tools: |
  Read AskUserQuestion
  mcp__headless-360__discover
  mcp__headless-360__describe
  mcp__headless-360__dispatch_readonly
  mcp__headless-360__dispatch
---

# Configure Nonprofit Cloud Fundraising

Turn on Nonprofit Cloud Fundraising for an org: resolve and assign the right permission sets and
groups **org-wide, by role**, confirm the plan, enable Fundraising, create a default Gift
Designation record, configure basic gift/recurring-donation-failure settings and Fundraising
feature toggles, and offer optional enhanced features. Every read/write runs through the **Salesforce-hosted
headless-360 MCP server** via its four meta-tools. Toggle writes use named or org-preference operations, never the
`IndustriesSettings` Metadata API (not available on every org). The org comes from the
session's OAuth JWT; this skill never handles credentials, and uses an org alias only to pin the optional CLI fallback to the session's org.

## Scope

- **In scope**: Person Accounts precondition check and confirmation-gated enablement (excludes
  HR-Service side effects), Fundraising license check, permission
  set/group resolution and **org-wide** assignment by profile, enabling Fundraising, creating a
  default Gift Designation record, configuring basic gift/recurring-donation-failure settings,
  Fundraising feature toggles, and optional enhanced features (Interest Tags, Interaction
  Summaries, Record Alerts, Life Events, Timeline).
- **Out of scope**: additional (non-default) gift/donation records; NPSP/Nonprofit Success Pack;
  the Marketing User checkbox.

---

## Layer 0 — License check, then Person Accounts check (read-only, always run first)

Run the Fundraising license check (Phase 1 step 2) first, so an
unlicensed org stops with zero writes. Then check whether Person Accounts is live via `mcp__headless-360__dispatch_readonly`
— a Tooling query, `SELECT QualifiedApiName FROM FieldDefinition WHERE
EntityDefinition.QualifiedApiName='Account' AND QualifiedApiName='IsPersonAccount'` (`totalSize > 0`
= live), the same check `hr-service-person-account-setup` uses. **Do not** filter `RecordType` on
`IsPersonType` — that column only exists once Person Accounts is already enabled, so it 400s with
`INVALID_FIELD` on exactly the orgs this gate needs to detect. `FieldDefinition` is always valid
regardless of org state.

Layer 0 writes nothing. Any Person Accounts change is confirmed in the step 5 plan and
written in step 6a. See `references/mcp-invocation.md`'s "Person Accounts
enablement (Layer 0)" and "Person Accounts record-type profile visibility".

> On any `401`/`403`/`404` from a `discover`/`describe`/`dispatch*` call, halt and surface the
> raw error rather than guessing — see the Error Taxonomy in `references/mcp-invocation.md`.

---

## Workflow

**Idempotency and resumability**: every phase check re-reads live org state — never a persisted
checkpoint. `state.json` is output-only, never read to resume. Every write step (6, 8, 9, 11)
queries for an existing match/state before creating or toggling, so re-running this skill — after
a pause, or days later — recognizes completed work instead of erroring on `DUPLICATE_VALUE` or
re-toggling something already on.

**Front-load verification instead of walking steps one at a time**: steps 6–11 each need a live
read before deciding whether to write anything — resolve all six checks as early as Phase 1
allows, before starting Phase 3's writes, rather than one at a time in step order. This is still
five to seven separate live queries, not one or two collapsed calls — collapsing it is
under-verification, not the fast path. It applies even when a request says "core setup is already
done, skip it": the live batch is still the minimum bar, and every fact it confirms still gets
recorded in `state.json`'s per-step booleans. See `references/mcp-invocation.md → "Front-loading
Phase 1's live checks"` for the full per-step breakdown and why "already done" never skips a read.

**User-facing output**: clean but not silent. Before Phase 2 and Phase 3, give a one-line preview
of what that phase will touch. After each phase's writes, re-check via a read-only query and give a
one-line confirmation — never from the write response alone. Everything else stays internal; step
14's full re-verification still runs at the end.

### Phase 0 — Reuse what the session already knows

Before repeating a `discover`/`describe`/`dispatch_readonly` call below, check whether this
session already returned the same fact for the *current* org via a successful tool response —
reuse it instead of re-reading. A user's verbal claim is never cache-eligible, only a live
response is. See `references/mcp-invocation.md → "Phase 0 caching rules"` for what qualifies and
when it's invalidated — Layer 0's pause-gate re-check and step 13 always re-read live regardless.

### Phase 1 — Discover and verify prerequisites

1. **Discover the Fundraising-related operations** — `mcp__headless-360__discover(query="Nonprofit Cloud Fundraising settings permission set gift designation")`, then `describe` the concrete targets: `GiftDesignation`, `FundraisingConfig` (incl. `DonorExternalIdField`), and `IndustriesSettings.orgPreferenceEnabled` and its toggles. See `references/mcp-invocation.md` for field lists/fallbacks and `references/permission-targeting.md` for the org-wide permission model.
2. **Check Fundraising licensing** (runs first, before Layer 0) — query `PermissionSetLicense` for `DeveloperName = 'FundraisingAccessPsl'` (the base license, distinct from add-ons like `AgentforceForFundraisingPsl`). If not present, **stop**: "Fundraising is not licensed on this org. Contact your Salesforce account team to provision it." Make zero writes.
3. **Resolve the required permission sets and groups** — query `PermissionSet` for both name variants (`force__FundraisingAccess`/`FundraisingAccess`) and `PermissionSetGroup` for `Fundraising_Admin`/`Fundraising_User`, confirming `Status = 'Updated'` (see Gotchas on `'Updating'`/`'Outdated'`). Stop and report exactly which is missing if any aren't found. NPC is on-core/unprefixed — never fall back to a managed-package namespace like `npe03__`/`npe01__`.
4. **Check whether Fundraising is already enabled** — `describe` the `FundraisingSettings` skill and use its `get-settings-view-model` read for `orgPreferenceEnabled`. Do this in Phase 1 — flipping it dispatches the named `set-fundraising-org-preference` operation, needing its own dedicated confirmation, since it's irreversible and org-wide (`references/mcp-invocation.md → "Enabling Fundraising (set-fundraising-org-preference)"`). If `false`, Phase 2 step 5 handles the gate.

### Phase 2 — Confirm before any write

5. **Present the plan, and gate on Fundraising enablement if needed** — summarize the full scope: Person Accounts enablement (if missing), permission set/group assignment, basic settings, feature toggles, and the step 12 optional-features offer. If step 4 found `orgPreferenceEnabled = false`, warn explicitly (irreversible and org-wide; dispatches the named `set-fundraising-org-preference` operation) and get a dedicated confirmation for this step, on top of the plan-wide one below. Confirmed → step 7 writes it, 6/8/9/10/11/12 all reachable. Declined → stop with zero writes: no later step runs, including permission set/group assignment (`STOPPED_ENABLEMENT_NOT_CONFIRMED`). If Layer 0 found Person Accounts missing, give it the same dedicated irreversibility confirmation (one combined ask is fine); declining stops with zero writes (`STOPPED_PERSON_ACCOUNTS_MISSING`). Confirm the rest of the plan via `AskUserQuestion` before any other write — the ordinary checkpoint, covering every remaining write including toggles; never a separate per-toggle confirmation.
6. **Assign `FundraisingAccess` org-wide, and classify each human user by role** — query all active, human `User` rows, classify each by `Profile.Name` (Admin/Standard/unclassified), and assign `FundraisingAccess` to every resolved human user, idempotently. See `references/permission-targeting.md` for the full targeting model and the custom-profile limitation.

### Phase 3 — Enable and configure

6a. **Apply the confirmed Person Accounts change** — only after step 5. Missing → create the Business Account record type, then run the enablement chain (its own operations only, not HR-Service's). A failed re-check stops with `STOPPED_OTHER`. Once it shows an active type (even if enabled), make both types visible to Standard User/System Administrator, Person Account default; on failure report manual and continue.

7. **Enable Fundraising.** Step 5 already resolved whether this runs; a decline there already stopped the run. Otherwise follow the `FundraisingSettings` skill's `set-fundraising-org-preference` step — see `references/mcp-invocation.md → "Enabling Fundraising (set-fundraising-org-preference)"`. If `describe` shows no dispatchable route for it on this org, treat that as a blocking capability gap and stop — do **not** fall back to a Metadata API write for this field. Re-verify via `dispatch_readonly` of `get-settings-view-model` before treating it as done — never trust the write response alone.
8. **Assign permission set groups by role** — `Fundraising_Admin` to every Admin-classified user, `Fundraising_User` to every Standard-classified user from step 6 — never both, never unclassified. Same idempotency rule as step 6.
9. **Create the default Gift Designation record** — `GiftDesignation` (`Name`, `IsActive = true`, `IsDefault = true`), confirmed via `describe`. Query for an existing `IsDefault = true` record first. Blocked whenever step 7 was blocked (`INVALID_TYPE` until the org preference is on); never run ahead of step 6 — the assigned user needs `FundraisingAccess` to see it.
10. **Configure basic settings** — `FundraisingConfig` fields for gift/recurring-donation-failure handling, confirmed via `describe` (see `references/mcp-invocation.md → "FundraisingConfig field defaults"`). Resolve `DonorExternalIdField` deterministically via an object describe on the donor object, looking for a field with `externalId: true` (see `references/mcp-invocation.md → "FundraisingConfig field defaults"` — do **not** query `FieldDefinition`/`EntityParticle` for an `IsExternalId` column, neither exposes one), else fall back to donor name — no prompt. This resolution is mandatory, never skippable: do not save `FundraisingConfig` with `DonorExternalIdField` unset, and run the describe even if every other setting is already configured. Blocked whenever step 7 was blocked.
11. **Configure the Fundraising-adjacent feature toggles** — the six toggles in `references/mcp-invocation.md → "Fundraising feature toggles"`: 2 route through named headless-360 operations, and the other 4 route through the generic Setup org-preference operation. (NextGen Commitment Processing is not a toggle here — step 7's `set-fundraising-org-preference` already force-enables it as a side effect.) Verify every write with a best-effort read-only Tooling query; if `IndustriesSettings` isn't available on the org, report the toggle as written-but-unverified and ask the admin to confirm it in Setup, never fall back to a metadata write. Blocked whenever step 7 was blocked.
12. **Offer optional enhanced features** — once core setup (6–11) is confirmed complete, step-by-step or via the front-loaded batch, ask once, combined, via `AskUserQuestion`: Interest Tags, Interaction Summaries, Record Alerts, Life Events, Timeline — all, some, or none, never one at a time. If Record Alerts is selected, follow up with one `AskUserQuestion` for the category's label and description (free text) and severity (a choice of `Error`, `Warning` or `Info`) — never create a category without an admin-supplied name. Timeline is irreversible and needs its own explicit warning/confirmation beyond the combined ask. See `references/mcp-invocation.md → "Optional enhanced features"` for the per-feature mechanism.

### Phase 4 — Report

13. **Verify** — re-query what was written (assignments, enablement flag, Gift Designation, settings, toggles) rather than trusting the write response either way — a `dispatch` can `500` and still have applied, or `200` and still have been silently rejected. Only a read-back is authoritative.
14. **Summarize for the user** — a compact table (Item | Status), not prose: permission sets/groups, enablement, Gift Designation, every toggle/feature (flag any fallback or skip), final `outcome`/`stopReason`. Same format for the step 12 pre-ask recap — see `references/mcp-invocation.md → "Status-recap table format"`.
15. **Write `state.json`** — see Output Expectations below. This is the final action regardless of outcome, including hard-stops.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Check licensing, then Person Accounts, read-only first; enable Person Accounts (step 6a) only after the admin confirms the plan | Irreversible — confirmed as part of the plan |
| Check Fundraising licensing before the Person Accounts check and permission sets | Stops an unlicensed org before any irreversible write |
| Always `describe` before a `dispatch` write | Confirms the exact input schema for each operation |
| Confirm the plan via `AskUserQuestion` before enabling Fundraising or assigning anything | Prevents unintended, hard-to-reverse org changes |
| Assign permission sets/groups to human users only | Integration/service users on Fundraising sets cause confusing access grants |
| Re-verify via read-only queries instead of trusting write responses | `dispatch` can `200` on a rejected create or `500` on a write that actually succeeded — neither response alone is proof |
| Check `orgPreferenceEnabled` (Phase 1) before assuming Fundraising is already on | One-way, irreversible, org-wide toggle — gated behind its own dedicated confirmation |
| Never treat a human's "done" answer at a pause gate as verified — re-run the read-only check before resuming | Only the org's own state is authoritative, not a report of it |
| Never persist or read a local checkpoint file to decide where to resume | `state.json` is output-only; live org state is the only checkpoint |
| Write `state.json` as the final action on every path, including hard-stops | Downstream eval scoring and admins need a machine-readable outcome regardless of where the flow stopped |
| Permission set/group assignment is org-wide by role | See `references/permission-targeting.md` |
| Attempt every write through headless-360 named operations or the generic Setup org-preference operation; never write `IndustriesSettings` (or any toggle) through the Metadata API or the `sf` CLI | The Metadata API isn't available on every org, so a Metadata-API-dependent flow breaks there |
| Never create a Record Alert category without an admin-supplied name — no example or default name | The category is admin-owned content; a made-up one is clutter they didn't ask for |
| Ask about optional enhanced features (step 12) once, combined — never one `AskUserQuestion` per feature | Avoids prompt fatigue for a set of independent, non-blocking add-ons |
| Never automate page-layout or Lightning-page component placement (e.g. the Business Milestones related list) — always manual, guided instructions | Placement/styling isn't well-driven through chat, and automation risks overwriting existing customizations |
| Gift Designation queries/creates (step 9) must never run ahead of permission set assignment (step 6) | Designations aren't visible or usable to the assigned user until `FundraisingAccess` is granted |

---

## Gotchas

Known failure modes and misreadings, with resolutions, are catalogued in full in
`references/gotchas.md` — read it before executing any step that involves `discover`,
permission set/group readiness, or Record Alerts. Additional
edge cases (write-response trust, resume/idempotency, pause-gate re-verification, the "who am I"
fallback, custom-profile/integration-user limits, donor External-Id) are in
`references/mcp-invocation.md`'s Error Taxonomy/gate sections and `references/permission-targeting.md`'s
known-limitations notes.

---

## Output Expectations

> **Known gap**: this schema doesn't yet track org-wide permission targeting or feature toggles.
> Extending it further is a tracked follow-up.

Write `state.json` to the working directory as the final action, matching this schema:

```json
{
  "prereqs": { "personAccountsEnabled": true, "fundraisingLicensed": true },
  "permSets": { "resolved": true, "assignedToHumanUsersOnly": true },
  "confirmedBeforeEnable": true,
  "fundraisingEnabled": true,
  "permissionSetGroupsAssigned": true,
  "defaultGiftDesignationCreated": true,
  "settingsConfigured": true,
  "outcome": "CONFIGURED",
  "stopReason": "",
  "optionalFeatures": {
    "offeredCombined": true,
    "recordAlerts": { "categoryCreated": true, "categoryAlreadyExisted": false, "orgPrefsOutcome": "manual_guidance_given" },
    "lifeEvents": { "licenseAssigned": true, "pageLayoutDeployAttempted": false },
    "timeline": { "enabled": true, "dedicatedConfirmationGiven": true }
  }
}
```

`outcome` is one of `CONFIGURED`, `STOPPED_PERSON_ACCOUNTS_MISSING`, `STOPPED_NOT_LICENSED`,
`STOPPED_NOT_CONFIRMED`, `STOPPED_ENABLEMENT_NOT_CONFIRMED`, `STOPPED_OTHER` — never any other
string, including something meaning "skipped" or "already done." There is no such value; inventing
one fails validation.

**`optionalFeatures` is a required top-level object whenever step 12 is reached** — reached means
attempting or resolving at least one of Record Alerts, Life Events, or Timeline, not finishing all
three. `orgPrefsOutcome` is one of `configured`, `manual_guidance_given`, `license_gap`,
`not_reached`. The Record Alerts org preferences are manual guidance only, so use `manual_guidance_given` once the admin opts in (category creation is reported separately in `categoryCreated`).
Populate every sub-field touched with what was actually observed; leave sub-fields for a feature
never touched at their not-yet-resolved value (`not_reached`/`false`) rather than dropping them.
Omit the whole `optionalFeatures` object only when step 12 was never reached at all — never omit it
just because the work is partial.

**All eight core fields above must be present in the written JSON with a literal `true`/`false` —
never omit a key, even for a step the request told you to skip.** A step the front-loaded batch
confirmed is *verified*, not skipped — give it the batch's real observed value (usually `true`),
not `false`. Reserve `false` for a field genuinely never checked by any means; even then the key
itself must stay in the object — a missing key and a `false` value are not the same output, and
only the latter passes validation. Populate every field from values actually observed via
`dispatch*`/the read-back — never fabricate. Set `stopReason` whenever `outcome` starts with
`STOPPED_`. Core setup pre-verified via the front-loaded batch, plus this session's
optional-enhanced-features work, still reports `outcome: CONFIGURED` — that enum has no separate
"already done" variant.

Use `STOPPED_ENABLEMENT_NOT_CONFIRMED` — not `STOPPED_OTHER` — when Phase 2 step 5's enablement
confirmation ends in "stop": an explicit admin decline. No writes were made, so leave the write-dependent
fields `false`.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Provisioning a Unified Employee (UEL) user, not a Fundraising setup | `service-itsm-agentic-setup-uel-user-create` |
| General headless-360 invocation conventions (tool shape, ECA setup) | See `references/mcp-invocation.md` in this skill, or the sibling reference in `service-itsm-incident-mgmt-configure` |

---

## Reference File Index

| File | When to read |
|------|--------------|
| `references/mcp-invocation.md` | Every phase — call shape, ECA setup, error taxonomy, and optional-features mechanisms |
| `references/permission-targeting.md` | Steps 6, 8 — the org-wide role-based permission model |
| `references/gotchas.md` | Before any step touching `discover`, toggle verification, permission set/group readiness, or Record Alerts — known failure modes and resolutions |
