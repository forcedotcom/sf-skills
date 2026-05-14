# ERD Template: Core Salesforce Objects (Architect.salesforce.com Style)

## Default Style

All ERDs now use the **official architect.salesforce.com aesthetic** by default:
- Dark border + light translucent fill boxes
- Header banner with Salesforce logo
- LEGEND bar with ENTITIES and RELATIONSHIPS
- Labeled relationship lines
- Footer with copyright

See `references/architect-aesthetic-guide.md` for full specification.

---

## Prompt Template (Architect.salesforce.com Style)

```
Create a Salesforce Core CRM ERD in the EXACT architect.salesforce.com style:

PAGE TITLE (very top, large bold text):
'Core CRM Overview Data Model'

HEADER SECTION (below title):
- Left: Salesforce cloud logo + 'SALESFORCE PLATFORM Overview' in dark teal (#0B827C) banner box
- Center: LEGEND with 'ENTITIES' section showing:
  * Cloud Entity box (dark teal #0B827C border, light teal ~25% opacity fill)
  * Related Entity box (dark teal border, lighter fill)
  * External Entity box (black border, white fill)
- Right: 'RELATIONSHIPS' section showing notation symbols for Parent/Child, Required, Optional, Many-to-Many

BOX STYLING - CRITICAL:
- DARK BORDER: Solid 2px border in dark teal (#0B827C)
- LIGHT TRANSLUCENT FILL: Same teal hue at ~25% opacity
- Rounded corners (8-12px radius)
- Text in dark gray/black on the light fill

ENTITY BOX FORMAT:
┌─────────────────────────┐
│ Logical Name            │  (Bold, larger)
│ APIName                 │  (Smaller, italic, gray)
│ • Field1                │  (Bullet points)
│ • Field2                │
└─────────────────────────┘

OBJECTS TO INCLUDE (all with dark teal border + light teal fill):

- Account (center position):
  Account
  Account
  • Account Number
  • Name
  • Industry
  • Type

- Contact (linked to Account):
  Contact
  Contact
  • Name
  • Email
  • Title
  • Phone

- Opportunity (linked to Account):
  Opportunity
  Opportunity
  • Name
  • Amount
  • Close Date
  • StageName

- Case (linked to Account and Contact):
  Case
  Case
  • CaseNumber
  • Type
  • Priority
  • Status

RELATIONSHIP LINES:
- Thin black lines with text labels ON the lines
- Contact → Account: "child of" (crow's foot on Contact side)
- Opportunity → Account: "child of" (crow's foot on Opportunity side)
- Case → Account: "related to" (crow's foot on Case side)
- Case → Contact: "related to" (optional)
- STRAIGHT LINES ONLY (horizontal and vertical, no diagonals)

FOOTER:
Left: '©2024 Salesforce - Subject to change without notice'
Right: 'Last modified: [current date]'

CRITICAL: Dark teal borders with LIGHT translucent teal fill - NOT solid filled boxes.
```

---

## Usage

```bash
# Quick draft at 1K (iterate here)
gemini --yolo "/generate '[paste prompt above]'"
open ~/nanobanana-output/*.png  # Review and refine

# Final at 4K (when satisfied)
uv run scripts/generate_image.py \
  -p "[your refined prompt]" \
  -f "core-crm-erd.png" \
  -r 4K
open ~/nanobanana-output/*core-crm*.png
```

---

## Cloud Color Reference

| Cloud | Border Color | Fill (~25% opacity) |
|-------|--------------|---------------------|
| Sales Cloud | `#0B827C` (Teal) | Light Teal |
| Service Cloud | `#9E2A7D` (Magenta) | Light Pink |
| Platform | `#5A67D8` (Purple) | Light Purple |

---

## Resolution Guide

| Phase | Resolution | Use Case |
|-------|------------|----------|
| Draft | 1K (CLI) | Quick iteration, prompt refinement |
| Final | 4K (Python) | Documentation, presentations |

**Tip**: Iterate at 1K until layout is correct, then generate 4K final.
