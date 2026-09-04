---
name: field-service-work-rule-designer-configure
description: "Designs the work rules for a Salesforce Field Service scheduling policy — the hard filters that determine which resources and time slots are eligible for an appointment. Step 2 of the three-part scheduling policy design flow; receives the policy block from sfs-scheduling-policy-designer and delegates to sfs-service-objective-designer when complete. Use this skill when a user wants to design or configure the work rules (hard eligibility filters) for a Field Service scheduling policy."
user-invocable: false
metadata:
  version: "1.0"
  domains: ["Field Service"]
---

# Salesforce Field Service – Work Rule Designer

**Designs the work rules for a scheduling policy.** This skill collects the work rule configuration through a structured interview — one question at a time — and emits a `workRules[]` block as output. It does not create any Salesforce records. When complete, delegates to `sfs-service-objective-designer`.

**Interview phases:** Scheduling Policy → **Work Rules** (this skill) → Service Objectives → Record Creation

---

## Work Rules

**Work rules are hard filters.** They refine the candidate list for a service appointment by rejecting any service resource that violates a rule. They are always applied before service objectives, and objectives only ever score the resources that survive the rules. If a requirement is "must," it's a work rule; if it's "prefer," it's an objective.

### The 16 work rule types

Each row: **name — engine (DB/Apex) — what it does.** "DB w/ ESO" means the rule runs at the database level *only when Enhanced Scheduling and Optimization is enabled*, and as Apex otherwise. Include at least one DB rule to narrow to ~20 candidates before Apex rules run.

| Work Rule | Engine | What it does |
|---|---|---|
| **Service Resource Availability** | Apex — **MANDATORY** | Ensures a resource is actually available: respects operating hours, travel, breaks, absences, and existing assignments. Also enforces capacity for capacity-based resources. Configurable breaks, gaps, overtime, and travel-to/from-home. |
| **Match Time Rule** | Apex | Constrains the scheduling window from an appointment's date/time fields. Ships with standard rules **Earliest Start Permitted** and **Due Date** (both **mandatory**), plus Scheduled Start / Scheduled End (arrival-window based). |
| **Match Skills** | Apex | Matches an appointment's skill requirements to a resource's assigned skills; can enforce skill level. Skill Type Logic is **All Skills Match (AND)** (default) or **At Least One Skill Matches (OR)** (OR requires ESO). |
| **Match Fields** | DB w/ ESO | Matches one appointment field to one resource field (1:1). Use Extended Match instead when comparing one appointment field against multiple resource values. |
| **Match Boolean** | DB w/ ESO | Requires a checkbox field on the resource to be true (or false). **Max 5 per policy.** Ships with standard "Active Resources." |
| **Extended Match** | Database | Custom-criteria matching via a junction object linking an appointment field to a related list on the resource (e.g., serviceable postal codes, product lines). |
| **Match Territory** | Database | Restricts to resources who are primary or relocation members of the appointment's service territory. |
| **Working Territories** | Database | Enforces **primary and secondary** service territory memberships. |
| **Maximum Travel from Home** | Database | Caps distance/travel time between a resource's home base and any assigned appointment. |
| **Required Resources** | DB w/ ESO | Forces assignment to a resource marked **Required** (Resource Preference on the WO/WOLI). Very restrictive. |
| **Excluded Resources** | DB w/ ESO | Prevents assigning a resource marked **Excluded** on the WO/WOLI. |
| **Count Rule** | Apex | Caps assignments, hours, or a custom value per resource per day (e.g., ≤8 scheduled hours, ≤N items on a truck). Time Resolution is **Daily**. Up to 10 custom-field count rules per policy. |
| **Work Capacity** | Apex — **ESO only** | Enforces per-territory Work Capacity Limit records (e.g., cap install work at 80% of territory capacity). |
| **Service Appointment Visiting Hours** | Apex | Enforces customer operating hours / allowed visit windows (e.g., weekdays 8 AM–noon). All-or-nothing rule (no relevance groups). |
| **TimeSlot Designated Work** | Apex | Reserves a time slot/shift for a specific work type — only that type schedules in that window. All-or-nothing rule (no relevance groups). |
| **Service Crew Resources Availability** | Apex | Ensures a crew-type resource is only assigned when the crew meets the parent record's minimum crew size. |

### Interview order — MANDATORY

