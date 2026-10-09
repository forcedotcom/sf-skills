# Hierarchy Visualization Examples

Formatting templates for displaying institutional structure to users.

## Nested Bullet Format (Recommended)

Used in Steps 3 and 10 to show hierarchy structure.

### Example 1: Simple 3-Campus Structure

```text
System: Riverside Community College System
├─ Campus: Main Campus
│  ├─ College: School of Arts & Sciences
│  │  ├─ Department: English Department
│  │  ├─ Department: Mathematics Department
│  │  └─ Department: Social Sciences Department
│  ├─ College: School of Business
│  │  ├─ Department: Accounting Department
│  │  └─ Department: Management Department
│  └─ College: School of Health Sciences
│     ├─ Department: Nursing Department
│     └─ Department: Allied Health Department
├─ Campus: North Campus
│  ├─ College: School of Arts & Sciences
│  │  └─ Department: Liberal Arts Department
│  └─ College: Technical Education
│     ├─ Department: Automotive Technology Department
│     └─ Department: Computer Science Department
└─ Campus: South Campus
   ├─ College: School of Arts & Sciences
   │  └─ Department: Humanities Department
   └─ College: Workforce Development
      └─ Department: Continuing Education Department
```text

### Formatting Rules

- Use box-drawing characters: `├─` (U+251C U+2500, branch with children below), `└─` (U+2514 U+2500, last branch at this level), `│` (U+2502, vertical continuation line)
- Indent each level by 3 spaces; always include the level label (`System:`, `Campus:`, `College:`, `Department:`)
- For the last item at a level use `└─`; for items with children continue the `│` line through them

---

## Compact Text Format

Used when user asks for quick summary or spot-check.

### Example: Full Path Display

**User asks**: "Show me the path for English Department"

**Output**:
```text
Complete path for English Department:

Level 1 (System): Riverside Community College System
└─ Level 2 (Campus): Main Campus
   └─ Level 3 (College): School of Arts & Sciences
      └─ Level 4 (Department): English Department

Business Profile: Linked
Parent relationships: All verified
Materialized path: Riverside Community College System / Main Campus / School of Arts & Sciences / English Department
```text

---

## Summary Statistics Format

Used in final output (Step 10) after all records created.

### Example: Creation Success

```text
Institutional hierarchy created successfully!

Created:
• 1 System Account (Riverside Community College System)
• 3 Campus Accounts (Main, North, South)
• 7 College Accounts (across all campuses)
• 12 Department Accounts (across all colleges)
• 23 Business Profiles (linked to all accounts)

Total: 23 Account records with proper parent-child relationships

Hierarchy verification: Complete (parent chains valid, 0 orphans)
Business Profiles: All linked

Would you like me to:
• Show the complete path for a specific department?
• Verify any account in the hierarchy?
• Export this structure summary?
```text

### Example: Partial Success with Errors

```text
⚠️ Institutional hierarchy created with errors

Created:
• 1 System Account (Riverside Community College System)
• 3 Campus Accounts (Main, North, South)
• 7 College Accounts (across all campuses)
• 12 Department Accounts (across all colleges)
• 21 of 23 Business Profiles created

Status: Account hierarchy is fully functional — all parent-child relationships valid.

Failed Business Profiles:
• Nursing Department (Main Campus → School of Health Sciences)
• Allied Health Department (Main Campus → School of Health Sciences)

Impact: These 2 departments cannot use Education Cloud features (course offerings, enrollment tracking) until Business Profiles are created.

Would you like me to retry creating the 2 missing Business Profiles?
```text

---

## Materialized Path Format

Used when displaying semantic anchors or full paths. The path is **not a stored field** — derive it on the fly by GET-ing the Account and walking its ParentId chain up to the System root, then joining the ancestor Names.

### Format Rules

- Separator: ` / ` (space-slash-space)
- Order: System → Campus → College → Department (root first, walked from the leaf up then reversed)
- Use full names, not abbreviations
- Example: `Riverside Community College System / Main Campus / School of Arts & Sciences / English Department`

### Display in Verification Output

```text
Materialized paths (derived from ParentId chains):

• Main Campus → School of Business → Accounting Department
  Path: Riverside Community College System / Main Campus / School of Business / Accounting Department

• North Campus → Technical Education → Computer Science Department
  Path: Riverside Community College System / North Campus / Technical Education / Computer Science Department

All 23 accounts have valid materialized paths
```text

---

## Interactive Spot-Check Format

Used when user requests verification of specific accounts.

### Example: User asks "Show me where Biology Department is"

**Output**:
```text
Found: Biology Department

Full hierarchy:
Level 1 (System): State University
└─ Level 2 (Campus): Main Campus
   └─ Level 3 (College): College of Arts & Sciences
      └─ Level 4 (Department): Biology Department

Account details:
• Name: Biology Department
• Record Type: Business
• Parent: College of Arts & Sciences
• Business Profile: Linked
• Materialized Path: State University / Main Campus / College of Arts & Sciences / Biology Department

Siblings (other departments under College of Arts & Sciences):
• Chemistry Department
• Physics Department
```text
