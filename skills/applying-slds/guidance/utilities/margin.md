---
id: slds.guidance.utilities.margin
title: Margin Utilities
description: SLDS margin utility classes for external spacing
summary: "Utilities for external spacing. Includes directional (top/right/bottom/left), aggregate (horizontal/vertical/around), and variable density classes. Base unit 4px with sizes from xxx-small (2px) to xx-large (48px)."

artifact_type: reference
domain: utilities
topic: margin

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.padding
  - slds.guidance.hooks.spacing

tags: [utilities, margin, spacing, external-spacing]
keywords: [slds-m, margin, external spacing, whitespace]
---

# Margin - External Spacing

External spacing between elements. Base unit: **4px**.

## Size Scale

| Size | Class Suffix | Value | Pixels |
|------|-------------|-------|--------|
| None | `none` | 0 | 0px |
| XXX Small | `xxx-small` | 0.125rem | 2px |
| XX Small | `xx-small` | 0.25rem | 4px |
| X Small | `x-small` | 0.5rem | 8px |
| Small | `small` | 0.75rem | 12px |
| Medium | `medium` | 1rem | 16px |
| Large | `large` | 1.5rem | 24px |
| X Large | `x-large` | 2rem | 32px |
| XX Large | `xx-large` | 3rem | 48px |

## Core Classes

### Directional Margins

| Class | Purpose |
|-------|---------|
| `slds-m-top_*` | Applies margin to the top edge |
| `slds-m-right_*` | Applies margin to the right edge |
| `slds-m-bottom_*` | Applies margin to the bottom edge |
| `slds-m-left_*` | Applies margin to the left edge |

### Aggregate Margins

| Class | Purpose |
|-------|---------|
| `slds-m-horizontal_*` | Applies margin to left and right edges |
| `slds-m-vertical_*` | Applies margin to top and bottom edges |
| `slds-m-around_*` | Applies margin to all four edges |

### Variable Density Classes

| Class | Purpose | Comfy | Compact |
|-------|---------|-------|---------|
| `slds-var-m-top_*` | Variable density top margin | Full size | 50% size |
| `slds-var-m-right_*` | Variable density right margin | Full size | 50% size |
| `slds-var-m-bottom_*` | Variable density bottom margin | Full size | 50% size |
| `slds-var-m-left_*` | Variable density left margin | Full size | 50% size |
| `slds-var-m-horizontal_*` | Variable density horizontal margins | Full size | 50% size |
| `slds-var-m-vertical_*` | Variable density vertical margins | Full size | 50% size |
| `slds-var-m-around_*` | Variable density all sides | Full size | 50% size |

## Common Patterns

```html
<!-- Card stack with consistent spacing -->
<div class="slds-card slds-m-bottom_medium">
  <!-- Card content -->
</div>
<div class="slds-card slds-m-bottom_medium">
  <!-- Card content -->
</div>
<div class="slds-card">
  <!-- Last card needs no bottom margin -->
</div>

<!-- Button group with horizontal spacing -->
<div class="slds-button-group">
  <button class="slds-button slds-button_neutral">Cancel</button>
  <button class="slds-button slds-button_brand slds-m-left_small">Save</button>
  <button class="slds-button slds-button_brand slds-m-left_small">Save & New</button>
</div>

<!-- Page sections with vertical rhythm -->
<section class="slds-m-vertical_large">
  <h2 class="slds-text-heading_medium slds-m-bottom_small">Section Title</h2>
  <div class="slds-m-bottom_medium">
    <!-- Section content -->
  </div>
</section>

<!-- Responsive form layout with variable density -->
<div class="slds-form-element slds-var-m-bottom_medium">
  <label class="slds-form-element__label">Field Label</label>
  <input class="slds-input" />
</div>
<div class="slds-form-element slds-var-m-bottom_medium">
  <label class="slds-form-element__label">Another Field</label>
  <input class="slds-input" />
</div>

<!-- Remove default margins when needed -->
<ul class="slds-m-around_none">
  <li>List item without inherited margins</li>
  <li>Another item</li>
</ul>
```

## Implementation Guidelines

### Standard Spacing Values

| Context | Recommended Class | Size |
|---------|------------------|------|
| Between cards/tiles | `slds-m-bottom_medium` | 16px |
| Between buttons | `slds-m-left_small` | 12px |
| Between form fields | `slds-m-bottom_medium` | 16px |
| Between page sections | `slds-m-vertical_large` | 24px |
| Icon to text | `slds-m-right_x-small` | 8px |
| Dense layouts | `slds-m-around_small` | 12px |
| Remove spacing | `slds-m-around_none` | 0px |

### Responsive Considerations

Use variable density classes for layouts that adapt to user preferences:
- Desktop comfy mode: Full spacing values
- Desktop compact mode: 50% reduced spacing
- Mobile: Consider using smaller sizes by default

## Best Practices

✅ Use `slds-m-bottom_medium` (16px) between stacked components
✅ Use `slds-m-left_small` (12px) between inline buttons
✅ Use `slds-m-vertical_large` (24px) between major page sections
✅ Use `slds-m-around_none` to remove default element margins
✅ Use variable density classes (`slds-var-m-*`) for responsive layouts
✅ Apply margins to the element that needs spacing from its siblings

❌ Don't use margins larger than `xx-large` (48px)
❌ Don't apply both top and bottom margins when one suffices
❌ Don't mix standard and variable density classes on the same element
❌ Don't use margin for internal spacing - use [Padding Utilities](ref:slds.guidance.utilities.padding) instead