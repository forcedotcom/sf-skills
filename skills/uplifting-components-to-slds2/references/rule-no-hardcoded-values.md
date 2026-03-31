# Rule: No Hardcoded Values

**Rule ID:** `slds/no-hardcoded-values-slds2`
**Severity:** Warning
**Scope:** All CSS properties with hardcoded values that have SLDS 2 hook equivalents — colors, spacing, sizing, typography, borders, radius, and shadows.

---

## What the Linter Does

The linter detects hardcoded values and reports them as warnings. Here's real output for an icon component:

```
  3:10  warning  Consider replacing the 32px static value with an SLDS 2 styling hook
                 that has a similar value: --slds-g-sizing-9.                              slds/no-hardcoded-values-slds2

  5:21  warning  Dynamic element with css-class "icon-container" using static value
                 "#066afe" for "background-color" css property. Consider replacing
                 the #066AFE static value with an SLDS 2 styling hook:
                 1. --slds-g-color-surface-inverse-1
                 2. --slds-g-color-surface-inverse-2
                 3. --slds-g-color-surface-container-inverse-1                             slds/no-hardcoded-values-slds2

  9:9   warning  Dynamic element with css-class "account-icon" using static value
                 "#ffffff" for "fill" css property. Consider replacing:
                 1. --slds-g-color-on-accent-1
                 2. --slds-g-color-on-accent-2
                 3. --slds-g-color-error-base-95
                 4. --slds-g-color-warning-base-95                                         slds/no-hardcoded-values-slds2
```

**Non-color values** get single suggestions — auto-fixable with `--fix`:

```css
/* 32px → sizing-9 (single suggestion, auto-fixed) */
width: var(--slds-g-sizing-9, 32px);
```

**Color values** get multiple suggestions — requires manual selection. The linter suggests hooks based on color-value similarity, **not semantic context**. You must inspect the HTML to choose correctly.

---

## What to Fix vs What to Skip

| Property Type | Example Values | Action |
|---|---|---|
| Color properties (`color`, `fill`, `background`, `background-color`, `stroke`, `border-*-color`, `outline-color`) | `#fff`, `rgb(0,0,0)` | **Fix** — replace with color hook + fallback |
| Spacing properties (`margin`, `padding`, `gap`) | `16px`, `1rem`, `24px` | **Fix** — replace with spacing hook + fallback |
| Sizing properties (`width`, `height`, `min-*`, `max-*`) | `32px`, `2rem` | **Fix** — replace with sizing hook + fallback |
| Font properties (`font-size`, `font-weight`, `line-height`) | `14px`, `bold`, `1.5` | **Fix** — replace with typography hook + fallback |
| Border properties (`border-radius`, `border-width`) | `8px`, `1px` | **Fix** — replace with radius/border hook + fallback |
| Shadow properties (`box-shadow`) | `0 4px 8px rgba(…)` | **Fix** — replace with shadow hook + fallback |
| Layout/structural values | `100%`, `auto`, `0`, `inherit`, `none` | **Skip** — leave unchanged, removing breaks rendering |

When the linter says "Remove the static value" for a layout value like `width: 100%` or `height: auto`, **do not remove it**.

---

## Replacement Pattern

Always include the original value as fallback:

```css
property: var(--slds-g-[hook], originalValue);
```

The fallback must be the **exact original value** from the source CSS (e.g., `#066AFE`, not a converted equivalent).

---

## Decision Tree

When examining a hardcoded value or deprecated token, follow this decision tree:

```
1. SLDS utility class available?
   └─ Yes → Remove CSS, add utility class to HTML
   └─ No  ↓

2. At least one 1:1 styling hook mapping?
   ├─ Exactly one  → Use it with fallback
   ├─ Multiple     → Inspect HTML context to choose (see decision guides)
   └─ None         ↓

3. No exact match
   └─ No close match → Leave hardcoded
```

### Step 1: Check for Utility Classes

If an SLDS utility class sets the exact property to the exact value, remove the CSS and replace with the class on the HTML element(s).

**Best fit vs perfect fit:** Use existing utilities that get you close enough, even if it means combining two or three classes. This keeps markup readable, styles consistent, and avoids unnecessary custom CSS. Don't write new CSS rules for edge cases unless absolutely necessary.

**When modifying CSS classes:**
- Before removing a CSS declaration, ensure you understand how it's used in HTML and in JS (computed classes)
- Update any tests after changing CSS classes — some tests use class query selectors that should be replaced with `data-tid` attributes

#### Example: Replacing with Utility Classes

Common CSS like `display: flex` with alignment can often be replaced entirely:

```css
/* Before — component.css */
.container {
    display: flex;
    flex-direction: row;
    justify-content: center;
    align-items: center;
}
```

```html
<!-- Before — component.html -->
<div class="container">
```

These styles map to SLDS grid utility classes:

```html
<!-- After — component.html (CSS removed entirely) -->
<div class="slds-grid slds-grid_align-center slds-grid_vertical-align-center">
```

Note: `flex-direction: row` is the default for `display: flex` — it can be removed entirely.

### Steps 2 & 3: Choose the Right Hook

For choosing between multiple hooks or finding the closest match, see the decision guides:

| Category | Decision Guide |
|---|---|
| Color (background, foreground, border color) | [color-hooks-decision-guide.md](color-hooks-decision-guide.md) — surface vs container, semantic vs palette, applied examples from real PRs |
| Spacing, sizing, typography, borders, radius, shadows | [non-color-hooks-decision-guide.md](non-color-hooks-decision-guide.md) — numbered scales, closest-match rules, density-aware variants |

---

## Common Mistakes

1. **Inventing hook names** — Only use hooks documented in the SLDS design system.
2. **Missing fallback** — Always include the original value: `var(--slds-g-hook, originalValue)`
3. **Confusing spacing and sizing** — Spacing is for margins/padding/gaps. Sizing is for width/height/dimensions.
4. **Using named hooks** — `--slds-g-spacing-medium`, `--slds-g-font-weight-bold`, `--slds-g-radius-large` do NOT exist. Only numbered hooks exist.
5. **Replacing layout values** — Don't replace `100%`, `auto`, `flex: 1`, `none`, or `0` with hooks.
6. **Blindly trusting linter suggestions for colors** — The linter matches by color value, not semantic context. Always inspect HTML before choosing.

## What NOT to Replace

Leave these unchanged (no SLDS hooks apply):

```css
width: 100%;                   /* layout values */
height: auto;                  /* layout values */
flex: 1;                       /* layout values */
display: none;                 /* layout values */
transition: color 0.3s ease;   /* animation values */
opacity: 0.5;                  /* opacity */
background: linear-gradient(…); /* gradients */
left: 50%;                     /* positioning offsets */
```
