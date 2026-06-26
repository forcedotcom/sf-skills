---
id: slds.guidance.development
title: SLDS Development Guide
description: Root-level guidance for generating or optimizing SLDS-compliant code
summary: "Comprehensive development guide covering the component selection hierarchy (LBC → Blueprints → Hooks → Custom), framework-specific patterns, styling hooks usage, linter resolution, naming conventions, and code generation best practices."

artifact_type: guide
domain: development
topic: development

content_format: structured
complexity: intermediate
audience: [implementer]

tasks: [learn, implement, choose]

refs:
  - slds.guidance.hooks.typography
  - slds.guidance.hooks.spacing
  - slds.guidance.uplift
  - slds.guidance.hooks
  - slds.guidance.hooks.color
  - slds.guidance.blueprints
  - slds.guidance.utilities
  - slds.guidance.icons
  - slds.guidance.design

tags: [development, lwc, slds, theming, styling-hooks]
keywords: [component hierarchy, Lightning Base Components, SLDS Blueprints, styling hooks, utility classes, code generation, linter, naming conventions]
---

# SLDS Development Guide

Root-level guidance for AI coding agents generating or optimizing SLDS-compliant code.

---

## What is SLDS?

The **Salesforce Lightning Design System** provides:

| Resource | Description |
|----------|-------------|
| **Lightning Base Components** | Pre-built LWC components with accessibility and theming built-in |
| **SLDS Blueprints** | CSS/HTML patterns for any framework (React, Vue, Angular, vanilla JS) |
| **Styling Hooks** | CSS custom properties (`--slds-g-*`) for theming |
| **Utility Classes** | Rapid styling classes for spacing, layout, visibility |
| **Icons** | SVG icons across action, utility, standard, custom, and doctype categories |

> **Version Note:** This guide targets **SLDS v2**. Legacy `--lwc-*` tokens and `slds-*--modifier` class syntax are deprecated.

---

## Component Selection Hierarchy

**Always follow this order when building UI:**

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Lightning Base Components (LWC only)                     │
├─────────────────────────────────────────────────────────────┤
│ 2. SLDS Blueprints (any framework)                          │
├─────────────────────────────────────────────────────────────┤
│ 3. Custom with Styling Hooks                                │
├─────────────────────────────────────────────────────────────┤
│ 4. Custom CSS (last resort, still use hooks for values)     │
└─────────────────────────────────────────────────────────────┘
```

### Level 1: Lightning Base Components (LWC Only)

Pre-built, accessible, themed components. **Always check first for LWC projects.**

| Component | Use Case |
|-----------|----------|
| `lightning-button` | All button actions |
| `lightning-input` | Text, email, number, date inputs |
| `lightning-combobox` | Dropdown selection |
| `lightning-datatable` | Tabular data with sorting/selection |
| `lightning-card` | Content containers |
| `lightning-modal` | Dialog overlays |

### Level 2: SLDS Blueprints

HTML/CSS patterns for non-LWC frameworks or when no Lightning Base Component exists.

### Level 3: Styling Hooks

CSS custom properties for theming. Use when customizing appearance.

```css
.my-card {
  background: var(--slds-g-color-surface-1);
  padding: var(--slds-g-spacing-4);
  border-radius: var(--slds-g-radius-border-2);
}
```

### Level 4: Custom CSS

**Only when no hook exists for the property.** See [When Hooks Don't Exist](#when-hooks-dont-exist).

---

## Framework-Specific Patterns

### LWC Layout

```html
<!-- Use lightning-layout for responsive grids -->
<lightning-layout multiple-rows>
  <lightning-layout-item size="12" medium-device-size="6">
    <lightning-card title="Card 1">Content</lightning-card>
  </lightning-layout-item>
</lightning-layout>
```

### Non-LWC Layout (React, Vue, Angular)

```html
<!-- Use SLDS grid classes -->
<div class="slds-grid slds-wrap slds-gutters">
  <div class="slds-col slds-size_1-of-1 slds-medium-size_1-of-2">
    <!-- Content -->
  </div>
