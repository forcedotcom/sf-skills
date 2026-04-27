---
id: slds.guidance.utilities.position
title: Position Utilities
description: SLDS CSS positioning utility classes
summary: "Utilities for CSS positioning (static, relative, absolute, fixed). Controls element positioning for dropdowns, modals, and overlays."

artifact_type: reference
domain: utilities
topic: position

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities

tags: [utilities, position, css-positioning]
keywords: [slds-is-relative, slds-is-absolute, slds-is-fixed, slds-is-static]
---

# Position - CSS Positioning Control

CSS positioning including static, relative, absolute, and fixed positioning.

## Core Classes

| Class | CSS Property | Purpose |
|-------|-------------|---------|
| `slds-is-static` | `position: static` | Reset element to normal document flow |
| `slds-is-relative` | `position: relative` | Position element relative to its normal position, create containing block for absolute children |
| `slds-is-absolute` | `position: absolute` | Position element relative to nearest positioned ancestor |
| `slds-is-fixed` | `position: fixed` | Position element relative to viewport |

## Common Patterns

### Dropdown Positioning
```html
<!-- Dropdown container with relative positioning -->
<div class="slds-dropdown-trigger slds-is-relative">
  <button class="slds-button">Actions</button>
  <!-- Dropdown positioned absolutely below trigger -->
  <div class="slds-dropdown slds-is-absolute" style="top: 100%; left: 0;">
    <ul class="slds-dropdown__list">
      <li class="slds-dropdown__item">Edit</li>
      <li class="slds-dropdown__item">Delete</li>
    </ul>
  </div>
</div>
```

### Modal Overlay
```html
<!-- Fixed position modal covering viewport -->
<section class="slds-modal slds-is-fixed" style="top: 0; left: 0; right: 0; bottom: 0; z-index: 9000;">
  <div class="slds-modal__container">
    <div class="slds-modal__content">
      Modal content here
    </div>
  </div>
</section>
<!-- Fixed backdrop behind modal -->
<div class="slds-backdrop slds-is-fixed" style="top: 0; left: 0; width: 100%; height: 100%; z-index: 8999;"></div>
```

### Badge Indicator
```html
<!-- Icon with absolutely positioned badge -->
<div class="slds-icon_container slds-is-relative">
  <svg class="slds-icon slds-icon-text-default">
    <use xlink:href="/assets/icons/utility-sprite.svg#notification"></use>
  </svg>
  <!-- Badge positioned at top-right corner -->
  <span class="slds-badge slds-is-absolute" style="top: -4px; right: -4px;">
    5
  </span>
</div>
```

### Tooltip Positioning
```html
<!-- Button with absolutely positioned tooltip -->
<div class="slds-is-relative">
  <button class="slds-button">Hover for info</button>
  <!-- Tooltip positioned above button -->
  <div class="slds-popover slds-is-absolute" style="bottom: 100%; left: 50%; transform: translateX(-50%); margin-bottom: 0.5rem;">
    <div class="slds-popover__body">Helpful information</div>
  </div>
</div>
```

### Sticky Elements
```html
<!-- Use CSS sticky for header (not utility class) -->
<header class="slds-page-header" style="position: sticky; top: 0; z-index: 100;">
  Page header remains visible on scroll
</header>

<!-- Fixed action bar at bottom -->
<div class="slds-is-fixed" style="bottom: 0; left: 0; right: 0; z-index: 100;">
  <div class="slds-button-group">
    <button class="slds-button slds-button_brand">Save</button>
    <button class="slds-button slds-button_neutral">Cancel</button>
  </div>
</div>
```

## Best Practices

✅ Use `slds-is-relative` on parent containers for absolutely positioned children
✅ Use `slds-is-absolute` for dropdowns, tooltips, and popovers
✅ Use `slds-is-fixed` for modals, backdrops, and viewport-relative elements
✅ Always specify positioning coordinates (`top`, `right`, `bottom`, `left`)
✅ Include appropriate `z-index` values for stacking context
✅ Use `slds-is-static` to reset positioning when needed

❌ Never use `slds-is-absolute` without a positioned ancestor
❌ Avoid `slds-is-fixed` for elements that should scroll with content
❌ Never position elements without defining coordinates
❌ Avoid excessive z-index values (stay within defined ranges)

## Z-Index Guidelines

| Layer | Z-Index Range | Use For |
|-------|---------------|---------|
| Base content | 1-10 | Regular page elements |
| Dropdowns | 5000-5999 | Dropdown menus, select lists |
| Sticky elements | 6000-6999 | Sticky headers, navigation |
| Modals | 9000-9999 | Modal dialogs, overlays |
| Toasts | 10000+ | Toast notifications, alerts |

### Z-Index Example
```html
<!-- Properly layered elements -->
<div class="slds-dropdown slds-is-absolute" style="z-index: 5000;">Dropdown</div>
<header class="slds-is-fixed" style="z-index: 6000;">Sticky header</header>
<div class="slds-modal slds-is-fixed" style="z-index: 9000;">Modal</div>
<div class="slds-notification slds-is-fixed" style="z-index: 10000;">Toast</div>
```

## Positioning Coordinates

When using position utilities, always define coordinates:

| Coordinate | Description | Example |
|------------|-------------|---------|
| `top` | Distance from top edge | `top: 0` or `top: 100%` |
| `right` | Distance from right edge | `right: 0` or `right: 1rem` |
| `bottom` | Distance from bottom edge | `bottom: 0` or `bottom: 100%` |
| `left` | Distance from left edge | `left: 0` or `left: 50%` |

### Coordinate Combinations
```html
<!-- Full coverage -->
<div class="slds-is-fixed" style="top: 0; right: 0; bottom: 0; left: 0;">

<!-- Top-right corner -->
<div class="slds-is-absolute" style="top: 0; right: 0;">

<!-- Centered horizontally -->
<div class="slds-is-absolute" style="left: 50%; transform: translateX(-50%);">

<!-- Bottom-aligned -->
<div class="slds-is-absolute" style="bottom: 0; left: 0; right: 0;">
```

## Browser Compatibility

All position utilities are fully supported in modern browsers:
- Chrome 1+
- Firefox 1+
- Safari 1+
- Edge 12+
- No vendor prefixes required