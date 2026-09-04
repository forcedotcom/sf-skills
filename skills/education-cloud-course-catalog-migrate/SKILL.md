---
name: education-cloud-course-catalog-migrate
description: "Use this skill to migrate course catalog data from external sources (CSV, PDF, website) and bulk-create Learning and LearningCourse records in Education Cloud. Triggers when a user wants to import courses, parse course catalog documents, or set up a course catalog for an academic term. Handles multi-source data ingestion, intelligent interpretation of course structures (lecture+lab linked courses via IsLinkedOnly flag, credit hours, course types), batch creation via sObject REST API, data quality validation, conflict resolution for existing courses, and gap identification. Explains what's missing (descriptions, types) and requests additional sources. Pauses for clarification on multi-component courses and conflicting data. DO NOT TRIGGER for creating individual Learning Course records manually, for creating Learning Programs (different workflow), or for enrollment/registration workflows."
metadata:
  version: "1.0"
  domains:
    - "Education"
  accessCheck:
    - type: "accessCheck"
      value: "IndustriesEducation.userHasEducationCloudAccess"
  cliTools:
    - tool: ["python3"]
      semver: ">=3.9.0"
---

# Migrating Course Catalog to Education Cloud

Import course catalog data from multiple sources (CSV, PDF, website) and bulk-create Learning Course records with structure detection and data quality validation.

## Scope

- **In scope**: Multi-source ingestion (CSV, PDF, web), Learning + LearningCourse bulk creation via sObject REST API (Composite batches up to 200), linked course detection (lecture+lab via IsLinkedOnly), credit hour parsing (Duration/DurationUnit), course type mapping, data quality validation, conflict resolution, gap identification/remediation
- **Out of scope**: Creating individual Learning Course records manually (delegate to metadata generation skills), creating Learning Programs (Learning.Type = 'LearningProgram' + separate child object), creating External Learning (Learning.Type = 'ExternalLearning'), course sections/offerings (CourseOffering object), enrollment/registration workflows (no dedicated skill yet — ask the user), SIS sync (separate integration workflow)

---

## Required Inputs

Gather or infer before proceeding:

- **Target org**: Active Salesforce org with Education Cloud enabled
- **Primary data source**: CSV file, PDF document, or website URL with course catalog data
- **Business Account**: the Academic Operations Business Account to link courses to (e.g., College of Engineering)
- **Academic term** (optional): context only, not stored on Learning Course

Additional sources (gathered during workflow):
- Supplementary data sources for missing fields (descriptions, types, mappings)
- Lecture-lab mapping files (if multi-component courses detected)
- Conflict resolution decisions (if existing courses found)

Defaults unless specified:
- Course status: Active (IsActive = true on Learning)
- Batch size: 25 records per Composite API call as an agent (API supports 200; tool-call payload limits are the binding constraint — see Step 7)
- Data quality validation: Enabled
- Learning.Type: 'LearningCourse' (required for course catalog entries)

---

## Execution Transport

**Resolve the API version first — do not hardcode.** `GET /services/data/` (no version segment) returns an endpoint map already resolved to the org's max version, not a `{version, label, url}` list. Pipe it into `scripts/resolve_api_version.py` to get `{"version": "69.0"}`; use as `vXX.X` everywhere below, including the transport probe.

Then probe transport health: `GET /services/data/vXX.X/limits` via headless-360 dispatch. 2xx → route all calls through it. On absent/4xx/5xx → probe other transports (other Salesforce MCP, custom MCP), use first healthy, announce it. None healthy → stop, ask user to connect one; never fabricate. (SOQL `/query` is routable on headless-360 — confirmed by live test; `/tooling/query` and `?fields=` are unconfirmed, use describe + direct record reads instead.)

Never fall back to `sf` CLI or shell out for org credentials — a slow/oversized batch is a batch-size problem (shrink it, step 7), not a transport failure, and CLI shell-out trips an unbypassable approval gate on some surfaces. A version too new for the org returns `404 NOT_FOUND` on an otherwise-healthy transport — re-read `GET /services/data/`, drop to the org's max version, retry, don't switch transport. See `references/gotchas.md` for both.

