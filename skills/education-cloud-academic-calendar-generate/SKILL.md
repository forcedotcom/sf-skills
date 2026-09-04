---
name: education-cloud-academic-calendar-generate
description: "Use this skill to set up, create, or generate an academic calendar for Education Cloud orgs. Creates Academic Year, Academic Terms (semester/quarter/trimester), Academic Sessions, registration windows, and add/drop deadlines from natural language or documents. Validates date ranges and handles overlapping sessions, linking terms to the year and sessions to their term. TRIGGER when: user asks to \"create an academic calendar\", \"set up semester dates\", \"generate the academic year\", \"add terms and sessions\", \"configure registration windows\", or \"add/drop deadlines\" — or uploads a calendar document (PDF, CSV, XLSX) containing term or session dates. DO NOT TRIGGER for querying or updating existing calendar records, scheduling courses, or configuring course offerings."
metadata:
  version: "1.0"
  domains:
    - "Education"
  minApiVersion: "68.0"
  accessCheck:
    - type: "orgPref"
      value: "EducationCloudEnabled"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.8"
  relatedSkills:
    - "education-cloud-multi-campus-configure"
---

# Education Cloud Academic Calendar Generation

Create the foundational academic calendar infrastructure for Education Cloud orgs, parsing calendar data from documents or natural language and generating validated Academic Year, Term, and Session records with proper date ranges and institutional linkage.

## Scope

- **In scope**: Academic Year records, Academic Term records (semester/quarter/trimester systems), Academic Session records (term subdivisions), registration windows, add/drop deadlines, date validation
- **Out of scope**: Course scheduling (delegate to course offering skills), individual course section dates, financial aid deadlines, exam schedules, institutional hierarchy setup (no dedicated skill exists yet for this — set up Accounts/campuses manually)

---

## Execution Model

All Salesforce operations use relative-path REST calls. Do not use CLI or shell commands to reach Salesforce (`sf`, `sfdx`, `curl`); the execution environment may not provide them. This does not apply to the skill's own local validation script (`scripts/validate_calendar_dates.py`, see step 4) — that runs locally and never touches the org.

- **Record CRUD**: sObject REST — `POST /services/data/<ver>/sobjects/<Object>`, `GET /services/data/<ver>/sobjects/<Object>/<Id>`, `PATCH /services/data/<ver>/sobjects/<Object>/<Id>`
- **Schema checks**: sObject describe — `GET /services/data/<ver>/sobjects/<Object>/describe` (confirm object + field API names exist before writing).
- **SOQL `/query` is routable**: `GET /services/data/<ver>/query` with the SOQL passed as a structured `queryParams: {"q": "..."}`, NOT inlined into the URL as `?q=...` — confirmed by live test: inlining `?q=` 404s (`ROUTE_NOT_FOUND`/`NOT_FOUND`) via headless-360 dispatch, while `queryParams` reliably 200s. Use it to list-scan for existing terms/sessions, or resolve records by the runtime Id captured at create time and read them back with a direct `GET .../sobjects/<Object>/<Id>` — either is valid.
- **All IDs are runtime variables** captured from create-response `body.id` — never hardcode a literal Salesforce Id.
- **Resolve API version dynamically** — see Execution Transport below. Do not hardcode a version.

---

## Required Inputs

Gather or infer before proceeding:

- **Calendar system**: Semester (Fall/Spring/Summer) or Quarter (Fall/Winter/Spring/Summer) or Trimester
- **Academic year span**: Start and end dates for the overall academic year
- **Term dates**: For each term - class start/end, registration open date, add/drop deadline
- **Session subdivisions**: Any sub-sessions within terms (e.g., Summer Session 1 and 2)

If the user provides a calendar document (PDF, CSV, spreadsheet), parse it to extract all dates. If the user provides natural language, ask for specific dates before proceeding.

Note: AcademicYear, AcademicTerm, and AcademicSession have no Account reference field — calendar records are not linked to a Business Account. Linkage is Year → Term (`AcademicYearId`) and Term → Session (`AcademicTermId`) only.

