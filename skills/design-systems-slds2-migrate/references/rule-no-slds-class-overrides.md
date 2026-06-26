# Rule: No SLDS Class Overrides

**Rule ID:** `slds/no-slds-class-overrides`
**Severity:** Warning
**Scope:** Detects CSS selectors that directly target `.slds-*` classes.

---

## What the Linter Does

The linter detects CSS classes that directly override SLDS classes and reports them as **warnings**. It does **not** auto-fix — all changes require manual work in both CSS and HTML.

```
  1:1  warning  Overriding slds-button isn't supported. To differentiate SLDS and
               custom classes, create a CSS class in your namespace.
               Examples: myapp-input, myapp-button.                  slds/no-slds-class-overrides
```

**Manual steps required:**
1. Rename `.slds-*` selectors in CSS to `{componentName}-{sldsElementPart}`
2. Add the new component class to markup (`.html` for LWC, `.cmp` for Aura) **alongside** the original SLDS class
3. Never remove the original SLDS class from markup

---

## Naming Convention

**Format:** `{componentName}-{sldsElementPart}` (camelCase component name)

| SLDS Class | Component: `userProfile` | Result |
|---|---|---|
| `.slds-button` | `userProfile` | `userProfile-button` |
| `.slds-card` | `userProfile` | `userProfile-card` |
| `.slds-modal__content` | `userProfile` | `userProfile-modal__content` |
| `.slds-button_brand` | `userProfile` | `userProfile-button_brand` |

---

## Common Patterns

### Pattern 1: Simple Selector

```css
/* Before CSS */
.slds-button { border-radius: 8px; }

/* After CSS */
.myComponent-button { border-radius: 8px; }
```

```html
<!-- After HTML (manual) -->
<button class="slds-button myComponent-button">Click</button>
```

### Pattern 2: Descendant Selector

```css
/* Before CSS */
.slds-card .slds-button { margin-top: 1rem; }

/* After CSS */
.myComponent-card .myComponent-button { margin-top: 1rem; }
```

```html
<!-- After HTML (manual) — each SLDS class gets a component class -->
<div class="slds-card myComponent-card">
  <button class="slds-button myComponent-button">Click</button>
</div>
```

### Pattern 3: Multi-Class Selector

```css
/* Before CSS */
.slds-card.slds-p-around_medium { border: 1px solid blue; }

/* After CSS */
.myComponent-card.myComponent-p-around_medium { border: 1px solid blue; }
```

```html
<!-- After HTML (manual) -->
<div class="slds-card slds-p-around_medium myComponent-card myComponent-p-around_medium">
```

---

## Core Rules

1. **Never remove SLDS classes** from markup (`.html` or `.cmp`) — only ADD component classes alongside them
2. **One-to-one mapping** — each SLDS class in a CSS selector gets exactly one component class
3. **CamelCase component name** — `sampleComponent-button`, not `sample-component-button`
4. **Preserve SLDS element names** — `.slds-button` becomes `componentName-button` (strip `slds-` prefix, keep the rest)

---

## Interaction with Other Rules

If the overridden CSS properties include hardcoded colors, you must also apply `rule-no-hardcoded-values.md` to those properties:

```css
/* Before */
.slds-icon-action-check { background: #4bca81; }

/* After — both rules applied */
.myComponent-icon-action-check { background: var(--slds-g-color-success-base-70, #4bca81); }
```

---

---

## Validation Checklist

**CSS:**
- [ ] All `.slds-*` overrides reported by the linter are addressed
- [ ] Component name is camelCase
- [ ] SLDS element names preserved after prefix

**Markup (`.html` for LWC, `.cmp` for Aura):**
- [ ] Original SLDS classes preserved
- [ ] Component classes added alongside SLDS classes
- [ ] Every element in CSS selector chain updated in markup
- [ ] One component class per SLDS class