Walk through the 16 work rule types **in the exact order of the table in *The 16 work rule types* above** — top to bottom, one rule at a time. **Do NOT split the interview into a separate "which rules apply" pass and a later "configure them" pass, and do NOT reorder the rules.** For each rule, in order:

1. **Decide whether it applies.** Service Resource Availability is always in (no question). For every other rule, either the user's stated business needs already make it obviously needed, or ask the short **Applies when / ask** question in that rule's entry below. Interpret the user's needs against the *What it does* column — e.g. "resources need the right skills" → Match Skills; "cap travel from home" → Maximum Travel from Home.
2. **If it applies and it has configuration, ask that rule's config question(s) right now** — before moving on to the next rule. Never defer configuration to the end. If the rule is selection-only (no config), just confirm it and continue.

Then continue to the next rule in the table. Ask one question at a time. Only after you have walked all 16 rules is the rule list final.

**Do NOT ask a relevance-group / subset question on every rule.** Most rules apply policy-wide, and asking "all or a subset?" after each one is noise. Instead:

- **React to scoping the user volunteers.** If while answering a rule's question the user signals the rule is only for a specific scenario, workforce, or work type — e.g. "only for part-time techs," "just for installation jobs," "tighter cap in France" — *then* pursue it: confirm the basis (Service Territory Member for a resource subset, Service Appointment for a work subset), get the Boolean field name, and record `relevanceGroup: { basis, booleanField }` on that rule. (First check the rule supports that basis under ES&O — see *Relevance Groups*.)
- **Otherwise sweep for it once, at the end.** After all 16 rules are walked, ask a single closing question: *"Are there any constraints here that should apply only to a certain part of your workforce or to certain types of work — rather than to everyone/everything? For example, different break or travel limits for part-time vs. full-time techs, or stricter handling for a specific work type or region."* Only if the user says yes do you scope the affected rules (per the *Relevance Groups* section). If no, leave every `relevanceGroup` null.

Always include exactly one **Service Resource Availability** rule — the only mandatory rule this skill emits. Never emit Earliest Start Permitted or Due Date — provisioned automatically.

---

### The rules, in interview order

Take these in the order shown — it matches the table above. For each entry: **Applies when** tells you how to decide it's needed; **Ask** lists the config questions to ask *immediately* on a yes; **Emit** gives the exact `params` keys — use them verbatim so the data-layer skill can map them.

---

**1. Service Resource Availability** *(always present — the only mandatory rule)*
Applies when: always. No applicability question.
Ask:
- "Can work run into **overtime**?" (yes/no)
- "Can resources **travel outside working hours** to/from home?" — if yes, ask how many minutes from home (to first job) and to home (from last job); "no limit" = 120; "no" = 0 for both
- Breaks interview (see *Interpreting and emitting break times* below)

Emit: `{ "enableOvertime": true|false, "travelFromHomeMinutes": <number>, "travelToHomeMinutes": <number>, "breaks": [ … ] }`
Note: Travel values are minutes — 0 = no travel outside working hours, 120 = effectively unlimited. If the user gives no availability detail, emit baseline (`enableOvertime: false`, travel keys and breaks omitted).

---

**2. Match Time Rule** *(arrival windows)*
Applies when: appointments should honor customer **arrival windows** / required arrival times. Ask: "Should appointments honor customer arrival windows?"
Emit: on a yes, emit the **two** default rules from the *Arrival Window Match Time rules* table below — do not ask the user to fill these in.

---

**3. Match Skills**
Applies when: resources need specific skills / proficiency levels.
Ask: "Should the resource also **meet a minimum skill level** (proficiency), or is simply *having* the skill enough?"
Emit: `{ "matchSkillLevel": true|false }`
Note: Do not ask about skill-type AND/OR logic — this skill does not configure `skillTypeLogic`.

---

**4. Match Fields**
Applies when: one appointment field must match one resource field (1:1). (For one appointment field vs. multiple resource values, use Extended Match instead.)
Ask: "Which Service Appointment field must match which Service Resource field, and with what operator?"
Emit: `{ "serviceProperty": "<SA field>", "resourceProperty": "<resource field>", "booleanOperator": "=" }`
Note: Operator is one of `=`, `>=`, `<=`, `>`, `<` (default `=`). Field names are the customer's own — pass through as given.

---

**5. Match Boolean**
Applies when: a checkbox on the resource must be true/false — including non-skill matching factors (e.g., serviceable postal codes).
Ask: "Which checkbox field on the resource must be true (or false)?"
Emit: `{ "resourceProperty": "<resource field>", "value": true|false }`
Note: Max 5 Match Boolean rules per policy.