Defaults unless specified:
- Calendar system: **Semester** (Fall, Spring, Summer)
- Academic year naming: **"Academic Year YYYY-YYYY"** format
- Registration windows: **Open 3-4 months before term start**
- Add/drop deadlines: **2 weeks after term start**

---

## Execution Transport

1. **Resolve API version**: `GET /services/data/` (unversioned) via headless-360 dispatch. Response is a map of endpoint paths already resolved to the org's current max version (e.g. `"limits": "/services/data/v69.0/limits"`) — not an array with a `version` field. Extract the version from any returned path (regex `v\d+\.\d+`) and use it as `<ver>` for every call below.
2. **Probe transport health**: `GET /services/data/<ver>/limits` via headless-360 dispatch. 2xx → route all calls through it. On absent/4xx/5xx → probe other available transports (other Salesforce MCP, authenticated `sf` CLI, custom MCP) with the same read, use first healthy, announce it. None healthy → stop, ask user to connect one; never fabricate.

---

## Workflow

All steps are sequential. Do not skip or reorder. If blocked, stop and ask for missing context.

0. **Verify foundation prerequisites** — Follow `references/foundation_prerequisites.md`: org edition, Lightning Experience, Education Cloud license, running user's EDU access, Education Cloud Foundation enabled (self-heal via confirm-then-enable if off). Do not proceed to Step 1 until all checks pass.

1. **Confirm calendar system**
   - Ask user: semester, quarter, or trimester system?
   - Identify expected term names based on system type

2. **Gather calendar data**
   - If user provides document (PDF, CSV, spreadsheet): parse to extract year, term, and session dates
   - If user provides natural language: extract dates from description
   - If insufficient detail: ask for specific dates (term start/end, registration windows, deadlines)

3. **Verify object and field schema**
   - Before writing, confirm each object and every field you will set exists on the org:
     `GET /services/data/<ver>/sobjects/AcademicYear/describe`, `.../AcademicTerm/describe`, `.../AcademicSession/describe`
   - Read the `fields` array; match your intended field API names (`Name`, `AcademicYearId`, `StartDate`, `EndDate`, `RegistrationOpenDate`, `RegistrationCloseDate`, `Season`, `AcademicTermId`, `ClassStartDate`, `ClassEndDate`, `AddDropDeadline`) against it.
   - Note picklist field `Season` (`AcademicTerm.Season`, values `Fall`/`Spring`/`Summer`/`Winter`): only send values present in that field's `picklistValues`. `AcademicSession.Type` is a different picklist (`Semester`/`Trimester`/`Quarter`/etc.) not used by this workflow — do not confuse it with `Season`.
   - If a field is absent: STOP — do not POST with an unverified field name; report the mismatch to the user.

4. **Validate date ranges**
   - Assemble the gathered year/term/session data into the JSON shape documented at the top of `scripts/validate_calendar_dates.py`, then run it once:
     ```bash
     python3 scripts/validate_calendar_dates.py <<'EOF'
     {"academicYear": {...}, "terms": [...], "sessions": [...]}
     EOF
     ```
   - The script checks term end > start, year spans all terms, registration open < term start, add/drop deadline within term bounds, and session containment within parent term — and computes each term's `RegistrationCloseDate`.
   - If `valid` is `false`: stop, report each entry in `errors` to the user, and ask for corrected dates. Do not proceed to step 5.
   - `warnings` (e.g., intentional session overlaps) do not block — surface each one to the user for confirmation in step 6.
   - Carry `computedRegistrationCloseDates` forward — step 8 uses it instead of recalculating.

5. **Detect duplicate terms**
   - AcademicTerm `Name` is not unique-constrained, so a duplicate name will NOT error on insert. List-scan for existing terms with matching names before creating: `GET /services/data/<ver>/query` with `queryParams: {"q": "SELECT Id, Name, StartDate, EndDate FROM AcademicTerm WHERE Name = 'Fall 2025'"}` — pass the SOQL via `queryParams`, not inlined as `?q=` in the URL (inlining 404s) — or, if the user has previously created a calendar for this year in the same session, reuse the Ids captured then instead of re-creating.
   - If a duplicate name is found, compare dates and ask the user whether to update the existing record or skip.
   - If the duplicate-check read itself fails (non-2xx, transport error): STOP — do not proceed to create the term. Report the failure to the user and ask how to proceed; do not silently create a possibly-duplicate record.

