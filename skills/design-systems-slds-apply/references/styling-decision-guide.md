# Styling Decision Guide

How to apply SLDS styling correctly using hooks, utilities, and custom CSS.

---

## Styling Hook Hierarchy

SLDS hooks follow a three-tier naming system:

| Tier | Prefix | Use |
|------|--------|-----|
| **Global Semantic** | `--slds-g-*` | System-wide. Use these by default. |
| **Shared** | `--slds-s-*` | Private/internal. **DO NOT USE.** Reserved for Salesforce. |
| **Component** | `--slds-c-*` | Scoped to specific LBCs. Use to customize LBC appearance. |

**Rule: Always use `--slds-g-*` hooks unless `--slds-c-*` hooks exist for your specific LBC.**

### Discovering `--slds-c-*` Hooks

Component hooks are scoped to specific Lightning Base Components. To find available hooks for an LBC:

1. **Inspect the LBC docs**: Check the component's [Lightning Component Library](https://developer.salesforce.com/docs/component-library/overview/components) page — look for "Styling Hooks" or "Custom Properties" sections
2. **Browser DevTools**: Render the LBC, inspect the element, and look for `--slds-c-*` properties in the computed styles
3. **Known patterns**: Component hooks follow `--slds-c-{component}-{property}-{state}` naming, e.g., `--slds-c-button-success-shadow-hover`

There is no centralized metadata file for `--slds-c-*` hooks — they are documented per-component. Some examples exist in `guidance/overviews/shadows.md` and `guidance/styling-hooks/index.md`.

---

## Hook Syntax

Always use `var()` with a fallback value:

```css
.my-card {
  background: var(--slds-g-color-surface-1, #ffffff);
  padding: var(--slds-g-spacing-4, 1rem);
  border-radius: var(--slds-g-radius-border-2, 0.25rem);
}
```

**Never reassign hook values.** Salesforce controls them and can change them.

### Choosing Fallback Values

The fallback in `var(--slds-g-*, fallback)` is used when the hook isn't loaded (e.g., outside Lightning Experience, in static HTML previews, or during SSR). Use the **light-mode default** value:

1. **Look up the value in `metadata/hooks-index.json`** — each hook has a `value` field showing its resolved default
2. **Use the search script**: `node scripts/search-hooks.cjs --prefix "--slds-g-color-surface-"` shows values
3. **Common defaults**: `#ffffff` for surfaces, `#181818` for text, `1rem` for spacing-4, `0.25rem` for radius-border-2

Always use the light-mode default. Dark-mode values are applied automatically when the hook is active — the fallback only matters when hooks aren't loaded at all.

---

## Color: The 85-5-10 Rule

All SLDS UIs should maintain this approximate color distribution:

| % | Role | What to use |
|---|------|-------------|
| **85%** | Foundation | Surfaces, backgrounds, containers. Neutral colors: whites, grays. Hooks: `--slds-g-color-surface-*` |
| **5%** | Accents | Primary actions, selected states, key CTAs. Hooks: `--slds-g-color-accent-*` |
| **10%** | Expressive | Data viz, custom branding. Use sparingly. Hooks: `--slds-g-color-palette-*` |

### Color Role Selection

Before picking a hook, classify what the color is for:

| Role | Hook prefix | Examples |
|------|-------------|----------|
| Surface (backgrounds) | `--slds-g-color-surface-*` | Page bg, modal bg, top-level panels |
| Surface container (nested surfaces) | `--slds-g-color-surface-container-*` | Card bg, embedded panels, list items |
| On-surface (text on surfaces) | `--slds-g-color-on-surface-*` | Body text, headings, icons |
| Accent (emphasis) | `--slds-g-color-accent-*` | Primary emphasis, selected state text/icons |
| Accent container (accent backgrounds) | `--slds-g-color-accent-container-*` | Buttons, selected tabs, emphasized controls |
| Border | `--slds-g-color-border-*` | Dividers, card borders |
| Error | `--slds-g-color-error-*` | Validation errors |
| Success | `--slds-g-color-success-*` | Confirmation states |
| Warning | `--slds-g-color-warning-*` | Caution messages |

**Always pair surfaces with on-surfaces.** Example: `surface-1` background + `on-surface-2` text.

**CRITICAL:** All color hooks require a numbered variant. There is no unnumbered base form (e.g., `--slds-g-color-on-surface` does not exist -- use `on-surface-1`, `-2`, or `-3`):

| Variant | Emphasis | Use for |
|---------|----------|---------|
| `-1` | Low | Captions, placeholder text, de-emphasized content |
| `-2` | Medium | Body text, labels, standard content |
| `-3` | High | Page titles, headings, primary emphasis |

### How to search hooks

```bash
# By prefix
node scripts/search-hooks.cjs --prefix "--slds-g-color-surface-"

# By category
node scripts/search-hooks.cjs --category "color"

# By CSS property
node scripts/search-hooks.cjs --property "background-color"

# Find hook for a hardcoded value
node scripts/search-hooks.cjs --value "#0176d3"
```

---

## Spacing: 4-Point Grid

SLDS uses a numbered scale, not named sizes:

