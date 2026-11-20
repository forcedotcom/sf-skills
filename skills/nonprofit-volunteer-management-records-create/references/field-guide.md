# Volunteer Management Record Creation — Field Guide

The field reference for creating Volunteer Management records: which fields exist, what each
means when creating a record, which to set (the tiers below), and their defaults. This file covers
how to fill fields; what an object means and how the model connects is in
`nonprofit-volunteer-management-model-get`.

## Where field facts come from

- **Standard fields** (API names, required flags, tiers, meaning) come from **this file**. Never
  describe an object to learn its standard fields, and don't make "checking the standard fields" a
  visible step.
- **A description is used for three things:** required **custom** fields the org added, **live
  picklist values**, and grounding a fix for a write error. When a description is in hand and
  differs from this file (an admin-renamed label, a picklist value, a required flag), the
  description wins; API names don't change on a rename, labels do.
- **If the user declines the read**, this file alone still covers every standard field. Required
  custom fields and bad picklist values then surface as write errors and are fixed in SKILL.md
  step 9.
- **Query only fields this file documents.** A column that isn't in an object's table doesn't
  exist for this skill — e.g. Operating Hours has no `Type` field, and selecting one fails the
  whole query with `INVALID_FIELD`.
- **Every reuse query is bounded** to the planned records (`Name IN (…)`, or `Name LIKE` a
  distinctive stem when the org may word it differently, e.g. `Name LIKE '%Forklift%'`). Never
  read a whole object. Reuse keys:
  - Volunteer Initiative, Location, Competency, Examination, Position: `Name`.
  - Job Position: `Name` + `VolunteerInitiativeId`.
  - Operating Hours: `TimeZone` + the set of Time Slot windows (`DayOfWeek` + `StartTime` +
    `EndTime`). Never the name.
  - Job Position Shift: `JobPositionId + StartDate + EndDate + StartTime + EndTime`.

  The calls, and the apostrophe rule, are in `references/mcp-invocation.md`.

## Tiers

The tier codes are internal; the user sees "required", "recommended" or "optional".

| Tier | Meaning | Action |
|------|---------|--------|
| **T1** | Always set | Every record needs it (required, or an identifier/relationship without which the record is invalid or useless). |
| **T2** | Set by default; explain if skipping | Set it unless the user opts out, and say what skipping costs. |
| **T3** | Set only if the program calls for it | Leave blank unless the plan or the user needs it. |
| **T4** | Never set — system-managed | Filled by the platform, a formula, an auto-number or a Data Processing Engine; writing it errors or is overwritten. |
| **T5** | Never mention | Belongs to another feature; irrelevant to creation. |

**Fill what's known; ask before inventing.** Fill values the plan or the user already gave. For a
field with no established value, propose one and ask; never invent a value the user didn't give.
Status may be proposed as `Upcoming`. **Location Type has no default and is always asked** (or
copied from the paired Location on an Address).

**`Description` (every object) — summarize from context.** Summarize what you already know about
that record (the plan on a chained run, or the conversation). When there's nothing record-specific,
leave it blank. That's why Volunteer Initiative and Position carry `Description` at T2 (a headline
record almost always has context) and every other object at T3.

**`Req` vs `Tier` differ on purpose.** `Req` is what the platform rejects when blank; `Tier` is what
this skill fills anyway. A shift with no `StartDate` is useless, so it is T1 though `Req: No`.

## Picklists

Read every picklist's values from the object description at run time; never assume a set, because
admins change them. Offer every active value.

- **Platform picklists** (Time Zone, Time Slot Day of Week and Type): the values are fixed. A value
  outside them is rejected before the write, never sent.
- **Every other picklist:** if no live value fits, ask whether to add one. Adding a value needs its
  own yes from the user (`references/mcp-invocation.md` → Adding a picklist value): on headless-360
  the user adds it in Setup, on the Salesforce CLI you add it for them. A value that isn't in the
  list yet is rejected on write, so add it first.

---

## Creation scope

