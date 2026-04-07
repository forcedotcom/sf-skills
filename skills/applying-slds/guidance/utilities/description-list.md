---
id: slds.guidance.utilities.description-list
title: Description List Utilities
description: SLDS description list utility classes for semantic key-value displays
summary: "Utilities for creating description lists with inline and horizontal layout variants."

artifact_type: reference
domain: utilities
topic: description-list

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.hooks.spacing

tags: [utilities, description-list, layout, semantic]
keywords: [slds-dl_inline, slds-dl_horizontal, description-list, dl]
---

# Description List - Semantic Key-Value Layouts

Utilities for creating responsive description lists with inline and horizontal layouts.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-dl_inline` | Creates inline layout where terms and descriptions flow horizontally |
| `slds-dl_inline__label` | Marks the term (`<dt>`) in an inline description list |
| `slds-dl_inline__detail` | Marks the description (`<dd>`) in an inline description list |
| `slds-dl_horizontal` | Creates horizontal layout with 30/70 width split |
| `slds-dl_horizontal__label` | Marks the term (`<dt>`) with 30% width |
| `slds-dl_horizontal__detail` | Marks the description (`<dd>`) with 70% width |

## Layout Variants

### Inline Layout
Terms and descriptions display side-by-side in a flowing layout. Responsive at `min-width: 30em`.

| Property | Value |
|----------|-------|
| Term float | `inline-start` with `clear` |
| Description float | `inline-start` |
| Description padding | `--slds-g-spacing-1` (4px) |

### Horizontal Layout
Terms and descriptions align in columns with fixed proportions. Responsive at `min-width: 30em`.

| Property | Value |
|----------|-------|
| Layout | `flex` with `wrap` |
| Term width | 30% |
| Description width | 70% |
| Term padding | `--slds-g-spacing-3` (12px) end |

## Common Patterns

### Basic Inline Description List
```html
<!-- Inline layout: terms and descriptions flow horizontally -->
<dl class="slds-dl_inline">
  <dt class="slds-dl_inline__label">Status:</dt>
  <dd class="slds-dl_inline__detail">Active</dd>

  <dt class="slds-dl_inline__label">Created:</dt>
  <dd class="slds-dl_inline__detail">January 15, 2024</dd>

  <dt class="slds-dl_inline__label">Owner:</dt>
  <dd class="slds-dl_inline__detail">Sarah Johnson</dd>
</dl>
```

### Horizontal Description List with Column Layout
```html
<!-- Horizontal layout: 30/70 column split for structured data -->
<dl class="slds-dl_horizontal">
  <dt class="slds-dl_horizontal__label">Account Name:</dt>
  <dd class="slds-dl_horizontal__detail">Acme Corporation</dd>

  <dt class="slds-dl_horizontal__label">Industry:</dt>
  <dd class="slds-dl_horizontal__detail">Technology</dd>

  <dt class="slds-dl_horizontal__label">Annual Revenue:</dt>
  <dd class="slds-dl_horizontal__detail">$50M - $100M</dd>
</dl>
```

### Inline Layout in Narrow Region
```html
<!-- Inline layout adapts to narrow containers -->
<div class="slds-region_narrow">
  <dl class="slds-dl_inline">
    <dt class="slds-dl_inline__label">Type:</dt>
    <dd class="slds-dl_inline__detail">Customer</dd>

    <dt class="slds-dl_inline__label">Priority:</dt>
    <dd class="slds-dl_inline__detail">High</dd>
  </dl>
</div>
```

### Horizontal Layout in Narrow Region
```html
<!-- Horizontal layout maintains column structure in narrow containers -->
<div class="slds-region_narrow">
  <dl class="slds-dl_horizontal">
    <dt class="slds-dl_horizontal__label">Contact:</dt>
    <dd class="slds-dl_horizontal__detail">John Smith</dd>

    <dt class="slds-dl_horizontal__label">Email:</dt>
    <dd class="slds-dl_horizontal__detail">john.smith@acme.com</dd>

    <dt class="slds-dl_horizontal__label">Phone:</dt>
    <dd class="slds-dl_horizontal__detail">(555) 123-4567</dd>
  </dl>
</div>
```

### Mixed Content Description List
```html
<!-- Horizontal layout with varied content types -->
<dl class="slds-dl_horizontal">
  <dt class="slds-dl_horizontal__label">Description:</dt>
  <dd class="slds-dl_horizontal__detail">
    Enterprise customer with multiple product installations requiring
    dedicated support and quarterly business reviews.
  </dd>

  <dt class="slds-dl_horizontal__label">Products:</dt>
  <dd class="slds-dl_horizontal__detail">
    Sales Cloud, Service Cloud, Marketing Cloud
  </dd>

  <dt class="slds-dl_horizontal__label">Support Level:</dt>
  <dd class="slds-dl_horizontal__detail">Premium</dd>
</dl>
```

## Responsive Behavior

### Breakpoint Activation
All description list utilities activate at `min-width: 30em` (480px):
- Below breakpoint: Standard stacked `<dl>` layout
- Above breakpoint: Applied utility layout (inline or horizontal)

### Narrow Region Support
Use `.slds-region_narrow` container to force responsive styles regardless of viewport:
- Inline layout maintains float behavior
- Horizontal layout maintains flex column structure

## Best Practices

✅ Use `slds-dl_inline` for compact, single-line key-value pairs
✅ Use `slds-dl_horizontal` for detailed information with longer descriptions
✅ Apply matching label and detail classes to all `<dt>` and `<dd>` elements
✅ Wrap in `.slds-region_narrow` for consistent layout in sidebars or modals
✅ Use semantic HTML (`<dl>`, `<dt>`, `<dd>`) for accessibility

❌ Never mix inline and horizontal classes on the same list
❌ Never omit the child classes (`__label`, `__detail`) when using parent classes
❌ Never use for non-semantic layouts (use grid or flexbox utilities instead)
❌ Never override the 30/70 width ratio for horizontal layouts