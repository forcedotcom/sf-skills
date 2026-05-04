# Rule: No Deprecated Tokens SLDS1

**Rule ID:** `slds/no-deprecated-tokens-slds1`
**Severity:** Error
**Scope:** Replaces legacy Aura `t(tokenName)` and `token(tokenName)` syntax with SLDS 2 styling hooks.

---

## What the Linter Does

The linter detects `t()` and `token()` function calls in CSS, `.cmp`, and `.html` files. These are Aura-era token accessors that are deprecated in SLDS 2.

Two message types:

**When a replacement exists:**
```
Consider removing t(colorTextDefault) or replacing it with --slds-g-color-on-surface-3.
Set the fallback to t(colorTextDefault).
```

**When no replacement exists:**
```
Update outdated design tokens to SLDS 2 styling hooks with similar values.
```

---

## Replacement Pattern

Always wrap in `var()` with the original LWC token as fallback:

```css
/* Before — Aura t() syntax */
color: t(colorTextDefault);
background-color: t(colorBackgroundAlt);

/* After — SLDS 2 hook with LWC fallback */
color: var(--slds-g-color-on-surface-3, var(--lwc-colorTextDefault));
background-color: var(--slds-g-color-surface-container-1, var(--lwc-colorBackgroundAlt));
```

The nested `var()` fallback ensures compatibility during migration — if the SLDS 2 hook isn't available, the LWC token still resolves.

---

## Common Token Mappings

### Text Colors

| Legacy Token | SLDS2 Hook | LWC Fallback |
|---|---|---|
| `t(colorTextPlaceholder)` | `--slds-g-color-on-surface-2` | `--lwc-colorTextPlaceholder` |
| `t(colorTextWeak)` | `--slds-g-color-on-surface-1` | `--lwc-colorTextWeak` |
| `t(colorTextDefault)` | `--slds-g-color-on-surface-3` | `--lwc-colorTextDefault` |
| `t(colorTextIconInverse)` | `--slds-g-color-on-surface-inverse-1` | `--lwc-colorTextIconInverse` |

### Background Colors

| Legacy Token | SLDS2 Hook | LWC Fallback |
|---|---|---|
| `t(colorBackground)` | `--slds-g-color-surface-container-2` | `--lwc-colorBackground` |
| `t(colorBackgroundAlt)` | `--slds-g-color-surface-container-1` | `--lwc-colorBackgroundAlt` |
| `t(colorBackgroundAlt2)` | `--slds-g-color-surface-container-2` | `--lwc-colorBackgroundAlt2` |

### Spacing

| Legacy Token | SLDS2 Hook | LWC Fallback |
|---|---|---|
| `t(spacingXxSmall)` | `--slds-g-spacing-1` | `--lwc-spacingXxSmall` |
| `t(spacingXSmall)` | `--slds-g-spacing-2` | `--lwc-spacingXSmall` |
| `t(spacingSmall)` | `--slds-g-spacing-3` | `--lwc-spacingSmall` |
| `t(spacingMedium)` | `--slds-g-spacing-4` | `--lwc-spacingMedium` |
| `t(spacingLarge)` | `--slds-g-spacing-5` | `--lwc-spacingLarge` |
| `t(templateGutters)` | `--slds-g-spacing-3` | `--lwc-templateGutters` |

### Border Radius

| Legacy Token | SLDS2 Hook | LWC Fallback |
|---|---|---|
| `t(borderRadiusSmall)` | `--slds-g-radius-border-1` | `--lwc-borderRadiusSmall` |
| `t(borderRadiusMedium)` | `--slds-g-radius-border-2` | `--lwc-borderRadiusMedium` |
| `t(borderRadiusLarge)` | `--slds-g-radius-border-3` | `--lwc-borderRadiusLarge` |

### Font Sizes

| Legacy Token | SLDS2 Hook | LWC Fallback |
|---|---|---|
| `t(fontSizeSmall)` | `--slds-g-font-scale-1` | `--lwc-fontSizeSmall` |
| `t(fontSizeMedium)` | `--slds-g-font-scale-2` | `--lwc-fontSizeMedium` |
| `t(fontSizeLarge)` | `--slds-g-font-scale-3` | `--lwc-fontSizeLarge` |
| `t(fontSizeXLarge)` | `--slds-g-font-scale-4` | `--lwc-fontSizeXLarge` |

### Font Weights

| Legacy Token | SLDS2 Hook | LWC Fallback |
|---|---|---|
| `t(fontWeightLight)` | `--slds-g-font-weight-3` | `--lwc-fontWeightLight` |
| `t(fontWeightRegular)` | `--slds-g-font-weight-4` | `--lwc-fontWeightRegular` |
| `t(fontWeightBold)` | `--slds-g-font-weight-7` | `--lwc-fontWeightBold` |

