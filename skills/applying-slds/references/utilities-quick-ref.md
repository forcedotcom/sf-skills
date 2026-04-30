# Utilities Quick Reference

SLDS utility classes for rapid styling. 1,147 classes across 27 categories.

---

## When to Use Utilities vs. Hooks

| Need | Use utility class | Use hook |
|------|------------------|----------|
| Margin/padding | `slds-m-bottom_medium`, `slds-p-around_small` | `var(--slds-g-spacing-4)` in custom CSS |
| Grid layout | `slds-grid`, `slds-col`, `slds-size_*` | -- |
| Visibility | `slds-hide`, `slds-show_*` | -- |
| Text styling | `slds-text-heading_medium` | `var(--slds-g-font-*)` |
| Borders | `slds-border_bottom` | `var(--slds-g-color-border-*)` |
| Colors | `slds-theme_*` | `var(--slds-g-color-*)` |

**Prefer utility classes for layout and spacing in markup.** Use hooks in custom CSS for colors, typography values, and dynamic theming.

---

## Most-Used Categories

### Grid (`slds-grid`, 80 classes)

```html
<div class="slds-grid slds-wrap slds-gutters">
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2 slds-large-size_1-of-3">
    <!-- Column content -->
  </div>
</div>
```

Key classes:
- `slds-grid` -- flex container
- `slds-wrap` -- allow wrapping
- `slds-gutters` -- column spacing
- `slds-col` -- flex column
- `slds-size_1-of-N` -- fractional width (1-of-1 through 1-of-12)
- `slds-medium-size_*`, `slds-large-size_*` -- responsive breakpoints
- `slds-grid_vertical` -- column direction
- `slds-grid_align-center` -- center alignment

### Margin (`slds-m-*`, 119 classes)

Pattern: `slds-m-{direction}_{size}`

| Direction | Class pattern |
|-----------|--------------|
| All | `slds-m-around_*` |
| Top | `slds-m-top_*` |
| Bottom | `slds-m-bottom_*` |
| Left | `slds-m-left_*` |
| Right | `slds-m-right_*` |
| Vertical | `slds-m-vertical_*` |
| Horizontal | `slds-m-horizontal_*` |

Sizes: `none`, `xxx-small`, `xx-small`, `x-small`, `small`, `medium`, `large`, `x-large`, `xx-large`

### Padding (`slds-p-*`, 120 classes)

Same pattern as margin: `slds-p-{direction}_{size}`

### Sizing (`slds-size_*`, 613 classes)

Fractional widths for columns and elements:
- `slds-size_1-of-2` -- 50%
- `slds-size_1-of-3` -- 33.3%
- `slds-size_2-of-3` -- 66.6%
- `slds-size_1-of-4` -- 25%
- `slds-size_full` -- 100%

Responsive: `slds-small-size_*`, `slds-medium-size_*`, `slds-large-size_*`

### Typography (`slds-text-*`, 24 classes)

- `slds-text-heading_large` -- large heading
- `slds-text-heading_medium` -- medium heading
- `slds-text-heading_small` -- small heading
- `slds-text-body_regular` -- body text
- `slds-text-body_small` -- small body text
- `slds-text-title` -- uppercase label
- `slds-text-color_default` -- default text color
- `slds-text-color_weak` -- secondary text color

### Visibility

- `slds-hide` -- hide element (`display: none`)
- `slds-show` -- show element (`display: block`)
- `slds-show_inline` -- show inline
- `slds-hidden` -- hidden via `visibility: hidden`; occupies space and is not a screen-reader helper
- `slds-assistive-text` -- screen-reader only text

Use `slds-assistive-text`, not `slds-hidden`, when content should remain available to assistive technology.

### Truncation

- `slds-truncate` -- single-line truncation with ellipsis
- `slds-line-clamp_*` -- multi-line truncation (2, 3, 4, 5 lines)

---

## How to Search

```bash
# Browse all categories
node scripts/search-utilities.cjs --category "all"

# Browse a specific category
node scripts/search-utilities.cjs --category "grid"

# Search by class name
node scripts/search-utilities.cjs --search "slds-m-bottom"

# Wildcard pattern
node scripts/search-utilities.cjs --pattern "slds-p-around_*"
```

---

## Deep Reference

- Utility index: `guidance/utilities/index.md`
- Individual category guides: `guidance/utilities/{category}.md`
- Full metadata (1,147 classes): `metadata/utilities-index.json`
