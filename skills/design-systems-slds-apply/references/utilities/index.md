---
id: slds.guidance.utilities
title: SLDS Utility Classes Index
description: Category index of SLDS utility classes for rapid styling
summary: "Index of all SLDS utility classes across 26 categories including grid, spacing, sizing, typography, visibility, borders, and positioning. Provides quick access by need and common usage patterns."

artifact_type: index
domain: utilities
topic: utilities

content_format: structured
complexity: foundational
audience: [implementer]

tasks: [choose, implement]

tags: [utilities, css-classes, layout, spacing, typography]
keywords: [utility classes, grid, spacing, sizing, typography, visibility, borders, position, truncate]

refs:
  - slds.guidance.overview.utilities
  - slds.guidance.hooks.color
  - slds.guidance.utilities.alignment
  - slds.guidance.utilities.borders
  - slds.guidance.utilities.box
  - slds.guidance.utilities.color
  - slds.guidance.utilities.dark-mode
  - slds.guidance.utilities.description-list
  - slds.guidance.utilities.floats
  - slds.guidance.utilities.grid
  - slds.guidance.utilities.horizontal-list
  - slds.guidance.utilities.hyphenation
  - slds.guidance.utilities.interactions
  - slds.guidance.utilities.layout
  - slds.guidance.utilities.line-clamp
  - slds.guidance.utilities.margin
  - slds.guidance.utilities.media-object
  - slds.guidance.utilities.name-value-list
  - slds.guidance.utilities.padding
  - slds.guidance.utilities.position
  - slds.guidance.utilities.print
  - slds.guidance.utilities.scrollable
  - slds.guidance.utilities.sizing
  - slds.guidance.utilities.themes
  - slds.guidance.utilities.truncate
  - slds.guidance.utilities.typography
  - slds.guidance.utilities.vertical-list
  - slds.guidance.utilities.visibility
---

# SLDS Utility Classes - Category Index

**26 categories** of utility classes for rapid styling without custom CSS.

## Layout & Positioning (6)

### [Grid](./grid.md)
Flexbox layout system for responsive grids. Use `slds-grid` + `slds-col` + `slds-wrap`.

### [Position](./position.md)
CSS positioning: `slds-is-relative`, `slds-is-absolute`, `slds-is-fixed`. For dropdowns, modals, overlays.

### [Scrollable](./scrollable.md)
`slds-scrollable`, `slds-scrollable_x`, `slds-scrollable_y` for scrollable containers.

### [Floats](./floats.md)
`slds-float_left`, `slds-float_right`. Legacy - prefer Grid.

### [Alignment](./alignment.md)
`slds-align_absolute-center` for centering content.

### [Layout](./layout.md)
`slds-has-buffer`, `slds-has-full-bleed` for global spacing.

## Spacing (2) - Most Used

### [Margin](./margin.md)
`slds-m-[direction]_[size]` for all margin directions and sizes.
Scale: `none`, `xxx-small` (2px) to `xx-large` (48px)

### [Padding](./padding.md)
`slds-p-[direction]_[size]` for all padding directions and sizes.
Scale: `none`, `xxx-small` (2px) to `xx-large` (48px)

## Sizing (1)

### [Sizing](./sizing.md)
Fractional widths: `slds-size_1-of-2` (50%), `slds-size_1-of-3` (33%)  
Responsive: `slds-small-size_*`, `slds-medium-size_*`, `slds-large-size_*`  
Full width: `slds-width_full`

## Typography (4)

### [Typography](./typography.md)
Headings: `slds-text-heading_large/medium/small`  
Body: `slds-text-body_regular/small`  
Colors: `slds-text-color_weak/error/success`  
Alignment: `slds-text-align_left/center/right`

### [Truncate](./truncate.md)
Single-line: `slds-truncate` (with `title` attribute)
Partial: `slds-truncate_container_25/50/75`

### [Line Clamp](./line-clamp.md)
Multi-line truncation:
- `slds-line-clamp` - 3 lines (default)
- `slds-line-clamp_x-small` - 2 lines
- `slds-line-clamp_medium` - 5 lines
- `slds-line-clamp_large` - 7 lines

### [Hyphenation](./hyphenation.md)
`slds-hyphenate` for long word breaking.

## Visual Styling (6)

### [Color](./color.md)
`slds-color__text_gray-1` through `gray-12`
`slds-color__background_gray-1` through `gray-12`
**Prefer** styling hooks for colors.

### [Borders](./borders.md)
**Borders**: `slds-border_top/bottom/left/right` for directional borders.

### [Box](./box.md)
`slds-box`, `slds-box_small/large` for bordered containers.

### [Themes](./themes.md)
`slds-theme_default`, `slds-theme_shade`, `slds-theme_inverse` for themed containers.

### [Visibility](./visibility.md)
Show/hide: `slds-show`, `slds-hide`
Responsive: `slds-show_medium`, `slds-hide_medium`
Screen reader: `slds-assistive-text`
Collapsed: `slds-is-collapsed`, `slds-is-expanded`

### [Dark Mode](./dark-mode.md)
Future dark mode support (currently use styling hooks).

## Specialized (5)

### [Description List](./description-list.md)
`slds-dl_horizontal`, `slds-dl_inline` for name-value pairs.

### [Media Object](./media-object.md)
`slds-media`, `slds-media__figure`, `slds-media__body` for image+text layouts.

### [Name-Value List](./name-value-list.md)
`slds-item_label`, `slds-item_detail` for structured data.

### [Horizontal List](./horizontal-list.md)
`slds-list_horizontal`, `slds-list__item` for inline lists.

### [Vertical List](./vertical-list.md)
`slds-list__item`, `slds-has-divider`, `slds-is-selected` for navigation/lists.

## Special Purpose (2)

### [Interactions](./interactions.md)
`slds-text-link`, `slds-text-link_reset`, `slds-has-blur-focus` for interactive elements.

### [Print](./print.md)
`slds-no-print` hides elements when printing.

---

## Quick Access by Need

**Layout**: [Grid](./grid.md) • [Position](./position.md) • [Sizing](./sizing.md) • [Alignment](./alignment.md) • [Layout](./layout.md)
**Spacing**: [Margin](./margin.md) • [Padding](./padding.md)
**Text**: [Typography](./typography.md) • [Truncate](./truncate.md) • [Line Clamp](./line-clamp.md) • [Hyphenation](./hyphenation.md)
**Display**: [Visibility](./visibility.md) • [Print](./print.md)
**Style**: [Borders](./borders.md) • [Box](./box.md) • [Color](./color.md) • [Themes](./themes.md)
**Lists**: [Horizontal List](./horizontal-list.md) • [Vertical List](./vertical-list.md) • [Name-Value List](./name-value-list.md) • [Description List](./description-list.md) • [Media Object](./media-object.md)
**Interactive**: [Interactions](./interactions.md)
**Scrolling**: [Scrollable](./scrollable.md) • [Floats](./floats.md)
**Theme**: [Dark Mode](./dark-mode.md)

## Usage Patterns

**Card Layout**:
```html
<div class="slds-card slds-m-bottom_medium">
  <div class="slds-card__body slds-p-around_medium">
    Content
  </div>
</div>
```

**Responsive Grid**:
```html
<div class="slds-grid slds-wrap slds-gutters">
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-3">
    Column
  </div>
</div>
```

**Typography**:
```html
<h1 class="slds-text-heading_large slds-m-bottom_medium">Title</h1>
<p class="slds-text-body_regular slds-text-color_weak">Description</p>
```

For detailed guidance on any category, see the linked category guides.

