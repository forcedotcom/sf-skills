---
id: slds.guidance.utilities.floats
title: Floats Utilities
description: SLDS float and clearfix utility classes for legacy layouts
summary: "Utilities for floating elements (float left/right/none, clear, clearfix). Mark as legacy - prefer Grid for new implementations."

artifact_type: reference
domain: utilities
topic: floats

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.grid

tags: [utilities, floats, clearfix, legacy]
keywords: [slds-float, slds-clear, slds-clearfix, float-left, float-right]
---

# Floats - Legacy Layout Utilities

Utilities for floating elements and clearing floats. **Legacy approach** - use Grid utilities for new implementations.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-float_left` | Floats element to the left using `inline-start` for RTL support |
| `slds-float_right` | Floats element to the right using `inline-end` for RTL support |
| `slds-float_none` | Removes float from an element with existing float |
| `slds-clear` | Clears floats on both sides with `clear: both` |
| `slds-clearfix` | Contains floats using `::after` pseudo-element technique |

## Common Patterns

### Basic Float Layout
```html
<!-- Image floated left with text wrapping -->
<div class="slds-clearfix">
  <img class="slds-float_left" src="avatar.jpg" alt="User avatar" />
  <p>Content wraps around the floated image on the left side.</p>
</div>
```

### Two-Column Float Layout
```html
<!-- Legacy two-column layout with floats -->
<div class="slds-clearfix">
  <div class="slds-float_left" style="width: 30%;">
    <!-- Sidebar content floated left -->
    <nav>Navigation items</nav>
  </div>
  <div class="slds-float_right" style="width: 65%;">
    <!-- Main content floated right -->
    <main>Main content area</main>
  </div>
</div>
```

### Clear Float After Element
```html
<!-- Clear floats to prevent wrapping -->
<div>
  <div class="slds-float_left">Floated element</div>
  <div class="slds-clear">This element starts below the float</div>
</div>
```

### Remove Float Conditionally
```html
<!-- Remove float at certain breakpoints -->
<div class="slds-float_left slds-medium-float_none">
  <!-- Floats on small screens, no float on medium+ -->
  Responsive float behavior
</div>
```

### Clearfix Container Pattern
```html
<!-- Parent contains all floated children -->
<section class="slds-clearfix">
  <div class="slds-float_left">Left column</div>
  <div class="slds-float_left">Center column</div>
  <div class="slds-float_right">Right column</div>
  <!-- Parent expands to contain all floats -->
</section>
```

## Best Practices

✅ Use [Grid Utilities](ref:slds.guidance.utilities.grid) (`slds-grid`) for new layouts instead of floats
✅ Apply `slds-clearfix` to parent containers of floated elements
✅ Place floated elements first in document flow, even when floating right
✅ Use `slds-float_none` to remove floats at specific breakpoints

❌ Do not use floats for complex multi-column layouts - use [Grid Utilities](ref:slds.guidance.utilities.grid)
❌ Do not forget `slds-clearfix` on parent containers - causes collapse
❌ Do not mix floats with flexbox or grid on the same element

## Migration Note

**Float utilities are legacy.** For new implementations, see [Grid Utilities](ref:slds.guidance.utilities.grid):
- Use `slds-grid` and `slds-col` for multi-column layouts
- Use `slds-grid_align-spread` for spacing elements apart
- Use `slds-grid_pull-padded` for content wrapping patterns

## Technical Details

- **Logical Properties**: Uses `inline-start` and `inline-end` for RTL support
- **Clearfix Method**: Implements `::after` pseudo-element with `display: table`
- **Browser Support**: Works in all supported browsers including IE11