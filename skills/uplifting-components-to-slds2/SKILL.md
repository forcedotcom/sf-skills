---
name: uplifting-components-to-slds2
version: "1.0.0"
description: "Migrate Lightning Web Components from SLDS 1 to SLDS 2 by running the SLDS linter and fixing violations. Use this skill whenever users mention SLDS 2, SLDS uplift, linter violations, LWC token migration, class overrides, hardcoded CSS values that need SLDS hook replacement, or styling hook selection. Covers all styling hook categories — color, spacing, sizing, typography, borders, radius, and shadows. Also use when users mention no-hardcoded-values, no-slds-class-overrides, lwc-to-slds-hooks, no-deprecated-tokens-slds1, or ask about SLDS component migration — even if they don't explicitly say \"uplift\" or \"migration\"."
---

# Goal

Systematically migrate Lightning Web Components from SLDS 1 to SLDS 2 using the SLDS linter and structured guidance for fixing violations across all styling hook categories.

## SLDS 2 Styling Hook Categories

| Category | Hook Prefix | What It Replaces |
|---|---|---|
| Color | `--slds-g-color-*` | Hardcoded colors, `--lwc-color*` tokens |
| Spacing | `--slds-g-spacing-*` | Hardcoded margins, padding, gaps |
| Sizing | `--slds-g-sizing-*` | Hardcoded widths, heights, dimensions |
| Typography | `--slds-g-font-*` | Hardcoded font sizes, weights, line heights |
| Border/Radius | `--slds-g-radius-border-*`, `--slds-g-sizing-border-*` | Hardcoded border-radius, border-width |
| Shadow | `--slds-g-shadow-*` | Hardcoded box-shadow values |

Color hooks require the most judgment (context-dependent selection). Non-color hooks are mostly numbered scales with straightforward mappings.

## Prerequisites

- Node.js 14.x or higher installed
- Access to component CSS and markup files (`.html` for LWC, `.cmp` for Aura)
- Terminal/command line access to run linter
- Git repository for backup (recommended)

---

# Workflow

```
1. **REQUIRED — ALWAYS run first:** npx @salesforce-ux/slds-linter@latest lint --fix . — NEVER skip this step. This handles simple violations automatically.
2. Review linter output -> Identify remaining manual fixes needed
3. Fix by violation type -> Use per-rule reference guides
4. Choose the right hook -> Context-first, inspect HTML before deciding
5. Validate -> Re-run linter and confirm zero errors
```

## Step 1: Run SLDS Linter
MANDATORY: This step is NOT optional.

```bash
npx @salesforce-ux/slds-linter@latest lint --fix .
```

The linter analyzes all CSS and markup files (`.html` for LWC, `.cmp` for Aura), auto-fixes simple violations, and reports remaining issues requiring manual intervention.

## Step 2: Analyze Linter Output

The linter reports violations in this format:

```
componentName.css
  15:3  warning  Overriding slds-button isn't supported. To differentiate SLDS and
                 custom classes, create a CSS class in your namespace.
                 Examples: myapp-input, myapp-button.                        slds/no-slds-class-overrides

  23:5  error    The '--lwc-colorBackground' design token is deprecated. Replace it with
                 the SLDS 2 styling hook and set the fallback to '--lwc-colorBackground'.
                 1. --slds-g-color-surface-2
                 2. --slds-g-color-surface-container-2                      slds/lwc-token-to-slds-hook

  30:8  warning  Consider replacing the #ffffff static value with an SLDS 2 styling hook
                 that has a similar value:
                 1. --slds-g-color-surface-1
                 2. --slds-g-color-surface-container-1
                 3. --slds-g-color-on-accent-1
                 4. --slds-g-color-on-accent-2
                 5. --slds-g-color-on-accent-3                              slds/no-hardcoded-values-slds2

  31:15  error   Consider removing t(fontSizeMedium) or replacing it with
                 var(--slds-g-font-size-base, var(--lwc-fontSizeMedium, 0.8125rem)).
                 Set the fallback to t(fontSizeMedium). For more info, see
                 Styling Hooks on lightningdesignsystem.com.               slds/no-deprecated-tokens-slds1
```

Four violation types, each with its own fix approach (see Step 3).

