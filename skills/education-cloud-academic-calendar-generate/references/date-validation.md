# Academic Calendar Date Validation Rules

## Basic Date Range Validation

### Rule: Term End After Start

**Requirement**: Every term's end date must be strictly after its start date.

**Check**: `END_DATE > START_DATE`

**Example Valid**:
- Start: 2025-08-18
- End: 2025-12-12
- Valid (117 days)

**Example Invalid**:
- Start: 2025-08-18
- End: 2025-08-15
- Invalid (end before start)

**Error Message**: "Term end date must be after start date"

---

### Rule: Academic Year Covers All Terms

**Requirement**: The Academic Year start date must be <= the earliest term start, and the Academic Year end date must be >= the latest term end.

**Check**: 
- `YEAR_START <= min(TERM_START_DATES)`
- `YEAR_END >= max(TERM_END_DATES)`

**Example Valid**:
- Academic Year: 2025-08-18 to 2026-08-14
- Fall 2025: 2025-08-18 to 2025-12-12
- Spring 2026: 2026-01-12 to 2026-05-15
- Summer 2026: 2026-05-26 to 2026-08-14
- Valid (year spans all terms)

**Example Invalid**:
- Academic Year: 2025-08-18 to 2026-05-31
- Summer 2026: 2026-05-26 to 2026-08-14
- Invalid (Summer extends beyond year end)

**Error Message**: "Academic Year must span all child terms"

---

## Registration and Deadline Validation

### Rule: Registration Opens Before Term Starts

**Requirement**: Registration open date must be before term start date.

**Check**: `REGISTRATION_OPEN < TERM_START`

**Typical Lead Time**: 3-4 months for Fall, 2-3 months for Spring, 1-2 months for Summer

**Example Valid**:
- Registration Opens: 2025-04-01
- Term Starts: 2025-08-18
- Valid (4.5 months lead time)

**Example Invalid**:
- Registration Opens: 2025-08-20
- Term Starts: 2025-08-18
- Invalid (opens after term starts)

**Error Message**: "Registration window must open before term start date"

---

### Rule: Add/Drop Deadline After or Equal to Session Start

**Requirement**: AcademicTerm has NO add/drop field — add/drop deadlines live on AcademicSession only (see `SKILL.md` Gotchas). A deadline must be on or after its session's start date, and before its session's end date.

**Check**: `SESSION_START <= ADD_DROP_DEADLINE < SESSION_END`

**Typical Timing**: 1-2 weeks after session start

**Example Valid**:
- Session Start: 2025-08-18
- Add/Drop Deadline: 2025-09-05
- Session End: 2025-12-12
- Valid (18 days after start, well before end)

**Example Invalid**:
- Session Start: 2025-08-18
- Add/Drop Deadline: 2025-08-10
- Invalid (deadline before session starts)

**No natural session exists**: If the user gives a per-term add/drop deadline but no session subdivisions, ask the user how to represent it (e.g. propose a single session per term to carry the deadline) — never write the date onto AcademicTerm and never silently drop it.

**Error Message**: "Add/drop deadline must be on or after session start date"

---

## Session Overlap Validation

### Rule: Overlapping Sessions Within Same Term Are Allowed

**Requirement**: Sessions within the same parent term CAN have overlapping date ranges. This is a common pattern for Summer sessions.

**Check**: Flag overlaps for user confirmation, but do not block creation.

**Example Valid (Intentional Overlap)**:
- Summer 2026 Term: 2026-05-26 to 2026-08-14
  - Summer Session 1: 2026-05-26 to 2026-07-03 (6 weeks)
  - Summer Session 2: 2026-06-26 to 2026-08-14 (7 weeks)
  - Overlap: 2026-06-26 to 2026-07-03 (1 week overlap is intentional)

**User Confirmation Prompt**:
> "Summer Session 1 and Summer Session 2 overlap from [START] to [END]. This is common for summer sessions where students can take courses in both. Is this overlap intentional?"

**Example Invalid (Likely Error)**:
- Fall 2025 Term: 2025-08-18 to 2025-12-12
  - Fall Session 1: 2025-08-18 to 2025-10-15
  - Fall Session 2: 2025-08-20 to 2025-12-12
  - Suspicious: Fall terms rarely have overlapping sessions — confirm with user