6. **Display proposed calendar structure and confirm**
   - Present a summary of what will be created: Academic Year name and dates, then each term's name/dates/registration window/computed `RegistrationCloseDate`, then each session's name and dates grouped under its parent term. See `examples/sample-output.md` for a filled-in rendering.
   - For every session-overlap warning from step 4: state the overlap period and ask the user to confirm it's intentional.
   - Ask user: "Should I create all of these records?"
   - Wait for user confirmation before proceeding to step 7

7. **Create Academic Year record**
   - After user confirms in step 6, insert Academic Year:
     ```http
     POST /services/data/<ver>/sobjects/AcademicYear
     {"Name": "Academic Year 2025-2026"}
     ```
   - Capture `academicYearId` from the response `body.id` for term linkage
   - Report: "Academic Year created: Academic Year 2025-2026"

8. **Create Academic Term records**
   - For each term (Fall, Spring, Summer or Quarter equivalents), insert with `AcademicYearId` set to `academicYearId` from step 7:
     ```http
     POST /services/data/<ver>/sobjects/AcademicTerm
     {"Name": "Fall 2025", "Season": "Fall", "StartDate": "2025-08-18", "EndDate": "2025-12-12",
      "AcademicYearId": "<academicYearId>",
      "RegistrationOpenDate": "2025-04-01", "RegistrationCloseDate": "2025-08-17"}
     ```
     - `RegistrationCloseDate` comes from step 4's `computedRegistrationCloseDates[<term name>]` — do not recompute it by hand.
     - `Season` is a restricted picklist: `Fall`, `Spring`, `Summer`, `Winter`. AcademicTerm has NO add/drop field — add/drop deadlines live on AcademicSession only.
   - Capture each `termId` from the response `body.id` for session linkage
   - Report progress: "Created 3 terms: Fall 2025, Spring 2026, Summer 2026"

9. **Create Academic Session records**
   - For each session subdivision (e.g., Summer Session 1, Summer Session 2), insert with `AcademicTermId` set to the parent `termId` from step 8:
     ```http
     POST /services/data/<ver>/sobjects/AcademicSession
     {"Name": "Summer Session 1", "ClassStartDate": "2026-05-26", "ClassEndDate": "2026-07-03",
      "AddDropDeadline": "2026-06-11", "AcademicTermId": "<termId>"}
     ```
   - Report progress: "Created 2 sessions: Summer Session 1, Summer Session 2"