---

## Workflow

All steps are sequential. Do not skip or reorder. If blocked, stop and ask for missing context.

### Phase 1 — Ingest Primary Source

1. **Identify data source type** — determine if primary source is CSV, PDF, or website URL. Ask user to provide the source if not already specified.

2. **Parse primary source** — extract course data:
   - For CSV: Use `Read` tool to load file, parse columns
   - For PDF: Use `Read` tool (supports PDF extraction), parse text. Over 20 pages, read in sequential page-range chunks and merge parsed rows before validating completeness — see `references/large-catalog-handling.md` §1
   - For website: Use `WebFetch` tool to retrieve HTML, parse course listings
   
   Look for: course codes (identity — split into SubjectAbbreviation + CourseNumber, see step 8/9), course names (Name), credit hours (Duration + DurationUnit), descriptions (Description), course types (Lecture/Lab/Exam/Drill/Recitation), prerequisites, corequisites, linked course indicators (IsLinkedOnly), delivery modality (if the same course code repeats with different Duration/DurationUnit — see `references/large-catalog-handling.md` §2).

3. **Validate data completeness** — pipe the parsed records into the completeness helper:
   ```bash
   python3 scripts/validate_completeness.py --required "CourseCode,Name,Duration" --recommended "Description,CourseType" <<'JSON'
   [ { "CourseCode": "...", "Name": "...", ... }, ... ]
   JSON
   ```
   The report gives present/missing counts per field. Optional fields (prerequisites, corequisites, linked courses) are not checked — their absence never blocks progress.

   If any required field shows `missing > 0`, report error and stop. If recommended fields are missing, note the gaps and continue to Phase 2.

### Phase 2 — Identify Gaps and Request Additional Sources

4. **Report data quality** — print a summary table showing which fields are present and which are missing. Example:
   ```text
   Data Quality Report:
   • Course codes: 120/120 OK
   • Course names: 120/120 OK
   • Credit hours: 120/120 OK
   • Descriptions: 115/120 (5 missing)
   • Course types: 118/120 (2 missing)
   ```

5. **Request supplementary sources** — if key fields are missing (descriptions, types), ask user: "Do you have additional sources — a website, department document, or mapping file?"
   
   - If yes: receive additional source, parse it, and merge data with primary source
   - If no: offer to create courses with placeholder values or stop and wait for complete data
   
   Repeat this step until all gaps are filled or user confirms to proceed with incomplete data.

   If subject-to-Business-Account mapping is ambiguous, resolve every ambiguous case in one pass (source doc + live public catalog + course level/number patterns) and present them together, not one round at a time (see `references/gotchas.md`).

6. **Detect multi-component courses** — pipe the course codes into the lecture/lab pairing helper:
   ```bash
   python3 scripts/detect_linked_courses.py --suffixes "L,LAB" <<'JSON'
   [ "BIO-201", "BIO-201L", ... ]
   JSON
   ```
   Each `{"lecture", "lab"}` pair returned is a candidate multi-component course.
   - If any pairs are found, pause and explain: "I found X multi-component (lecture + lab) courses. Structure them as (1) separate standalone courses, or (2) linked courses (IsLinkedOnly flag, students must take both)?"
   
   If user selects "linked courses", request a mapping file or confirm the naming pattern is reliable.

   **Detect modality duplicates** — group parsed rows by course code. Same code, different `Duration`/`DurationUnit`/`Description` = a modality variant (e.g. Online vs. On-Campus), not a duplicate — never silently dedupe/merge. Resolve the representation once per run, not per-course. See `references/large-catalog-handling.md` §2.

### Phase 3 — Batch Create Learning and LearningCourse Records

