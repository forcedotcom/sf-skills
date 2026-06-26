# LWC Template: Record Form Mockup

## Prompt Template

```
Salesforce Lightning Web Component record form mockup:

COMPONENT: lightning-record-form style

HEADER:
- Object icon and label
- Edit/Save/Cancel buttons (right)
- Record name as title

LAYOUT:
- Two-column layout for desktop
- Responsive single column for mobile

SECTIONS:
[Define sections with fields]

FIELD TYPES:
- Text inputs with labels above
- Picklists as dropdown
- Lookups with search icon
- Date pickers with calendar
- Currency with formatting
- Checkboxes for boolean

STYLING:
- SLDS record page styling
- Compact spacing
- Blue section headers
- Required field indicators (*)
- Help text icons where applicable
```

## Example

```bash
gemini "/generate 'Salesforce LWC record form mockup:
Object: Opportunity
Mode: Edit

Sections:
1. Opportunity Information:
   - Opportunity Name* (text)
   - Account Name* (lookup with search)
   - Type (picklist)
   - Lead Source (picklist)

2. Amount & Dates:
   - Amount (currency)
   - Close Date* (date picker)
   - Stage* (picklist)
   - Probability (percentage)

Footer: Save and Cancel buttons
Style: SLDS, professional, desktop view'"
```