### Line Heights

| Legacy Token | SLDS2 Hook | LWC Fallback |
|---|---|---|
| `t(lineHeightHeading)` | `--slds-g-font-lineheight-2` | `--lwc-lineHeightHeading` |

---

## Tokens with No SLDS 2 Equivalent

### Z-Index

Z-index tokens have no SLDS 2 hook. Use the hardcoded value directly:

```css
/* Before */
z-index: t(zIndexSticky);

/* After — hardcoded, no hook available */
z-index: 9000;
```

### Duration

Duration tokens are for internal component transitions. Use `--lwc-*` directly — do NOT invent `--slds-g-duration-*` hooks:

```css
/* Bad — inventing a non-existent hook */
transition: var(--slds-g-duration-slowly, var(--lwc-durationSlowly));

/* Good — use --lwc-* directly */
transition: var(--lwc-durationSlowly);
```

Available duration tokens: `--lwc-durationInstantly`, `--lwc-durationPromptly`, `--lwc-durationSlowly`.

---

## Wizard Token Mappings

### oneDesktopSetupWizardTokens

From `oneDesktopSetupWizardTokens.tokens` — map wizard token → base token → SLDS 2:

| Wizard Token | SLDS2 Replacement |
|---|---|
| `wizardColorTextHeader` | `var(--slds-g-color-on-surface-3, var(--lwc-colorTextDefault))` |
| `wizardColorActiveMilestoneTracker` | `var(--lwc-colorBackgroundButtonBrand)` |
| `wizardColorInactiveMilestoneTracker` | `var(--slds-g-color-surface-container-1, var(--lwc-colorBackgroundInputDisabled))` |
| `wizardColorTextMilestoneTracker` | `var(--slds-g-color-on-surface-3, var(--lwc-colorTextActionLabelActive))` |
| `wizardFontWeightMilestoneTracker` | `var(--slds-g-font-weight-4, var(--lwc-fontWeightRegular))` |
| `wizardFontSizeMilestoneTracker` | `var(--slds-g-font-scale-2, var(--lwc-fontSizeMedium))` |
| `wizardColorBackgroundError` | `var(--slds-g-color-surface-container-2, var(--lwc-colorBackgroundInput))` |
| `wizardBorderRadiusError` | `var(--slds-g-radius-border-2, var(--lwc-borderRadiusMedium))` |

### s1wizardNamespace

From `s1wizardNamespace.tokens`:

| S1wizard Token | SLDS2 Replacement |
|---|---|
| `s1wizardContactFieldBackground` | `var(--slds-g-color-on-surface-1, var(--lwc-colorBackgroundActionbarIconUtility))` |
| `s1wizardComicHeadingFontFamily` | `var(--slds-g-font-family, var(--lwc-fontFamily))` |
| `s1wizardComicHeadingTextSize` | `var(--slds-g-font-scale-4, var(--lwc-fontSizeXLarge))` |
| `s1wizardComicHeadingTextColor` | `var(--slds-g-color-on-surface-3, var(--lwc-colorTextDefault))` |

---

## Font-Family Cleanup

After the linter runs, it may add verbose font-stack fallbacks to `font-family`. For **font-family only**, trim to just the hook tokens — remove the hardcoded font stack:

```css
/* Linter output — verbose */
font-family: var(--slds-g-font-family, var(--lwc-fontFamily, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif));

/* Cleaned up — tokens only */
font-family: var(--slds-g-font-family, var(--lwc-fontFamily));
```

For all other properties, **keep** the linter's fallbacks (rgb, rem, px values).

---

## Mandatory Rules

**Rule 1: ONLY USE LINTER-SUGGESTED HOOKS**
- Read the linter output first
- Only use hooks that the linter suggests as replacements
- If the linter says "no replacement", see "Tokens with No SLDS 2 Equivalent" above

**Rule 2: ALWAYS INCLUDE FALLBACK**
- Format: `var(--slds-g-[hook], var(--lwc-[token]))`
- The `--lwc-*` fallback ensures the component still works if the SLDS 2 hook isn't available

**Rule 3: MINIMAL CHANGES**
- Only fix actual `slds/no-deprecated-tokens-slds1` violations
- Do not refactor surrounding code or styles
- Reference line numbers for all modifications

---

## Validation Checklist

- [ ] All `t()` and `token()` calls have SLDS 2 replacements (or documented as no-equivalent)
- [ ] Replacements use linter-suggested hooks
- [ ] Original token included as LWC fallback: `var(--slds-g-*, var(--lwc-*))`
- [ ] Duration tokens use `--lwc-*` directly (not invented `--slds-g-duration-*`)
- [ ] Z-index tokens use hardcoded values
- [ ] Font-family has no font-stack fallback (tokens only)
- [ ] Re-run linter shows zero errors for this rule