This skill creates the **program structure**. The tables below cover every object it writes.
Per-person and operational records (assignments, availability, a person's qualifications, rollups)
are out of scope — see [Out of scope](#out-of-scope--never-created).

### VolunteerInitiative — the program container (top of the graph)

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `Name` | Text (Name) | Yes | **T1** | The name of the program — the top-level initiative its job positions, shifts, and assignments roll up under. | — |
| `Status` | Unrestricted picklist | No | **T2** | The lifecycle status of the program. | Propose `Upcoming` for a new program. |
| `Description` | Text(255) | No | **T2** | A description of the program. | Set by default; summarize from context. |
| `StartDate` | Date | No | T3 | The date the program's volunteering starts. | Optional; set together with `EndDate` for a bounded program. |
| `EndDate` | Date | No | T3 | The date the program's volunteering ends. | Optional; set alongside `StartDate` for a bounded program. |
| `IsPublished` | Boolean | No | T3 | Whether the program is visible to volunteers in an Experience Cloud site (default `false`). | Nothing out of the box publishes it — set only if publishing now. |
| `ParentVolunteerInitiative` (`ParentVolunteerInitiativeId`) | Lookup → VolunteerInitiative | No | T3 | The parent program in the initiative hierarchy — engagement rollups aggregate up to parents (max 5 levels, max 1000 child relations). | Write the parent first, then the children in a second call with the parent's **literal Id** — a `@refId` to another Volunteer Initiative in the same call fails with `MALFORMED_ID`. |
| `TotalVolunteerHours`, `TotalActiveVolunteerCount`, `AttendanceRate`, `OpenAssignmentCount`, `FilledAssignmentCount`, `TotalAssignmentCount` | Number | No | **T4** | Data Processing Engine engagement rollups — hours volunteered, active volunteers, attendance rate, and open/filled/total assignment counts. | Empty containers until you build the automation; writing them is meaningless/overwritten — never set. |

### Location — the physical/virtual site

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `Name` | Text (Name) | Yes | **T1** | The name of the site where the volunteer work happens — what job positions link to and matching compares against. | — |
| `LocationType` | Unrestricted picklist | Yes | **T1** | The kind of site. | **No default — always ask.** Offer the live values; if none fits, offer to add one. |
| `TimeZone` | Platform picklist (IANA) | No | **T2** | The site's time zone — it feeds the shift and Operating-Hours time zones used in time-based matching. | Set by default when shifts/matching are time-based — it feeds the shift and Operating-Hours time zones; skipping it breaks time-correct scheduling. |
| `VisitorAddress` (`VisitorAddressId`) | Lookup → Address | No | **T2** (new site) | A lookup to the site's postal `Address` record. | A Location has **no inline postal fields**, so the street address lives in a paired `Address`: create the **Location first**, then the Address, then back-fill this lookup. See the **Address** entity below for the fill policy and the 3-step circular write. |
| `Description` | Text | No | T3 | A brief description of the site. | Summarize from context; leave blank if none. |

Query for an existing Location by name and reuse it before creating one. A virtual Location has no Address.

### Address — the paired postal address for a Location

Every **new onsite** Location gets a paired `Address`; that's where the street address lives
(`Location` itself has none). A virtual Location gets none unless the user asks. A **reused**
Location: read its `VisitorAddressId` — if it's set, the Location already has an Address, so don't
create one; if it's empty, offer one.

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `Parent` (`ParentId`) | Master-detail → Location | Yes | **T1** | The site (Location) this address is the postal address for. | Set to the paired Location's **literal Id**. Master-detail, so it can't be moved to another Location later. See the 3-step write below. |
| `LocationType` | Unrestricted picklist | Yes | **T1** | The kind of site — mirrors the paired Location's type. | Required, **no default** — **copy the paired Location's `LocationType`**; it must come from the Location, never assumed. |
| `Street`, `City`, `State`, `PostalCode`, `Country` | Text | No | **T1** (user-supplied) | The site's postal address — the reason this record exists (a Location has no inline street fields). | **Ask the user; never fabricate.** Populate whatever they give; a sub-field they omit stays blank. |
| `AddressType` | Unrestricted picklist | No | **T2** | The kind of address. | Offer the live values; if none fits, offer to add one or leave it blank. |
| `TimeZone` | Platform picklist (IANA) | No | **T2** | The site address's time zone. | **Copy the Location's `TimeZone`** — matters for organizations spanning zones. |
| `Description` | Text | No | T3 | A brief description of the site's address. | Summarize from context; blank if none. |
| `Latitude`, `Longitude` | Double | No | T3 | The geographic coordinates of the site's address. | Copy from the Location **only if** it carries geo values; else skip. |
| `DrivingDirections` | Text | No | T3 | Directions to the site. | Copy from the Location if present. |
| `GeocodeAccuracy` | Picklist | No | **T4** | The accuracy level of the site address's geocode. | Geocoding-managed system value — never hand-set. |

**3-step write.** `Address.ParentId` → Location is required and `Location.VisitorAddressId` →
Address points back, so one call can't create the pair. **(1)** Write the **Location** (no
`VisitorAddressId`); **(2)** write the **Address** with `ParentId` = the Location's literal Id;
**(3)** update the Location's `VisitorAddressId` to the Address's Id. Calls in
`references/mcp-invocation.md`.

### OperatingHours — an availability schedule (matching)

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `Name` | Text (Name) | Yes | **T1** | The name of the availability schedule — the set of weekly windows (its TimeSlots) a volunteer's availability is matched against. | Time zone + a short window-set descriptor — see *Naming* below. |
| `TimeZone` | Platform picklist (IANA) | Yes | **T1** | The time zone the schedule's TimeSlots are read in; matching uses it to align a volunteer's availability with shift times. | Required and **not safely defaultable** — ask (or take from the Location's time zone). |
| `Description` | Text | No | T3 | A description of the schedule. | Summarize from context; blank if none. |

**Create Operating Hours and Time Slots only when the user explicitly asks.** Nothing links them
to a Location or Job Position; a volunteer's own availability record (out of scope) points at them
at runtime.

**Reuse.** One Operating Hours can serve many volunteers. Before creating one, query for an
existing Operating Hours with the same `TimeZone` and the same set of Time Slot windows, and reuse
it. The name never decides reuse.

**Naming.** Time zone + a short window-set descriptor (`America/Los_Angeles — Mornings`,
`America/New_York — Weekends`), so schedules that share a time zone stay distinct. A site label
(`Raceway Hours`) is fine as a human-readable tag, but the name never binds the record to a site.
Use a bare time-zone name only when that zone has a single schedule.

### TimeSlot — a weekly availability window (child of OperatingHours)

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `OperatingHours` (`OperatingHoursId`) | Master-Detail → OperatingHours | Yes | **T1** | The availability schedule this window belongs to. | Set to the parent's **literal Id**. **Write the Operating Hours first, then its Time Slots in a second call.** |
| `DayOfWeek` | Platform picklist | No | **T1** | The day of the week the volunteer is available (`Sunday`…`Saturday`). | Defaults to `Sunday` when unset — rarely the intended day, so **ask**. |
| `StartTime` | Time | Yes | **T1** | The time the availability window starts. | No default — ask. |
| `EndTime` | Time | Yes | **T1** | The time the availability window ends. | Must be ≥ `StartTime`. No default — ask. |
| `Type` | Platform picklist | No | T3 | The kind of time slot (`Normal` or `Extended`). | Defaults to `Normal`; Volunteer Management doesn't use it — skip unless the user asks for `Extended`. |
| `TimeSlotNumber` | Auto-number | System | **T4** | The record's auto-generated name (autonumber mask `TS-{0000}` — e.g. `TS-0001`). | Platform-assigned (`createable=false`); never set. |

**No duplicate windows.** Within an OperatingHours, don't create a TimeSlot that duplicates an
existing window (same `DayOfWeek` + `StartTime` + `EndTime`). Reuse the parent OperatingHours and
its existing TimeSlots instead of re-creating an identical set.

### Position — reusable role template (optional)

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `Name` | Text (Name) | Yes | **T1** | The name of the reusable role template that postings are created from. | — |
| `Status` | Unrestricted picklist | No | **T2** | The status of the role template. | Propose `Upcoming`. |
| `Description` | Text(255) | No | **T2** | A description of the role. | Set by default. |
| `IsInternalApprovalRequired` | Boolean | No | T3 | Whether volunteer signup for postings that use this role requires internal approval (default `false`). | Does nothing until the customer sets up an Approval Process. |
| `Type` | Unrestricted picklist | No | T3 | The type of role. | Skip unless the org has values or the user asks to add one. |
| `Code` | Text | No | T3 | A short code for the role. | — |

Create a Position when a role is shared across postings or programs, including the same role posted at several Locations. Put a qualification every posting of that role needs on the Position once, not on each Job Position.

### PositionQualification — a requirement on the template

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `Position` (`PositionId`) | Master-Detail → Position | Yes | **T1** | The role template this requirement belongs to; matching checks it for every Job Position that uses the Position. | Set to the Position's literal Id — write the Position first. |
| `QualificationReferenceRecord` (`QualificationReferenceRecordId`) | Lookup {Competency, Examination} | Yes | **T1** | The Competency or Examination a volunteer must have to fill the role. | Matching uses only Competency requirements; an Examination requirement is informational. |
| `QualificationLevel` | Integer | No | **T2** | The qualification level the role requires — matching compares a volunteer's level against it. | Set it whenever matching is wanted: a Competency requirement without a level is skipped by matching. |
| `ProficiencyLevel` | Unrestricted picklist | No | T3 | A descriptive proficiency label for the requirement. | Not used in matching. |

### JobPosition — a concrete posting (role × site)

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `Name` | Text (Name) | Yes | **T1** | The name of the posting volunteers browse and sign up for. | — |
| `Title` | Text(255) | Yes | **T1** | The title of the posting. | Also required — **both `Name` and `Title` must be set.** Can hold the same value or differ (e.g. an internal-facing name vs. an external/public one). |
| `Status` | Unrestricted picklist | No | **T2** | The lifecycle status of the posting. | Propose `Upcoming`. |
| `Location` (`LocationId`) | Lookup → Location | No | **T2** | The site where this posting's work happens. | Optional; set it when the work has a site — it drives time and place matching. |
| `VolunteerInitiative` (`VolunteerInitiativeId`) | Lookup → VolunteerInitiative | No | **T2** | The parent program this posting rolls up to. | **API name is `VolunteerInitiativeId`** (label "Related Volunteer Initiative") — *not* `RelatedVolunteerInitiative` (that field is on JobPositionAssignment). |
| `Position` (`PositionId`) | Lookup → Position | No | T3 | The reusable role template this posting is created from. | Only when a Position template is in use. Its qualifications are checked by matching; nothing is copied. |
| `Description` | Text Area(255) | No | T3 | A description of the posting shown to volunteers. | Summarize from context; blank if none. |
| `StartDate` / `EndDate` | Date | No | T3 | The posting's active window. | — |
| `Manager` (`ManagerId`) | Lookup → Account | No | T3 | The posting's manager (an Account). | — |
| `Code` | Text(255) | No | T3 | A short code for the posting. | — |
| `LastFilledDate` | Date | No | T3 | The date the posting was last filled. | Nothing fills it automatically. A new posting hasn't been filled, so leave it blank unless the user gives a date. |

### JobPositionQualification — a posting-specific requirement

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `JobPosition` (`JobPositionId`) | Master-Detail → JobPosition | Yes | **T1** | The posting this requirement applies to. | Set to the Job Position's literal Id — write the Job Position first. |
| `QualificationReferenceRecord` (`QualificationReferenceRecordId`) | Lookup {Competency, Examination} | Yes | **T1** | The Competency or Examination this posting requires, in addition to its Position's requirements. | Matching uses only Competency requirements; an Examination requirement is informational. Ask. |
| `QualificationLevel` | Integer | No | **T2** | The qualification level this posting requires — matching compares a volunteer's level against it. | Set it whenever matching is wanted: a Competency requirement without a level is skipped by matching. |
| `ProficiencyLevel` | Unrestricted picklist | No | T3 | A descriptive proficiency label for the requirement. | Not used in matching. |
| `Description` | Text(255) | No | T3 | A description of the requirement. | From context; blank if none. |

Matching uses QualificationLevel on Competency qualifications. A Job Position's own qualifications and its Position's qualifications are checked together, keeping the higher level per Competency. Nothing is copied from the Position to the Job Position — don't add a Job Position Qualification that repeats one on its Position.

### JobPositionShift — a dated, time-bounded slot

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `JobPosition` (`JobPositionId`) | Lookup → JobPosition | Yes | **T1** | The posting this shift is a dated, time-bounded slot of. | Set to the Job Position's literal Id. |
| `StartDate` | Date | No | **T1** | The date the shift takes place. | **No `StartDateTime` field exists** — date and time are separate. Ask. |
| `EndDate` | Date | No | **T1** | The shift's end date. | Equal to `StartDate` on a same-day shift; **later when the shift crosses midnight or spans days** (StartDate/EndDate are independent DATE fields). |
| `StartTime` | Time | No | **T1** | The time the shift starts. | — |
| `EndTime` | Time | No | **T1** | The time the shift ends. | Must be after `StartTime` **only on a same-day shift** (`EndDate == StartDate`); when the shift ends on a later `EndDate` the end time may be earlier (e.g. 23:00 → 03:00 next day). |
| `TimeZone` | Platform picklist (IANA) | No | **T1** | The shift's time zone. | No safe default — take it from the Location, or ask. |
| `Status` | Unrestricted picklist | No | **T2** | The lifecycle status of the shift. | Propose `Upcoming`; `scripts/expand-series.py` writes `Upcoming` when the spec has no `status`. |
| `MaximumAttendeesCount` | Integer | No | T3 | The maximum number of volunteers for the shift. | Set when the shift has a headcount limit. Capacity is counted, never enforced — blocking a full shift needs a customer validation rule. |
| `Description` | Text(255) | No | T3 | A description of the shift. | Summarize from context; blank if none. |
| `Name` | Auto-number | System | **T4** | The record's auto-generated name (autonumber mask `JPS-{0000000000}` — e.g. `JPS-0000000001`). | Platform-assigned (`createable=false`); never set. |
| `PositionAssignmentCount` | Integer | No | **T4** | The number of volunteers assigned to the shift. | Maintained by the platform as assignments are added — never set. |
| `RemainingCapacity` | Formula | No | **T4** | The remaining open spots on the shift. | Formula: when both counts are set and the maximum is above 0, `MAX(0, MaximumAttendeesCount − PositionAssignmentCount)`; otherwise blank. Never set. |
| `RecurrenceSchedule` (`RecurrenceScheduleId`) | Lookup → RecurrenceSchedule | No | **T5** | A lookup to the recurrence schedule the shift belongs to. | Owned by Volunteer Management's own recurrence feature — never create or link; write one shift per occurrence instead. |

Bound every series with an end date or a count (`count` in `scripts/expand-series.py`); never an open-ended set.

### Competency — a skill a qualification can require

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `Name` | Text (Name) | Yes | **T1** | The competency name — what qualifications and matching point at. | Ask. |
| `Category` | Unrestricted picklist | No | T3 | The category of the competency. | Skip unless the org has values or the user asks to add one. |
| `Description` | Text Area(1000) | No | T3 | A description of the competency. | From context; blank if none. |

Query for an existing Competency by name and reuse it before creating one.

### Examination — a credential a qualification can require

| Field | Type | Req | Tier | Meaning | Policy |
|-------|------|-----|------|---------|--------|
| `Name` | Text (Name) | Yes | **T1** | The examination or credential name. | Ask. |
| `Status` | Unrestricted picklist | No | T3 | The status of the examination. | Optional; offer the live values. |
| `Description` | Text Area(255) | No | T3 | A description of what the credential verifies. | From context; blank if none. |

Examinations are not used in matching; query for an existing one by name and reuse it before creating one.

---

## Out of scope / never created

Created at runtime or during volunteer onboarding, or part of the person data model Volunteer
Management builds on. This skill never writes them; if the user asks, say so.

| Entity | Why it's not created here |
|--------|---------------------------|
| `RecurrenceSchedule` | Volunteer Management's own recurrence feature owns it; write discrete `JobPositionShift` records instead. |
| `JobPositionAssignment` | A person doing a shift — operational, created when a volunteer signs up. |
| `PersonLocationAvailability` | A volunteer's own availability (ties a Location + OperatingHours) — set during onboarding. |
| `PersonCompetency` / `PersonExamination` | A person's own qualifications — recorded per volunteer. |
| `ConstituentRole` | Marks a Person Account as a volunteer — per-person onboarding. |
| `DonorGiftSummary` | A Data Processing Engine rollup target, not authored directly. |
| `Account` / `Person Account` | The volunteer themselves — a person record created during onboarding, not by program-structure setup. |
| `PartyRelationshipGroup` | Designates an Account as a household — person data model. |
| `AccountAccountRelation` / `AccountContactRelation` / `ContactContactRelation` | Relationship links between people and organizations — person data model. |

---

## Creation limits & validation rules

Enforce/respect these when generating the graph:

- **Volunteer Initiative hierarchy:** max 5 levels of `ParentVolunteerInitiativeId`; max 1000 child relations.
- **Shift generation:** a tree call takes at most 200 records. Expand every series with `scripts/expand-series.py`; over 200 records it needs `--out-dir`, which writes one body per 200-record batch.
- **JobPositionShift:** end datetime ≥ start datetime — i.e. `EndDate ≥ StartDate`, with `EndTime > StartTime` required **only when `EndDate == StartDate`** (a shift that crosses midnight or spans days has a later `EndDate`, so its `EndTime` may be earlier); `MaximumAttendeesCount ≥ 0`.
- **JobPositionAssignment:** end datetime ≥ start datetime.
- **Capacity:** counted, never enforced — nothing out of the box blocks a signup when a shift is full. A customer validation rule may reject writes; handle its error in SKILL.md step 9.
