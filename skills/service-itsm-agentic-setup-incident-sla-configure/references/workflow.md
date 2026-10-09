# Incident SLA setup — full step-by-step workflow

Detailed companion to `SKILL.md`. The SKILL.md body carries the phase **overview**, the
**Rules / Constraints** table, and the **Verification Checklist**; this file carries the
per-phase step-by-step detail (every read, delegated write, and API quirk). All steps are
sequential. **Always read before you write.** Every call goes through `mcp__headless-360__*`
tools. Call shapes / templates / response envelope / gotchas live in `references/mcp-invocation.md`.

## Before you start — Reuse what the session already knows

Each Phase 3a read carries a **skip-if-already-known** clause: skip only when the same fact was
produced **this session** by a successful `dispatch_readonly` on the current org and unwritten since —
a user statement is never cache-eligible. Cacheable: IT Service Management enablement (Phase 1a,
only if `ENABLED`), master Incident Mgmt pref (step 1, only if
`ENABLED`), SLA feature + Versioning (Phase 1b), Incident describe (3, incl. the `Incident.Priority`
picklist), the priority-matrix flag (Phase 2 step 2), `BusinessHoursId` (4), SLA Connect ops (2). (Step 5 resolves no Account — Incident has
none.) **When in doubt, re-check.**

## Phase 1a — IT Service Management enablement gate

**Resolve this gate first, before Phase 1b and before the Master Incident Mgmt pref below.**
"IT Service Management" (`service-cloud-itsm-setup`) is a higher-level org gate — it sits above every per-feature ITSM master toggle, including Master
Incident Management. Read via the Setup Discovery Connect API
(`GET .../connect/setup/discovery/features`), filtered client-side to the **exact** apiName
`service-cloud-itsm-setup` — never a look-alike. It has two states, `ENABLED` /
`NOT_ENABLED` (no `NOT_AVAILABLE` — treat any unexpected value as a halt).

