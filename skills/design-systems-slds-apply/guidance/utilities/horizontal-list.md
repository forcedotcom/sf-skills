---
id: slds.guidance.utilities.horizontal-list
title: Horizontal List Utilities
description: SLDS horizontal list utility classes
summary: "Utilities for horizontal lists with flexbox and divider variants."

artifact_type: reference
domain: utilities
topic: horizontal-list

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities

tags: [utilities, horizontal-list, flexbox, dividers]
keywords: [slds-list_horizontal, slds-has-dividers_left, slds-has-dividers_right, horizontal list, list dividers]
---

# Horizontal List - Flexbox Lists with Dividers

Creating horizontal lists with flexbox layout and optional dividers.

**Note:** Divider classes require the `slds-list_horizontal` base class and must use directional variants (`_left` or `_right`).

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-list_horizontal` | Creates a flex container for horizontal list layout |
| `slds-list_horizontal-large` | Adds padding to child links (12px block, 16px inline) |
| `slds-has-dividers_left` | Adds 2px circular dividers on the left side of items (requires `slds-list_horizontal`) |
| `slds-has-dividers_right` | Adds 2px circular dividers on the right side of items (requires `slds-list_horizontal`) |

## Common Patterns

### Basic Horizontal List
```html
<!-- Simple horizontal list with flexbox layout -->
<ul class="slds-list_horizontal">
  <li class="slds-list__item">Home</li>
  <li class="slds-list__item">Products</li>
  <li class="slds-list__item">Services</li>
  <li class="slds-list__item">Contact</li>
</ul>
```

### Horizontal List with Left Dividers
```html
<!-- Horizontal list with dot dividers on the left of each item -->
<ul class="slds-list_horizontal slds-has-dividers_left">
  <li class="slds-list__item">View All</li>
  <li class="slds-list__item">Recently Viewed</li>
  <li class="slds-list__item">Created by Me</li>
</ul>
```

### Large Horizontal List with Links
```html
<!-- Large variant with padding on anchor elements -->
<ul class="slds-list_horizontal slds-list_horizontal-large">
  <li class="slds-list__item">
    <a href="/home">Home</a>
  </li>
  <li class="slds-list__item">
    <a href="/about">About</a>
  </li>
  <li class="slds-list__item">
    <a href="/contact">Contact</a>
  </li>
</ul>
```

### List with Left-side Dividers and Large Spacing
```html
<!-- Dividers appear on the left of each item with large padding -->
<ul class="slds-list_horizontal slds-list_horizontal-large slds-has-dividers_left">
  <li class="slds-list__item"><a href="/first">First Item</a></li>
  <li class="slds-list__item"><a href="/second">Second Item</a></li>
  <li class="slds-list__item"><a href="/third">Third Item</a></li>
</ul>
```

### List with Right-side Dividers
```html
<!-- Dividers appear on the right of each item except last -->
<ul class="slds-list_horizontal slds-has-dividers_right">
  <li class="slds-list__item">Option A</li>
  <li class="slds-list__item">Option B</li>
  <li class="slds-list__item">Option C</li>
</ul>
```

## Best Practices

✅ Use `slds-list_horizontal` on the list container (`<ul>` or `<ol>`)
✅ Apply `slds-list__item` to each list item for proper structure
✅ Use `slds-has-dividers_left` or `slds-has-dividers_right` with `slds-list_horizontal` for dividers
✅ Use `slds-list_horizontal-large` when links need 12px vertical and 16px horizontal padding
✅ Divider classes always require the `slds-list_horizontal` base class

❌ Do not combine multiple divider classes on the same element
❌ Do not apply horizontal list classes to non-list elements
❌ Do not nest horizontal lists without proper spacing
❌ Do not override the 2px divider size with custom CSS