**Important:** The linter flags all hardcoded values. Fix color, spacing, sizing, typography, border, and shadow values — but **skip layout values** (`100%`, `auto`, `0`, `inherit`, `none`). See [rule-no-hardcoded-values.md](references/rule-no-hardcoded-values.md) for the full fix-vs-skip triage table.

## Step 3: Fix Violations by Type

Each rule has a dedicated reference guide with full examples and decision logic:

| Violation Rule | Quick Summary | Reference |
|---|---|---|
| `slds/no-hardcoded-values-slds2` | Replace hardcoded values with SLDS hook + original as fallback | [rule-no-hardcoded-values.md](references/rule-no-hardcoded-values.md)|
| `slds/lwc-token-to-slds-hook` | Replace `--lwc-*` tokens with SLDS 2 hook, keep LWC token as fallback | [rule-lwc-token-to-slds-hook.md](references/rule-lwc-token-to-slds-hook.md) |
| `slds/no-slds-class-overrides` | Create component-prefixed class, add to markup alongside SLDS class | [rule-no-slds-class-overrides.md](references/rule-no-slds-class-overrides.md) |
| `slds/no-deprecated-tokens-slds1` | Replace legacy `t()`/`token()` syntax with SLDS 2 hook + LWC fallback | [rule-no-deprecated-tokens-slds1.md](references/rule-no-deprecated-tokens-slds1.md) |

**Always include fallback values** — `var(--slds-g-hook, originalValue)` where `originalValue` is the exact original from the source CSS.

### Class Override Quick Reference

Class overrides require changes to **both CSS and markup** (`.html` or `.cmp`). This is the most commonly missed step:

1. **CSS:** Rename `.slds-*` selector → `{componentName}-{sldsElementPart}` (camelCase)
2. **Markup:** Add the new class **alongside** the SLDS class — never remove the SLDS class

```css
/* Before */ .slds-button { border-radius: 8px; }
/* After */  .myComponent-button { border-radius: 8px; }
```
```html
<!-- Markup: both classes --> <button class="slds-button myComponent-button">Click</button>
```

See [rule-no-slds-class-overrides.md](references/rule-no-slds-class-overrides.md) for descendant selectors, multi-class selectors, and naming conventions.

## Step 4: Choose the Right Hook

**Color hooks** require context-based selection. **REQUIRED: When any violation involves a color property (`color`, `background-color`, `background`, `fill`, `border-color`), you MUST read [color-hooks-decision-guide.md](references/color-hooks-decision-guide.md) BEFORE choosing a hook.** The linter lists possible hooks in no particular order — do NOT pick the first suggestion. The guide contains property-based rules that determine the correct hook.

**Non-color hooks** are simpler — match the CSS value to the numbered scale. See **[non-color-hooks-decision-guide.md](references/non-color-hooks-decision-guide.md)** for value-to-hook lookup tables covering spacing, sizing, typography, borders, radius, and shadows.

## Step 5: Validate and Verify

**Linter feedback loop — repeat until zero errors:**

```
1. npx @salesforce-ux/slds-linter@latest lint .
2. Review errors -> fix by type (Step 3)
3. Re-run linter
4. Repeat until output shows: 0 errors
```

---

# Validation

- [ ] No `.slds-*` classes in CSS selectors
- [ ] No `var(--lwc-*)` tokens without SLDS 2 replacements
- [ ] All hooks include fallback values
- [ ] Background/foreground color hooks from same family
- [ ] Original SLDS classes preserved in HTML
- [ ] Spacing uses numbered hooks (not named like `spacing-medium`)
- [ ] Typography uses numbered hooks (not named like `font-weight-bold`)
- [ ] Component renders correctly in light/dark mode and density settings

See **[migration-checklist.md](references/migration-checklist.md)** for the full validation checklist.

---

# Output

Return the fully migrated CSS (and updated HTML markup where class overrides were fixed) with zero SLDS linter violations. All styling hooks must include fallback values preserving the original CSS values.

---

# Advanced Patterns

## Color-Mix for Transparency

When a hardcoded value uses `rgba()` or transparency, use `color-mix()` with the SLDS hook to preserve opacity:

```css
/* Before */
border-color: rgba(186, 5, 23, 0.7);

/* After — use oklab color space for perceptual consistency */
border-color: color-mix(in oklab, var(--slds-g-color-palette-red-40, rgb(181,54,45)), transparent 30%);
```

