# Hierarchy Parsing Rules

Decision logic for resolving ambiguous institutional structures during parsing.

**Key principle**: Support any number of hierarchy levels (2+). Do not assume fixed level names or depth. Infer structure from source content (nesting, indentation, headings, list structure).

## Parsing PDF Documents

### Noise Filtering

Before parsing hierarchy content, drop lines matching common noise patterns (case-insensitive):

Common noise indicators:
- Page numbers: `Page 1`, `1`, `- 2 -`
- Copyright symbols: `© 2025`, `® Company Name`
- URLs and email addresses
- Single-word lines at top/bottom of pages (likely headers/footers)

### Hierarchy Level Detection

**Approach**: Use indentation, list nesting, and keyword patterns to infer levels. Do not map to fixed level names (Campus/College/Department) — use whatever names appear in source.

| Pattern | Likely Level Type | Example |
|---------|------------------|---------|
| Contains "System", "District", all caps, or ends in "System" | Top level (System) | `RIVERSIDE COMMUNITY COLLEGE SYSTEM`, `State University System` |
| Contains "Campus", "Location", "Site", geographic qualifier | Geographic level | `Main Campus`, `North Location`, `Downtown Campus`, `Regional Center` |
| Contains "School of", "College of", "Faculty of" | Academic division | `School of Arts & Sciences`, `College of Engineering`, `Faculty of Medicine` |
| Contains "Department", "Dept", "Division", "Program" | Sub-division | `Computer Science Department`, `Accounting Dept`, `Marketing Division` |
| Contains "Unit", "Team", "Section", "Lab" | Lowest level | `Research Unit`, `Clinical Lab`, `Admissions Team` |

**If source has >4 levels**: Parse all levels. Store each node's level name exactly as it appears (e.g., "Region", "District", "Branch", "Unit").

### Ambiguous Cases

**Problem**: Child node appears without explicit parent.

**Example input**:
```text
Main Campus
North Campus
School of Business
School of Arts & Sciences
```text

**Resolution**:
1. If children appear immediately after a parent name without intervening parents → assign to that parent
2. If children appear in a separate section → ask user: "I found these nodes: [list]. Which parent does each belong to?"

**Problem**: Duplicate names across branches (e.g., "School of Arts & Sciences" under multiple parents).

**Example**:
```text
Main Campus
  - School of Arts & Sciences
North Campus
  - School of Arts & Sciences
```text

**Resolution**:
Append parent name in parentheses:
- `School of Arts & Sciences (Main Campus)`
- `School of Arts & Sciences (North Campus)`

## Parsing Website HTML

### Content Extraction Priority

1. **Navigation menus**: Look for `<nav>` elements with class names like `campus-nav`, `org-structure`, `hierarchy`
2. **Unordered lists**: Parse `<ul>` with nested `<li>` elements as hierarchy levels — each nesting level = one hierarchy level
3. **Headings**: Use heading levels to infer hierarchy depth: `<h1>` → Level 0, `<h2>` → Level 1, `<h3>` → Level 2, etc.
4. **Breadcrumbs**: Extract hierarchy from breadcrumb navigation (`<nav aria-label="breadcrumb">`)

**Do not assume fixed mapping** (h2=Campus, h3=College). Just track relative depth: h1 is top, h2 is one level down, etc. Fetch the page, then read off the heading tags (`<h2>`, `<h3>`, `<h4>`, …) at each nesting depth. If HTML structure is non-standard, fall back to asking user for clarification.

## Parsing Plain Text Description

### Expected Format

Users may describe hierarchy in natural language:

> "We have Riverside Community College System with three campuses: Main Campus, North Campus, and South Campus. Main Campus has School of Business and School of Health Sciences. North Campus has Technical Education. Each school has departments."

### Extraction Strategy

1. **System**: First sentence often contains system name (top level)
2. **Level 1**: Look for keywords indicating first subdivision (campuses, regions, locations, branches)
3. **Level 2**: Look for "has", "includes", "contains" followed by organizational unit names (schools, colleges, divisions)
4. **Level 3+**: Look for nested indicators ("each X has Y", "programs:", "departments:"), or recursive "contains"/"includes" patterns

**Parse based on nesting depth, not fixed level names.** If text says "Region → District → Campus → College → Department", parse all 6 levels (including System).

### Validation Questions

Ask user to confirm when:
- Zero children found for a parent node
- Ambiguous parent-child relationship (e.g., "Computer Science" — is it at level 2 or level 3?)
- Unusual depth (1 level only, or >6 levels)

**Validation prompt template**:
```text
I extracted this structure:

System: [Name]
├─ Level 1: [Name]
│  └─ (No children found)
└─ Level 1: [Name]

Is this correct, or should I look for child nodes elsewhere?
```text

## Edge Cases

| Scenario | How to Handle |
|----------|---------------|
| Only 1 level below System (flat structure) | Ask user: "I found a flat structure — should I create this as-is, or do you have additional sub-levels?" |
| Multiple system-level entities | Clarify: "I found multiple top-level names — which one is the System?" |
| Children listed without parent | Ask: "Which parent do these nodes belong to: [list]" |
| Abbreviations in source (e.g., "CS Dept") | Expand to full name: "Computer Science Department" (ask user if unclear) |
| >6 hierarchy levels | Confirm: "I found [N] levels — is this correct, or should some levels be combined?" |

## Confidence Scoring

Before confirming structure with user, assess parsing confidence:

| Confidence | Criteria | Action |
|-----------|----------|--------|
| High | 2+ levels present, clear parent-child relationships, no duplicates | Proceed to confirmation |
| Medium | Ambiguity (duplicate names resolved, or single missing level) | Show structure and ask for confirmation |
| Low | Missing levels, unclear parent relationships, or extensive noise | Ask user for clarification before showing structure |

High/Medium confidence: show parsed structure and ask "Should I proceed?"

Low confidence: show what was extracted and ask "I had trouble parsing — can you clarify the structure?"
