---
id: slds.guidance.utilities.grid
title: Grid Utilities
description: SLDS flexbox grid system utilities
summary: "Utilities for flexible, responsive layouts using CSS Flexbox. Includes grid containers, columns, gutters (2px-96px), alignment, and responsive breakpoints."

artifact_type: reference
domain: utilities
topic: grid

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [implement]

refs:
  - slds.guidance.utilities
  - slds.guidance.overview.utilities
  - slds.guidance.utilities.sizing

tags: [utilities, grid, flexbox, layout, responsive]
keywords: [slds-grid, slds-col, slds-wrap, slds-gutters, slds-container]
---

# Grid - Flexbox Layout System

Creating flexible, responsive layouts using CSS Flexbox.

## Core Classes

| Class | Purpose |
|-------|---------|
| `slds-grid` | Initialize flex container (`display: flex`) |
| `slds-col` | Initialize flex item/column (`flex: 1 1 auto`) |
| `slds-wrap` | Allow columns to wrap to new rows (`flex-wrap: wrap`) |
| `slds-nowrap` | Keep columns on single line (`flex-wrap: nowrap`) |

## Grid Flow Modifiers

| Class | Purpose |
|-------|---------|
| `slds-grid_vertical` | Stack columns vertically (`flex-direction: column`) |
| `slds-grid_vertical-reverse` | Stack columns vertically in reverse order (`flex-direction: column-reverse`) |
| `slds-grid_reverse` | Reverse horizontal flow (`flex-direction: row-reverse`) |
| `slds-grid_frame` | Full-viewport grid (`min-width: 100vw; min-height: 100vh`) |
| `slds-grid_overflow` | Create horizontal scrolling grid (`flex-flow: row nowrap`) |

## Gutters

| Class | Gutter Width | Per Side |
|-------|-------------|----------|
| `slds-gutters_xxx-small` | 2px total | 1px |
| `slds-gutters_xx-small` | 4px total | 2px |
| `slds-gutters_x-small` | 8px total | 4px |
| `slds-gutters_small` | 24px total | 12px |
| `slds-gutters` | 24px total (default) | 12px |
| `slds-gutters_medium` | 32px total | 16px |
| `slds-gutters_large` | 48px total | 24px |
| `slds-gutters_x-large` | 64px total | 32px |
| `slds-gutters_xx-large` | 96px total | 48px |

### Gutter Variants
- `slds-gutters_direct` - Apply gutters only to direct child columns (not nested grids)
- `slds-gutters_direct-xxx-small` through `slds-gutters_direct-xx-large` - Direct gutters with size variants

## Alignment

### Horizontal Alignment (Main Axis)
| Class | Purpose |
|-------|---------|
| `slds-grid_align-center` | Center columns horizontally (`justify-content: center`) |
| `slds-grid_align-space` | Equal space around columns (`justify-content: space-around`) |
| `slds-grid_align-spread` | Space columns from edges (`justify-content: space-between`) |
| `slds-grid_align-end` | Right align columns (`justify-content: flex-end`) |

### Vertical Alignment (Cross Axis)
| Class | Purpose |
|-------|---------|
| `slds-grid_vertical-align-start` | Align columns to top (`align-items: flex-start`) |
| `slds-grid_vertical-align-center` | Vertically center columns (`align-items: center`) |
| `slds-grid_vertical-align-end` | Align columns to bottom (`align-items: flex-end`) |
| `slds-grid_vertical-stretch` | Stretch columns to fill height (`align-items: stretch`) |

### Individual Column Alignment
| Class | Purpose |
|-------|---------|
| `slds-align-top` | Align individual column to top (`align-self: flex-start`) |
| `slds-align-middle` | Align individual column to middle (`align-self: center`) |
| `slds-align-bottom` | Align individual column to bottom (`align-self: flex-end`) |

## Column Flex Control

| Class | Purpose |
|-------|---------|
| `slds-grow` | Allow column to grow (`flex-grow: 1`) |
| `slds-grow-none` | Prevent column from growing (`flex-grow: 0`) |
| `slds-shrink` | Allow column to shrink (`flex-shrink: 1`) |
| `slds-shrink-none` | Prevent column from shrinking (`flex-shrink: 0`) |
| `slds-no-flex` | Remove flexbox from column (`flex: none`) |
| `slds-no-space` | Set column to min-width of 0 |
| `slds-has-flexi-truncate` | Enable truncation in flexible container (`flex: 1 1 0%; min-width: 0`) |

## Column Positioning

| Class | Purpose |
|-------|---------|
| `slds-col_bump-top` | Push column to top using `margin-block-start: auto` |
| `slds-col_bump-right` | Push column to right using `margin-inline-end: auto` |
| `slds-col_bump-bottom` | Push column to bottom using `margin-block-end: auto` |
| `slds-col_bump-left` | Push column to left using `margin-inline-start: auto` |

## Column Borders

| Class | Purpose |
|-------|---------|
| `slds-col_rule-top` | Add 1px border to top side (large screens only) |
| `slds-col_rule-right` | Add 1px border to right side (large screens only) |
| `slds-col_rule-bottom` | Add 1px border to bottom side (large screens only) |
| `slds-col_rule-left` | Add 1px border to left side (large screens only) |

## Container Sizing

