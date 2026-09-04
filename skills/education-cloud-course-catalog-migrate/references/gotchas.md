# Gotchas

| Issue | Resolution |
|-------|------------|
| CSV column headers don't match expected names | Infer column mapping from context (e.g., "Code" → course code, split via `scripts/split_course_code.py` into SubjectAbbreviation/CourseNumber — not CipCode, see step 8/9; "Title" → Name, "Credits" → Duration) |
| Credit hours stored as "3.0 credits" instead of numeric | Parse and extract numeric value, set DurationUnit = "Credit Hours" |
| Course codes have inconsistent formatting | Normalize before creating (e.g., "BIO 201" → "BIO-201", "bio-201" → "BIO-201") |
| PDF has multi-column layout | Text extraction may be out of order — validate course sequence makes sense |
| Website has pagination | Fetch all pages before parsing (detect "next page" links and loop) |
| Missing Business Account ID | Ask the user to supply the Account Id (ProviderId), read a known Account with `GET /services/data/vXX.X/sobjects/Account/<id>`, or look it up by name with a SOQL `/query` (confirmed routable via headless-360) |
| Course type values don't match Education Cloud picklist | Map common values (e.g., "Lec" → "Lecture", "Laboratory" → "Lab", "Drill" → "Drill", "Recitation" → "Recitation") |
| Composite API returns partial success | Check response for each record — some may fail while others succeed (allOrNone = false) |
| Two-object create pattern complexity | Create Learning records first (store IDs), then create LearningCourse records with LearningId lookups |
| Source value not in describe's picklist list (e.g. DurationUnit = "Program Points") | `restrictedPicklist: true` means only active-today values are valid, not that the set is closed — offer the user the option to add the new picklist value via metadata, in addition to remapping or placeholder options. Do not assume it's a dead end |

More edge-case gotchas (linked-course mapping, enrollment conflicts, sharing defaults, describe caching, ambiguous subject codes, post-write visibility, record-type-scoped picklists, shell-out stalls): see `references/gotchas-detail.md`.