---

**6. Extended Match** *(advisory only — data-layer skill will not build this)*
Applies when: custom-criteria matching via a junction object (e.g., serviceable postal codes, product lines).
Ask: None — no params to collect. Advise the user to set up before deploying:
1. A junction object with exactly **two** Master-Detail relationships (to Service Resource + matched object) — packaged trigger requires exactly two or the rule fails
2. A Service Appointment Lookup field driving the match; a reference field on the junction matched against it
3. Once those exist, create and configure the rule manually in Setup (Field Service Settings → Scheduling → Work Rules)

Capture intended objects/fields in `prerequisites` as advisory text — do not emit in `workRules[]`.

---

**7. Match Territory** — *(skip entirely; not part of the interview)*
This interview never emits a standalone Match Territory rule. **Skip it silently** — do not ask a Match Territory question, and do not announce or narrate that you are skipping it. Move straight from rule 6 to rule 8 with no mention of Match Territory at all. (If a user explicitly asks for primary/relocation-only territory scoping, advise manual configuration then — but never raise it yourself. Also: don't cover a resource by both Match Territory and Working Territories.)

---

**8. Working Territories**
Applies when: work must be restricted to the resource's **primary and secondary** service territory memberships.
Ask: None — selecting the rule is sufficient.
Emit: `{ "workingLocationEnablePrimary": true }`

---

**9. Maximum Travel from Home**
Applies when: capping distance/travel time between a resource's home and any assigned appointment / controlling travel cost across large territories.
Ask: "Is the cap by **distance** or by **travel time**?" (see the cap-type note below), plus the cap value.
Emit: `{ "maxTravelFromHome": <number>, "maxTravelFromHomeType": "Distance"|"Travel Time" }`
Note: Distance unit (miles vs km) is not part of the rule — governed by org locale. For Travel Time, value is minutes.

---

**10. Required Resources** *(selection-only)*
Applies when: any work order ever has a resource marked **Required** that must always be assigned. Ask: "Do any work orders ever have a specific resource marked *Required* that must always be assigned to that job?"
Emit: `{}`
Prerequisite: Resource Preference records must exist on the work order / WOLI — the rule enforces them but does not create them.

---

**11. Excluded Resources** *(selection-only)*
Applies when: any work order ever has a resource marked **Excluded** that must never be assigned. Ask: "Do any work orders ever have a resource marked *Excluded* that must never be assigned?"
Emit: `{}`
Prerequisite: Resource Preference records must exist on the work order / WOLI — the rule enforces them but does not create them.

---

**12. Count Rule**
Applies when: capping the number/duration of appointments (or a custom value) per resource per day.
Ask: Have the user describe the limit in plain terms, then classify into:
- `countBy` — `"Appointments"` (count of jobs), `"Hours"` (duration cap), or `"Custom"` (sum of a custom SA field)
- `maxValue` — the numeric cap (for Hours, convert to hours)
- `fieldHint` — the SA field to sum; `null` for a plain Appointments count

Emit: `{ "countBy": "Appointments"|"Hours"|"Custom", "maxValue": <number>, "fieldHint": "<SA field>"|null }`
Note: Time Resolution is always Daily; counted object is always Service Appointment — data-layer skill sets both automatically. Up to 10 custom-field count rules per policy. When countBy is Custom or Hours against a field, add prerequisite: "Confirm field `<fieldHint>` exists on Service Appointment."

---

**13. Work Capacity** *(ESO only — selection-only)*
Applies when: Work Capacity Limit records cap how much work schedules per territory. Ask: "Do you use Work Capacity Limit records to cap how much work can be scheduled per territory?"
Emit: `{}`
Prerequisite: WorkCapacityLimit records must be configured per territory outside the policy.

---

**14. Service Appointment Visiting Hours** *(selection-only)*
Applies when: customers have allowed visit windows that should block scheduling outside those hours. Ask: "Do customers have allowed visit windows (e.g., weekdays only, or mornings only) that should block scheduling outside those hours?"
Emit: `{}`
Note: Do not ask for the windows — they are per-account data on OperatingHours records, not a policy-wide value. All-or-nothing rule — no relevance-group scoping.
Prerequisite: Each account must have visiting/operating hours populated; the Work Order's Visiting Hours must resolve from the account.

---

**15. TimeSlot Designated Work** *(selection-only)*
Applies when: certain time slots must be reserved for specific types of work. Ask: "Do you need to reserve certain time slots for specific types of work (e.g., install work only in morning slots)?"
Emit: `{}`
Note: Do not ask for slot→work mappings — that is data setup. Phrase the selection as "types of work," not "Work Type" (the designation is broader than the Work Type object). All-or-nothing rule — no relevance-group scoping.
Prerequisite: Time slots must be configured to designate the intended work.

---

**16. Service Crew Resources Availability**
Applies when: crew-type resources must only be assigned when the crew meets the parent record's minimum crew size.
Ask:
- "Should the rule evaluate individual crew members' availability and skills, not just the crew record?" → `considerCrewMembership`
- "What is the maximum number of extra resources beyond the base crew that can be pulled in?" → `maxAdditionalResources` (optional)

Emit: `{ "considerCrewMembership": true|false, "maxAdditionalResources": <number> }` (omit `maxAdditionalResources` if blank)

---

### Configuration reference notes

These deep-dives support the **Ask** lines above; consult them when configuring the rule that references them.

**Arrival Window Match Time rules (default pair — rule 2).** When the user confirms appointments should honor customer arrival windows, emit **two** Match Time rules with these exact default settings — do not ask the user to fill these in, they are the standard arrival-window configuration:

| Setting | Rule A | Rule B |
|---|---|---|
| Name | `Arrival Window Start` | `Arrival Window End` |
| Service Schedule Time Property | `SchedStartTime` | `SchedStartTime` |
| Service Time Operator | `Later than or Equal to` | `Before or Equal to` |
| Service Time Property | `ArrivalWindowStartTime` | `ArrivalWindowEndTime` |
| Pass Empty Values | `true` | `true` |

Emit each as a Match Time work rule whose `params` carry those four values (keys `serviceScheduleTimeProperty`, `serviceTimeOperator`, `serviceTimeProperty`, `passEmptyValues`). These are separate from the mandatory Earliest Start Permitted / Due Date rules (never emitted).

**Interpreting and emitting break times — clock time vs. shift-start offset (rule 1).** A Service Resource Availability rule expresses breaks in one of two shapes, and **this skill decides the shape and emits the values the data-layer skill needs** — the data-layer skill never receives a clock time it has to convert. Choose the shape as follows:

- **One fixed daily break at an absolute clock time** (e.g. "30 minutes at 12:00 every day") → emit it as an **absolute** break: `{ "mode": "absolute", "startClock": "12:00", "durationMinutes": 30 }`. No offset math, no working-day start needed.
- **One or more breaks defined as an offset from the start of the working day** (e.g. "a 30-minute lunch starting 3 hours into the shift") → emit each as an **offset** break, in **minutes from the start of the working day**: `{ "mode": "offset", "earliestStartOffsetMinutes": 180, "latestEndOffsetMinutes": 240, "durationMinutes": 30 }`. All three of `earliestStartOffsetMinutes`, `latestEndOffsetMinutes`, and `durationMinutes` are **mandatory** for an offset break. **When the user states the break in offset terms already** (e.g. "3 hours after the start of day"), that offset *is* `earliestStartOffsetMinutes` (180) — **do not ask for the working-day start; you don't need it.**
- **Breaks given as clock times but there is more than one** (e.g. "15 minutes at 10:00 and 30 minutes at 12:00") → you must use the **offset** shape, which means **converting each clock time into an offset from the start of the working day**. You cannot do that without knowing when the day starts, so **ask the user for the shift / working-day start**, then compute `earliestStartOffsetMinutes = (break start clock − day start)` in minutes for each break. Never assume the day starts at midnight (that would turn "10:00" into a wrong 600-minute offset). *(Only ask for the day start in this clock-time case — never when the break is already expressed as an offset.)*

**Always emit `latestEndOffsetMinutes` for every offset break — ask for it directly, do not fabricate a window.** The earliest start comes from what the user stated (an offset, or a converted clock time) — **do not invent ± tolerance windows around it** (no "±1 hour" / "±2 hour" options). If the user only gave a break start (or a duration with no stated finish-by), **ask them plainly for the latest the break may end**, phrased in the *same terms they used*: if they gave an offset ("starts 3 hours after start of day"), ask "what is the latest it may end, as time after the start of the day?" and convert (e.g. "4 hours after start" → 240); if they gave a clock time, ask for a clock time and convert with the day start. If the user says the break is fixed/pinned with no flex, set `latestEndOffsetMinutes = earliestStartOffsetMinutes + durationMinutes`. Never emit an offset break missing any of the three fields, and never guess the latest-end. If a break requirement is too involved to convert reliably, ask clarifying questions or recommend the manual approach rather than guessing.

**Maximum Travel from Home — establish the cap type, not the unit (rule 9).** When a requirement caps how far a resource may travel from home, **ask the user whether the cap is by distance or by travel time** — the two are configured differently and the data-layer skill needs to know which. Emit the value and the type in `params`: `{ "maxTravelFromHome": 50, "maxTravelFromHomeType": "Distance" | "Travel Time" }`. Interpret the user's phrasing to set the *type* — "50 miles"/"50 km" ⇒ `Distance`, "45 minutes" ⇒ `Travel Time` — but **do not ask for or emit a distance unit (miles vs km): it is not part of the work-rule config**; the unit is governed by the org's locale/distance settings elsewhere, so the rule stores only the number. For `Travel Time` the value is minutes. Never emit the cap value without its type.

---

## Relevance Groups

A relevance group scopes a single work rule or service objective so it applies only to certain appointments or resources, instead of the whole policy. This lets one policy hold different logic for different work or resource types — e.g., different break/travel limits for part-time vs. full-time employees, or expedited scheduling for high-value accounts.

### How it works, and the division of labor

A relevance group is driven by a Boolean (true/false) field. Every standard or custom Boolean field on the Service Appointment and Service Territory Member objects is selectable in the rule/objective's Relevance Group dropdown. On a work rule or objective, you pick the limiting Boolean field; the rule/objective then applies only to records where that field is true. The two bases are just the two objects the Boolean can live on:

- **Service Appointment basis** — scopes by the appointment being evaluated (e.g., a formula checkbox "Platinum Account" that's true when the related account tier is Platinum). Use to target appointment types.
- **Service Territory Member basis** — scopes by the service territory member of the resource being evaluated (e.g., "Part-Time" / "Full-Time" checkboxes). Use to target resource populations. Only primary and relocation memberships are supported — not secondary.

In the design: decide the basis (Service Appointment vs. Service Territory Member) and the name of the Boolean field that identifies the subset, then record both on the rule/objective in the build spec (`relevanceGroup: { basis, booleanField }`). This skill only decides which field scopes which rule/objective — wiring the group onto the record is the data-layer skill's concern.

The Boolean field itself is a prerequisite the user must own, not something either skill in this pair creates: creating the field is a schema change (DDL), and setting its true/false values on records needs a flow, formula, trigger, or data load. So advise the user to, before deploying: (1) create one custom Boolean field on the appropriate object (Service Territory Member for a resource subset, Service Appointment for a work subset) per subset; (2) populate it true for exactly the records in that subset (via flow/formula/import), keeping subsets mutually exclusive where the rule type requires it. Then reference that field by name in the build spec so the data-layer skill can attach it as the relevance group.

### Worked example (the canonical pattern)

To apply a Match Boolean rule (or any scoping) to only certain appointment types: identify (or have the user create) a Boolean field on the Service Appointment that is true for those appointments, and name it as the rule's relevance group in the build spec. The rule then applies only to appointments where the field is true. The same pattern with a Service Territory Member Boolean (e.g., Part-Time vs. Full-Time) lets you design two copies of the Maximum Travel from Home rule with different limits — one scoped to part-timers, one to full-timers.

For objectives, the classic example is combining ASAP with a relevance group: a formula checkbox "Platinum Account" on the appointment, an ASAP objective named "Expedite Platinum Accounts" scoped to it with a high weight, so platinum jobs schedule sooner (accepting more travel). Give scoped high-priority objectives a clearly higher weight, or the engine may prefer not to schedule the appointment at all because of its ASAP penalty.

### Scoping any rule or objective to a subset (the general rule)

This applies to every work rule and every service objective — not just breaks or availability. Whenever a request says a rule or objective should apply to only certain resources or only certain work, rather than the whole policy, the mechanism is a relevance group. Watch for this signal and reach for it every time:

- "…applies to certain types of resources" (e.g. "resources in France", "part-time techs", "senior engineers", "the install crew") → create a Service Territory Member relevance group: a Boolean field on Service Territory Member that is true for exactly those resources, selected as the rule/objective's relevance group.
- "…applies to certain types of work" (e.g. "installation jobs", "platinum-account appointments", "emergency work orders", "jobs over 2 hours") → create a Service Appointment relevance group: a Boolean field on Service Appointment that is true for exactly those appointments, selected as the rule/objective's relevance group.

Always check whether the specific rule/objective supports the basis you need. Not every rule/objective can be scoped by Service Territory Member, and not every one can be scoped by Service Appointment. Before recommending a relevance group, verify the relevance-group support matrix for that exact rule or objective — consider only Enhanced Scheduling & Optimization (ES&O) support and ignore the legacy/non-Enhanced columns. If the needed basis isn't supported for that rule/objective under ES&O, say so and suggest the closest supported alternative instead of inventing one.

When two subsets each need a different configuration of the same rule/objective, design one instance per subset — never one merged instance. A single rule/objective instance applies to every record it covers, so you cannot express "France gets pattern A, everyone else gets pattern B" in one instance. Instead specify one instance per subset, each scoped by its own distinct Boolean field, and keep the groups mutually exclusive (for single-coverage rule types like Service Resource Availability, an overlap throws an error — see *Key rules and gotchas*). Example: "Resources in France get a 15-minute break at 10 AM and a lunch between 12 and 2; all other resources get a 30-minute break between 12 and 3" needs two Service Resource Availability rules — "Availability – France" scoped to a `Break_Group_France__c` STM checkbox, "Availability – Standard" scoped to a `Break_Group_Standard__c` STM checkbox — each carrying only its own group's breaks, with every resource landing in exactly one group.

When the scenario is genuinely too complex, recommend a manual design. If a request combines multiple subsets, ambiguous values, and relevance-group fields that don't exist yet, don't force a single merged instance into the spec. Walk the user through the relevance-group design above and let them refine it (or spec only the parts that are unambiguous), rather than emitting a plausible-looking but wrong merged rule/objective. Prefer asking clarifying questions (which subset? resources or work? what Boolean field identifies each? is that basis supported for this rule/objective under ES&O?) over guessing.

### Key rules and gotchas

- **Relevance groups must be mutually exclusive.** If two rules with relevance groups overlap, the more restrictive one wins — and for Service Resource Availability, an overlap throws an error. Each resource must be covered by exactly one Service Resource Availability rule.
- **Additive rule types** — can appear multiple times and legitimately cover the same resources/appointments: Count Rule, Extended Match, Match Boolean, Match Fields, Match Time.
- **Single-coverage rule types** — a resource/appointment must be covered by at most one instance at a time: Match Skills, Match Territory, Maximum Travel from Home, Required Resources, Service Crew Resource Availability, Service Resource Availability, Working Territories. (Also: don't cover a resource by both Match Territory and Working Territories at once.)
- **All-or-nothing rules — no relevance groups:** TimeSlot Designated Work and Service Appointment Visiting Hours. Also Work Capacity doesn't support relevance groups.
- **Objectives** can be repeated with relevance groups too, but a record must not meet the criteria for two objectives of the same type at once — except Resource Priority, which can legitimately apply twice to the same appointments if each instance points to a different resource priority field (e.g., "Primary Priority" and "Secondary Priority"/"Tenure").
- Support for whether a rule/objective can be scoped by appointment vs. territory member differs between the Enhanced and non-Enhanced engines — verify the support tables when scoping. Group Nearby and Same Site objectives do not support relevance groups at all.

---

## Output

Once all rules are confirmed, emit the `workRules[]` block and show a plain-English summary — rule name, what it filters, any key parameters. Ask the user to confirm before delegating.

The `workRules[]` block carried forward to the next step:

```json
{
  "workRules": [
    {
      "type": "<rule type>",
      "name": "<policy name> - <rule label>",
      "mandatory": true | false,
      "params": { ... },
      "relevanceGroup": { "basis": "ServiceAppointment" | "ServiceTerritoryMember", "booleanField": "<field API name>" } | null
    }
  ],
  "prerequisites": [ "<advisory text for items the user must set up manually>" ]
}
```

---

## Handoff

When the user confirms the work rules, delegate to `sfs-service-objective-designer`. Pass both the `policy` block and the `workRules[]` block as context — the objective designer uses the selected rules to contextually surface relevant objectives (e.g., Match Skills selected → suggest Skill Level and Skill Preference objectives).

Do not start the service objective interview here. Transition message:

> "Work rules are locked in. Next: service objectives — the scoring criteria that rank the eligible candidates. I'll walk through the trade-off questions one at a time."