7. **Prepare batch creation plan** — pipe the parsed course records into the batching helper. The Composite API accepts up to 200 records/call, but an agent's tool-call payload has a smaller practical ceiling (~56KB/150 records). Use `--batch-size 25` when executing as an agent (raise toward 200 only if the calling environment confirms it can handle larger payloads):
   ```bash
   python3 scripts/batch_courses.py --batch-size 25 <<'JSON'
   [ { "Name": "...", ... }, ... ]
   JSON
   ```
   Each element of the returned array is one Composite API call's worth of records. Print: "Starting course catalog import. I'll use Composite API to create records in batches. Total: X courses."

   If a batch still won't inline through a healthy dispatch transport, re-run with a smaller `--batch-size` (e.g. 10) instead of switching transport. Track dispatch vs. fallback counts and report both in the Phase 5 summary.

   **Over 200 courses (8+ batches)**: disclose total batch count upfront, print the Batch N complete line after every batch (not just at the end), and — only if the surface exposes a parallel-task/subagent tool — follow the fan-out rules in `references/large-catalog-handling.md` §3-4. Never assume that capability exists; default to sequential batches.

8. **Check for existing courses** — before creating Batch 1, scope the check to this batch's own course codes, never a global fetch (an unrelated catalog entry already in the org is not a conflict).

   Split this batch's course codes first (`scripts/split_course_code.py`) — key the check on those identity fields, never `CipCode` (many orgs leave it null — see `references/gotchas.md`).

   > **Headless-360 note**: SOQL `/query` is routable via the headless-360 dispatch tool (confirmed by live test) — query `LearningCourse`, matching each split `{SubjectAbbreviation, CourseNumber}` pair exactly (SOQL has no tuple `IN`, so OR the pairs): `SELECT Id, LearningId, Name, SubjectAbbreviation, CourseNumber FROM LearningCourse WHERE (SubjectAbbreviation = 'BIO' AND CourseNumber = '201') OR ...`. If Ids are unknown and a SOQL lookup isn't available, ask the user to supply them (or a prior import manifest). Never do this via Bash/CLI — see `references/gotchas.md`.

   If any rows come back (i.e. a SubjectAbbreviation+CourseNumber pair in this batch already exists in the org), pause and explain conflict:
   - Show existing course details vs. new import data side-by-side
   - Check if existing courses have dependencies (course offerings, enrollments)
   - Offer options: (1) Update existing courses, (2) Skip existing courses, (3) Cancel and review manually
   
   Wait for user decision before proceeding.

9. **Create Batch 1** — two-step process for each course:

   > **Field placement (verified via describe)**: `CipCode`, `Duration`, `DurationUnit`, `ProviderId` are createable on **Learning ONLY** — `ProviderId` on the child fails with `INVALID_FIELD_FOR_INSERT_UPDATE`. LearningCourse takes `Name`, `LearningId`, `CourseType`, `IsLinkedOnly`, `SubjectAbbreviation`, `CourseNumber`, `Description`, `CourseLevelDescription`, `FieldOfStudy` — it inherits the account link via `LearningId`. Confirm with describe before building the body.

   > **CipCode is opt-in.** Federal CIP taxonomy field, not the course's identity — leave unset unless the source supplies a real CIP code and the user confirms.

   **Step 1: Create Learning (parent) records via Composite API:**
   ```http
   POST /services/data/vXX.X/composite/sobjects
   {
     "allOrNone": false,
     "records": [
       {
         "attributes": {"type": "Learning", "referenceId": "learning1"},
         "Name": "<course-name>",
         "Type": "LearningCourse",
         "Description": "<description>",
         "ProviderId": "<account-id>",
         "Duration": <hours>,
         "DurationUnit": "Credit Hours",
         "IsActive": true
       },
       ...
     ]
   }
   ```

   Capture each returned Id (order matches the `records` array) to use as `LearningId` in Step 2.

   **Step 2: Create LearningCourse (child) records via Composite API:**
   ```http
   POST /services/data/vXX.X/composite/sobjects
   {
     "allOrNone": false,
     "records": [
       {
         "attributes": {"type": "LearningCourse"},
         "Name": "<course-record-name>",
         "LearningId": "<learning-id-from-step-1>",
         "SubjectAbbreviation": "<subject-prefix>",
         "CourseNumber": "<course-number>",
         "CourseType": "<parsed-course-type>",
         "IsLinkedOnly": false
       },
       ...
     ]
   }
   ```

   Set `CourseType` from the parsed/mapped course type for that record (see the Gotchas table for value mapping) — do not hard-code it. A lab record must get `CourseType: "Lab"`, not `"Lecture"`.

   > **CourseType** picklist values (verified): `Lecture`, `Lab`, `Exam`, `Drill`, `Recitation`.

   > **`restrictedPicklist: true` means only today's values are valid to submit, not that the set is closed.** If a source value (e.g. `DurationUnit` = "Program Points") isn't in describe's list, don't silently drop/remap it — offer adding the picklist value via metadata alongside remapping or a placeholder (see `references/gotchas.md`).

   Print progress: `Batch 1 complete — X Learning + X LearningCourse records created`.

