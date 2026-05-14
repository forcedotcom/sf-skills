<!-- Parent: building-omnistudio-flexcard/SKILL.md -->

# FlexCard Best Practices

## Layout Design Patterns

### Single Card

Use for displaying summary information about a single record. Group related fields into logical sections.

```
┌──────────────────────────────────┐
│  Header: Record Name             │
├──────────────────────────────────┤
│  Section 1: Key Details          │
│  ┌────────────┬─────────────┐    │
│  │ Field A    │ Field B     │    │
│  │ Field C    │ Field D     │    │
│  └────────────┴─────────────┘    │
├──────────────────────────────────┤
│  Section 2: Status               │
│  ┌──────────────────────────┐    │
│  │ Status Badge  │ Date     │    │
│  └──────────────────────────┘    │
├──────────────────────────────────┤
│  [Action Button 1] [Action 2]   │
└──────────────────────────────────┘
```

**Guidelines:**
- Limit to 8-10 fields per card to avoid information overload
- Place the most important fields in the top section
- Use consistent field alignment (label-left or label-top)
- Group related fields in the same row when they share context

### Card List

Use for displaying a collection of related records. Each card in the list renders from one item in the data source array.

```
┌──────────────────────────────────┐
│  Card 1: Record A                │
│  Field 1 | Field 2 | [Action]   │
├──────────────────────────────────┤
│  Card 2: Record B                │
│  Field 1 | Field 2 | [Action]   │
├──────────────────────────────────┤
│  Card 3: Record C                │
│  Field 1 | Field 2 | [Action]   │
└──────────────────────────────────┘
  Showing 1-3 of 15  [Next →]
```

**Guidelines:**
- Keep each list card compact (3-5 fields maximum)
- Include a clear identifier field (Name, Title, or ID) in each card
- Add pagination when the data source can return more than 10 records
- Use consistent card height to maintain visual rhythm
- Provide a "View All" link when the list is truncated

### Tabbed Card

Use when a single record has multiple contexts worth displaying. Each tab represents a different state with its own data source or field set.

```
┌──────────────────────────────────┐
│  [Tab 1: Overview] [Tab 2: History] [Tab 3: Related] │
├──────────────────────────────────┤
│  Tab 1 Content                   │
│  ┌──────────────────────────┐    │
│  │ Fields for this context  │    │
│  └──────────────────────────┘    │
└──────────────────────────────────┘
```

**Guidelines:**
- Limit to 3-5 tabs to avoid horizontal overflow
- Use concise tab labels (1-2 words)
- Load non-active tab data lazily (on tab selection)
- Mark the default active tab based on the most common use case

### Flyout Card

Use for progressive disclosure: show a summary, then expand for details on demand.

```
┌──────────────────────────────────┐
│  Summary: Key Fields  [▼ More]   │
└──────────────────────────────────┘
       ↓ (on click)
┌──────────────────────────────────┐
│  Summary: Key Fields  [▲ Less]   │
├──────────────────────────────────┤
│  Detail Section                  │
│  Additional fields, history,     │
│  related records, etc.           │
└──────────────────────────────────┘
```

**Guidelines:**
- Keep the summary to 2-3 fields that answer "what is this?"
- Load flyout content on demand, not on initial card render
- Provide a clear visual indicator for the expand/collapse action
- Maintain the flyout state if the user scrolls away and returns

---

## Data Source Optimization

### Minimize IP Calls

- Use a single IP that returns all required data rather than multiple IPs for individual fields
- If the card has multiple data sources, ensure they do not query overlapping data
- Cache IP responses where the data does not change frequently (use IP caching options)

### Input Parameter Efficiency

- Pass only the parameters the IP needs; do not forward the entire page context
- Use `{recordId}` as the primary context parameter for record-level cards
- Avoid passing large objects as input parameters; pass IDs and let the IP query

### Response Structure

- Design IP responses to match the FlexCard's field mapping structure directly
- Avoid deep nesting in IP responses when the FlexCard only needs top-level fields
- Use `resultListPath` to point directly to the array node in list-type cards

### Error Handling in Data Sources

- Configure a fallback state for when the IP returns an error
- Set reasonable timeout values for data source calls
- Log data source errors for debugging without exposing raw error messages to end users

---

## Action Configuration

### OmniScript Launch Actions

| Consideration | Guidance |
|---------------|----------|
| **Parameter mapping** | Map card data fields to OmniScript input fields explicitly |
| **Pre-population** | Pass enough context for the OmniScript to pre-fill known values |
| **Return handling** | Refresh the FlexCard data source after the OmniScript completes |
| **Error states** | Handle the case where the OmniScript fails or is cancelled |

### Navigation Actions

| Consideration | Guidance |
|---------------|----------|
| **Record navigation** | Use `{recordId}` merge fields, not hardcoded IDs |
| **URL navigation** | Use relative URLs for internal Salesforce navigation |
| **External URLs** | Open in a new tab; warn users if leaving Salesforce |
| **Conditional navigation** | Disable navigation buttons when the target is invalid |

