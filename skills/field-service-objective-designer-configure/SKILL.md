---
name: field-service-objective-designer-configure
description: "Designs service objectives for a Salesforce Field Service scheduling policy via a structured trade-off interview. Guides the user through objective selection and derives weights by establishing crossover equivalences against Minimize Travel (the anchor). Produces a finalized weight table with penalty-rate interpretation and a plain-English policy summary. Use this skill when a user wants to design or weight Field Service scheduling service objectives; called after work rule design and delegates to sfs-sobject-create for record creation."
user-invocable: false
owning_team: sfs-setup-experience
metadata:
  version: "1.0"
  domains: ["Field Service"]
---

# Salesforce Field Service – Service Objective Designer

**Designs the service objectives for a scheduling policy.** Collects objective selection and derives each weight through a structured trade-off interview — one question at a time — and emits a `serviceObjectives[]` block. It creates no Salesforce records; when complete, delegates to `sfs-sobject-create`.

**Interview phases:** Scheduling Policy → Work Rules → **Service Objectives** (this skill) → Record Creation

The `policy` block (from `sfs-scheduling-policy-designer`) and `workRules[]` block (from `sfs-work-rule-designer`) arrive as context; this skill adds `serviceObjectives[]` and hands the complete design to `sfs-sobject-create`.

---

## Background: How SFS Scoring Works

The optimizer assigns penalty points to each candidate schedule. Lower total penalty = better schedule. Each objective contributes penalty points based on its weight and its own scale (its worst-case scenario).

**Minimize Travel weight is the anchor** — set at 1000; all other weights derive relative to it. The general formula, common to every objective (stated once, not re-derived per objective):

```text
penaltyPerViolation = max( 1, roundingFn( (1000 × weight) / scale ) ) × finalMultiplier
total_penalty       = ceil( violations / granularity ) × penaltyPerViolation
```

Two consequences of the shared ×1000 internal multiplier:

- It cancels out of every derivation between two objectives — which is why the interview's continuous approximations stay valid and every "derive weight_X from weight_Y" formula is clean of any ×1000 term. Where the rounding isn't exact for integer weights (ASAP's round, Skill Level/Preference's roundInt), small drift is possible — flagged per objective below.
- The `max(1, …)` floor guarantees every included objective has some effect even at a very low weight.

**One exception:** Same Site's final multiplier (×0.01) nets to an effective ×10, not ×1000 — the one place the "divide by the other objective's rate" shortcut needs adjustment.

---

## Penalty Formulas by Objective

Use these to show math and back-calculate weights. General mechanics (×1000, floor, why derivations stay valid) are above, not repeated.

**Minimize Travel (anchor)** — Scale 120 min (2 hr = default `MaxGrade__c`), round5, ×1/60 (per-minute → per-second). `penaltyPerViolation_travel = max(1, round5(1000×weight_travel/120)) × (1/60)`. At weight 1000 → 8333.33333 → 138.88889 pts/sec (whole-second granularity). Continuous: `travel_penalty(X_min) ≈ X × weight_travel/120` — ≈8.333 pts/min at 1000.
*Precision:* Travel is per-second; Overtime (same scale) is per-minute — a 61-sec trip costs more than a 60-sec one. Floor binds only below ≈0.12.

**ASAP** — Scale 43,200 min (30 days), round. `penaltyPerViolation_asap = max(1, round(1000×weight_asap/43200))`. Whole-minute granularity: `asap_penalty(X_sec) = ceil(X_sec/60) × penaltyPerViolation`. Continuous: `asap_penalty(Y_min) ≈ Y × weight_asap/43200`.
*Precision:* Weights 1–21 are dead — round(1000×21/43200)=0, clamped to 1, so all give the identical 1 pt/min rate. Above that, drift is small (weight 250 → effective 259.2, 3.7%). Validate with the integer formula when precision matters.

**Same Site** — Scale 1 (binary), round5, ×0.01 → **effective ×10, the exception**. `penaltyPerViolation_same_site = max(1, round5(1000×weight_same_site)) × 0.01`. At weight 50 → 500 pts/violation.
*Precision:* round5 exact for integer weights. Flat per-event regardless of time. Effective multiplier is ×10, not ×1000.