| Class | Max Width | Purpose |
|-------|-----------|---------|
| `slds-container_small` | 480px | Restrict width for small content |
| `slds-container_medium` | 768px | Restrict width for medium content |
| `slds-container_large` | 1024px | Restrict width for large content |
| `slds-container_x-large` | 1280px | Restrict width for extra large content |
| `slds-container_fluid` | 100% | Full viewport width |

### Container Positioning
| Class | Purpose |
|-------|---------|
| `slds-container_center` | Center container horizontally |
| `slds-container_left` | Left align container |
| `slds-container_right` | Right align container |

## Pull Padded Utilities

| Class | Purpose |
|-------|---------|
| `slds-grid_pull-padded` | Normalize 12px padding when nesting |
| `slds-grid_pull-padded-xxx-small` | Normalize 2px padding |
| `slds-grid_pull-padded-xx-small` | Normalize 4px padding |
| `slds-grid_pull-padded-x-small` | Normalize 8px padding |
| `slds-grid_pull-padded-small` | Normalize 12px padding |
| `slds-grid_pull-padded-medium` | Normalize 16px padding |
| `slds-grid_pull-padded-large` | Normalize 24px padding |
| `slds-grid_pull-padded-x-large` | Normalize 32px padding |
| `slds-grid_pull-padded-xx-large` | Normalize 48px padding |

## Common Patterns

### Basic Three-Column Grid
```html
<!-- Equal width columns with gutters -->
<div class="slds-grid slds-wrap slds-gutters">
  <div class="slds-col slds-size_1-of-3">
    Column 1 content
  </div>
  <div class="slds-col slds-size_1-of-3">
    Column 2 content
  </div>
  <div class="slds-col slds-size_1-of-3">
    Column 3 content
  </div>
</div>
```

### Responsive Card Layout
```html
<!-- Mobile: full width, Tablet: half width, Desktop: third width -->
<div class="slds-grid slds-wrap slds-gutters_small">
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-3">
    <article class="slds-card">Card 1</article>
  </div>
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-3">
    <article class="slds-card">Card 2</article>
  </div>
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-3">
    <article class="slds-card">Card 3</article>
  </div>
</div>
```

### Centered Modal Dialog
```html
<!-- Vertically and horizontally centered content -->
<div class="slds-grid slds-grid_align-center slds-grid_vertical-align-center slds-grid_frame">
  <div class="slds-col slds-container_small">
    <section class="slds-modal__container">
      Modal content here
    </section>
  </div>
</div>
```

### Sidebar Layout with Auto-push
```html
<!-- Sidebar with main content pushed to opposite side -->
<div class="slds-grid slds-gutters">
  <nav class="slds-col slds-size_3-of-12">
    Sidebar navigation
  </nav>
  <main class="slds-col slds-col_bump-left">
    <!-- bump-left creates margin-inline-start: auto -->
    Main content area
  </main>
</div>
```

### Nested Grid with Direct Gutters
```html
<!-- Parent grid with nested grid using direct gutters -->
<div class="slds-grid slds-wrap slds-gutters_direct-medium">
  <div class="slds-col slds-size_1-of-2">
    <div class="slds-grid slds-wrap slds-gutters_direct-small">
      <div class="slds-col slds-size_1-of-2">Nested 1</div>
      <div class="slds-col slds-size_1-of-2">Nested 2</div>
    </div>
  </div>
  <div class="slds-col slds-size_1-of-2">
    Parent column 2
  </div>
</div>
```

## Best Practices

✅ Use `slds-wrap` for responsive card layouts that need to stack on mobile
✅ Start mobile-first with `slds-size_1-of-1` then add breakpoint-specific sizes
✅ Use `slds-gutters_small` (24px) for standard spacing between columns
✅ Apply `slds-has-flexi-truncate` when text needs to truncate within flexible columns
✅ Use `slds-container_center` with `slds-container_large` for centered page layouts
✅ Apply `slds-grid_pull-padded` when nesting grids to maintain visual alignment

❌ Avoid nesting grids more than 2 levels deep
❌ Never use `slds-col` without a parent `slds-grid`
❌ Avoid mixing grid utilities with float-based layouts
❌ Never combine `slds-grid_align-spread` with `slds-gutters` (creates double spacing)

## Deprecated Utilities

The following grid utilities are deprecated. Use the specified replacements.

### Responsive Nowrap Classes
| Deprecated | Replacement |
|------------|-------------|
| `slds-nowrap_small` | Use responsive grid classes instead |
| `slds-nowrap_medium` | Use responsive grid classes instead |
| `slds-nowrap_large` | Use responsive grid classes instead |

### Column Padding Classes
| Deprecated | Replacement |
|------------|-------------|
| `slds-col_padded` | Use `slds-p-horizontal_small` |
| `slds-col_padded-medium` | Use `slds-p-horizontal_medium` |
| `slds-col_padded-large` | Use `slds-p-horizontal_large` |
| `slds-col_padded-around` | Use `slds-p-around_small` |
| `slds-col_padded-around-medium` | Use `slds-p-around_medium` |
| `slds-col_padded-around-large` | Use `slds-p-around_large` |

Note: Column sizing utilities (`slds-size_*`) are defined in the [Sizing Utilities](ref:slds.guidance.utilities.sizing) category, not grid utilities.