# SLDS Migration Examples

Before/after examples organized by violation type.

## Table of Contents

- [Class Override Example](#class-override-example)
- [LWC Token Example](#lwc-token-example)
- [Hardcoded Value Examples](#hardcoded-value-examples)
- [Aura t() Token Migration](#aura-t-token-migration)
- [Deprecated Class Removal](#deprecated-class-removal)
- [Color-Mix with Transparency](#color-mix-with-transparency)
- [calc() with Legacy Tokens](#calc-with-legacy-tokens)
- [Tokens with No SLDS 2 Equivalent](#tokens-with-no-slds-2-equivalent)
- [Multi-File End-to-End (Aura)](#multi-file-end-to-end-aura)

---

## Class Override Example

**Violation:**
```
dataTable.css
  5:1   warning  Overriding slds-table isn't supported. To differentiate SLDS and
                 custom classes, create a CSS class in your namespace.
                 Examples: myapp-input, myapp-button.                      slds/no-slds-class-overrides
  12:1  warning  Overriding slds-button isn't supported...                 slds/no-slds-class-overrides
```

**Before:**
```css
.slds-table {
  border-width: var(--slds-g-sizing-border-1, 1px);
  border-radius: var(--slds-g-radius-border-2, 0.25rem);
}

.slds-table .slds-button {
  padding: var(--slds-g-spacing-2, 0.5rem) var(--slds-g-spacing-2, 1rem);
}
```

```html
<table class="slds-table">
  <tr><td><button class="slds-button">Edit</button></td></tr>
</table>
```

**After:**
```css
.dataTable-table {
  border-width: var(--slds-g-sizing-border-1, 1px);
  border-radius: var(--slds-g-radius-border-2, 0.25rem);
}

.dataTable-table .dataTable-button {
  padding: var(--slds-g-spacing-2, 0.5rem) var(--slds-g-spacing-2, 1rem);
}
```

```html
<table class="slds-table dataTable-table">
  <tr><td><button class="slds-button dataTable-button">Edit</button></td></tr>
</table>
```

---

## LWC Token Example

**Violation:**
```
panelHeader.css
  3:3  error  The '--lwc-colorBackgroundAlt' design token is deprecated. Replace it with
              the SLDS 2 styling hook and set the fallback to '--lwc-colorBackgroundAlt'.
              1. --slds-g-color-surface-2
              2. --slds-g-color-surface-container-2                        slds/lwc-token-to-slds-hook
```

**Before:**
```css
.header-bar {
  background-color: var(--lwc-colorBackgroundAlt);
}
```

```html
<div class="THIS">
  <div class="header-bar">Settings</div>
  <div class="panel-content">...</div>
</div>
```

**Context:** `.header-bar` is a section within the component → choose container.

**After:**
```css
.header-bar {
  background-color: var(--slds-g-color-surface-container-2, var(--lwc-colorBackgroundAlt));
}
```

---

## Hardcoded Value Examples

### Tile with Border and Spacing

**Violation:**
```
tile.css
  2:20  warning  Consider replacing the #ffffff static value with an SLDS 2 styling hook
                 that has a similar value:
                 1. --slds-g-color-surface-1
                 2. --slds-g-color-surface-container-1
                 3. --slds-g-color-on-accent-1
                 4. --slds-g-color-on-accent-2
                 5. --slds-g-color-on-accent-3                             slds/no-hardcoded-values-slds2
```

**Before:**
```css
.info-tile {
  background-color: #ffffff;
  border: 1px solid #e5e5e5;
  padding: 1rem;
}
```

**Context:** Tile is a container sitting on a page surface → choose `surface-container-1` from the list.

**After:**
```css
.info-tile {
  background-color: var(--slds-g-color-surface-container-1, #ffffff);
  border: var(--slds-g-sizing-border-1, 1px) solid var(--slds-g-color-border-1, #e5e5e5);
  padding: var(--slds-g-spacing-4, 1rem);
}
```

### Link Colors

**Before:**
```css
.nav-link {
  color: #0176d3;
}

.nav-link:hover {
  color: #014486;
}
```

**Context:** Links are interactive → accent family. Default = accent-2 (accessible). Hover goes one up: accent-3.

**After:**
```css
.nav-link {
  color: var(--slds-g-color-accent-2, #0176d3);
}

.nav-link:hover {
  color: var(--slds-g-color-accent-3, #014486);
}
```

### Alert Validation States

**Before:**
```css
.alert-error {
  border-color: #c23934;
  background: #fddde3;
}

.alert-error-text {
  color: #c23934;
  font-size: 12px;
}

.alert-success {
  border-color: #4bca81;
}
```

**After:**
```css
.alert-error {
  border-color: var(--slds-g-color-border-error-1, #c23934);
  background: var(--slds-g-color-error-container-1, #fddde3);
}

.alert-error-text {
  color: var(--slds-g-color-on-error-1, #c23934);
  font-size: var(--slds-g-font-scale-neg-1, 12px);
}

.alert-success {
  border-color: var(--slds-g-color-border-success-1, #4bca81);
}
```

### Brand Icon with Accent Background

**Before:**
```css
.icon-container {
  width: 2rem;
  height: 2rem;
  background-color: #066AFE;
}

.account-icon {
  fill: #FFFFFF;
}
```

**Context:** Blue background with white icon = brand element → accent family. `on-accent` pairs with `accent-container`.

**After:**
```css
.icon-container {
  width: var(--slds-g-sizing-9, 2rem);
  height: var(--slds-g-sizing-9, 2rem);
  background-color: var(--slds-g-color-accent-container-1, #066AFE);
}

.account-icon {
  fill: var(--slds-g-color-on-accent-1, #FFFFFF);
}
```

### Profile Header — Spacing, Typography, and Shadow

**Before:**
```css
.profile-header {
  padding: 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.profile-name {
  font-size: 18px;
  font-weight: 700;
  line-height: 1.25;
  margin-bottom: 0.5rem;
}

.profile-role {
  font-size: 14px;
  font-weight: 400;
  line-height: 1.5;
}
```

**After:**
```css
.profile-header {
  padding: var(--slds-g-spacing-5, 1.5rem);
  border-radius: var(--slds-g-radius-border-3, 0.75rem);
  box-shadow: var(--slds-g-shadow-1, 0 2px 4px rgba(0,0,0,0.1));
}

.profile-name {
  font-size: var(--slds-g-font-scale-4, 18px);
  font-weight: var(--slds-g-font-weight-7, 700);
  line-height: var(--slds-g-font-lineheight-2, 1.25);
  margin-bottom: var(--slds-g-spacing-2, 0.5rem);
}

.profile-role {
  font-size: var(--slds-g-font-scale-1, 14px);
  font-weight: var(--slds-g-font-weight-4, 400);
  line-height: var(--slds-g-font-lineheight-4, 1.5);
}
```

### Search Input — Border and Focus

**Before:**
```css
.search-input {
  border: 1px solid #ccc;
  border-radius: 0.5rem;
  padding: 0.5rem 0.75rem;
  font-size: 14px;
}

.search-input:focus {
  border-width: 3px;
}
```

**After:**
```css
.search-input {
  border: var(--slds-g-sizing-border-1, 1px) solid var(--slds-g-color-border-2, #ccc);
  border-radius: var(--slds-g-radius-border-2, 0.5rem);
  padding: var(--slds-g-spacing-2, 0.5rem) var(--slds-g-spacing-3, 0.75rem);
  font-size: var(--slds-g-font-scale-1, 14px);
}

.search-input:focus {
  border-width: var(--slds-g-sizing-border-3, 3px);
}
```

### What NOT to Replace

Layout values (`100%`, `auto`, `0`, `flex: 1`, `none`), animation properties, opacity, and overlay alpha values (`rgba(0,0,0,0.5)`) should remain unchanged. See [rule-no-hardcoded-values.md](rule-no-hardcoded-values.md) for the full list.

---

## Aura t() Token Migration

**Before:**
```css
.THIS .stepTitle {
  color: t(colorTextPlaceholder);
  font-size: t(fontSizeMedium);
  padding: t(spacingSmall);
}
```

**After:**
```css
.THIS .stepTitle {
  color: var(--slds-g-color-on-surface-2, var(--lwc-colorTextPlaceholder));
  font-size: var(--slds-g-font-scale-2, var(--lwc-fontSizeMedium));
  padding: var(--slds-g-spacing-3, var(--lwc-spacingSmall));
}
```

**Why these hooks:** `colorTextPlaceholder` maps to `on-surface-2` (muted foreground text). `fontSizeMedium` maps to `font-scale-2` (1rem). `spacingSmall` maps to `spacing-3` (0.75rem). See [rule-no-deprecated-tokens-slds1.md](rule-no-deprecated-tokens-slds1.md) for all token mappings.

---

## Deprecated Class Removal

**Before (`.cmp`):**
```html
<span class="slds-icon_container slds-icon-utility-error">
  <lightning:icon iconName="utility:error" />
</span>
```

**After:**
```html
<span class="slds-icon_container">
  <lightning:icon iconName="utility:error" />
</span>
```

**Why remove:** `slds-icon-utility-*` classes are removed in SLDS 2. The `<lightning:icon>` component applies its own styling via `iconName`. Keeping the deprecated class causes linter errors and has no visual effect.

---

## Color-Mix with Transparency

**Before:**
```css
.THIS .errorBorder { border: 2px solid rgba(186, 5, 23, 0.7); }
```

**After:**
```css
.THIS .errorBorder {
  border: var(--slds-g-sizing-border-2, 2px) solid color-mix(in oklab, var(--slds-g-color-palette-red-40, rgb(181,54,45)), transparent 30%);
}
```

**Why color-mix:** `rgba()` can't wrap a CSS variable for the color component alone. `color-mix(in oklab, ...)` lets you apply transparency to the hook's resolved value at runtime. Formula: X% opacity = (100-X)% transparent. Use opaque `rgb()` fallback to avoid double transparency when both `color-mix` and `rgba` are applied.

---

## calc() with Legacy Tokens

**Before:**
```css
height: t('calc(' + lineHeightButton + ' + 2px)');
```

**After (if calc needed):**
```css
height: calc(var(--lwc-lineHeightButton) + 2px);
```

**Simplified (try first):**
```css
height: var(--lwc-lineHeightButton);
```

**Why simplify:** The `+ 2px` in legacy `t()` calc expressions was often a workaround for rendering inconsistencies. Try without it first — if the component renders correctly, the simpler form is preferred.

---

## Tokens with No SLDS 2 Equivalent

```css
/* Before */
z-index: var(--lwc-zIndexSticky);
transition: opacity var(--slds-g-duration-slowly, var(--lwc-durationSlowly)) ease-in-out;

/* After — z-index: hardcoded, duration: --lwc-* directly */
z-index: 9000;
transition: opacity var(--lwc-durationSlowly) ease-in-out;
```

**Why:** Not every legacy token has an SLDS 2 equivalent. Z-index and duration are internal layout/animation concerns — hardcode z-index, use `--lwc-*` for duration. Inventing `--slds-g-duration-*` triggers `slds/no-slds-namespace-for-custom-hooks`.

---

## Multi-File End-to-End (Aura)

**CSS before:**
```css
.THIS .slds-card__header {
  background: var(--lwc-colorBackgroundAlt);
  z-index: var(--lwc-zIndexSticky);
  border-bottom: 1px solid #ddd;
}
```

**CSS after:**
```css
.THIS .relatedList-card-header {
  background: var(--slds-g-color-surface-container-2, var(--lwc-colorBackgroundAlt));
  z-index: 9000;
  border-bottom: var(--slds-g-sizing-border-1, 1px) solid var(--slds-g-color-border-1, #ddd);
}
```

**Markup before (`.cmp`):**
```html
<h2 class="slds-card__header">Related Items</h2>
```

**Markup after:**
```html
<h2 class="slds-card__header relatedList-card-header">Related Items</h2>
```

Three rules applied: token replacement, class override, hardcoded border. `slds-card__header` is a part within a card → choose `container`.