**Minimize Overtime** — **Identical mechanics to Minimize Travel** (scale 120, round5, weight 1000 → 8333.33333) **except:** final multiplier is ×1.0 not ×1/60, so the rate is per-**minute** (8333.33333 pts/min); and penalty groups into whole minutes — `overtime_penalty(X_sec) = ceil(X_sec/60) × penaltyPerViolation` — so a 61-sec block costs the same as 120-sec. `penaltyPerViolation_overtime = max(1, round5(1000×weight_overtime/120)) × 1.0`. Continuous: `≈ Z × weight_overtime/120`; comparable to Travel.
*Precision:* Floor binds below ≈0.12.

**Preferred Resource** — Scale 1 (binary), roundInt, ×1.0. `penaltyPerViolation_preferred = max(1, roundInt(100 × 10.0 × weight_preferred)) × 1.0` (100×10.0 = 1000). At weight 375 → 375,000 pts/violation. Derivation: `weight_preferred = T_equiv × (weight_travel/120)` — with weight_travel 1000: `= T_equiv × 8.333`.
*Precision:* Zero rounding error for integer weights (exact form `X_violations × 1000 × weight_preferred`). Floor only below weight 0.001.

**Resource Priority** — Scale 10 (priority 0–10; 0 = best, 10 = lowest), no rounding (raw decimal). `penaltyPerViolation_resource_priority = max(1, (weight_resource_priority/10.0) × 1000)`. At weight 1875 → 187,500 pts/priority point. Total for priority P: `P × penaltyPerViolation`. P=0 → 0; P=10 → max.
*Precision:* Full float, no rounding. Linear — priority 5 = 50% of max.

**Skill Level** — Scale 10 (10-point scale), roundInt. `penaltyPerViolation_skill_level = max(1, roundInt(1000×weight_skill_level/10))`. Total for skill level S: `S × penaltyPerViolation`.
*Applicability:* Multiple skill requirements → SFS averages the scores; none → no impact. Least vs. Most Qualified mode (set in the interview) flips the preferred direction but not the formula.
*Precision:* Zero rounding error for integer weights. Floor negligible below weight ≈0.01.

**Skill Preference** — Scale 10 (skill priority 1–10; 1 = most preferred, 10 = least; null → 10), roundInt. `penaltyPerViolation_skill_preference = max(1, roundInt(1000×weight_skill_preference/10))`. Total for skill priority SP: `SP × penaltyPerViolation`. Applicability (same Skill Type, OR matching on the companion Match Skills rule) set in the interview.
*Precision:* Zero rounding error for integer weights. Linear in SP.