| Hook | Value | Pixels | Use for |
|------|-------|--------|---------|
| `--slds-g-spacing-1` | 0.25rem | 4px | Tight inline spacing |
| `--slds-g-spacing-2` | 0.5rem | 8px | Between related items |
| `--slds-g-spacing-3` | 0.75rem | 12px | Small gaps |
| `--slds-g-spacing-4` | 1rem | 16px | Standard padding/margin |
| `--slds-g-spacing-5` | 1.5rem | 24px | Section gaps |
| `--slds-g-spacing-6` | 2rem | 32px | Between sections |
| `--slds-g-spacing-8` | 3rem | 48px | Large separations |
| `--slds-g-spacing-12` | 5rem | 80px | Page-level spacing |

---

## Typography Hooks (Naming Exception)

Typography hooks break from the `{prefix}-{number}` pattern used by spacing and color:

| Hook | Pattern | Use |
|------|---------|-----|
| `--slds-g-font-size-base` | Single value | Base application font size (13px / 0.8125rem) |
| `--slds-g-font-scale-*` | Numbered scale | All other sizes: `font-scale-1` (14px) through `font-scale-10` |
| `--slds-g-font-scale-neg-*` | Negative scale | Smaller sizes: `font-scale-neg-1` through `neg-4` |
| `--slds-g-font-scale-var-*` | Density-aware | Adapts to compact/comfy display density settings |

**Common mappings:**

| Size | Hook | Approximate value |
|------|------|-------------------|
| Small body text | `--slds-g-font-scale-neg-1` | 12px |
| Default body | `--slds-g-font-size-base` | 13px |
| Larger body | `--slds-g-font-scale-1` | 14px |
| Subheading | `--slds-g-font-scale-2` | 16px |
| Heading | `--slds-g-font-scale-4` | 20px |
| Page title | `--slds-g-font-scale-6` | 28px |
| Display | `--slds-g-font-scale-8` | 40px |

**CRITICAL:** `--slds-g-font-size-3`, `--slds-g-font-size-4`, etc. do NOT exist. Only `--slds-g-font-size-base` is valid. For numbered sizes, use `--slds-g-font-scale-*`.

---

## When Hooks Don't Exist

Not all CSS properties have styling hooks. Not all values have hook equivalents either (e.g., `min-width: 7rem` for label alignment). Use this decision tree:

```
Does a hook exist for this property?
├─ YES → Use it: var(--slds-g-*, fallback)
├─ NO → Is there a utility class?
│       ├─ YES → Use the utility class
│       └─ NO → Use minimal custom CSS with:
│               1. Custom class prefix (my-*, c-*)
│               2. Use hooks for related values (e.g., hook colors in gradients)
│               3. Document why no hook/utility exists
```

**Properties without hooks (use custom CSS):**
- `transform`, `transition` (use `--slds-g-duration-*` for timing only)
- `z-index` (use SLDS utility classes when possible)
- `cursor`, `overflow`
- Complex gradients (use hook colors within gradient syntax)

**Values without hook equivalents (acceptable hardcoding):**

Some dimension values have no SLDS hook (e.g., `min-width: 7rem` for label alignment, `max-height: 20rem` for scrollable panels). This is acceptable when:
1. No SLDS sizing hook or utility class covers the value
2. A comment explains the value is intentional
3. SLDS grid utilities (`slds-size_*`) were considered as alternatives

```css
.c-field-label {
  /* No SLDS hook exists for this width; intentional for label alignment */
  min-width: 7rem;
}
```

**Example -- gradient with hook colors:**
```css
.my-gradient-bg {
  background: linear-gradient(
    to bottom,
    var(--slds-g-color-surface-1, #ffffff),
    var(--slds-g-color-surface-2, #f3f3f3)
  );
}
```

---

## Hook vs. Utility vs. Custom CSS

| Need | First choice | Fallback |
|------|-------------|----------|
| Color (bg, text, border) | Hook: `var(--slds-g-color-*)` | -- |
| Spacing (margin, padding) | Utility: `slds-m-*`, `slds-p-*` | Hook: `var(--slds-g-spacing-*)` |
| Layout (grid, columns) | Utility: `slds-grid`, `slds-col` | -- |
| Typography (size) | Hook: `var(--slds-g-font-scale-*)` or `var(--slds-g-font-size-base)` | Utility: `slds-text-*` |
| Typography (weight) | Hook: `var(--slds-g-font-weight-*)` | -- |
| Visibility (show/hide) | Utility: `slds-hide`, `slds-show` | -- |
| Borders (width, radius) | Hook: `var(--slds-g-radius-*)` | Utility: `slds-border-*` |
| Shadows | Hook: `var(--slds-g-shadow-*)` | -- |
| Anything else | Custom CSS with custom class prefix | Use hook values where possible |

---

## Deep Reference

- Styling hooks index: `guidance/styling-hooks/index.md`
- Color hooks deep dive: `guidance/styling-hooks/color/`
- Color overview (85-5-10 rule): `guidance/overviews/color.md`
- Spacing overview: `guidance/overviews/spacing.md`
- Typography hooks: `guidance/styling-hooks/typography.md`
- Borders overview: `guidance/overviews/borders.md`
- Shadows overview: `guidance/overviews/shadows.md`
- All 523 hooks searchable: `metadata/hooks-index.json`
