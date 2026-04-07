# SLDS Quality Checks Reference

Complete catalog of quality checks performed during SLDS component validation.

> **Scope note:** The SLDS linter already catches class overrides (`slds/class-override`), deprecated tokens (`slds/lwc-token-to-slds-hook`), and hardcoded values (`slds/no-hardcoded-values`). The checks below cover what the linter does **not** catch. Linter violation counts are incorporated into the final score separately — see Step 1 in SKILL.md.

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

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| T002 | Fallback values present | Critical | All `var(--slds-g-*)` include a fallback value |

### Hook Family Pairing

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| T010 | Surface pairing | Warning | `surface-*` bg paired with `on-surface-*` text |
| T011 | Container pairing | Warning | `surface-container-*` bg paired with `on-surface-*` text |
| T012 | Accent pairing | Warning | `accent-*` bg paired with `on-accent-*` text |
| T013 | Feedback pairing | Warning | Feedback colors paired with correct text hooks |

### Spacing Hook Usage

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| T020 | Spacing uses hooks | Warning | Spacing uses `var(--slds-g-spacing-*)` or utilities |
| T021 | No magic pixel values | Warning | No arbitrary `px` values for spacing |
| T022 | Base-8 alignment | Info | Spacing values align to 4, 8, 12, 16, 24, 32, 48px |

### Typography Hook Usage

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| T030 | Font family hooks | Warning | `font-family` uses `var(--slds-g-font-family-*)` |
| T031 | Font size hooks | Warning | `font-size` uses `var(--slds-g-font-scale-*)` or `var(--slds-g-font-size-base)` — NOT `var(--slds-g-font-size-N)` |
| T032 | Font weight hooks | Warning | `font-weight` uses `var(--slds-g-font-weight-*)` |
| T033 | Line height hooks | Info | `line-height` uses `var(--slds-g-font-line-height-*)` |

### Other Styling Hooks

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| T040 | Shadow hooks | Warning | Shadows use `var(--slds-g-shadow-*)` |
| T041 | Border radius hooks | Warning | Border radius uses `var(--slds-g-radius-*)` |
| T042 | Border width hooks | Info | Border width uses `var(--slds-g-border-width-*)` |

### Hook Validity

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| T050 | Color hooks numbered | Warning | Every `--slds-g-color-*` hook ends in a number (no bare `on-surface`, `on-accent`, etc.) |
| T051 | No invented hooks | Critical | Every `--slds-g-*` hook referenced actually exists in `metadata/hooks-index.json` |

---

## Accessibility Checks

### Labels and Names

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| A001 | Input labels | Critical | All `<input>`, `<select>`, `<textarea>` have labels |
| A002 | Button names | Critical | All `<button>`, `<lightning-button>` have accessible names |
| A003 | Link names | Critical | All `<a>` have descriptive text content |
| A004 | Icon alt text | Critical | All icons have `alternative-text` or empty for decorative |
| A005 | Image alt text | Critical | All `<img>` have `alt` attribute |

### ARIA and Semantics

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| A010 | Heading hierarchy | Warning | H1 → H2 → H3 without skipping |
| A011 | ARIA roles | Warning | `role` attributes used correctly |
| A012 | ARIA labels | Warning | `aria-label`, `aria-labelledby` used appropriately |
| A013 | ARIA live | Info | Dynamic content uses `aria-live` regions |
| A014 | ARIA invalid | Warning | Invalid form fields have `aria-invalid="true"` |

### Keyboard and Focus

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| A020 | Tab order | Warning | `tabindex` values are 0 or -1 only |
| A021 | Focus visible | Warning | No `outline: none` without alternative focus style |
| A022 | Interactive elements | Warning | Clickable elements are `<button>` or `<a>` |
| A023 | Focus management | Info | Modals trap focus, return focus on close |

### Visual Accessibility

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| A030 | Color not sole indicator | Warning | Status/errors use icon or text, not just color |
| A031 | Touch targets | Info | Interactive elements >= 44x44px on mobile |
| A032 | Text sizing | Info | Text can scale without breaking layout |

