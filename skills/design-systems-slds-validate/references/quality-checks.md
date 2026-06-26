# SLDS Quality Checks Reference

Complete catalog of quality checks performed during SLDS component validation.

> **Scope note:** The SLDS linter already catches class overrides (`slds/class-override`), deprecated tokens (`slds/lwc-token-to-slds-hook`), and hardcoded values (`slds/no-hardcoded-values`). The checks below cover what the linter does **not** catch. Linter violation counts are incorporated into the final score separately — see Step 1 in SKILL.md.

### Detection Legend

| Symbol | Meaning |
|--------|---------|
| **Script** | Automated by `analyze-quality.cjs` |
| **Linter** | Caught by the SLDS linter |
| **Manual** | Requires agent review (Step 3) |

---

## Table of Contents

- [Theming and Styling Checks](#theming-and-styling-checks)
- [Accessibility Checks](#accessibility-checks)
- [Code Quality Checks](#code-quality-checks)
- [Component Usage Checks](#component-usage-checks)
- [Detection Patterns](#detection-patterns)

---

## Theming and Styling Checks

### Hook Fallbacks (not caught by linter)

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| T002 | Fallback values present | Critical | Script | All `var(--slds-g-*)` include a fallback value |

### Hook Family Pairing

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| T010 | File-level hook family pairing | Warning | Script | Each background hook family present in a file has a matching `on-*` family present somewhere in the same file |
| T011 | Surface/container pairing correctness | Warning | Manual | `surface-*` and `surface-container-*` backgrounds are paired with appropriate `on-surface-*` text in the same selector/context |
| T012 | Accent pairing correctness | Warning | Manual | `accent-*` and `accent-container-*` backgrounds are paired with appropriate `on-accent-*` text in the same selector/context |
| T013 | Feedback pairing correctness | Warning | Manual | Feedback colors are paired with the correct `on-error-*`, `on-warning-*`, `on-success-*`, or `on-info-*` text hooks in the same selector/context |

### Spacing Hook Usage

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| T020 | Spacing uses hooks | Warning | Manual | Spacing uses `var(--slds-g-spacing-*)` or utilities |
| T021 | No magic pixel values | Warning | Script | No arbitrary `px` values for spacing |
| T022 | Base-8 alignment | Info | Manual | Spacing values align to 4, 8, 12, 16, 24, 32, 48px |

### Typography Hook Usage

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| T030 | Font family hooks | Warning | Manual | `font-family` uses `var(--slds-g-font-family-*)` |
| T031 | Font size hooks | Warning | Manual | `font-size` uses `var(--slds-g-font-scale-*)` or `var(--slds-g-font-size-base)` — NOT `var(--slds-g-font-size-N)` |
| T032 | Font weight hooks | Warning | Manual | `font-weight` uses `var(--slds-g-font-weight-*)` |
| T033 | Line height hooks | Info | Manual | `line-height` uses `var(--slds-g-font-line-height-*)` |

### Other Styling Hooks

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| T040 | Shadow hooks | Warning | Manual | Shadows use `var(--slds-g-shadow-*)` |
| T041 | Border radius hooks | Warning | Manual | Border radius uses `var(--slds-g-radius-*)` |
| T042 | Border width hooks | Info | Manual | Border width uses `var(--slds-g-border-width-*)` |

### Hook Validity

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| T050 | Color hooks numbered | Warning | Manual | Every `--slds-g-color-*` hook ends in a number (no bare `on-surface`, `on-accent`, etc.) |
| T051 | No invented hooks | Critical | Script | Every `--slds-g-*` hook referenced actually exists in `metadata/hooks-index.json` |

---

## Accessibility Checks

### Labels and Names

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| A001 | Input labels | Critical | Script | All `<lightning-input>` have `label` attribute |
| A002 | Button names | Critical | Manual | All `<button>`, `<lightning-button>` have accessible names |
| A003 | Link names | Critical | Manual | All `<a>` have descriptive text content |
| A004 | Icon alt text | Critical | Script | All icons have `alternative-text` or empty for decorative |
| A005 | Image alt text | Critical | Script | All `<img>` have `alt` attribute |

### ARIA and Semantics

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| A010 | Heading hierarchy | Warning | Script | H1 → H2 → H3 without skipping |
| A011 | ARIA roles | Warning | Manual | `role` attributes used correctly |
| A012 | ARIA labels | Warning | Manual | `aria-label`, `aria-labelledby` used appropriately |
| A013 | ARIA live | Info | Manual | Dynamic content uses `aria-live` regions |
| A014 | ARIA invalid | Warning | Manual | Invalid form fields have `aria-invalid="true"` |

### Keyboard and Focus

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| A020 | Tab order | Warning | Script | `tabindex` values are 0 or -1 only |
| A021 | Focus visible | Warning | Script | No `outline: none` without alternative focus style |
| A022 | Interactive elements | Warning | Script | Clickable elements are `<button>` or `<a>` |
| A023 | Focus management | Info | Manual | Modals trap focus, return focus on close |

### Visual Accessibility

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| A030 | Color not sole indicator | Warning | Manual | Status/errors use icon or text, not just color |
| A031 | Touch targets | Info | Manual | Interactive elements >= 44x44px on mobile |
| A032 | Text sizing | Info | Manual | Text can scale without breaking layout |

---

## Code Quality Checks

### CSS Anti-patterns

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| Q001 | No !important | Warning | Script | No `!important` declarations |
| Q002 | No inline styles (HTML) | Warning | Script | No `style="..."` attributes in HTML |
| Q025 | No inline styles (JS) | Warning | Script | No `.style.*=` direct property assignment in JS |
| Q003 | No deep nesting | Info | Manual | Selectors <= 3 levels deep |
| Q004 | No ID selectors | Info | Manual | No `#id` in CSS selectors |
| Q005 | No universal selectors | Info | Manual | No `*` in CSS selectors |

### Naming Conventions

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| Q010 | Component prefix | Warning | Manual | Custom classes use component prefix |
| Q011 | CamelCase prefix | Warning | Manual | Prefix follows camelCase convention |
| Q012 | Avoid dynamic SLDS class manipulation | Warning | Script | Avoid `.classList.add/remove/toggle('slds-*')` patterns in JS |
| Q013 | BEM consistency | Info | Manual | Class names follow consistent BEM pattern |

### Maintainability

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| Q020 | No magic numbers | Warning | Manual | All numeric values have clear purpose |
| Q021 | Z-index scale | Warning | Script | Z-index values follow defined scale |
| Q022 | No fixed dimensions | Warning | Manual | Avoid fixed `width`/`height` in px |
| Q023 | CSS file size | Info | Manual | CSS file < 500 lines |

---

## Component Usage Checks

### Lightning Base Components

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| C001 | Use LBC inputs | Warning | Script | Use `<lightning-input>` not `<input>` |
| C002 | Use LBC buttons | Warning | Script | Use `<lightning-button>` not `<button>` |
| C003 | Use LBC icons | Warning | Manual | Use `<lightning-icon>` not custom SVG |
| C004 | Use LBC combobox | Warning | Script | Use `<lightning-combobox>` not `<select>` |
| C005 | Use LBC datatable | Info | Manual | Use `<lightning-datatable>` for tables |

### SLDS Blueprint Compliance

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| C010 | Card structure | Warning | Manual | Cards use `slds-card` class structure |
| C011 | Modal structure | Warning | Manual | Modals use `slds-modal` class structure |
| C012 | Form structure | Warning | Manual | Forms use `slds-form` or `slds-form-element` |
| C013 | Button variants | Info | Manual | Buttons use `slds-button_*` variants |

### Semantic HTML

| ID | Check | Severity | Detection | Pass Criteria |
|----|-------|----------|-----------|---------------|
| C020 | Use button element | Warning | Manual | Clickable elements use `<button>` |
| C021 | Use nav element | Info | Manual | Navigation uses `<nav>` |
| C022 | Use article element | Info | Manual | Self-contained content uses `<article>` |
| C023 | Use section element | Info | Manual | Thematic grouping uses `<section>` |
| C024 | No div soup | Info | Manual | Meaningful elements used over nested `<div>` |

---

## Detection Patterns

### Regex Patterns for CSS Analysis

> Hardcoded colors, SLDS class overrides, and deprecated LWC tokens are already caught by the SLDS linter. These patterns cover supplementary checks only.

```javascript
// Missing fallback — matches var(--slds-g-*) with NO comma before closing paren
const MISSING_FALLBACK = /var\(--slds-g-[^,)]+\)/g;

// !important usage
const IMPORTANT = /!important/g;

// Magic pixel spacing values (not inside a var() fallback)
const MAGIC_PX = /\b(?:margin(?:-[a-z-]+)?|padding(?:-[a-z-]+)?|gap|row-gap|column-gap)\s*:\s*\d+px\b(?![^;]*var\()/g;

// High z-index (3+ digits)
const HIGH_ZINDEX = /z-index\s*:\s*(\d{3,})/g;

// Focus outline removed
const OUTLINE_NONE = /outline\s*:\s*none/g;
```

### Regex Patterns for HTML Analysis

> Native `<input>` labeling via `<label for="">` requires cross-element analysis that regex cannot handle reliably. The checks below focus on Lightning Base Component attributes and structural issues.

```javascript
// Lightning input without label attribute
const LBC_INPUT_NO_LABEL = /<lightning-input(?![^>]*\blabel\b)[^>]*>/gi;

// Icon without alternative-text
const ICON_NO_ALT = /<lightning-icon(?![^>]*alternative-text)[^>]*>/gi;

// Image without alt
const IMG_NO_ALT = /<img(?![^>]*\balt\b)[^>]*>/gi;

// Inline styles
const INLINE_STYLE = /style\s*=\s*["'][^"']+["']/gi;

// Positive tabindex (should be 0 or -1 only)
const TABINDEX_POSITIVE = /tabindex\s*=\s*["']([1-9]\d*)["']/gi;

// Heading hierarchy (track sequence to detect skipped levels)
const HEADINGS = /<h([1-6])[^>]*>/gi;

// Div with click handler (should be button)
const CLICKABLE_DIV = /<div[^>]*onclick[^>]*>/gi;

// Native elements where LBC alternatives exist (info-level)
const NATIVE_INPUT = /<input\s/gi;
const NATIVE_BUTTON = /<button\s/gi;
const NATIVE_SELECT = /<select\s/gi;
```

### File Analysis Strategy

1. **CSS Files**: Parse with regex, track line numbers, categorize findings; cross-reference hooks against `hooks-index.json` (T051)
2. **HTML Files**: Parse with regex, validate structure, check attributes
3. **JS Files**: Check for inline style assignment (`.style.*=`) and dynamic SLDS class manipulation (`.classList.add('slds-*')`)
4. **Cross-file/manual**: Review relationships between files that regex cannot validate reliably

---

## Severity Levels

| Level | Weight | Action Required |
|-------|--------|-----------------|
| Critical | -10 pts | Must fix before deployment |
| Warning | -3 pts | Should fix, review if acceptable |
| Info | -1 pt | Nice to fix, no blocking |

---

## Category Scoring

The script outputs individual category scores. It does **not** produce a combined overall grade — the agent computes that using the formula in SKILL.md Step 4:

```
Overall = (Linter × 0.30) + (Theming × 0.20) + (Accessibility × 0.20)
        + (CodeQuality × 0.15) + (ComponentUsage × 0.15)
```

> **Linter Compliance** is scored separately from linter output (count violations × 10, min 0).

### Automation Coverage

The script automates **17 of 53** checks listed above (marked **Script** in the Detection column). The remaining 36 require agent manual review (Step 3 in SKILL.md). Categories with fewer automated checks — especially Code Quality (4 of 13) and Component Usage (3 of 14) — will tend toward 100 when no automated findings exist. Treat the automated score as provisional: manual review findings must be reported separately and can block a production recommendation even when the score is high.

### Theming

```
Score = 100 - (critical issues in category × 10)
              - (warnings in category × 3)
              - (info in category × 1)
Min: 0
```

### Accessibility

```
Score = 100 - (critical issues in category × 10)
              - (warnings in category × 3)
              - (info in category × 1)
Min: 0
```

### Code Quality

```
Score = 100 - (critical issues in category × 10)
              - (warnings in category × 3)
              - (info in category × 1)
Min: 0
```

### Component Usage

```
Score = 100 - (critical issues in category × 10)
              - (warnings in category × 3)
              - (info in category × 1)
Min: 0
```
