---
id: slds.guidance.utilities.borders
title: Borders Utilities
description: SLDS directional border utility classes
summary: "Utilities for applying borders to specific edges of elements."

artifact_type: reference
domain: utilities
topic: borders

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.box
  - slds.guidance.utilities.margin
  - slds.guidance.utilities.padding
  - slds.guidance.hooks.borders

tags: [utilities, borders]
keywords: [slds-border_top, slds-border_bottom, slds-border_left, slds-border_right]
---

# Borders - Directional Border Utilities

Utilities for applying 1px solid borders to specific edges of elements.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-border_top` | Adds a 1px solid border to the top edge |
| `slds-border_bottom` | Adds a 1px solid border to the bottom edge |
| `slds-border_left` | Adds a 1px solid border to the left edge |
| `slds-border_right` | Adds a 1px solid border to the right edge |

**Properties**: All borders use `var(--slds-g-sizing-border-1)` (1px) width and `var(--slds-g-color-border-1)` color.

## Common Patterns

### Section Divider
```html
<!-- Divider between content sections -->
<section class="slds-border_bottom slds-p-vertical_medium">
  <h2>Section Title</h2>
  <p>Section content here</p>
</section>
```

### Accent Bar Card
```html
<!-- Card with colored left accent border -->
<div class="slds-card slds-border_left" style="border-left-width: 4px; border-left-color: var(--slds-g-color-brand-base-60);">
  <div class="slds-card__body">
    <h3>Featured Content</h3>
    <p>Card content with brand accent</p>
  </div>
</div>
```

### Status Message with Border Accent
```html
<!-- Success message with green left border -->
<div class="slds-p-around_medium slds-border_left" style="border-left-width: 4px; border-left-color: var(--slds-g-color-success-base-50);">
  <strong>Success:</strong> Record saved successfully.
</div>
```

### Top Border for Card Header
```html
<!-- Card with top border separator -->
<div class="slds-card">
  <div class="slds-card__header slds-border_top">
    <h2 class="slds-card__header-title">Card Title</h2>
  </div>
  <div class="slds-card__body slds-card__body_inner">
    Card content
  </div>
</div>
```

### Bottom Border for List Items
```html
<!-- List with bottom borders -->
<ul class="slds-has-dividers_bottom-space">
  <li class="slds-item slds-border_bottom slds-p-vertical_small">
    List item one
  </li>
  <li class="slds-item slds-border_bottom slds-p-vertical_small">
    List item two
  </li>
  <li class="slds-item slds-p-vertical_small">
    List item three (no border)
  </li>
</ul>
```

## Best Practices

✅ Use `slds-border_bottom` for section dividers
✅ Use `slds-border_left` with 4px width for accent bars on cards and messages
✅ Combine border utilities with spacing utilities for layout control
✅ Use inline styles with design tokens for custom border colors
✅ Use `slds-border_top` for visual separation in card headers

❌ Never apply multiple directional border classes to the same element
❌ Never use arbitrary color values instead of design tokens
❌ Never override the default 1px width without specific design requirements
❌ Never use border utilities when a component has built-in border styling

## Token Reference

### Border Tokens
- **Width**: `var(--slds-g-sizing-border-1)` (1px)
- **Color**: `var(--slds-g-color-border-1)` (default gray)

### Common Color Overrides
- **Brand**: `var(--slds-g-color-brand-base-60)`
- **Success**: `var(--slds-g-color-success-base-50)`
- **Warning**: `var(--slds-g-color-warning-base-60)`
- **Error**: `var(--slds-g-color-error-base-50)`

## Related Utilities

- **Box Utilities** - For containers with borders and padding, see [Box Utilities](ref:slds.guidance.utilities.box)
- **Spacing Utilities** - For padding and margins, see [Margin](ref:slds.guidance.utilities.margin) and [Padding](ref:slds.guidance.utilities.padding) utilities
