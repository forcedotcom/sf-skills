# Common Patterns

Frequently encountered patterns, class lists, and edge cases for SLDS 2 migration.

---

## Deprecated SLDS 2 Classes

These classes are removed in SLDS 2. Remove them from markup (`.html` for LWC, `.cmp` for Aura):

| Deprecated Class | Action |
|---|---|
| `slds-icon-utility-error` | Remove — icon component handles styling |
| `slds-icon-utility-*` (all variants) | Remove — use icon component variants instead |

```html
<!-- Before -->
<span class="slds-icon_container slds-icon-utility-error">

<!-- After -->
<span class="slds-icon_container">
```

---

## Color Palette Fallbacks

When using palette hooks for data visualization or decorative color, include RGB fallbacks:

| SLDS2 Hook | RGB Fallback | Common Use |
|---|---|---|
| `--slds-g-color-palette-red-40` | `rgb(181,54,45)` | Critical indicators, data viz |
| `--slds-g-color-palette-blue-50` | `rgb(0,112,210)` | Brand colors, primary actions |
| `--slds-g-color-palette-green-50` | `rgb(4,132,75)` | Positive indicators, data viz |

```css
color: var(--slds-g-color-palette-red-40, rgb(181,54,45));
background: var(--slds-g-color-palette-blue-50, rgb(0,112,210));
```

For transparency with palette hooks, use `color-mix()` — see Advanced Patterns in [SKILL.md](../SKILL.md).

---

## Tokens with No SLDS 2 Equivalent

Some legacy tokens have no direct SLDS 2 hook. Use `--lwc-*` or hardcoded values:

| Token | Action | Replacement |
|---|---|---|
| `lineHeightButton` | Use `--lwc-*` directly | `var(--lwc-lineHeightButton)` |
| `durationInstantly` | Use `--lwc-*` directly | `var(--lwc-durationInstantly)` |
| `durationPromptly` | Use `--lwc-*` directly | `var(--lwc-durationPromptly)` |
| `durationSlowly` | Use `--lwc-*` directly | `var(--lwc-durationSlowly)` |
| `zIndexSticky` | Use hardcoded value | `9000` |

**Do not invent `--slds-g-*` hooks** for these tokens. The linter will flag invented hooks with `slds/no-slds-namespace-for-custom-hooks`.

---

## Custom Hook Namespace

When no SLDS 2 hook exists for an internal/custom value, use `--lwc-*` directly. Do not use the `--slds-g-*` namespace for custom purposes.

```css
/* Bad — inventing SLDS namespace for internal values */
transition: var(--slds-g-duration-slowly, var(--lwc-durationSlowly));

/* Good — use --lwc-* when no official SLDS 2 equivalent */
transition: var(--lwc-durationSlowly);
```

---

## Font-Family Post-Linter Cleanup

After the linter runs, it may add verbose font-stack fallbacks to `font-family`. For **font-family only**, trim to just the hook tokens — remove the hardcoded font stack:

```css
/* Linter output — verbose */
font-family: var(--slds-g-font-family, var(--lwc-fontFamily, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif));

/* Cleaned up — tokens only */
font-family: var(--slds-g-font-family, var(--lwc-fontFamily));
```

For all other properties, **keep** the linter's rgb/rem/px fallbacks.
