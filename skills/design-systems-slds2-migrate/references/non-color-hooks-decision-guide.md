# Non-Color Styling Hooks Guide

Reference for replacing hardcoded spacing, sizing, typography, border, radius, and shadow values with SLDS 2 styling hooks. These hooks use numbered scales with straightforward mappings — unlike color hooks, they rarely require context-based decisions.

**Pattern for all replacements:**
```css
property: var(--slds-g-[hook], originalValue);
```

**Important: Only replace values that match a hook's actual rendered value.** If a hardcoded value falls between two hooks (e.g., `3px` when hooks offer `4px` and `8px`), leave it unchanged. The linter auto-fix handles exact matches; manual fixes should only apply when there's a clear correspondence. Forcing a non-matching value into the nearest hook changes the component's visual appearance.

---

## Critical Rule: Never Invent Hooks

**Only use hooks that actually exist in SLDS 2.** The linter is the source of truth for which hooks exist and what values they map to. Do not:

- **Guess hook names** — Hooks like `--slds-g-spacing-medium`, `--slds-g-font-weight-bold`, `--slds-g-radius-large` do NOT exist. SLDS 2 uses numbered scales only (e.g., `--slds-g-spacing-4`, `--slds-g-font-weight-7`).
- **Extrapolate patterns** — If you see `--slds-g-spacing-1` through `--slds-g-spacing-12`, do not assume `--slds-g-spacing-13` exists. Each category has a fixed scale defined by the design system.
- **Invent semantic names** — There are no `--slds-g-spacing-page`, `--slds-g-font-heading`, or `--slds-g-shadow-modal` hooks. Hooks are numeric, not semantic.

**When unsure whether a hook exists:** Run the linter (`npx @salesforce-ux/slds-linter@latest lint --fix .`). It will suggest valid hooks for flagged values. If the linter doesn't flag a value or doesn't suggest a hook, leave it hardcoded.

---

## Table of Contents