10. **Handle multi-component courses** — if user selected "linked courses" in step 6:
    - Create lecture courses with `CourseType: "Lecture"`, `IsLinkedOnly = false`
    - Create lab courses with `CourseType: "Lab"`, `IsLinkedOnly = true`
    - Use the `detect_linked_courses.py` pairs (or a user-supplied mapping file) to determine which labs are linked-only
    - Print: `X linked lab courses created (IsLinkedOnly = true)`

11. **Repeat for remaining batches** — continue steps 8-10 for Batch 2, Batch 3, etc. until all courses created.

### Phase 4 — Data Quality Validation and Conflict Resolution

12. **Scan for incomplete records** — after all batches complete, read back each newly created record by the Id captured from its create response:
    ```http
    GET /services/data/vXX.X/sobjects/Learning/<id>
    GET /services/data/vXX.X/sobjects/LearningCourse/<id>
    ```

    > **Headless-360 note**: SOQL `/query` is routable via the headless-360 dispatch tool (confirmed by live test) — a `CreatedDate = TODAY` query works as an alternative to iterating captured Ids with direct record GETs.

    Run the completeness helper **separately per sObject** — `CourseType` exists only on `LearningCourse`, `Description` only on `Learning`; combining both shapes into one call false-positives every parent as missing `CourseType`:
    ```bash
    python3 scripts/validate_completeness.py --required "Name" --recommended "Description" <<'JSON'
    [ { "Name": "...", "Description": "...", ... }, ... ]   # Learning read-backs only
    JSON
    ```
    Repeat with `--recommended "CourseType"` against LearningCourse read-backs only. Identify courses with missing descriptions (Learning report) or missing types (LearningCourse report). Print data quality report (same format as step 4).

13. **Detect conflicting data** — if multiple sources provided different values for the same course, flag conflicts, e.g. "CHEM-301: website says X, PDF says Y — which should I use?" Wait for user decision, then update the conflicting courses.

14. **Remediate gaps** — if user provides additional sources to fill gaps, parse them and update the incomplete courses:
    ```http
    PATCH /services/data/vXX.X/sobjects/Learning/<id>
    {"Description": "..."}
    
    PATCH /services/data/vXX.X/sobjects/LearningCourse/<id>
    {"CourseType": "<parsed-course-type>"}
    ```

### Phase 5 — Summary and Verification

15. **Generate import summary** — print final report:
    ```text
    Course catalog import finished!
    Summary:
    • X Learning + X LearningCourse records created
    • Y standalone, Z linked lab courses (IsLinkedOnly)
    • All courses linked to <Business Account name>, set Active
    Data sources used: 1. <primary> 2. <supplementary 1> 3. <supplementary 2>
    ```

    **If any gaps were remediated from a supplementary source (step 5/14 ran)**, the final report MUST also include, in this order:
    - **Data Quality Report** — two tables, "Initial data (from `<primary source>`)" and "After supplementary source (`<supplementary source>`)", each listing every field from step 4 with its present/total count. This is the before/after pair, not just the final counts.
    - **Gap Remediation** — grouped by field (e.g. "Courses with missing descriptions (filled from `<source>`)"), a numbered list of every remediated course with the value it received. One list per remediated field.

16. **Offer verification** — ask user: "Would you like me to query specific courses to verify the data? For example, I can show you a course with its LearningCourse child record, or check for any remaining data quality issues."