</div>
```

---

## Common Patterns Quick Reference

| Pattern | LWC Component | Blueprint |
|---------|---------------|-----------|
| Forms | `lightning-input`, `lightning-combobox` | Input, Combobox |
| Data Tables | `lightning-datatable` | Data Tables |
| Modals | `lightning-modal` | Modals |
| Cards | `lightning-card` | Cards |

**Form validation pattern (LWC):**
```javascript
handleSubmit() {
  const allValid = [...this.template.querySelectorAll('lightning-input')]
    .reduce((valid, input) => input.reportValidity() && valid, true);
  if (allValid) { /* submit */ }
}
```

**Modal pattern (LWC):**
```javascript
import LightningModal from 'lightning/modal';
export default class MyModal extends LightningModal {
  handleClose() { this.close('result'); }
}
```

---

## Core Rules

### Do ✅
- Follow hierarchy: LBC → Blueprints → Styling Hooks → Custom CSS
- Use `var(--slds-g-*)` with fallbacks for all themeable values
- Create custom classes (e.g., `my-*`) instead of overriding `.slds-*`
- Verify components/hooks exist before implementing

### Don't ❌
- Hard-code colors, spacing, or typography
- Override `.slds-*` classes directly
- Use deprecated `--lwc-*` tokens as primary values
- Use color alone to convey meaning

---

## When Hooks Don't Exist

Not all CSS properties have styling hooks. Use this decision tree:

```
Does a styling hook exist for this property?
├─ YES → Use the hook with fallback: var(--slds-g-*, fallback)
├─ NO → Is there a utility class?
│       ├─ YES → Use the utility class
│       └─ NO → Use minimal custom CSS with:
│               1. Custom class (my-*, c-*)
│               2. Document why no hook/utility exists
│               3. Use hooks for related values (e.g., colors in gradients)
```

**Properties without hooks (examples):**
- `transform`, `transition` (use `--slds-g-timing-*` for duration only)
- `z-index` (use SLDS utility classes when possible)
- `cursor`
- `overflow`
- Complex gradients (use hook colors within gradient syntax)

**Example - gradient with hook colors:**
```css
.my-gradient-bg {
  /* No gradient hook exists, but use hook colors */
  background: linear-gradient(
    to bottom,
    var(--slds-g-color-surface-1),
    var(--slds-g-color-surface-2)
  );
}
```

---

## Naming Conventions

### Custom Class Names

Use a consistent prefix to avoid collision with SLDS:

| Pattern | Use Case | Example |
|---------|----------|---------|
| `my-*` | General custom styling | `my-card-header` |
| `c-*` | LWC component-specific | `c-accountList-row` |
| `[namespace]-*` | Package/app namespace | `acme-dashboard-widget` |

**Avoid:**
- Generic names: `container`, `wrapper`, `header`
- SLDS-like names: `custom-slds-button`
- BEM on SLDS classes: `slds-card__custom-header`

### Custom Hook Names (for app-level theming)

```css
:root {
  /* Namespace your custom hooks */
  --my-app-primary: var(--slds-g-color-brand-1);
  --my-app-card-padding: var(--slds-g-spacing-4);
}
```

---

## Code Generation Style

When generating SLDS code, follow these patterns:

### Minimal HTML + Classes

```html
<!-- Prefer utility classes over custom CSS for common patterns -->
<div class="slds-card slds-p-around_medium slds-m-bottom_small">
  <h2 class="slds-text-heading_medium">Title</h2>
</div>
```

### Avoid Unnecessary JavaScript

Use CSS/HTML solutions when possible:
- `slds-hide` instead of `{if}` for simple visibility
- `slds-is-selected` class toggling instead of complex state

### Component Structure (LWC)

```html
<template>
  <lightning-card title="Title">
    <div class="slds-p-around_medium">
      <!-- Content uses utility classes for spacing -->
    </div>
  </lightning-card>
</template>
```

```css
/* Component CSS only for truly custom styles */
.my-custom-element {
  /* Use hooks */
  background: var(--slds-g-color-surface-2);
}
```

---

## Resources

| Resource | URL |
|----------|-----|
| SLDS Linter | https://developer.salesforce.com/docs/platform/slds-linter/guide |
| Lightning Components | https://developer.salesforce.com/docs/component-library/overview/components |
| SLDS Website | https://www.lightningdesignsystem.com/ |
| Styling Hooks Index | https://www.lightningdesignsystem.com/2e1ef8501/p/591960-global-styling-hooks |
