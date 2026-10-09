# Sample Output Renderings

Filled-in examples for the display steps referenced from `SKILL.md`. Values match `examples/semester-calendar.json`.

## Proposed Calendar Structure (Workflow step 6)

```text
Academic Year 2025-2026 (2025-08-18 to 2026-08-14)

Fall 2025
  StartDate: 2025-08-18  EndDate: 2025-12-12
  RegistrationOpenDate: 2025-04-01  RegistrationCloseDate: 2025-08-17

Spring 2026
  StartDate: 2026-01-12  EndDate: 2026-05-15
  RegistrationOpenDate: 2025-09-01  RegistrationCloseDate: 2026-01-11

Summer 2026
  StartDate: 2026-05-26  EndDate: 2026-08-14
  RegistrationOpenDate: 2026-03-01  RegistrationCloseDate: 2026-05-25
  Sessions:
    Summer Session 1: 2026-05-26 to 2026-07-03
    Summer Session 2: 2026-06-26 to 2026-08-14
    (overlap 2026-06-26 to 2026-07-03 — confirm intentional)

Should I create all of these records?
```

## Completion Summary (Workflow step 10)

```text
Academic Year created: Academic Year 2025-2026 (2025-08-18 to 2026-08-14)

Terms created: 3
  Fall 2025: 2025-08-18 to 2025-12-12
  Spring 2026: 2026-01-12 to 2026-05-15
  Summer 2026: 2026-05-26 to 2026-08-14

Sessions created: 2
  Summer Session 1: 2026-05-26 to 2026-07-03 (parent: Summer 2026)
  Summer Session 2: 2026-06-26 to 2026-08-14 (parent: Summer 2026)
  Overlap 2026-06-26 to 2026-07-03 confirmed intentional by user.

Linkage: Academic Year -> Terms (AcademicYearId) -> Sessions (AcademicTermId)
```

## On-Demand Verification — Calendar View

```text
| Record Type | Name              | Start Date  | End Date    | Duration | Registration Open | Registration Close | Add/Drop     |
|-------------|-------------------|-------------|-------------|----------|--------------------|---------------------|--------------|
| Term        | Summer 2026       | 2026-05-26  | 2026-08-14  | 11 weeks | 2026-03-01         | 2026-05-25          | -            |
| Session     | Summer Session 1  | 2026-05-26  | 2026-07-03  | 6 weeks  | -                  | -                   | 2026-06-11   |
| Session     | Summer Session 2  | 2026-06-26  | 2026-08-14  | 7 weeks  | -                  | -                   | 2026-07-16   |

Overlap: Summer Session 1 and Summer Session 2 overlap 2026-06-26 to 2026-07-03 (1 week).
```