17. **Check the running user can actually see what was just created** — don't just flag this, check it (see `references/gotchas.md` for the resolve-running-user + FLS/RecordTypeVisibility pattern), against every object touched (`Learning`, `LearningCourse`, `Account` if Person Accounts came up). Name any gap and its profile, offer the specific fix, and wait for confirmation before writing `Profile`/`PermissionSet` metadata. Default-Private OWD/sharing is org-wide, not per-user — flag it, don't offer to change it.

---

## Rules / Constraints

| Constraint | Rationale |
|-----------|-----------|
| Use Composite API, batched at 25 records/call for agent execution (API supports up to 200) | sObject REST standard in H360 MCP; a 150-record payload (~56KB) exceeds typical tool-call limits |
| Create Learning first, then LearningCourse | LearningCourse.LearningId requires parent to exist first |
| Always set Learning.Type = 'LearningCourse' | Learning is polymorphic — Type distinguishes courses from programs |
| Always query for existing courses before creating | Prevents duplicates; lets user decide on conflicts |
| Pause for clarification on multi-component courses | IsLinkedOnly flag affects enrollment behavior — user must confirm structure |
| Report data quality gaps before proceeding | Lets user provide complete data before committing to org |
| Wait for user decision on conflicting data | Agent cannot determine which source is authoritative |
| Do not invent missing data | Placeholder values must be explicitly approved by user |
| Set ProviderId (Business Account) on the parent Learning ONLY | Createable on Learning, not LearningCourse — see step 9 field-placement note |
| Set all courses to Active status by default (IsActive = true) | Must be Active to appear in catalog search/registration |
| Use sObject REST API, not CLI commands for org calls | H360 MCP skills have no execution environment for reaching the org. The `scripts/` helpers are local data transforms (no org call) — if no Bash tool is available, perform the equivalent check inline instead of skipping it |
| Use tool-agnostic language | Skill ships to multiple AI surfaces beyond Claude Code |
| Over 200 courses or 20+ source pages: follow `references/large-catalog-handling.md`, not ad hoc chunking | Improvised chunking risks split-page data loss or duplicate creates |

---

## Gotchas

See `references/gotchas.md` for known failure modes and resolutions (parsing quirks, missing Business Account, picklist mapping, partial Composite failures, and more).

---

## Output Expectations

Deliverables:
- X Learning records created (Type = 'LearningCourse')
- X LearningCourse child records created (LearningId lookups)
- Data quality report showing completeness per field
- Import summary listing all data sources used
- Optional: course verification via direct record reads or SOQL `/query` (both routable via headless-360)

No files are produced — all output is org records created via sObject REST API.

---

## Cross-Skill Integration

| Need | Delegate to |
|------|-------------|
| Create individual Learning Course manually | Platform metadata generation skills |
| Create Learning Programs | No dedicated skill yet — ask the user |
| Set up course sections/offerings | No dedicated skill yet — ask the user |
| Configure enrollment eligibility rules | No dedicated skill yet — ask the user |

---

## Reference File Index

- `references/gotchas.md` — known failure modes and their resolutions
- `references/gotchas-detail.md` — lower-frequency gotchas, linked from gotchas.md
- `references/large-catalog-handling.md` — rules for >200 courses or >20-page source docs: paginated reads, modality-duplicate detection, checkpointing, gated parallel fan-out (steps 2, 6, 7)
- `scripts/resolve_api_version.py` — extracts org's max API version from the headless-360 endpoint map (Execution Transport)
- `scripts/validate_completeness.py` — required/recommended field presence check (steps 3, 12)
- `scripts/detect_linked_courses.py` — lecture/lab course-code pairing (step 6)
- `scripts/detect_modality_variants.py` — flags CourseCode rows differing by Duration/DurationUnit/Description, for `large-catalog-handling.md` §2
- `scripts/batch_courses.py` — Composite API batch splitting (step 7)
- `scripts/split_course_code.py` — SubjectAbbreviation/CourseNumber splitting (step 9)