### Action Button Placement

- Place primary actions at the bottom of the card or in the card header
- Limit to 2-3 actions per card; use a "More Actions" overflow menu for additional actions
- Use descriptive button labels ("Submit Claim", not "Submit" or "Go")
- Visually distinguish primary actions (filled button) from secondary actions (outline button)

---

## SLDS Compliance for Styling

### Required Practices

- Use SLDS design tokens for all colors, spacing, font sizes, and border radii
- Use `slds-card` or `slds-tile` patterns for card containers
- Use `slds-grid` and `slds-col` for multi-column layouts within cards
- Apply `slds-text-heading_small` and related text utilities for consistent typography

### Color Usage

```
Correct:  Use SLDS token  →  var(--slds-g-color-brand-base-50)
Wrong:    Hardcoded hex    →  #0176d3
Wrong:    Hardcoded rgb    →  rgb(1, 118, 211)
```

- Status indicators: use `slds-badge` with appropriate color variants
- Background colors: use `slds-box` with `slds-theme_shade` or `slds-theme_default`
- Text colors: rely on inherited SLDS text colors; override only when necessary

### Spacing

- Use SLDS spacing utilities: `slds-m-top_small`, `slds-p-around_medium`, etc.
- Maintain consistent spacing between card sections (use `slds-m-bottom_medium`)
- Do not use pixel values directly; map to the SLDS spacing scale

### Dark Mode Compatibility

- All colors must come from SLDS CSS custom properties (`--slds-g-color-*`)
- Test card rendering in both light and dark modes
- Avoid background images that only work on light backgrounds
- Use `currentColor` for icon fills so they adapt to the text color

---

## Accessibility Requirements

### Interactive Elements

- Every button must have an `aria-label` or visible text label
- Links must have descriptive text (not "Click here" or "Learn more" without context)
- Icon-only buttons require `aria-label` describing the action

### Keyboard Navigation

- All action buttons must be focusable via Tab key
- Buttons must activate on Enter and Space key presses
- Tab order must follow the visual reading order (top-to-bottom, left-to-right)
- Flyout expand/collapse must be keyboard accessible

### Screen Reader Support

- Use semantic heading elements for card titles and section headers
- Data fields should have associated labels readable by screen readers
- Status indicators must convey meaning through text, not color alone
- Dynamic content updates should use `aria-live` regions

### Color Contrast

- Text on card backgrounds must meet WCAG 2.1 AA contrast ratio (4.5:1)
- Interactive element boundaries must have 3:1 contrast against their background
- Do not use color as the sole method of conveying information (add icons or text)

---

## Performance with Large Data Sets

### Data Volume Guidelines

| Record Count | Recommended Approach |
|-------------|---------------------|
| 1-5 | Load all records in a single card list |
| 6-25 | Load with pagination (show 5-10 per page) |
| 26-100 | Server-side pagination via IP; load one page at a time |
| 100+ | Reconsider the UX; use search/filter instead of browsing |

### Rendering Performance

- Limit child card nesting to 2 levels maximum
- Avoid rendering more than 25 cards simultaneously in a card list
- Use conditional visibility to hide sections rather than rendering and hiding with CSS
- Lazy-load tab content and flyout details on user interaction

### Data Source Performance

- Set appropriate IP cache durations for data that does not change frequently
- Avoid chaining multiple IPs when a single IP can return all needed data
- Use `resultListPath` to avoid client-side data transformation
- Monitor IP execution times; optimize IPs that take longer than 2 seconds

---

## Child Card Composition

### When to Use Child Cards

- The parent card displays summary data and the child card shows related detail
- Multiple cards share a common layout pattern that should be defined once
- Different sections of a card require independent data sources

### Composition Guidelines

- Pass data from parent to child via input parameters, not global variables
- Keep child cards self-contained: they should work independently for testing
- Limit nesting to 2 levels (parent → child → grandchild maximum)
- Document the parent-child data flow in the FlexCard's description

### Data Flow Pattern

```
Parent FlexCard
  ├── Data Source: IP_GetAccountSummary
  │     └── Passes {AccountId} to child
  └── Child FlexCard: AccountContacts
        └── Data Source: IP_GetContacts
              └── Input: {AccountId} from parent
```

### Avoiding Composition Anti-Patterns

| Anti-Pattern | Problem | Solution |
|-------------|---------|----------|
| Deep nesting (3+ levels) | Performance degradation, hard to debug | Flatten the structure; combine data in the IP |
| Shared mutable state | Child cards modifying parent data | Use one-way data flow (parent → child only) |
| Duplicate data sources | Same IP called by parent and child | Consolidate into parent data source; pass results down |
| Tightly coupled children | Child card cannot function without parent | Design children to accept input parameters and work standalone |
