# Validation Checklists

Run through these checks before finalizing any SLDS-authored component. Check IDs align with the validating-slds skill's quality-checks.md.


## Theming & Styling (T-series)

Code produced by this skill should score high on T-series checks.

| Check | What to verify | Audit ID |
|-------|---------------|----------|
| **Hook fallbacks** | Every `var(--slds-g-*)` has a fallback value | T002 |
| **Surface pairing** | `surface-*` bg paired with `on-surface-*` text | T010 |
| **Container pairing** | `surface-container-*` bg paired with `on-surface-*` text | T011 |
| **Accent pairing** | `accent-*` bg paired with `on-accent-*` text | T012 |
| **Feedback pairing** | Feedback colors paired with correct text hooks | T013 |
| **Spacing hooks** | Spacing uses `var(--slds-g-spacing-*)` or utility classes | T020 |
| **No magic pixels** | No arbitrary `px` values for spacing | T021 |
| **Font family hooks** | `font-family` uses `var(--slds-g-font-family-*)` | T030 |
| **Font size hooks** | `font-size` uses `var(--slds-g-font-scale-*)` or `var(--slds-g-font-size-base)` -- NOT `var(--slds-g-font-size-N)` | T031 |
| **Font weight hooks** | `font-weight` uses `var(--slds-g-font-weight-*)` | T032 |
| **Shadow hooks** | Shadows use `var(--slds-g-shadow-*)` | T040 |
| **Border radius hooks** | Border radius uses `var(--slds-g-radius-*)` | T041 |
| **Color hooks numbered** | Every `--slds-g-color-*` hook ends in a number (no bare `on-surface`, `on-accent`, etc.) | T050 |
| **No invented hooks** | Every hook referenced actually exists in `metadata/hooks-index.json` | T051 |
| **No hardcoded colors** | No hex, rgb, or named colors (linter also catches this) | linter |
| **No class overrides** | No `.slds-*` class overrides (linter also catches this) | linter |
| **No deprecated tokens** | No `--lwc-*` tokens (linter also catches this) | linter |

---

## Code Quality (Q-series)

| Check | What to verify | Audit ID |
|-------|---------------|----------|
| **No !important** | No `!important` declarations | Q001 |
| **No inline styles** | No `style="..."` in HTML | Q002 |
| **Custom class prefix** | Custom classes use `my-*`, `c-*`, or namespace prefix | Q010 |
| **No dynamic SLDS class manipulation** | Avoid `.classList.add/remove/toggle('slds-*')` patterns in JS | Q012 |
| **No magic numbers** | All numeric values have clear purpose | Q020 |

---

## Component Usage (C-series)

| Check | What to verify | Audit ID |
|-------|---------------|----------|
| **LBC inputs** (LWC) | Use `<lightning-input>` not `<input>` | C001 |
| **LBC buttons** (LWC) | Use `<lightning-button>` not `<button>` | C002 |
| **LBC icons** (LWC) | Use `<lightning-icon>` not custom SVG | C003 |
| **Blueprint structure** | Cards use `slds-card`, modals use `slds-modal`, etc. | C010-C013 |

---

## Accessibility Reminders (A-series)

Deep accessibility is owned by the **accessibility skill**. These are minimal reminders to nudge agents.

| Check | What to verify | Audit ID |
|-------|---------------|----------|
| **Icon alt text** | All `<lightning-icon>` have `alternative-text` (empty string for decorative) | A004 |
| **Image alt text** | All `<img>` have `alt` attribute | A005 |
| **Color not sole indicator** | Status uses icon or text too, not just color | A030 |
| **No outline:none** | Don't remove focus outline without replacement | A021 |

For full WCAG compliance, apply the accessibility skill after authoring.

---

## Quick Validation Script

Run the SLDS linter to catch the most common issues automatically:

```bash
npx @salesforce-ux/slds-linter@latest lint .
```

The linter catches:
- `slds/class-override` -- overriding SLDS classes
- `slds/lwc-token-to-slds-hook` -- deprecated tokens
- `slds/no-hardcoded-values` -- hardcoded colors/spacing

Everything above the linter line must be checked manually or by the auditing skill.