**Group Nearby** — Scale 1 (binary — in cluster or not), round5, ×1.0 (full ×1000, unlike Same Site's ×0.01). `penaltyPerViolation_group_nearby = max(1, round5(1000×weight_group_nearby)) × 1.0`. At weight 167 → 167,000 pts/violation. Derivation: `weight_group_nearby = T_equiv × (weight_travel/120)` — with weight_travel 1000: `= T_equiv × 8.333`.
*Precision:* Flat per-event — each appointment outside its cluster costs the same regardless of distance.

**Minimize Gaps** — Scale 1 (each qualifying idle gap = 1 violation; configurable minimum 30 min–24 hr, shorter gaps uncounted), round. `penaltyPerViolation_gaps = max(1, round(1000×weight_gaps))`. Total: `Σ over routes/shifts [ clump_counter(route) × penaltyPerViolation ]`.
*Precision:* Zero rounding error for integer weights (exact form `clump_count × 1000 × weight_gaps`). Floor negligible below 0.001. Per gap per route — 3 gaps on one resource = 3× the rate.

---

## Conversation Flow

**Two global rules (govern everything below):**

1. **Round every derived weight up to the next whole number** — ceiling, not nearest. SFS policies don't accept decimal weights.
2. **Never compare raw weight values across objectives** to infer priority — always compute and compare penalty rates per unit, since each has its own scale.

---

### Step 1: Objective Selection

First explain the concept: service objectives are soft scoring criteria that grade candidates who already survived the work rules — unlike work rules, they never reject anyone, they just influence which eligible candidate the optimizer prefers. Note that Minimize Travel is always included automatically as the anchor, fixed weight 1000, that every other weight derives against through trade-off math — the user need not select it.

Then present the remaining nine objectives **one category at a time**, in this fixed order, waiting for the user's selection before the next category:

**1. Customer-Experience Objectives** — present these three, ask which (if any):
- ASAP — Serve customers as early as possible
- Same Site — If two jobs are at the same place, do them back-to-back
- Group Nearby — Cluster jobs that are geographically close

**2. Cost / Efficiency Objectives** — present these three (Travel already included), ask which of the remaining two:
- Minimize Travel *(already included automatically — anchor, fixed weight 1000)*
- Minimize Gaps — Keep technicians continuously busy
- Minimize Overtime — Avoid paying overtime

**3. Workforce / Assignment-Quality Objectives** — present these four, ask which (if any):
- Preferred Resource — Use the preferred/named technician when possible
- Resource Priority — Prefer higher-priority resources (e.g. staff over contractors)
- Skill Level — Match the right level of expertise to the job
- Skill Preference — Honor preference rankings within a skill type (e.g. language preference)

**Per-objective follow-up questions** — ask right after the category they belong to is answered, before the next category:

- **Minimize Travel** (always — ask once, at the end of the Cost/Efficiency category): "Should Minimize Travel also count the legs to/from a resource's home base — home to first job, and last job back home — or exclude those from scoring?" Capture as two independent flags: `excludeTravelFromHome` and `excludeTravelToHome` (true = excluded). Default both false.
- **Same Site** (only if selected): "Should Same Site treat two appointments as the same site only when they share the exact latitude/longitude — useful for campuses or farms — or use the default grouping (within about one second of travel time)?" Capture as `useExactLocation` (true = exact lat/long only). Default false.
- **Minimize Gaps** (only if selected): Ask the minimum idle duration the company counts as a gap (30 min–24 hr). Capture as `params.minGapMinutes`; default 30. Asking here keeps "what counts as a gap" separate from "how hard to close one."

Once all three categories are answered and follow-ups captured, move to Step 2.

---

### Step 2: Trade-Off Interview

For each selected objective (other than Minimize Travel), ask a trade-off question. The goal is the crossover point where the user considers the two options equally acceptable — that equivalence lets you calculate the weight. After they answer, solve for the unknown weight by setting the two penalty expressions equal, then round up per the global rules. Always show the math.

**Offer concrete preset answers alongside the open question.** After the question template, give a few ready-made crossover points spanning light/medium/strong preference so the user can pick one instead of inventing numbers. Always also invite their own exact trade-off. Presets are a convenience, not a separate calculation path.

#### ASAP Trade-Off

> "If you could schedule an appointment right now but it would add [X] minutes of travel, versus scheduling it [Y] hours from now with no extra travel — at what point would those feel roughly equivalent to you?"

Presets: "15 min travel ≈ 12 hr delay" (mild), "30 min travel ≈ 24 hr delay" (moderate), "60 min travel ≈ 48 hr delay" (strong).

Math (user gives X min travel, Y hr delay):
```text
travel_penalty(X) = asap_penalty(Y × 60)
X × (weight_travel / 120) = (Y × 60) × (weight_asap / 43200)
weight_asap = X × weight_travel × 6 / Y
```
With weight_travel = 1000: `weight_asap = X × 6000 / Y`.

**Integer-formula validation:** confirm `penaltyPerViolation = max(1, round(1000 × weight_asap / 43200))`, then `effective_weight = penaltyPerViolation × 43200 / 1000`. If it differs meaningfully (>5% drift), note it.
**Low-weight warning:** if derived weight < 22, warn that SFS clamps the per-minute penalty to 1 (the floor) — any weight 1–21 produces identical behavior.

#### Same Site Trade-Off

**Framing note:** Do NOT compare Same Site to travel time — same-site appointments are already at the same location. Compare against ASAP or Preferred Resource (if selected).

**If ASAP is selected — Same Site vs. ASAP:**
> "Imagine two appointments at the same site. The optimizer can either: (A) Assign both to the same resource, but they get scheduled [H] hours later than they could be. (B) Split them so they're scheduled right now. At what scheduling delay would you say 'just split them'?"

Presets: "keep together up to 1 hr later" (weak), "up to 4 hr later" (moderate), "up to 8 hr later" (strong).
Math (delay threshold D_equiv in minutes): `weight_same_site = D_equiv × (weight_asap / 43200)`

**If ASAP NOT selected but Preferred Resource IS — Same Site vs. Preferred Resource:**
> "Would you split same-site appointments (different resources) to honor a preferred resource assignment for one of them? Or keep them together even if it means ignoring the preferred resource?"

Presets: "equally important" (F = 1), "same-site matters twice as much" (F = 2), "same-site matters half as much" (F = 0.5).
Math: `weight_same_site = F × weight_preferred`

**If neither is selected — fall back to travel comparison:**
> "How many minutes of extra travel would make it worth splitting same-site appointments?"

Presets: "10 extra minutes", "20 extra minutes", "30 extra minutes".
Math: `weight_same_site = T_equiv × (weight_travel / 120)`

#### Minimize Overtime Trade-Off

> "If an appointment could be scheduled now but it would use [Z] minutes of overtime, versus scheduling it [H] hours from now during regular hours — when would those feel equally acceptable?"

Presets: "15 min OT ≈ 6 hr delay" (avoid OT strongly), "30 min OT ≈ 12 hr delay" (moderate), "60 min OT ≈ 24 hr delay" (accept OT readily).

Math (user gives Z min overtime, H hr delay):
```text
overtime_penalty(Z) = asap_penalty(H × 60)
Z × (weight_overtime / 120) = (H × 60) × (weight_asap / 43200)
weight_overtime = weight_asap × H / (Z × 6)
```
*Requires weight_asap calculated first if ASAP is selected.*
**Overtime vs. Travel fallback (if ASAP not selected):** `weight_overtime = T_equiv × weight_travel / Z`, where T is the equivalent minutes of travel the user would accept over Z minutes of overtime.

#### Preferred Resource Trade-Off

> "If an appointment has a preferred resource assigned, how important is honoring it? Imagine the preferred resource is available but would require [X] extra minutes of travel — at what point would you say 'just use the closer resource'?"

Presets: "15 extra minutes" (light), "30 extra minutes" (moderate), "60 extra minutes" (strong).
Math (travel threshold T_equiv): `weight_preferred = T_equiv × (weight_travel / 120)`

#### Group Nearby Trade-Off

**Framing note:** Group Nearby and Minimize Travel are natural competitors — keeping a cluster intact may cost more total travel than breaking it. The trade-off: the maximum additional overall travel the user will spend to keep a cluster together.

> "What is the maximum additional overall travel you'd add to the schedule to keep all appointments in a cluster together? If maintaining the cluster costs more than that, the optimizer should break it and save the travel instead."

Presets: "10 extra minutes" (weak), "20 extra minutes" (moderate), "30 extra minutes" (strong).
Math (T_equiv): `weight_group_nearby = T_equiv × (weight_travel / 120)`

#### Resource Priority Trade-Off

Background to share:
> "The Resource Priority objective ranks service resources on a scale of 0–10, where 0 = highest priority (best candidate) and 10 = lowest. For example, assign internal staff priority 1 and contractors 5+. The optimizer applies a penalty proportional to priority — a priority 5 resource incurs 50% of the full weight as penalty, a priority 0 resource none."

> "Imagine two available resources: Resource A is a staff technician (priority 1) but is [X] minutes further away. Resource B is a contractor (priority [P]) and is the closer option. At what point would you say 'just use the contractor'?"

Presets: "30 extra minutes" (mild), "60 extra minutes" (moderate), "90 extra minutes" (strong).
Math (T_equiv, staff priority P_high = 1, contractor priority P_low): `weight_resource_priority = T_equiv × weight_travel / (12 × (P_low - P_high))`
Example (staff 1, contractor 5, T_equiv = 90): `= 90 × 1000 / (12 × 4) = 1,875`

#### Skill Level Trade-Off

Background to share:
> "The Skill Level objective steers the optimizer toward either the least or most qualified resource that meets an appointment's skill requirements. Penalty = the resource's raw skill level × the objective weight — so a skill level 8 resource incurs 8× the penalty of a skill level 1 resource."

**Step 1 — Ask which mode they want:**
> "Which mode would you like?
> - **Least Qualified** — prefers the lowest-skilled resource that still meets the requirement. Good for preserving senior resources for complex jobs, or keeping costs down.
> - **Most Qualified** — prefers the highest-skilled resource available. Good for first-time fix rates or when outcome quality is the priority."

**If Least Qualified:**
> "Imagine two eligible resources: a junior technician (skill level [S_low]) and a senior technician (skill level [S_high]). The senior tech is closer. In Least Qualified mode, the optimizer prefers the junior tech to preserve the senior for harder jobs. How many extra minutes of travel would you accept to route the junior tech?"

**If Most Qualified:**
> "Imagine two eligible resources: a junior technician (skill level [S_low]) and a senior technician (skill level [S_high]). The junior tech is closer. In Most Qualified mode, the optimizer prefers the senior tech. How many extra minutes of travel would you accept to route the senior tech?"

Presets: "15 extra minutes" (mild), "30 extra minutes" (moderate), "45 extra minutes" (strong).
Math (same formula regardless of mode): `weight_skill_level = T_equiv × weight_travel / (120 × (S_high - S_low))`
Example — Least Qualified (S_low=4, S_high=8, T_equiv=30): `= 30 × 1000 / (120 × 4) = 62.5 → round up to 63`

#### Skill Preference Trade-Off

Background to share:
> "The Skill Preference objective applies when a work order has multiple skill requirements of the same Skill Type and a preference exists for one over another. Each requirement has a Skill Priority from 1 to 10 — 1 = most preferred, 10 = least. The optimizer assigns a penalty proportional to that priority."

Also capture the **Skill Type** (required for this objective to function). Skill Preference operates on one Skill Type — the family of skills (e.g. Language) evaluated by a companion Match Skills rule with "At Least One Skill Matches (OR)." Ask:
> "Which Skill Type does this preference rank within? Give me its Developer Name — it must match a Match Skills work rule set to At Least One Skill Matches (OR), since Skill Preference has no effect under AND matching."

Record as `skillType` param (Skill Type Developer Name, maps to `{ns}Skill_Type__c` on the goal). Flag if no Match Skills rule with OR logic exists for that Skill Type.

> "Imagine a work order where the customer can be served by either a [Skill A]-speaking technician (skill priority [SP_high_pref]) or a [Skill B]-speaking technician (skill priority [SP_low_pref]), but they prefer [Skill A]. The [Skill A] technician is further away. How many extra minutes of travel would you accept to assign the [Skill A] technician?"

Presets: "15 extra minutes" (mild), "30 extra minutes" (moderate), "45 extra minutes" (strong).
Math (T_equiv, SP_high_pref = more preferred, SP_low_pref = less preferred): `weight_skill_preference = T_equiv × weight_travel / (12 × (SP_low_pref - SP_high_pref))`
Example (Spanish priority 1, English priority 6, T_equiv = 45): `= 45 × 1000 / (12 × 5) = 750`

#### Minimize Gaps Trade-Off

*Minimum gap duration was captured in Step 1 as `params.minGapMinutes` (default 30). Don't re-ask it. This section covers the weight math only.*

**If ASAP is selected — Minimize Gaps vs. ASAP:**
> "The optimizer can either: (A) Leave a gap in a technician's schedule and schedule a new appointment [H] hours earlier. (B) Compress the schedule to eliminate the gap, but that appointment gets scheduled [H] hours later. At what scheduling delay would you say 'just leave the gap and schedule earlier'?"

Presets: "leave the gap up to 2 hr later" (weak), "up to 4 hr later" (moderate), "up to 8 hr later" (strong).
Math (delay threshold D_equiv in minutes): `weight_gaps = D_equiv × weight_asap / 43200`
Example (weight_asap = 250, D_equiv = 240 min): `= 240 × 250 / 43200 = 1.389 → ceil to 2`

**If ASAP NOT selected — fall back to travel comparison:**
> "How many extra minutes of travel across the schedule would make it worth leaving a gap in a technician's shift rather than compressing it?"

Presets: "10 extra minutes", "20 extra minutes", "30 extra minutes".
Math: `weight_gaps = T_equiv × weight_travel / 7200`

**Integer-formula validation:** confirm `penaltyPerViolation = max(1, round(1000 × weight_gaps))`. For very small weights (below ~1), warn that the max(1,…) floor clamps the penalty to a fixed minimum.

---

### Step 3: Output the Results

After all trade-off questions are answered, present a table with one row per included objective, showing its **weight** and a one-line **rationale** grounded in the trade-off the user stated (e.g. for ASAP, the "X min travel ≈ Y hours delay" crossover; for Same Site, "1 split ≈ D min of ASAP delay"). Minimize Travel is always the anchor at 1000.

Then describe **relative priority** using penalty points per unit — not raw weights, since the multiplier differs per objective. Compute each rate: Travel `weight_travel / 120` per minute; ASAP `weight_asap / 43200` per minute of delay; Overtime `weight_overtime / 120` per minute; Same Site `weight_same_site × 10` per event (×10, not ×1000); Preferred Resource and Group Nearby `weight × 1000` per event; Resource Priority `weight × (P / 10)` per resource (show a couple priority tiers); Skill Level `S × weight × 100` per resource (show relevant tiers); Skill Preference `weight × (SP / 10)` per skill assignment (show relevant priorities); Minimize Gaps `weight_gaps × 1000` per gap (flat).

Use these rates to explain relative priority in plain English, grounded in the trade-offs the user stated — e.g. "This reflects your stated preference that 30 minutes of travel equals 12 hours of delay." Offer to re-run any trade-off if the implied priority doesn't match expectations.

---

### Policy at a Glance (2–3 sentence business summary)

After presenting the weights and penalty rates, generate a 2–3 sentence business summary of what this policy is optimized for — an executive soundbite for stakeholders who don't care about the math.

**How to generate it:**

1. Classify objectives by category: Customer-experience (ASAP, Same Site, Group Nearby); Cost/efficiency (Minimize Travel, Gaps, Overtime); Workforce/assignment-quality (Preferred Resource, Resource Priority, Skill Level, Skill Preference).
2. Determine which category dominates by comparing penalty rates across objectives — the one generating the largest penalties is the dominant focus.
3. Identify key trade-off tensions from the crossover values stated — these reveal what the policy will sacrifice for what.
4. Write 2–3 sentences naming a primary and secondary focus, what the optimizer prioritizes in plain terms, and what it's willing to sacrifice up to what threshold. If one category's penalties are 5×+ higher, call it out; if two are close, name them co-primary. Only call the policy "Balanced" if all three categories are within ~2× of each other.

Use business language grounded in the user's stated values (e.g. "drive up to 2 hours," "wait up to 24 hours") — not penalty math. This summary is also a good candidate for the scheduling policy record's Description field — suggest it at handoff.

---

## Emit the Build Spec (handoff contract)

The skill's final deliverable and sole contract with `sfs-sobject-create`. Once the design is settled (policy settings, work rules, relevance groups, weights), emit **one** structured build spec as a JSON object. `sfs-sobject-create` consumes it verbatim and never re-derives intent, so it must be complete and self-contained.

**Hard boundary:** emit **design values only** — no Salesforce object names, field API names, record IDs, composite-API reference syntax, or creation ordering (those belong to the data-layer skill). Describe rules/objectives by their canonical type name (exactly as used here: e.g. Match Skills, Minimize Travel, Resource Priority) plus business parameters. Unknown parameter → omit or mark null; never invent an API field name.

```jsonc
{
  "specVersion": "1.0",
  "policy": {
    "name": "scheduling policy name",
    "description": "free text; include the Policy at a Glance summary",
    "inDayOptimization": true,
    "commitMode": "Always Commit | Rollback"
  },
  "workRules": [{
    "type": "canonical work rule type name (e.g. 'Match Skills')",
    "name": "instance display name — see naming convention below",
    "mandatory": false,
    "params": {},   // business params only. e.g. Service Resource Availability absolute break: breaks:[{mode:'absolute',startClock:'12:00',durationMinutes:30}]; offset break: breaks:[{mode:'offset',earliestStartOffsetMinutes:180,latestEndOffsetMinutes:210,durationMinutes:30}]; Maximum Travel from Home: maxTravelFromHome:45, maxTravelFromHomeType:'Travel Time'
    "relevanceGroup": { "basis": "Service Appointment | Service Territory Member | null", "booleanField": "scoping Boolean field name, or null for policy-wide" }
  }],
  "serviceObjectives": [{
    "type": "canonical objective type name (e.g. 'Minimize Travel')",
    "name": "instance display name — see naming convention below",
    "weight": 1000,
    "params": {},   // objective-specific business params. e.g. Skill Level mode:'Least Qualified'; Resource Priority priorityField concept; Minimize Gaps minGapMinutes; Skill Preference skillType; Minimize Travel excludeTravelFromHome/excludeTravelToHome; Same Site useExactLocation
    "relevanceGroup": { "basis": "Service Appointment | Service Territory Member | null", "booleanField": "scoping Boolean field name, or null for policy-wide" },
    "rationale": "one-line human trace of how the weight was derived (the stated crossover)"
  }],
  "prerequisites": ["human-readable notes the user must satisfy before deployment — e.g. 'Create Boolean field Break_Group_France__c on Service Territory Member and set it true for French resources.'"],
  "notes": "caveats, low-weight-floor warnings, or unresolved ambiguities"
}
```

**Rules for emitting:**

1. **Naming convention** (every rule and objective): `name` = canonical type name + abbreviated policy name, separated by `" - "` — e.g. policy "First test on shorter" → "Match Skills - First test", "Minimize Travel - First test". Abbreviate the policy name (drop filler like "on shorter"/"policy"); don't append it verbatim. *Exception:* the two Arrival Window Match Time rules keep their own names — append the abbreviated policy name rather than replacing with the type: "Arrival Window Start - First test", "Arrival Window End - First test".
2. **Always include** Minimize Travel at weight 1000 and exactly one Service Resource Availability rule with `"mandatory": true`, even if never discussed. Never emit Earliest Start Permitted or Due Date.
3. **One instance per subset** — if a rule/objective was split across relevance groups, emit a separate entry per group, each with its own `relevanceGroup`.
4. **Weights are whole numbers**, already ceiling-rounded per the Conversation Flow rules.
5. **Parameters are business values, not field mappings** — "a 30-min break between 12:00 and 15:00" goes in as durations/times; the field mapping lives in the data-layer skill.
6. **Surface prerequisites explicitly** — any relevance-group Boolean field, custom priority field, or skill-type dependency the design assumes goes in `prerequisites` so the user and data-layer skill know it must pre-exist.
7. **Show the spec and get approval before handing off.** Present the complete build spec as a JSON code block and ask plainly whether it looks good (e.g. "Here's the full build spec — does this look right, or would you like to change anything?"). Wait for explicit confirmation; apply requested edits and re-show. Only after approval proceed to handoff.
8. **Don't create anything.** Once approved, tell the user it's ready for `sfs-sobject-create`. If asked to "build/deploy/create it," finalize the spec — don't perform CRUD.

---

## Handoff

When the user confirms the weights and summary, the objective design phase is complete. **Delegate to `sfs-sobject-create`**, passing the build spec above (with the `policy` from `sfs-scheduling-policy-designer`, `workRules` from `sfs-work-rule-designer`, and `serviceObjectives` from this skill) so it can create the scheduling policy, work rules, and service objectives in dependency order.

Do not create records here or start the creation flow — `sfs-sobject-create` owns all Salesforce API calls. Transition message:

> "Objective design is complete. Next, I'll hand off to record creation, which will create all the Salesforce records — the scheduling policy, work rules, and service objectives — in the correct order. Ready to proceed?"