---

### Rule: Sessions Must Be Contained Within Parent Term

**Requirement**: Every session's start and end dates must fall within its parent term's date range.

**Check**:
- `SESSION_START >= TERM_START`
- `SESSION_END <= TERM_END`

**Example Valid**:
- Summer 2026 Term: 2026-05-26 to 2026-08-14
- Summer Session 1: 2026-05-26 to 2026-07-03
- Valid (session fully contained within term)

**Example Invalid**:
- Summer 2026 Term: 2026-05-26 to 2026-08-14
- Summer Session 1: 2026-05-15 to 2026-07-03
- Invalid (session starts before term)

**Error Message**: "Session dates must fall within parent term date range"

---

## Duplicate Detection

### Rule: No Duplicate Term Names for Same Academic Year

**Requirement**: Within a single Academic Year, term names must be unique.

**Check**: `AcademicTerm.Name` is not unique-constrained — a duplicate name will NOT error on insert. List-scan for existing terms with matching names via SOQL `/query` (routable via headless-360) before creating: `GET /services/data/<ver>/query` with `queryParams: {"q": "SELECT Id, Name, StartDate, EndDate FROM AcademicTerm WHERE Name = 'Fall 2025'"}` — pass the SOQL via `queryParams`, not inlined as `?q=` in the URL (inlining 404s); otherwise reuse Ids captured earlier in the same session. If the read fails, stop and ask the user before creating — do not risk a silent duplicate.

**Example Valid**:
- Academic Year 2025-2026
  - Fall 2025
  - Spring 2026
  - Summer 2026
- Valid (all unique names)

**Example Invalid (Duplicate Name)**:
- Academic Year 2025-2026
  - Fall 2025 (existing, created on 2025-03-15)
  - Fall 2025 (new, attempting to create on 2025-07-20)
- Duplicate (same name, same year)

**Resolution**:
1. If dates match existing record: Skip creation, report "Fall 2025 already exists with same dates"
2. If dates differ: Ask user whether to update existing or skip

---

### Rule: Duplicate with Different Dates Requires User Confirmation

**Requirement**: If a term with the same name exists but has different dates, stop and ask user how to proceed.

**Example Conflict**:
- **Existing**: Fall 2025 (2025-08-25 to 2025-12-19)
- **New**: Fall 2025 (2025-08-18 to 2025-12-12)

**User Prompt**:
> "A Fall 2025 term already exists with dates 2025-08-25 to 2025-12-19. Your new data has dates 2025-08-18 to 2025-12-12. Would you like to:
> 1. Update the existing term with new dates
> 2. Skip creating Fall 2025
> 3. Cancel and review the existing term first"

---

## Date Format Validation

### Rule: Date Strings Must Be in ISO 8601 Format

**Requirement**: All dates parsed from user input or documents must be converted to YYYY-MM-DD format before inserting.

**Valid Formats**:
- `2025-08-18`
- `08/18/2025` → Convert to `2025-08-18`
- `August 18, 2025` → Convert to `2025-08-18`

**Invalid Formats**:
- `8/18/25` → Ambiguous (is it 2025 or 1925?)
- `18-08-2025` → Day-first format (common in Europe, ambiguous)

**Resolution**: If date format is ambiguous, ask user to clarify which format convention they're using.

---

## Validation Workflow

### Step-by-Step Validation Process

1. **Parse all dates from input** → Convert to YYYY-MM-DD format
2. **Validate basic ranges** → Check end > start for all terms and sessions
3. **Validate Academic Year coverage** → Check year spans all terms
4. **Validate registration windows** → Check open date < term start
5. **Validate add/drop deadlines** → Check start <= deadline < end
6. **Check for overlapping sessions** → Flag for user confirmation (but allow)
7. **Check for duplicate terms** → Query existing, ask user if conflict found
8. **Validate session containment** → Check sessions within parent term bounds

**If any validation fails**: Stop, report specific error with field values, and ask user to provide corrected dates.

**If all validations pass**: Proceed to record creation.
