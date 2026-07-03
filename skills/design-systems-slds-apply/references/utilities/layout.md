---
id: slds.guidance.utilities.layout
title: Layout Utilities
description: SLDS layout utility classes for global spacing and component connection
summary: "Utilities for global spacing (has-buffer, has-full-bleed, magnet utilities). Provides consistent buffer margins, full-bleed layouts, and seamless card connections."

artifact_type: reference
domain: utilities
topic: layout

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.hooks.spacing

tags: [utilities, layout, spacing, magnet]
keywords: [slds-has-buffer, slds-has-full-bleed, slds-has-magnet]
---

# Layout - Global Spacing & Component Connection

Global spacing management and seamless component connections.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-has-buffer` | Applies consistent global margin using `--slds-g-spacing-3` token |
| `slds-has-full-bleed` | Removes all margins to create full-bleed layouts |
| `slds-has-bottom-magnet` | Removes bottom margin and border radius to connect with element below |
| `slds-has-top-magnet` | Removes top margin and border radius to connect with element above |

## Common Patterns

### Standard Buffer Spacing
```html
<!-- Apply consistent spacing around cards -->
<div class="slds-card slds-has-buffer">
  <div class="slds-card__header">Card with buffer margin</div>
  <div class="slds-card__body">Content has global spacing on all sides</div>
</div>
```

### Full-Bleed Hero Section
```html
<!-- Remove margins for edge-to-edge layouts -->
<div class="slds-page-header slds-has-full-bleed">
  <div class="slds-page-header__row">
    <div class="slds-page-header__col-title">Full-width header with no margins</div>
  </div>
</div>
```

### Connected Card Components
```html
<!-- Connect two cards vertically without gap -->
<div class="slds-card slds-has-bottom-magnet">
  <div class="slds-card__header">First Card</div>
  <div class="slds-card__body">This card connects to the one below</div>
</div>
<div class="slds-card slds-has-top-magnet">
  <div class="slds-card__header">Second Card</div>
  <div class="slds-card__body">Appears seamlessly connected to card above</div>
</div>
```

### Multiple Connected Components
```html
<!-- Chain multiple cards together -->
<div class="slds-box slds-has-bottom-magnet">
  <h2>Section Header</h2>
</div>
<div class="slds-card slds-has-top-magnet slds-has-bottom-magnet">
  <div class="slds-card__body">Middle card connected on both sides</div>
</div>
<div class="slds-box slds-has-top-magnet">
  <p>Footer content</p>
</div>
```

### Combined Buffer and Magnet
```html
<!-- Use buffer with magnet for special layouts -->
<div class="slds-card slds-has-buffer slds-has-bottom-magnet">
  <div class="slds-card__body">Card with side margins but connected below</div>
</div>
<div class="slds-card slds-has-top-magnet slds-has-buffer">
  <!-- Special case: removes bottom margin, border-radius, top border, and box-shadow -->
  <div class="slds-card__body">Connected card with modified buffer behavior</div>
</div>
```

## Best Practices

✅ Use `slds-has-buffer` on cards and boxes for consistent component spacing
✅ Apply magnet utilities to Cards, Page Headers, and Box components
✅ Use `slds-has-bottom-magnet` on the top component and `slds-has-top-magnet` on the bottom component
✅ Use `slds-has-full-bleed` for hero sections and full-width backgrounds

❌ Avoid using magnet utilities on non-card-like elements
❌ Do not mix magnet utilities with custom margin styles
❌ Never apply `slds-has-full-bleed` to components that need spacing
❌ Do not use magnet utilities when visual separation is needed