---

## Code Quality Checks

### CSS Anti-patterns

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| Q001 | No !important | Warning | No `!important` declarations |
| Q002 | No inline styles | Warning | No `style="..."` in HTML |
| Q003 | No deep nesting | Info | Selectors <= 3 levels deep |
| Q004 | No ID selectors | Info | No `#id` in CSS selectors |
| Q005 | No universal selectors | Info | No `*` in CSS selectors |

### Naming Conventions

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| Q010 | Component prefix | Warning | Custom classes use component prefix |
| Q011 | CamelCase prefix | Warning | Prefix follows camelCase convention |
| Q012 | No SLDS naming | Warning | Custom classes don't start with `slds-` |
| Q013 | BEM consistency | Info | Class names follow consistent BEM pattern |

### Maintainability

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| Q020 | No magic numbers | Warning | All numeric values have clear purpose |
| Q021 | Z-index scale | Warning | Z-index values follow defined scale |
| Q022 | No fixed dimensions | Warning | Avoid fixed `width`/`height` in px |
| Q023 | CSS file size | Info | CSS file < 500 lines |

---

## Component Usage Checks

### Lightning Base Components

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| C001 | Use LBC inputs | Warning | Use `<lightning-input>` not `<input>` |
| C002 | Use LBC buttons | Warning | Use `<lightning-button>` not `<button>` |
| C003 | Use LBC icons | Warning | Use `<lightning-icon>` not custom SVG |
| C004 | Use LBC combobox | Warning | Use `<lightning-combobox>` not `<select>` |
| C005 | Use LBC datatable | Info | Use `<lightning-datatable>` for tables |

### SLDS Blueprint Compliance

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| C010 | Card structure | Warning | Cards use `slds-card` class structure |
| C011 | Modal structure | Warning | Modals use `slds-modal` class structure |
| C012 | Form structure | Warning | Forms use `slds-form` or `slds-form-element` |
| C013 | Button variants | Info | Buttons use `slds-button_*` variants |

### Semantic HTML

| ID | Check | Severity | Pass Criteria |
|----|-------|----------|---------------|
| C020 | Use button element | Warning | Clickable elements use `<button>` |
| C021 | Use nav element | Info | Navigation uses `<nav>` |
| C022 | Use article element | Info | Self-contained content uses `<article>` |
| C023 | Use section element | Info | Thematic grouping uses `<section>` |
| C024 | No div soup | Info | Meaningful elements used over nested `<div>` |

---

## Detection Patterns

### Regex Patterns for CSS Analysis

> Hardcoded colors, SLDS class overrides, and deprecated LWC tokens are already caught by the SLDS linter. These patterns cover supplementary checks only.

```javascript
// Missing fallback — matches var(--slds-g-*) with NO comma before closing paren
const MISSING_FALLBACK = /var\(--slds-g-[^,)]+\)/g;

// !important usage
const IMPORTANT = /!important/g;

// Magic pixel values (not inside a var() fallback)
const MAGIC_PX = /:\s*\d+px(?![^;]*var\()/g;

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
4. **Cross-file**: Validate CSS classes used in HTML exist in CSS

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

The script automates ~20 of the ~60 checks listed above. The remaining checks require agent manual review (Step 3 in SKILL.md). Categories with fewer automated checks (Code Quality, Component Usage) will tend toward 100 when no automated findings exist — agents should factor in manual review findings when interpreting these scores.

### Theming

```
Score = 100 - (T002/T051 criticals × 10) - (T010-T013 warnings × 3) - (T020-T042 info × 1)
Min: 0
```

### Accessibility

```
Score = 100 - (A001-A005 criticals × 10) - (A010-A023 warnings × 3) - (A030-A032 info × 1)
Min: 0
```

### Code Quality

```
Score = 100 - (Q001-Q005 warnings × 3) - (Q010-Q023 info × 1)
Min: 0
```

### Component Usage

```
Score = 100 - (C001-C005 warnings × 3) - (C010-C024 info × 1)
Min: 0
```