- [Spacing Hooks](#spacing-hooks)
- [Sizing Hooks](#sizing-hooks)
- [Typography Hooks](#typography-hooks)
- [Border Width Hooks](#border-width-hooks)
- [Border Radius Hooks](#border-radius-hooks)
- [Shadow Hooks](#shadow-hooks)
- [Uplift Decision Tree](#uplift-decision-tree--non-color)
- [Common Mistakes](#common-mistakes)
- [Accessibility Notes](#accessibility-notes)

---

## Spacing Hooks

**Prefix:** `--slds-g-spacing-*`
**Use for:** `margin`, `padding`, `gap`, `row-gap`, `column-gap`
**Do NOT use for:** `width`, `height`, or other dimension properties (use sizing hooks)

**Scale range: 1–12.** There is no `--slds-g-spacing-13` or higher. If a value exceeds 5rem/80px, leave it hardcoded.

### Density-Aware Spacing

For components that adapt between comfy and compact display density, use density-aware variants:

| Hook Pattern | Applies To |
|---|---|
| `--slds-g-spacing-var-*` | All sides (margin, padding) |
| `--slds-g-spacing-var-block-*` | Vertical only (top/bottom) |
| `--slds-g-spacing-var-inline-*` | Horizontal only (left/right) |

Use density-aware hooks for data tables, forms, cards, tabs, and navigation components that need to respond to the user's density preference.

### Examples

```css
/* Before */
.card-body { padding: 1rem; }
.list-item { margin-bottom: 0.5rem; }
.grid { gap: 1.5rem; }

/* After — hook names come from the linter, not guesswork */
.card-body { padding: var(--slds-g-spacing-4, 1rem); }
.list-item { margin-bottom: var(--slds-g-spacing-2, 0.5rem); }
.grid { gap: var(--slds-g-spacing-5, 1.5rem); }

/* Multi-value shorthand */
.button { padding: var(--slds-g-spacing-2, 0.5rem) var(--slds-g-spacing-4, 1rem); }
```

---

## Sizing Hooks

**Prefix:** `--slds-g-sizing-*`
**Use for:** `width`, `height`, `min-width`, `max-width`, `min-height`, `max-height`
**Do NOT use for:** `margin`, `padding`, `gap` (use spacing hooks)
**Scale range: 1–16.** There is no `--slds-g-sizing-17` or higher.

### Examples

```css
/* Before */
.icon { width: 32px; height: 32px; }

/* After */
.icon { width: var(--slds-g-sizing-9, 32px); height: var(--slds-g-sizing-9, 32px); }
```

---

## Typography Hooks

### Font Scale

**Prefix:** `--slds-g-font-scale-*` (and `--slds-g-font-size-base` for 13px)
**Use for:** `font-size`
**Scale range: neg-4 through 10**, plus `base` (0.8125rem/13px). Negative values (`neg-1` to `neg-4`) are for small/caption text. There is no `--slds-g-font-scale-11` or higher.

Density-aware variant: `--slds-g-font-scale-var-*` (also 1–10) — adapts between comfy and compact.

### Font Weight

**Prefix:** `--slds-g-font-weight-*`
**Use for:** `font-weight`
**Scale range: 1–7.** Maps to CSS weight values 100–700. There is no `--slds-g-font-weight-8` or higher.

**Weight pairing guidance in SLDS 2:**
- Display text (large scale) → lighter weight
- Titles/headings → regular weight
- Buttons/small body titles → semi-bold weight
- Inline emphasis within body → bold weight (sparingly)

### Line Height

**Prefix:** `--slds-g-font-lineheight-*`
**Use for:** `line-height`
**Scale range: 1–6.** Values range from 1 to 2. There is no `--slds-g-font-lineheight-7` or higher.

### Font Family

| Hook | Use Case |
|---|---|
| `--slds-g-font-family` | Default font family |
| `--slds-g-font-family-base` | Base font family |
| `--slds-g-font-family-monospace` | Code snippets |

### Content Width

**Prefix:** `--slds-g-sizing-content-*` and `--slds-g-sizing-heading-*`
**Use for:** `max-width` on text containers (uses `ch` units for readable line lengths)
**Scale range:** `content` 1–3, `heading` 1–3.

### Typography Examples

```css
/* Before */
.title { font-size: 18px; font-weight: bold; line-height: 1.25; }
.body { font-size: 14px; font-weight: normal; line-height: 1.5; }

/* After — let the linter confirm the correct scale numbers */
.title {
  font-size: var(--slds-g-font-scale-4, 18px);
  font-weight: var(--slds-g-font-weight-4, bold);
  line-height: var(--slds-g-font-lineheight-2, 1.25);
}
.body {
  font-size: var(--slds-g-font-scale-1, 14px);
  font-weight: var(--slds-g-font-weight-4, normal);
  line-height: var(--slds-g-font-lineheight-4, 1.5);
}
```

---

## Border Width Hooks

**Prefix:** `--slds-g-sizing-border-*`
**Use for:** `border-width`, `border`, `border-top`, etc. (the width component)
**Scale range: 1–4.** Maps to 1px–4px. There is no `--slds-g-sizing-border-5` or higher.

Border widths are NOT density-aware — they stay constant regardless of comfy/compact settings.

**SLDS 2 philosophy:** Use borders sparingly. Prefer spacing or shadows for visual separation. Use borders purposefully for structure, interactivity indication, and state communication.

### Examples

```css
/* Before */
.input { border: 1px solid #ccc; }

/* After */
.input { border: var(--slds-g-sizing-border-1, 1px) solid var(--slds-g-color-border-2, #ccc); }
```

---

## Border Radius Hooks

**Prefix:** `--slds-g-radius-border-*`
**Use for:** `border-radius`
**Scale range: 1–4** plus special values `circle` and `pill`. There is no `--slds-g-radius-border-5` or higher.

Choose radius by **component type**, not by matching px values. The hook resolves to the design-system value; the original value is preserved as fallback only.

| Hook | Components |
|---|---|
| `--slds-g-radius-border-1` | Badges, checkboxes |
| `--slds-g-radius-border-2` | Text inputs, comboboxes, text areas, tooltips |
| `--slds-g-radius-border-3` | Menus, popovers |
| `--slds-g-radius-border-4` | Cards, modals, docked composers |
| `--slds-g-radius-border-circle` | Buttons, button icons, avatars, radios, pills |
| `--slds-g-radius-border-pill` | Pill-shaped elements |

Border radius hooks are NOT density-aware.

### Examples

```css
/* Before */
.card { border-radius: 8px; }
.button { border-radius: 50%; }

/* After — chosen by component type, not px value */
.card { border-radius: var(--slds-g-radius-border-4, 8px); }
.button { border-radius: var(--slds-g-radius-border-circle, 50%); }
```

---

## Shadow Hooks

**Prefix:** `--slds-g-shadow-*`
**Use for:** `box-shadow`
**Scale range: 1–6.** Directional variants (`-block-start-*`, `-block-end-*`, `-inline-start-*`, `-inline-end-*`) use range **1–4**. Focus variants (`-outline-focus-*`, `-outset-focus-*`, `-inset-focus-*`, `-inset-inverse-focus-*`) only have **1**.

Match shadow depth to the element's stacking order — higher shadows for elements visually above others:

| Hook | Components |
|---|---|
| `--slds-g-shadow-1` | Page headers, joined tables, filter panels, dropdowns, inline edit, slider handles |
| `--slds-g-shadow-2` | Menus, docked form footer, docked utility bar, color picker, notifications |
| `--slds-g-shadow-3` | Panels, docked composer, tooltips, toasts |
| `--slds-g-shadow-4` | Modals, popovers, App Launcher |

### Directional Shadows

For components positioned against screen edges:

| Hook Pattern | Direction |
|---|---|
| `--slds-g-shadow-block-start-*` | Upward |
| `--slds-g-shadow-block-end-*` | Downward (inherits from base) |
| `--slds-g-shadow-inline-start-*` | Left |
| `--slds-g-shadow-inline-end-*` | Right |

### Focus Shadows

| Hook Pattern | Use Case |
|---|---|
| `--slds-g-shadow-outline-focus-*` | Simple outline focus |
| `--slds-g-shadow-outset-focus-*` | Double ring outset focus (white inner, brand outer) |
| `--slds-g-shadow-inset-focus-*` | Single ring inset focus |
| `--slds-g-shadow-inset-inverse-focus-*` | Double ring inset focus (brand inner, white outer) |

**SLDS 2 philosophy:** Don't apply shadows to base-level components that sit on a surface without covering other components.

### Examples

```css
/* Before */
.modal { box-shadow: 0 4px 8px rgba(0,0,0,0.1); }
.dropdown { box-shadow: 0 2px 4px rgba(0,0,0,0.1); }

/* After */
.modal { box-shadow: var(--slds-g-shadow-4, 0 4px 8px rgba(0,0,0,0.1)); }
.dropdown { box-shadow: var(--slds-g-shadow-1, 0 2px 4px rgba(0,0,0,0.1)); }
```

---

## Uplift Decision Tree — Non-Color

When the linter flags a non-color hardcoded value, follow this process:

### Step 1: Run the Linter First

Always run `npx @salesforce-ux/slds-linter@latest lint --fix .` before manual fixes. The linter handles exact value-to-hook matches automatically. Only proceed to manual fixes for values the linter flags but cannot auto-fix.

### Step 2: Density-Aware or Standard?

Only use density-aware hooks if the original value was a variable density token:
- `--lwc-varSpacingMedium` → `--slds-g-spacing-var-4`
- `--lwc-spacingMedium` → `--slds-g-spacing-4` (non-variable, use standard hook)

### Step 3: No Exact Match — Should You Replace?

**Shadow:** If a shadow hook is nearly identical (e.g., offset differs by 1px), replace with the closest equivalent. Otherwise, leave as-is.

**Border Radius:** Replace by component type (see table above), not by px value. If the element doesn't match a known component type, leave hardcoded.

**Typography:** If between two scale values, use the closest. If far outside the available range, leave as-is.

**Spacing/Sizing:** If within 10% of a hook value, update to the closest hook. Otherwise leave as-is.

**Hardcoded numerical/structural values:** Never change or remove values like `width: 100%`, `height: 50%`, `max-width: 200px`, `flex: 1`, `height: auto`, `display: none`, `line-height: 1.5`, or `0`. These are layout and structural values, not candidates for hooks. Leave them exactly as they are in the source CSS.

---

## Common Mistakes

1. **Inventing hooks that don't exist** — This is the most common and damaging mistake. Named hooks (`--slds-g-spacing-medium`) and out-of-range numbered hooks do not exist. Always verify with the linter.

2. **Confusing spacing and sizing** — Spacing is for margins/padding/gaps. Sizing is for width/height/dimensions. Using the wrong one makes the value density-unaware or disrupts the grid system.

3. **Replacing or removing hardcoded numerical values** — Never change `width: 100%`, `height: 50%`, `max-width: 200px`, `flex: 1`, `height: auto`, `display: none`, `line-height: 1.5`, or `0`. These are structural/layout values — do not replace them with hooks and do not remove them.

4. **Missing fallback values** — Always include the original value as fallback: `var(--slds-g-spacing-4, 1rem)`. Without fallbacks, the component breaks if the hook is unavailable.

5. **Ignoring density-aware variants** — For data-dense components (tables, forms, lists), use `--slds-g-spacing-var-*` and `--slds-g-font-scale-var-*` so spacing and text adapt to comfy/compact settings.

6. **Using `--slds-c-*` or `--slds-s-*` hooks** — Only `--slds-g-*` (global) hooks are valid for migration. Component and scoped hooks are not for direct use in CSS.

---

## Accessibility Notes

### Touch Targets
- Minimum 24x24 CSS pixels for pointer inputs (WCAG 2.2 Level AA)
- Minimum 44x44 for touch inputs (industry standard)
- Use spacing hooks for padding to achieve target sizes on interactive elements

### Typography Readability
- Use body-level font scale or larger for primary body text
- Default base font size (13px) is at the lower limit for comfortable reading
- Use a line height of 1.5 as default for body text (WCAG 1.4.12)
- Optimal line length: 45-75 characters (use content width hooks for max-width)

### Focus Visibility
- Use appropriate border-width hooks for focus state borders
- Use `--slds-g-shadow-outset-focus-*` for focus rings (double-ring pattern visible on any background)
- Focus borders must maintain 3:1 minimum contrast with adjacent surfaces

### Border Contrast
- Borders must maintain 3:1 contrast ratio with adjacent surfaces
- Use higher-contrast border color hooks for interactive elements
- Use lower-contrast border color hooks for decorative/non-interactive borders
