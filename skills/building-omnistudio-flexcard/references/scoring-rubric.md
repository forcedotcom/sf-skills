# FlexCard Scoring Rubric: Breakdown Detail

Detailed point-by-point scoring criteria for the 130-point FlexCard validation. Read during Phase 3 when running the full scoring rubric.

## Design & Layout (25 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Layout type matches use case | 5 | Single, list, tabbed, or flyout chosen appropriately |
| Field grouping is logical | 5 | Related fields are visually grouped together |
| Responsive behavior | 5 | Card adapts to different viewport widths |
| Consistent spacing | 5 | Margins and padding follow SLDS (Salesforce Lightning Design System) spacing scale |
| Visual hierarchy | 5 | Primary information is prominent, secondary is de-emphasized |

## Data Binding (20 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| IP references are valid | 5 | All referenced IPs exist and are active |
| Merge field syntax correct | 5 | `{datasource.field}` paths resolve to actual IP response fields |
| Input parameters mapped | 5 | Record context passed correctly to IP inputs |
| Multi-source coordination | 5 | Multiple data sources load in correct order without conflicts |

## Actions & Navigation (20 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Action buttons functional | 5 | All buttons trigger their configured actions |
| OmniScript params mapped | 5 | Context data flows correctly into launched OmniScripts |
| Navigation targets valid | 5 | Record and URL navigation resolves correctly |
| Labels are descriptive | 5 | Action labels clearly communicate what the action does |

## Styling (20 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| SLDS tokens used | 5 | Colors, fonts, spacing via design tokens |
| Consistent typography | 5 | Text sizes follow SLDS type scale |
| Card pattern compliance | 5 | Uses standard SLDS card or tile patterns |
| Dark mode compatible | 5 | No hardcoded colors; works with SLDS dark theme |

## Accessibility (15 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| ARIA labels on interactive elements | 5 | Buttons, links, and inputs have accessible names |
| Keyboard navigable | 5 | All actions reachable via Tab, activated via Enter/Space |
| Color contrast sufficient | 5 | Meets WCAG 2.1 AA contrast ratio (4.5:1 for text) |

## Testing (15 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Populated data verified | 3 | Card renders correctly with full data |
| Empty state verified | 3 | Empty-state message displays properly |
| Error state verified | 3 | Graceful handling of IP errors |
| Multi-record verified | 3 | Card list renders correct items |
| Mobile viewport verified | 3 | Layout adapts to small screens |

## Performance (15 points)

| Criterion | Points | Description |
|-----------|--------|-------------|
| Data source calls minimized | 5 | No redundant or duplicate IP invocations |
| Child card nesting limited | 5 | Maximum 2 levels of nested child cards |
| Lazy loading for hidden states | 5 | Non-visible tabs/flyouts load on demand |