**Formula:** To achieve X% opacity, use `(100 - X)%` transparent in `color-mix`.
- 70% opacity → `transparent 30%`
- 50% opacity → `transparent 50%`

Use opaque `rgb()` as fallback (not `rgba()`) — `color-mix` handles the transparency.

## calc() Expressions with Tokens

When migrating `t('calc(...)')` or `calc()` with deprecated tokens:

```css
/* Before — Aura t() with calc */
height: t('calc(' + lineHeightButton + ' + 2px)');

/* After — if calc is still needed */
height: calc(var(--lwc-lineHeightButton) + 2px);

/* After — if calc was unnecessary, simplify */
height: var(--lwc-lineHeightButton);
```

For `calc()` with `--lwc-*` tokens being replaced:

```css
/* Before */
padding: calc(var(--lwc-spacingMedium) + 4px);

/* After */
padding: calc(var(--slds-g-spacing-4, var(--lwc-spacingMedium)) + 4px);
```

**Tip:** Often the `calc()` is unnecessary and can be simplified. Check if the result matches an existing hook value.

---

# Key Constraints

- **Never invent hook names** — only use hooks documented in the SLDS design system
- **Always include fallback values** — the fallback must be the exact original value from the source CSS
- **Never change hardcoded numerical values** — values like `100%`, `50%`, `200px`, `1.5`, `auto`, `0`, `inherit`, `none`, `flex: 1` are structural/layout values. Do not replace them with hooks and do not remove them — they are not styling hook candidates
- **No exact match? Leave as-is** — if a hardcoded value doesn't closely correspond to any hook's rendered value, leave it unchanged rather than force-fitting
- **Match hook number to original value intensity** — don't default to `-1`. Pick the variant closest to the original. See [color-hooks-decision-guide.md](references/color-hooks-decision-guide.md)
- **Only numbered scales** — named hooks like `spacing-medium`, `font-weight-bold`, `radius-large` do NOT exist

# Troubleshooting

| Issue | Solution |
|---|---|
| Linter suggests 2+ color hook options | Inspect HTML context to determine element's semantic role — see color-hooks-decision-guide.md |
| Visual appearance changed after migration | Verify fallback values match originals; check surface vs container family |
| No hook available for hardcoded value | Leave unchanged; do not invent custom hook names |
| Linter says "Remove the static value" for `100%`, `auto`, etc. | Leave unchanged — these are layout values. Removing them breaks rendering. |
| CSS class naming errors | Use exact camelCase component name: `myComponent-button`, not `MyComponent-button` |
| Spacing/sizing doesn't match | Check value-to-hook mapping in non-color-hooks-decision-guide.md; verify spacing vs sizing usage |
| Named hook not working (e.g., `spacing-medium`) | Named hooks don't exist — use numbered scale: `spacing-4` for 16px, `font-weight-7` for inline bold emphasis (not headings) |
| Component looks different in compact density | Use density-aware hooks (`--slds-g-spacing-var-*`) for components that adapt to density |

---

# References

- **[Color Hooks Decision Guide](references/color-hooks-decision-guide.md)** — All 5 color hook families, decision trees, background-foreground pairing, palette accessibility
- **[Non-Color Hooks Decision Guide](references/non-color-hooks-decision-guide.md)** — Spacing, sizing, typography, borders, radius, and shadow hooks with lookup tables
- **[Rule: No Hardcoded Values](references/rule-no-hardcoded-values.md)** — Linter behavior, fix-vs-skip triage, replacement pattern, utility class workflow
- **[Rule: LWC Token to SLDS Hook](references/rule-lwc-token-to-slds-hook.md)** — Deprecated `--lwc-*` token replacement patterns
- **[Rule: No Deprecated Tokens SLDS1](references/rule-no-deprecated-tokens-slds1.md)** — Legacy `t()`/`token()` Aura syntax replacement patterns
- **[Rule: No SLDS Class Overrides](references/rule-no-slds-class-overrides.md)** — Class renaming and HTML updates
- **[Migration Examples](references/examples.md)** — Before/after examples by scenario and complexity
- **[Common Patterns](references/common-patterns.md)** — Classes never to override, deprecated SLDS 2 classes, palette fallbacks, tokens with no SLDS 2 equivalent
- **[Migration Checklist](references/migration-checklist.md)** — Full validation checklist