- `ENABLED` → proceed to Phase 1b.
- `NOT_ENABLED` → tell the user plainly that IT Service Management is not enabled, then a single
  `AskUserQuestion`: enable it now (note it's **reversible** — it can be disabled again later) or
  stop.
  - **Enable** → dispatch the enable route **directly** — there is no owning SOR to delegate this
    write to yet (unlike the Master Incident Mgmt gate below, which delegates to
    `service-itsm-incident-mgmt-configure`); this is a scoped, temporary exception to "delegate
    every write," flagged for a future delegate swap once a dedicated SOR exists. Halt and surface
    the raw error on any failure. Re-read to confirm `ENABLED` before continuing.
  - **Stop** → halt, point to Setup for manual enablement.

Shapes: `references/mcp-invocation.md` (Phase 1a).

## Phase 1b — SLA Management for IT Service prerequisite gate

**Resolve this gate first, on its own. Reads are safe up front; confirm the org before any write.**
"SLA Management for IT Service" is enabled only when **both** Simplified SLA Setup **and** SLA
Versioning are on; either off → not enabled. These are **two separate writes** — enabling SLA
Management (which flips its composite prefs atomically, and requires Entitlements already on) does
**not** turn on Versioning; Versioning is a distinct, **permanent, one-way** write. Both the reads and
the writes are **delegated to `itsm-shakti/SLASettings`** (owns the SLA-Management
settings surface) — discover → describe → dispatch rather than re-deriving the routes here.
Shapes / preconditions / `enableBlockedReasons` / ack wording: `references/mcp-invocation.md`.

- **Read both** (`dispatch_readonly`); proceed to Phase 2 **only when both are on**.
- **On an OFF org, read the master license first** (Phase 3a step 1, `service-cloud-itsm-incident`):
  `NOT_AVAILABLE` → **HALT** — don't flip the permanent Versioning switch where Incident SLA can't run.
- **Two separate `AskUserQuestion` acks — never merge.** (a) master Incident Mgmt `NOT_ENABLED` → ask
  to enable it first (reversible, no permanence warning). (b) a *distinct* permanence ack: completing
  the gate also turns on **SLA Versioning** (a **separate** write), which **can't be turned off** (SLA
  Management disables later but Versioning stays on). Offer **enable**/**stop** — no "versioning-off";
  a bare "enable SLA" is **not** consent.
- **Decline (b), non-empty `enableBlockedReasons`, or a re-read mismatch → HALT** — enable no SLA
  Mgmt/Versioning, don't proceed to Phase 2/3a (a reversible master enable from (a) stands). **After
  any write, re-read both and report the REAL state** — never trust `201`/`204`.

## Phase 2 — Predefined (OOB) vs Custom

Once the gate passes, offer the OOB policy **before** any custom-flow questions. **Incident only.**

1. **Prerequisite + detect.** Confirm master Incident Mgmt pref `ENABLED` (Phase 3a step 1). Then
   `dispatch_readonly` `GET /headless/invoke/platform/slasettings` (get-existing-checkbox-states) —
   its lowercase-keyed map's `incident` value is the authoritative "is the OOB default seeded?"
   answer (this is the seeder's own dedup read; it maps to display name **"Standard Support for
   Incidents"**). An empty map `{}` or a missing `incident` key means not seeded.
   - **`incident: true`** → **no re-seed** (no idempotency), no custom upsell; report it is seeded.
     **If warn/escalate actions were requested → resolve the named existing milestones → Phase 5 →
     Phase 6 verify → STOP** (attach actions even though the policy was already seeded).
2. **Fork.** **First — before presenting the fork prompt** — read the live `Incident.Priority`
   picklist. This is the **Phase 3a step 3 `Incident/describe`** pulled forward (its
   `fields[].picklistValues`), cached per “Before you start” — so the Custom branch's Phase 3a step 3 is then a
   no-op, not a second describe (**Custom-Priority coverage note; informational — NOT an OOB option**). If it carries
   **custom active values beyond the four standard tiers** (Critical / High / Moderate / Low) — e.g.
   an org-added `Emergency` — the fork prompt must **say plainly that the predefined policy covers
   only the standard tiers**, so those custom values get **no First Response milestone under OOB**.
   Do **not** *proactively* offer to bolt a milestone for them onto the predefined policy, and **never
   re-seed** (the seeder builds one fixed bundle server-side and isn't idempotent — re-running
   duplicates). Point the user to the **Custom** path by default, which reconciles every value against
   the live picklist **and adds a milestone for each custom active Priority value** (Phase 3b / Phase 4A
   step 4). **But if the user *explicitly* asks to add a milestone for a custom tier onto the seeded
   policy, honor it** — resolve the seeded *Standard Support for Incidents* policy by name (SOQL) and
   delegate a **direct `csp-sun/create-milestone`** against that policy id (the same milestone-attach op
   the Custom flow uses at Phase 4A step 4 — a direct attach, **not** a re-seed of the bundle). The
   default decision stays a clean Predefined-vs-Custom fork; the explicit attach is opt-in only.
   **Priority matrix note.** Also read the matrix flag (`references/mcp-invocation.md` → Priority
   matrix flag). The predefined policy is priority-tiered, and with the matrix **off** every Incident
   gets the org's default priority, so only that tier's milestones fire. If it is off, say so plainly
   in the fork prompt (when the fork is skipped, on the Priority-tiered option of the strategy
   question instead) and point to `service-itsm-incident-priority-configure` to turn it on. This is a
   warning, not a gate — never enable the matrix from this skill.
   **Business Hours note (only when the user specified hours).** The seeder takes **no** Business Hours
   input — it always attaches the org's active **default** Business Hours (`IsDefault = true`), or none
   if the org has no active default. So if the user named a schedule or described a calendar (e.g.
   "Mon–Fri 9–6 IST"), run the Phase 3a step 4 query first and say plainly in the fork prompt that the
   predefined policy would use *<default name>* (or no Business Hours), **not** their requested hours,
   and recommend **Custom**, which honors them. Never patch the seeded policy's Business Hours after
   the seed. If the user said nothing about hours, add no note and ask nothing about them.
   **Then** ask one `AskUserQuestion`, **Predefined first / recommended** (unless a note above
   redirects to Custom):
   Salesforce's predefined Incident policy (*Standard Support for Incidents* — priority-tiered) **or**
   a custom one. One-way: predefined seeds an **active** policy + Entitlement, no un-seed path (manual
   delete only).
   - **Predefined →** **do not resolve or ask for an Account.** The seeder wires the policy's
     Entitlement and BusinessHours **server-side itself** (org default Business Hours), so Phase 3a
     steps 4 (Resolve Business Hours) and 5 (Account) are Custom-flow inputs and are **not** run here
     (beyond the read the Business Hours note above needs) — asking about Business Hours or an Account
     on this branch is an over-ask. The Phase 6 test Incident sets the seeded Entitlement's `EntitlementId`
     **directly** (no Account needed). → **Phase 4B** → **Phase 5** (if actions requested) →
     Phase 6 verify → **STOP**.
   - **Custom →** existing Phase 3a → 3b → 3c → 4A → 5 (if asked) → 6, unchanged.

## Phase 3a — Preflight & discovery

**On any `401` / `403` / `404` from a step below, halt and surface the raw error** — the org/client is misconfigured. `401` → MCP auth (ECA/token). `403` → user perm OR ITSM Incident Management license/pref missing. `404` → `headless-360` not activated OR Entitlement Management not enabled for Incident.

1. **Master Incident Management pref — direct read** *(skip conditions in “Before you start”)*.
   `dispatch_readonly` `GET .../connect/setup/discovery/features`, filter `features[]` to the **exact**
   `apiName == "service-cloud-itsm-incident"` — never a look-alike (`service-cloud-incident-management`
   is generic Case-based Incident Management, not our target). Read `status`: `ENABLED` → proceed;
   `NOT_AVAILABLE` (license missing) → **halt and surface it** — cannot be enabled here, no delegate/ack;
   `NOT_ENABLED` → **explicit `AskUserQuestion` ack first (never auto-enable as an implied SLA
   dependency)**, then delegate to `service-itsm-incident-mgmt-configure` inline — that ack is the
   delegate's confirm-to-write, so never ask twice — and re-read; if declined, halt — every SLA artifact below depends on the master being on. Full shape + why
   setup-org-preferences 404s here: `references/mcp-invocation.md` (Preflight A).
2. **Discover the Connect operations** — *(skip if already verified this session — see “Before you start”)*.
   `mcp__headless-360__discover(query="sla-management milestone")` to confirm the SLA Management
   Connect API is indexed, then `mcp__headless-360__describe(id=<operation_id>)`
   for the `milestone-types`, `sla-policies`, and `sla-policies/{id}/milestones` POST operations to pull
   their exact input schemas + HTTP routes. If `discover` returns nothing after rewording the query,
   the corpus does not index this surface for the org — direct the user to **Setup → SLA/Entitlement
   setup** and stop.
3. **Verify Incident Management + SLA fields** — *(skip if `Incident.describe` result for the
   current org is already in context — see “Before you start”)*. Otherwise `dispatch_readonly` on
   `GET /services/data/v{version}/sobjects/Incident/describe` and confirm `fields[]` includes
   `EntitlementId`, `SlaStartDate`, `SlaExitDate`. If the describe 404s or fields are missing, direct
   the user to enable Entitlement Management for Incident and stop. **This same describe also yields
   the live `Incident.Priority` picklist** (`fields[].picklistValues`) consumed by the Phase 2 fork
   note and the Phase 3b / Phase 4A step 4 reconciliation — so on the Custom branch it is already in
   context from Phase 2 step 2 (“Before you start” skip).
4. **Resolve Business Hours** — *(skip if the `BusinessHoursId` and name for the current org are
   already captured this session)*. Otherwise `dispatch_readonly` the active Business Hours query
   (`references/mcp-invocation.md` → Resolve Business Hours; returns name, default flag, time zone,
   and weekly windows). Then resolve by what the user said — first match wins:
   - **Named a schedule** ("use EMEA Support hours") → exactly one active record with that name
     (case-insensitive) → use it, **no question**. No match or several → `AskUserQuestion` listing the
     active records by name; on no match also offer **Create "<name>"** — ask its time zone, days
     and start/end time, then plan a create (Phase 4A step 1) under the user's name.
   - **Described a calendar** ("Mon–Fri 9–6 IST", "24×7") → reuse an active record whose time zone and
     weekly windows match, **no question**. None matches → plan to **create** one (Phase 4A step 1),
     named after the description (e.g. `Incident SLA — Mon–Fri 09:00–18:00 IST`).
   - **Named only a time zone** ("use IST", no days or hours) → `AskUserQuestion`: **24×7 in that time
     zone (Recommended)** or **Custom hours**. Custom hours → ask which days and the start/end time.
     Then treat the answer as a described calendar (reuse a match, else plan a create).
   - **Said nothing** → exactly one active `IsDefault=true` record → suggested default, **no
     question**. No default / several / other ambiguity → `AskUserQuestion` listing the active records
     by name.
   - **No active records at all** → tell the user plainly, then `AskUserQuestion`: create a **24×7**
     schedule in the org's time zone (Phase 4A step 1) or stop and create one in Setup.
   Capture the Id internally (never shown) and the name — or "new: `<name>` (to be created)" — for
   Phase 3c. Every create is confirmed at Phase 3c and never sets `IsDefault`.
5. **Account — NOT required for Incident; do not resolve or ask for one.** Unlike Case, `Incident`
   has no customer-`Account` field, and the Custom flow's Entitlement auto-provisions on activation
   (`createEntitlement=true`, Phase 4A step 5) **without** an `AccountId` — no write in this flow consumes an
   Account (engagement is per-Incident via `EntitlementId`; see Phase 4A step 6). So **skip this step** — asking
   for an Account here is an over-ask that also seeds the false "Account-scoped auto-apply" premise.
   (Only revisit if a specific leaf's `describe` proves it hard-requires an `AccountId`; it does not
   today.) If the user *volunteers* an Account name, acknowledge it but do not treat it as required.
6. **Read existing SLA artifacts (idempotency probe)** — `dispatch_readonly` SOQL for `SlaProcess` by
   name (`... WHERE Name = '<name>' AND SobjectType = 'Incident'` — the field is `SobjectType`;
   `ProcessType` returns `INVALID_FIELD`), each `MilestoneType` the strategy would create,
   `SlaMilestone` under the matched policy, and `Entitlement` by name (no Account filter — Incident has none). If
   **every** artifact already exists with the requested config, set `noOp=true` and skip Phase 3b +
   Phase 4A (skip condition (b)); any missing/divergent artifact → proceed to Phase 3b.

**Coexistence with an existing active Incident policy (Custom flow).** When the Phase 2 / Phase 3a
reads surface a *different* active Incident SLA policy already present (e.g. a predefined *Standard
Support for Incidents* detected at Phase 2 step 1) **and the user has explicitly asked for Custom**
(this is the deliberate-Custom case while that policy stays seeded — not the upsell path Phase 2
forbids): **do NOT offer to deactivate, replace, or un-scope the existing policy** — changing a policy
the user didn't ask to touch is out of this skill's scope and risks disrupting a live SLA (deactivation
is technically reachable via `activate-sla-policy` `isActive=false`, but that is not this flow's job),
and predefined has **no un-seed path (manual delete only)**. The
two are meant to coexist — creating the custom policy never removes or hides the existing one: both
remain in **Setup → SLA/Entitlement setup** and both stay usable. The custom policy coexists cleanly
**because it engages per-Incident via `EntitlementId`** (Phase 4A step 6), not by any Account-scoped auto-apply
(Incident has no Account field to scope on) — narrate that, don't fork on it: "your existing *<name>*
policy stays active; this custom policy is applied per-Incident by setting the Incident's Entitlement
to it." State the one genuinely singular point without inventing a fix: an Incident engages exactly
**one** Entitlement (its `EntitlementId`); to put the custom policy on a specific Incident, set that
Incident's `EntitlementId` to the custom Entitlement (the mechanism Phase 6 already uses) — **never**
reorder or disable the other policy's criteria. Keep this a Phase 3c plan-narration, **not** a
Replace-vs-Keep-both prompt. **The closing report follows the same rule:** the existing/predefined
policy stays the broad org-wide one and the custom is targeted per-Incident — do **not** end the report
by offering to broaden the custom policy to auto-apply to **all** Incidents or to "decide/resolve
precedence" against the existing policies (there is no leaf that arbitrates cross-policy precedence);
point to `EntitlementId` for targeting a specific Incident instead.

## Phase 3b — Milestone Strategy

Every SLA policy needs at least one milestone. Load `examples/milestone-patterns.md` — it lists the
skip conditions (concrete shape in prompt / idempotent no-op / explicit up-front authorization) and
the five strategy options with their `AskUserQuestion` prompt, defaults, and MilestoneType-reuse
rules. Skip condition (c) still requires Phase 3c plan-narration before dispatch. Multi-milestone
selection expands to N creates in Phase 4A step 4 (one delegation per milestone, `order` 1..N, same SlaProcess).

## Phase 3c — Confirm before mutating

1. **Confirm the plan** — present the resolved config (target **org**, **SLA Policy** name,
   **Business Hours: `<name>`** (and, if Phase 3a step 4 planned a create, its time zone + weekly windows and
   that it will be **created** — a new record this skill does not remove later), the **engagement model** (per-Incident via `EntitlementId` — **no
   Account**, since Incident has no Account field), and the **full per-milestone list** — never
   collapse Priority-tiered / Custom to "N milestones"). For a Priority-tiered plan with the matrix
   off, repeat the Phase 2 matrix note here. **Skip the `AskUserQuestion`** (but still narrate the
   plan before dispatch) when up-front authorization was granted (note `(authorized in prompt)`), the
   branch is a no-op, or it was already confirmed in conversation (note `(confirmed in conversation)`);
   otherwise require an explicit "yes" before Phase 4A. Everything after this step mutates the org.

## Phase 4A — Create SLA Artifacts (delegated writes — exact order, each depends on the previous)

**The skill decides every input below; the raw writes are delegated to the approved SLA leaf
capabilities** (discover → describe → dispatch each) — they own the approved Connect contracts, so do
not re-derive request shapes here. Capture each returned `id` for chaining only (never surface it —
Output contract).

1. **Business Hours (only if Phase 3a step 4 planned a create).** `dispatch`
    `POST /services/data/v{version}/sobjects/BusinessHours` with the confirmed name, time zone, and
    weekly windows (shape: `references/mcp-invocation.md` → Resolve Business Hours). **Inline, not
    delegated** — no served SOR owns Business Hours writes yet; a scoped exception like the Phase 1a
    enable. Re-read by Id to confirm `IsActive = true` before step 3; on any failure halt and surface
    the raw error (nothing else has been written yet).
2. **MilestoneType(s) → delegate to `csp-sun/MilestoneTypes`.** Decide the set + reuse rule **here**:
   reuse a single MilestoneType across milestones that share a name (Priority-tiered "Incident First
   Response" is reused across **all** its milestones, including any custom active Priority value);
   create separate MilestoneTypes for distinct concerns (Response + Resolution = two; Escalation
   ladder = three); skip a name the Phase 3a probe already found. Delegate the raw create per required
   type; a detected/reused one is narrated by name only (Output contract: name, never `→ <Id>`).
3. **SLA Policy → delegate to `csp-sun/create-sla-policy`.** Pass `processType='Incident'`, the
   `businessHourId` resolved in Phase 3a and confirmed in Phase 3c, and the entry/exit criteria
   confirmed there. Created **inactive** — activation is the explicit step 5 so the auto-entitlement is provisioned. **The
   create response echoes nulls — verify via SOQL, not the body; narrate the policy by name, never
   the Id** (Output contract).
4. **Milestone(s) → delegate to `csp-sun/create-milestone`, one delegation per milestone** in
    ascending time-trigger order (`order` 1..N, same policy). Build each `milestoneCriteria` **here**
    from `assets/attach-milestone.json` + the per-pattern `filterItems` in
    `examples/milestone-patterns.md`. **This is where the Priority reconciliation lands:** match every
    criteria value against the **live** `Incident.Priority` picklist, drop/rename unmatched standard
    rows, **and add a milestone for each custom active Priority value** the org added — no active value
    left without an SLA. The leaf owns the UPPERCASE `milestoneState=ACTIVE`, `filterType=RuleFilter`,
    no-`slaProcessId`-in-body, and confirm-from-body (this endpoint returns `201` even on a failed
    save) contract. On any failure, halt (no half-attached policy) — narrate each by `MilestoneType`
    name, never its Id/`triggerId` (Output contract).
5. **Activate + auto-provision Entitlement → delegate to `csp-sun/activate-sla-policy`.** Activate
    the policy and provision its Entitlement in one call — `isActive` and `createEntitlement` are
    **QUERY params, not a body** (always send `createEntitlement` explicitly). This is the **custom
    flow only** — it replaces the old `active:true`-on-create + manual `POST /sobjects/Entitlement`.
    The **OOB seed path does not run this step at all**: its single `save-selected-options` call seeds
    an already-active policy and auto-provisions the Entitlement itself (see Phase 4B). The leaf carries the
    no-500 activation contract: a `200` with a returned `entitlementId` is the success shape. Capture the
    returned `entitlementId`. **Verify by reading the policy back (`active=true`)**, never the write response.
6. **Engagement targeting (Incident has NO Account-scoped auto-apply).** Unlike Case, **`Incident`
    has no customer-`Account` field** (its only Account-ish field is the polymorphic `ReportedById`),
    so an Entitlement's auto-apply criteria **cannot be Account-scoped for Incident** — do not attempt
    it, and **do not ask for or bind an Account for auto-apply scope** (that was an over-ask that also
    caused a mid-flow contradiction). **Default: per-Incident targeting** — the custom policy engages by
    setting an Incident's `EntitlementId` to this policy's Entitlement (the same mechanism Phase 6
    uses); create **no auto-apply criterion**, and say so in the plan/report ("engages per-Incident via
    `EntitlementId`; no auto-apply criterion — Incident has no Account field to scope on"). Only if the
    user **explicitly** wants an org-wide always-match criterion do you delegate to
    `csp-sun/create-entitlement-criteria` (`entitlementId` from step 5; leaf owns the uppercase
    `AND|OR|CUSTOM` `criteriaType` contract — mixed-case / `RuleFilter` / `Formula` silently fail to
    open on the Setup edit page; verify by "read every rule in the org, match by `entitlementId`") —
    and first surface that an always-match criterion **collides** with any existing broad Incident
    policy (Coexistence rule). Narrate by name, never the Id.

## Phase 4B — Seed the Predefined Incident Policy

Reached only from Phase 2 Predefined (replaces Phase 3b/3c/4A). The predefined **"Standard
Support for Incidents"** bundle is seeded by **one** call to the platform's own default-policy
seeder — the same action the SLA Settings Setup page runs — served headless on the Aura dispatcher
route. Core's seeder builds the entire active bundle itself (policy + MilestoneTypes + milestones +
Entitlement + entitlement criteria), so the skill neither hand-lists the milestones nor provisions
the Entitlement. This replaces the former hand-rebuilt seed (a raw `active:true` `POST .../sla-policies`
+ 6 `create-milestone` calls + a manual `POST /sobjects/Entitlement`) — that whole replica is retired.
The detect + seed are **delegated to `itsm-shakti/SLASettings`** (contract owner of the seeder route).

Follow the seed recipe in `references/mcp-invocation.md` (**Predefined Incident Policy**):

1. **Detect (dedup).** `dispatch_readonly` `GET /headless/invoke/platform/slasettings`
   (get-existing-checkbox-states) — its lowercase-keyed map's `incident` value is the authoritative
   "is the OOB default already seeded?" answer. **`incident: true`** → **no re-seed** (the seeder is
   NOT idempotent — re-running duplicates), no custom upsell; report it seeded and skip to Phase 5/6.
2. **Seed.** `dispatch` `PATCH /headless/invoke/platform/slasettings/save-selected-options` with body
   `{"selectedOptions": ["incident"]}` — **the value MUST be lowercase `incident`**; the capitalized
   `Incident` returns a server-side `500`. A `200` with body `true` is success. This provisions the
   full **active** bundle + auto-entitlement in one shot — no manual Entitlement, and no Connect
   activate PATCH, so the 500 that path could throw never arises.
3. **Verify.** Re-read `GET /headless/invoke/platform/slasettings` and confirm `incident: true`, then
   SOQL `SlaProcess` for **"Standard Support for Incidents"** `IsActive = true` (do not trust the write
   body), selecting `BusinessHours.Name` too. Narrate the policy by name, never its Id, and report
   which Business Hours it uses by name — or plainly that it has none (no active default existed).

Then Phase 5 (if actions requested), Phase 6 (a non-lowest tier — Moderate/Low, not Critical — subject
to the Phase 6 step 2 stopping rule),
and **STOP** — no *proactive* custom offer. Any custom-Priority coverage gap was surfaced at the
Phase 2 fork (as an informational note + redirect to the Custom path), **not** by proactively
augmenting the seeded OOB policy here. **The one exception is an *explicit* user request** to attach a
milestone (or a warn/escalate action) to the seeded policy — honor it via a **direct
`csp-sun/create-milestone`** (resolve the *Standard Support for Incidents* policy by name; a direct
attach, **never** a re-seed), then verify and STOP.

## Phase 5 — Milestone Actions (optional: Warn / Escalate)

After milestones exist (Phase 4A or 4B), **only if** the user asked to warn/escalate/notify: apply
the requested checkpoint(s) to **every milestone the user named** (not just one), each offset computed
from that milestone's own target. Map "warn at X%" → an offset *before* target, "on breach" →
*at/after* it; **confirm the full set before writing** (up-front auth waives the re-ask; narrate it
regardless — no headless delete), then, per milestone, delegate to headless
**`create-milestone-action`** (`discover` → `describe` → `dispatch`). **Confirm each from the response
body** (`success` + non-empty `actionMappings`; a *timed* checkpoint also returns a `triggerId`), never
the `201`. Narrate each by its **`MilestoneType` name**, never the milestone Id/`triggerId` (Output
contract). **Id-leak guard — Ids most often leak here:** you hold the policy Id and each
milestone Id internally (you need them to target each action write), but the **pre-write plan table
AND the closing report MUST key every row by the milestone's tier / Priority / MilestoneType name**
(e.g. row header `Emergency`, `Critical`), **never** its Id. Do **not** write `Emergency
(553VW000000…)`, a `Policy … (552VW000009…)` header, or any `55…`/`553…` Id in a table cell, a
parenthetical, or the report — those Ids are chaining-only. Formula, roles, example body, defaults,
IST business-hours note: `references/mcp-invocation.md` (Milestone Actions).

## Phase 6 — Verify

1. **Verify the SLA Policy** — SOQL on `SlaProcess` (do not trust the create response); confirm it
    read back `active=true` — from the activation delegation (Custom flow) or from the seeder (OOB).
2. **Create a test Incident** to prove engagement — **both flows: set the policy's `EntitlementId`
    directly on the test Incident** (`Incident` has no Account field, so there is no Account-scoped
    auto-apply to rely on; `EntitlementId`-direct is the reliable engagement path — Custom uses the
    Entitlement returned by activation, OOB the seeded Entitlement). For Priority-tiered / OOB
    strategies, test a tier **other than the lowest `order`** — Critical is order-1, the collapse
    fallback, so it can't detect a dropped criterion. If a direct `Priority` insert is rejected (it
    may be matrix-derived), set `Urgency`/`Impact` to derive the tier and read `Priority` back.
    **Stopping rule:** if the matrix flag is off, create **one** test Incident only. If the matrix is on
    but the derived `Priority` is still the order-1 tier after **one** `Impact`/`Urgency` adjustment,
    stop creating test Incidents. Either way, report that the SLA engages but the other tiers were not
    checked, say why (matrix off / matrix maps these inputs to that tier), and point to
    `service-itsm-incident-priority-configure`. Narrate by `IncidentNumber`, never the Id.
3. **Verify engagement + tiering** — SOQL that an `EntityMilestone` landed on the **correct tier**
    (a Moderate/Low Incident → the 240/960 tier, NOT 30/120) with a `TargetDate` — that row is the
    reliable engagement proof. `Incident.SlaStartDate` is populated when you set `EntitlementId` at
    insert, but can be **null** when the Entitlement is auto-applied via criteria (the milestone still
    lands); treat a null `SlaStartDate` as a non-blocker, not a failure. The create `201` always
    echoes `milestoneCriteria:[]`; only this runtime read proves the ACTIVE criteria persisted.
4. **Report results** using the output format in `examples/output-templates.md`.

---

The **Rules / Constraints** table and the **Verification Checklist** live in `SKILL.md`
(body) — read them there before executing; they are the non-negotiable gates this step-by-step
detail implements.
