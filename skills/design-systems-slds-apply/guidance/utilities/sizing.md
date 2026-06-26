---
id: slds.guidance.utilities.sizing
title: Sizing Utilities
description: SLDS width sizing utility classes for responsive layouts
summary: "Utilities for width sizing. Fractional widths (1-of-2 through 1-of-12), absolute sizes, responsive breakpoints, and flex ordering."

artifact_type: reference
domain: utilities
topic: sizing

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.grid

tags: [utilities, sizing, width, responsive, fractional]
keywords: [slds-size, slds-order, fractional width, responsive sizing]
---

# Sizing - Width Control

Width sizing and flex ordering.

## Core Classes

### Fractional Widths

Based on 12-column grid system with denominators of 2, 3, 4, 5, 6, 7, 8, and 12.

| Class | Purpose |
|-------|---------|
| `slds-size_1-of-2` | Sets width to 50% |
| `slds-size_1-of-3` | Sets width to 33.333% |
| `slds-size_2-of-3` | Sets width to 66.6667% |
| `slds-size_1-of-4` | Sets width to 25% |
| `slds-size_3-of-4` | Sets width to 75% |
| `slds-size_1-of-5` | Sets width to 20% |
| `slds-size_2-of-5` | Sets width to 40% |
| `slds-size_3-of-5` | Sets width to 60% |
| `slds-size_4-of-5` | Sets width to 80% |
| `slds-size_1-of-6` | Sets width to 16.6667% |
| `slds-size_5-of-6` | Sets width to 83.3333% |
| `slds-size_1-of-7` | Sets width to 14.2857% |
| `slds-size_1-of-8` | Sets width to 12.5% |
| `slds-size_1-of-12` | Sets width to 8.3333% |
| `slds-size_5-of-12` | Sets width to 41.6667% |
| `slds-size_7-of-12` | Sets width to 58.3333% |
| `slds-size_11-of-12` | Sets width to 91.6667% |

### Absolute Sizes

Fixed widths in rem units.

| Class | Purpose |
|-------|---------|
| `slds-size_xxx-small` | Sets width to 3rem (48px) |
| `slds-size_xx-small` | Sets width to 6rem (96px) |
| `slds-size_x-small` | Sets width to 12rem (192px) |
| `slds-size_small` | Sets width to 15rem (240px) |
| `slds-size_medium` | Sets width to 20rem (320px) |
| `slds-size_large` | Sets width to 25rem (400px) |
| `slds-size_x-large` | Sets width to 40rem (640px) |
| `slds-size_xx-large` | Sets width to 60rem (960px) |
| `slds-size_full` | Sets width to 100% |

### Responsive Breakpoints

Breakpoint-specific sizing with mobile-first approach.

| Breakpoint | Viewport Width | Prefix |
|------------|---------------|--------|
| x-small | ≥ 320px (20em) | `slds-x-small-size_*` |
| small | ≥ 480px (30em) | `slds-small-size_*` |
| medium | ≥ 768px (48em) | `slds-medium-size_*` |
| large | ≥ 1024px (64em) | `slds-large-size_*` |
| x-large | ≥ 1280px (80em) | `slds-x-large-size_*` |
| max-small | < 480px (30em) | `slds-max-small-size_*` |
| max-medium | < 768px (48em) | `slds-max-medium-size_*` |
| max-large | < 1024px (64em) | `slds-max-large-size_*` |

### Flex Ordering

Controls visual order in flexbox layouts.

| Class | Purpose |
|-------|---------|
| `slds-order_1` | Sets flex order to 1 |
| `slds-order_2` | Sets flex order to 2 |
| `slds-order_3` | Sets flex order to 3 |
| `slds-order_4` | Sets flex order to 4 |
| `slds-order_5` | Sets flex order to 5 |
| `slds-order_6` through `slds-order_12` | Sets flex order 6-12 |

## Common Patterns

### Three-Column Layout
```html
<!-- Three equal columns -->
<div class="slds-grid slds-wrap">
  <div class="slds-size_1-of-3">
    <!-- Column 1: 33.333% width -->
  </div>
  <div class="slds-size_1-of-3">
    <!-- Column 2: 33.333% width -->
  </div>
  <div class="slds-size_1-of-3">
    <!-- Column 3: 33.333% width -->
  </div>
</div>
```

### Responsive Grid
```html
<!-- Full width mobile, half tablet, quarter desktop -->
<div class="slds-grid slds-wrap">
  <div class="slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-4">
    <!-- Card adapts from 100% → 50% → 25% -->
  </div>
  <div class="slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-4">
    <!-- Card adapts from 100% → 50% → 25% -->
  </div>
</div>
```

### Sidebar Layout
```html
<!-- Fixed sidebar with flexible content -->
<div class="slds-grid">
  <nav class="slds-size_medium">
    <!-- Sidebar: 320px fixed width -->
  </nav>
  <main class="slds-col">
    <!-- Content: Fills remaining space -->
  </main>
</div>
```

### Reordered Content
```html
<!-- Visual order differs from DOM order -->
<div class="slds-grid">
  <div class="slds-size_1-of-3 slds-order_3">
    <!-- Appears third visually -->
  </div>
  <div class="slds-size_1-of-3 slds-order_1">
    <!-- Appears first visually -->
  </div>
  <div class="slds-size_1-of-3 slds-order_2">
    <!-- Appears second visually -->
  </div>
</div>
```

### Form Layout
```html
<!-- Two-column form with responsive stacking -->
<div class="slds-form" role="form">
  <div class="slds-grid slds-wrap slds-gutters">
    <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
      <!-- First Name field: Full width mobile, half desktop -->
    </div>
    <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
      <!-- Last Name field: Full width mobile, half desktop -->
    </div>
    <div class="slds-col slds-size_1-of-1">
      <!-- Email field: Always full width -->
    </div>
  </div>
</div>
```

## Best Practices

✅ Use fractional widths for flexible grid layouts
✅ Apply responsive classes for mobile-first design
✅ Combine with `slds-grid` and `slds-wrap` for proper grid behavior
✅ Use `slds-col` for flexible remaining space
✅ Apply `slds-gutters` to parent grid for consistent spacing
✅ Use semantic HTML elements with sizing utilities

❌ Avoid mixing fractional and absolute sizes on siblings
❌ Never use sizing utilities without proper grid container
❌ Avoid using more than 12 total columns per row
❌ Never rely solely on `slds-order_*` for accessibility - maintain logical DOM order