10. **Generate completion summary**
    - Display a final summary: the created Academic Year with its dates, each created Term with its date range, and each created Session grouped under its parent Term, plus a one-line note on the Year → Term → Session linkage. See `examples/sample-output.md` for a filled-in rendering.
    - If any sessions overlap (per step 4's warnings), note the overlap period and that it was confirmed intentional.
    - If any terms were skipped due to duplicates, list them with reason

---

## On-Demand Verification

Available at any time after step 10, not a required workflow step — use only when the user asks to spot-check a record or view a calendar range.

- **Specific record** (e.g., "show me Fall 2025"): cold-read by its captured Id — `GET /services/data/<ver>/sobjects/AcademicTerm/<termId>` (returns all fields; do not use a `?fields=` selector) — or, if the Id was not captured, look it up by name with `GET /services/data/<ver>/query` and `queryParams: {"q": "SELECT Id FROM AcademicTerm WHERE Name = 'Fall 2025'"}` (pass the SOQL via `queryParams`, not inlined as `?q=` in the URL — inlining 404s). Display all field values in table format with parent hierarchy.
- **Calendar view** (e.g., "show all dates for Summer 2026"): cold-read the term and each child session by their captured Ids — `GET /services/data/<ver>/sobjects/AcademicTerm/<termId>` and `GET /services/data/<ver>/sobjects/AcademicSession/<sessionId>` — and display as a table (Record Type, Name, Start Date, End Date, Duration, Registration Open, Registration Close, Add/Drop). Calculate and display overlap periods if applicable. See `examples/sample-output.md` for a filled-in rendering.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Verify object + field API names via describe before writing | Prevents a failed POST on an unverified field; `Season` picklist values must match `AcademicTerm.Season`'s `picklistValues` |
| Term end date must be after start date | Platform validation will reject invalid date ranges |
| Registration window must open before term starts | Students cannot register after classes begin |
| Add/drop deadline (on AcademicSession) after or equal to term start | Deadline before classes start is logically invalid; AcademicTerm has no add/drop field |
| Academic Year must span all its child terms | Term dates outside year range cause reporting issues |
| Overlapping sessions within same term are allowed | Common pattern for Summer sessions (e.g., Session 1: May-Jul, Session 2: Jun-Aug) |
| Term names should match calendar system convention | Fall/Spring/Summer for semester, Fall/Winter/Spring/Summer for quarter |
| Resolve API version dynamically, don't hardcode | Org's max API version changes over time; a stale hardcoded version drifts from the org's current one |
| Check for duplicate terms via SOQL `/query` before creating, pass `q` via `queryParams` not inlined in the URL | `/query` is routable via headless-360, but only with `queryParams` — inlining `?q=` 404s (confirmed by live test); term `Name` is not unique-constrained so duplicates do not error on insert; a failed duplicate-check read must block creation, not be skipped |

---

## Gotchas

| Issue | Resolution |
|-------|------------|
| User provides relative dates ("next Fall") | Convert to absolute dates before inserting (e.g., "next Fall" → "Fall 2026" with specific dates) |
| Overlapping sessions flagged as error | Confirm with user — overlaps are intentional in many institutions (e.g., Summer Session 1 and 2 overlap by 1 week) |
| Duplicate term with different dates | Ask user whether to update existing or skip — do not auto-update without confirmation |
| Registration window after term start | This is invalid — ask user to provide correct registration open date |
| Academic Year end date before last term end date | Extend Academic Year to cover all terms, or adjust term dates |
| Input carries a term-level add/drop date but no session subdivisions | AcademicTerm has no add/drop field — surface the term-vs-session placement to the user or propose a session per term to carry the date; never write it onto AcademicTerm and never silently drop it |
| User provides 3-part year range (2025-2026-2027) | Clarify with user — Academic Year spans exactly 2 years (e.g., 2025-2026) |
| Session without parent term | Every session must link to a term — if user provides session dates without term, ask which term it belongs to |

---

## Output Expectations

Deliverables:

- **Academic Year record**: Single year record spanning all terms (e.g., "Academic Year 2025-2026")
- **Academic Term records**: 3-4 term records per year (Fall, Spring, Summer for semester; Fall, Winter, Spring, Summer for quarter)
- **Academic Session records**: 0-N session records (typically 2 Summer sessions for semester systems)
- **Summary report**: Table listing all created records with names, dates, and linkages

Terms link to the parent Academic Year (`AcademicYearId`); sessions link to the parent Term (`AcademicTermId`). These objects have no Account reference field.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Institutional hierarchy (Accounts, campuses) | No dedicated skill yet — set up manually |
| Course scheduling and offerings | Course offering generation skills |

---

## Reference File Index

| File | When to read |
|------|-------------|
| `references/foundation_prerequisites.md` | Step 0 — org edition, Lightning Experience, EDU license, permission set assignment, Education Cloud Foundation enablement; run before Step 1 on every standalone invocation |
| `references/calendar-systems.md` | When user's calendar system is unclear or non-standard |
| `references/date-validation.md` | When validating complex date overlaps or multi-session terms |
| `examples/semester-calendar.json` | To verify output structure for semester system |
| `examples/quarter-calendar.json` | To verify output structure for quarter system |
| `examples/sample-output.md` | To see filled-in renderings of the proposed-structure display, completion summary, and calendar-view table |
| `scripts/validate_calendar_dates.py` | Invoked in step 4 to validate date ranges and compute `RegistrationCloseDate` deterministically |
